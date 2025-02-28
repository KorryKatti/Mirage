from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime
import threading
import time
import secrets
import hashlib
import sqlite3
import os
import json
import psutil
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path='')
CORS(app)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'zip', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load server configuration
with open('servers.json', 'r') as f:
    SERVER_CONFIG = json.load(f)

# Get server ID from command line or environment
SERVER_ID = os.environ.get('SERVER_ID', 'server1')
SERVER_INFO = next(s for s in SERVER_CONFIG['servers'] if s['id'] == SERVER_ID)
HOST = SERVER_INFO['host']
PORT = SERVER_INFO['port']

# Initialize SQLite database
def init_db():
    with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, password TEXT, token TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS channels
                     (name TEXT PRIMARY KEY, topic TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      channel TEXT,
                      sender TEXT,
                      content TEXT,
                      type TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS files
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      filename TEXT,
                      original_name TEXT,
                      uploader TEXT,
                      channel TEXT,
                      size INTEGER,
                      mime_type TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

init_db()

# In-memory storage for active users and their message queues
active_users = {}
channels = {'#general': {'topic': 'Welcome to Mirage IRC', 'users': set()}}

# Server stats
server_stats = {
    'start_time': time.time(),
    'total_messages': 0,
    'active_users_count': 0,
    'cpu_usage': 0,
    'memory_usage': 0,
    'last_updated': time.time()
}

def update_server_stats():
    while True:
        try:
            server_stats.update({
                'active_users_count': len(active_users),
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.Process().memory_percent(),
                'last_updated': time.time()
            })
        except Exception as e:
            print(f"Error updating server stats: {e}")
        time.sleep(5)

def get_server_load():
    return {
        'id': SERVER_ID,
        'host': HOST,
        'port': PORT,
        'stats': server_stats,
        'uptime': time.time() - server_stats['start_time']
    }

@app.route('/api/server/stats', methods=['GET'])
def server_stats_endpoint():
    return jsonify(get_server_load())

def broadcast_to_other_servers(message, exclude_server=None):
    for server in SERVER_CONFIG['servers']:
        if server['id'] != exclude_server:
            try:
                url = f"http://{server['host']}:{server['port']}/api/server/broadcast"
                requests.post(url, json=message, timeout=1)
            except:
                pass

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
        c = conn.cursor()
        try:
            hashed_password = hash_password(password)
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                     (username, hashed_password))
            conn.commit()
            return jsonify({'message': 'Registration successful'})
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username already exists'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        
        if result and result[0] == hash_password(password):
            token = secrets.token_hex(16)
            c.execute('UPDATE users SET token = ? WHERE username = ?',
                     (token, username))
            conn.commit()
            
            active_users[username] = {
                'token': token,
                'channels': set(['#general']),
                'last_poll': time.time(),
                'message_queue': []
            }
            channels['#general']['users'].add(username)
            
            return jsonify({
                'token': token,
                'username': username,
                'channels': list(active_users[username]['channels']),
                'server': {
                    'id': SERVER_ID,
                    'host': HOST,
                    'port': PORT
                }
            })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/server/broadcast', methods=['POST'])
def handle_broadcast():
    data = request.json
    if 'type' in data:
        if data['type'] == 'message':
            channel = data.get('channel', '#general')
            if channel in channels:
                for user in channels[channel]['users']:
                    if user in active_users:
                        active_users[user]['message_queue'].append(data['content'])
    return jsonify({'status': 'ok'})

@app.route('/api/message', methods=['POST'])
def send_message():
    token = request.headers.get('Authorization')
    data = request.json
    
    username = None
    for user, info in active_users.items():
        if info['token'] == token:
            username = user
            break
    
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401
    
    message_type = data.get('type', 'message')
    content = data.get('content')
    channel = data.get('channel', '#general')
    
    if message_type == 'command':
        handle_command(username, content, channel)
        return jsonify({'status': 'ok'})
    
    timestamp = datetime.now().strftime('%H:%M')
    formatted_message = f'[{timestamp}] <{username}> {content}'
    
    with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO messages (channel, sender, content, type)
                     VALUES (?, ?, ?, ?)''',
                  (channel, username, content, message_type))
        conn.commit()
    
    for user in channels[channel]['users']:
        if user in active_users:
            active_users[user]['message_queue'].append(formatted_message)
    
    return jsonify({'status': 'ok'})

@app.route('/api/poll', methods=['GET'])
def poll_messages():
    token = request.headers.get('Authorization')
    
    username = None
    for user, info in active_users.items():
        if info['token'] == token:
            username = user
            break
    
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_data = active_users[username]
    messages = user_data['message_queue']
    user_data['message_queue'] = []
    user_data['last_poll'] = time.time()
    
    return jsonify({
        'messages': messages,
        'users': {
            channel: list(channels[channel]['users'])
            for channel in user_data['channels']
        }
    })

def handle_command(username, command, channel):
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == '/join':
        if len(parts) > 1:
            new_channel = parts[1]
            if not new_channel.startswith('#'):
                new_channel = f'#{new_channel}'
            
            if new_channel not in channels:
                channels[new_channel] = {'topic': '', 'users': set()}
            
            channels[new_channel]['users'].add(username)
            active_users[username]['channels'].add(new_channel)
            broadcast_system_message(f'* {username} has joined {new_channel}', new_channel)
    
    elif cmd == '/part':
        if channel in active_users[username]['channels']:
            active_users[username]['channels'].remove(channel)
            channels[channel]['users'].remove(username)
            broadcast_system_message(f'* {username} has left {channel}', channel)
    
    elif cmd == '/nick':
        if len(parts) > 1:
            new_nick = parts[1]
            old_nick = username
            # Implementation for nickname change would go here
            broadcast_system_message(f'* {old_nick} is now known as {new_nick}')
    
    elif cmd == '/me':
        if len(parts) > 1:
            action = ' '.join(parts[1:])
            broadcast_system_message(f'* {username} {action}', channel)

def broadcast_system_message(message, channel='#general'):
    timestamp = datetime.now().strftime('%H:%M')
    formatted_message = f'[{timestamp}] {message}'
    
    if channel == '#general':
        for user in active_users:
            active_users[user]['message_queue'].append(formatted_message)
    else:
        for user in channels[channel]['users']:
            if user in active_users:
                active_users[user]['message_queue'].append(formatted_message)

# Cleanup inactive users periodically
def cleanup_inactive_users():
    while True:
        current_time = time.time()
        inactive_users = []
        
        for username, data in active_users.items():
            if current_time - data['last_poll'] > 30:  # 30 seconds timeout
                inactive_users.append(username)
        
        for username in inactive_users:
            for channel in active_users[username]['channels']:
                channels[channel]['users'].remove(username)
            del active_users[username]
            broadcast_system_message(f'* {username} has disconnected (timeout)')
        
        time.sleep(10)

cleanup_thread = threading.Thread(target=cleanup_inactive_users, daemon=True)
cleanup_thread.start()

# Start the stats update thread
stats_thread = threading.Thread(target=update_server_stats, daemon=True)
stats_thread.start()

# Serve static files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    token = request.headers.get('Authorization')
    channel = request.form.get('channel', '#general')
    
    username = None
    for user, info in active_users.items():
        if info['token'] == token:
            username = user
            break
    
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        unique_filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Store file info in database
        with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO files 
                        (filename, original_name, uploader, channel, size, mime_type)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (unique_filename, filename, username, channel, 
                      os.path.getsize(filepath), file.content_type))
            file_id = c.lastrowid
            conn.commit()
        
        # Broadcast file upload message
        file_url = f"/api/download/{file_id}"
        message = f"* {username} shared a file: {filename} ({file_url})"
        broadcast_system_message(message, channel)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'url': file_url
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<int:file_id>')
def download_file(file_id):
    token = request.headers.get('Authorization')
    
    username = None
    for user, info in active_users.items():
        if info['token'] == token:
            username = user
            break
    
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
            c = conn.cursor()
            c.execute('SELECT filename, original_name, mime_type FROM files WHERE id = ?', 
                     (file_id,))
            result = c.fetchone()
            
            if not result:
                return jsonify({'error': 'File not found'}), 404
            
            filename, original_name, mime_type = result
            return send_file(
                os.path.join(app.config['UPLOAD_FOLDER'], filename),
                mimetype=mime_type,
                as_attachment=True,
                download_name=original_name
            )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<string:channel>')
def list_files(channel):
    token = request.headers.get('Authorization')
    
    username = None
    for user, info in active_users.items():
        if info['token'] == token:
            username = user
            break
    
    if not username:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        with sqlite3.connect(f'mirage_{SERVER_ID}.db') as conn:
            c = conn.cursor()
            c.execute('''SELECT id, original_name, uploader, size, timestamp 
                        FROM files WHERE channel = ? ORDER BY timestamp DESC''',
                     (channel,))
            files = [{
                'id': row[0],
                'name': row[1],
                'uploader': row[2],
                'size': row[3],
                'timestamp': row[4],
                'url': f'/api/download/{row[0]}'
            } for row in c.fetchall()]
            
            return jsonify({'files': files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=True)
