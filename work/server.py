from flask import Flask, request, jsonify
from datetime import datetime
import threading
import time
import secrets
import hashlib
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Initialize SQLite database
def init_db():
    with sqlite3.connect('mirage.db') as conn:
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
        conn.commit()

init_db()

# In-memory storage for active users and their message queues
active_users = {}
channels = {'#general': {'topic': 'Welcome to Mirage IRC', 'users': set()}}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    with sqlite3.connect('mirage.db') as conn:
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
    
    with sqlite3.connect('mirage.db') as conn:
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
                'channels': list(active_users[username]['channels'])
            })
    
    return jsonify({'error': 'Invalid credentials'}), 401

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
    
    with sqlite3.connect('mirage.db') as conn:
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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=6667, debug=True)
