from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
import time
import json
import hashlib

app = Flask(__name__)
CORS(app, 
     supports_credentials=True,
     resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"], "allow_headers": ["Authorization", "Content-Type"]}}
)


DB_FILE = "db.sqlite"

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# init db
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        c.execute('ALTER TABLE rooms ADD COLUMN password_hash TEXT')
        print("Column added ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("password_hash column already exists")
        else:
            raise

    
    # Check if 'users' table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not c.fetchone():
        c.execute('''CREATE TABLE users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    avatar_url TEXT,
                    description TEXT,
                    password TEXT NOT NULL,
                    token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')
        print("Created users table")
    
    # Check if 'rooms' table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
    if not c.fetchone():
        c.execute('''CREATE TABLE rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_private INTEGER DEFAULT 0,
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')
        print("Created rooms table")
    
    # Check if 'room_members' table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='room_members'")
    if not c.fetchone():
        c.execute('''CREATE TABLE room_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(room_id) REFERENCES rooms(id),
                    FOREIGN KEY(username) REFERENCES users(username)
                  )''')
        print("Created room_members table")

    # Check if 'inbox messages' table exists 
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inbox_messages'")
    if not c.fetchone():
        c.execute('''CREATE TABLE inbox_messages(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(sender) REFERENCES users(username),
                  FOREIGN KEY(recipient) REFERENCES users(username)
                  )''')
        print("create inbox messages table")
    
    conn.commit()
    conn.close()
    print("Database initialization completed")

init_db()

@app.route('/api/register',methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    avatar_url = data.get('avatar_url', '').strip()
    description = data.get('description') or ''
    password = data.get('password', '')


    if not username or not email or not password:
        return jsonify({'error':"I can't see a single field you filled"}),400
    
    word_count = len(description.split())
    if word_count > 500:
        return jsonify({'error':"You are talking too much in the description"}),400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()


    # existing checking
    c.execute('SELECT * FROM users WHERE username=? OR email=?',(username,email))
    if c.fetchone():
        conn.close()
        return jsonify({'error':" the user already exists"}),400
    
    # i hash da password
    hashed_pw = generate_password_hash(password)

    c.execute('''
    INSERT INTO users (username,email,avatar_url,description,password)
              VALUES (?,?,?,?,?)             
''',(username,email,avatar_url,description,hashed_pw))
    
    conn.commit()
    conn.close()

    return jsonify({'message':"Welcome to MIRAGE"}),201


MAX_MESSAGES = 100
MESSAGE_LIFESPAN = 60 * 30 * 30  

MESSAGES_FILE = "messages.txt"

# Load messages from file if exists, else create file
def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    else:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f)

messages = load_messages()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': "I can't see a single field you filled"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    stored_password = row[0]
    if not check_password_hash(stored_password, password):
        conn.close()
        return jsonify({'error': 'wrong password'}), 401

    token = str(uuid.uuid4())
    c.execute('UPDATE users SET token=? WHERE username=?', (token, username))
    conn.commit()
    conn.close()

    return jsonify({'token': token, 'username': username}), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({'error': 'no token provided'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # check if token exists
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'invalid token'}), 401

    # clear token
    c.execute('UPDATE users SET token=NULL WHERE token=?', (token,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'logged out successfully'}), 200




@app.route('/api/usercount', methods=['GET'])
def user_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return str(count), 200  # plain text


# post 0.0.3 additions

@app.route('/api/user/<username>',methods=['GET'])
def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?',(username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error':'user not found'}),404
    
    user_data = {
        'username': row[1],
        'avatar_url':row[3],
        'description':row[4],
        'created_at':row[6]
    }

    return jsonify(user_data),200

@app.route('/api/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    room_name = data.get('room_name', '').strip()
    is_private = int(data.get('is_private', 0))
    password = data.get('password', '').strip() if is_private else None
    token = request.headers.get('Authorization')

    if not room_name or not token or (is_private and not password):
        return jsonify({'error': "invalid fields received"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # validate token
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            return jsonify({'error': "unauthorized"}), 401

        # ensure name is a clean string
        if isinstance(room_name, (list, tuple)):
            room_name = room_name[0]
        elif not isinstance(room_name, str):
            return jsonify({'error': "room_name must be a string"}), 400

        # check if room exists
        c.execute('SELECT id FROM rooms WHERE name=?', (room_name,))
        if c.fetchone():
            return jsonify({'error': "room already exists"}), 400

        # hash pw if private
        pw_hash = hash_pw(password) if is_private else None

        # create room
        c.execute('''
            INSERT INTO rooms (name, is_private, password_hash)
            VALUES (?, ?, ?)
        ''', (room_name, is_private, pw_hash))
        room_id = c.lastrowid

        # add creator to members
        c.execute('INSERT INTO room_members (room_id, username) VALUES (?, ?)', (room_id, user[0]))
        conn.commit()

    return jsonify({'message': f'room "{room_name}" created', 'room_id': room_id}), 201

# took help from deepseek because private room switching wasn't working

@app.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.get_json()
    room_name = data.get('name', '').strip()
    password = data.get('password', '').strip()
    token = request.headers.get('Authorization')

    if not room_name or not token:
        return jsonify({'error': 'missing room name or token'}), 400

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # validate token
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            return jsonify({'error': 'unauthorized'}), 401

        # fetch room + pw hash
        c.execute('SELECT id, is_private, password_hash FROM rooms WHERE name=?', (room_name,))
        room = c.fetchone()
        if not room:
            return jsonify({'error': 'room not found'}), 404

        room_id, is_private, stored_hash = room

        # check if already member (remove this check to allow re-joining)
        # c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, user[0]))
        # if c.fetchone():
        #     return jsonify({'error': 'already in room'}), 400

        # check password if private
        if is_private:
            if not password:
                return jsonify({'error': 'password required'}), 403
            if stored_hash != hash_pw(password):
                return jsonify({'error': 'wrong password'}), 403

        # Add or update membership
        c.execute('''
            INSERT OR REPLACE INTO room_members (room_id, username, joined_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (room_id, user[0]))
        
        conn.commit()

    return jsonify({
        'message': f'{user[0]} joined room "{room_name}"',
        'room_id': room_id,
        'room_name': room_name
    }), 200

@app.route('/api/send_room_message', methods=['POST'])
def send_room_message():
    data = request.get_json()
    token = request.headers.get('Authorization')
    room_id = data.get('room_id')
    message = data.get('message', '').strip()

    if not token or not room_id or not message:
        return jsonify({'error': 'missing fields'}), 400

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            return jsonify({'error': 'unauthorized'}), 401

        c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, user[0]))
        if not c.fetchone():
            return jsonify({'error': 'you are not in this room'}), 403

    message_data = {
        'username': user[0],
        'message': message,
        'created_at': time.time(),
        'room_id': room_id
    }

    messages.append(message_data)
    now = time.time()
    messages[:] = [m for m in messages if now - m['created_at'] < MESSAGE_LIFESPAN]
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)
    save_messages(messages)

    return jsonify({'message': 'sent'}), 200

@app.route('/api/get_room_messages', methods=['GET'])
def get_room_messages():
    token = request.headers.get('Authorization')
    room_id = request.args.get('room_id')

    if not token or not room_id:
        return jsonify({'error': 'missing token or room id'}), 400

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            return jsonify({'error': 'unauthorized'}), 401

        c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, user[0]))
        if not c.fetchone():
            return jsonify({'error': 'you are not in this room'}), 403

    filtered = [m for m in messages if str(m.get('room_id')) == str(room_id)]
    return jsonify({'messages': filtered}), 200

@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'missing token'}), 400

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            return jsonify({'error': 'unauthorized'}), 401

        c.execute('SELECT id, name FROM rooms WHERE is_private=0')
        rooms = c.fetchall()

        c.execute('SELECT room_id FROM room_members WHERE username=?', (user[0],))
        user_rooms = {r[0] for r in c.fetchall()}

    data = []
    for room_id, name in rooms:
        data.append({
            'room_id': room_id,
            'name': name,
            'joined': room_id in user_rooms
        })

    return jsonify({'rooms': data}), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'message': 'pong'}), 200

# inbox feature for system messages as well as private messaging between users

@app.route('/api/send_inbox_message',methods=['POST'])
def send_inbox_message():
    data = request.get_json()
    token = request.headers.get('Authorization')
    recipient = data.get('recipient')
    message = data.get('message','')
    # do the message sending and storing
    if not token:
        return jsonify({'error':'invalid token , please re-login'}),401
    
    if not recipient or not message:
        return jsonify({'error':'missing recipient or message'}),400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    sender = user[0]
    
    c.execute('SELECT username FROM users WHERE username=?',(recipient,))
    recipient = c.fetchone()
    if not recipient:
        conn.close()
        return jsonify({'erorr':'recipient not found'}),404
    recipient = recipient[0]
    # inserting messages into the table
    c.execute('INSERT INTO inbox_messages (sender,recipient,message) VALUES (?,?,?)',(sender,recipient,message))
    conn.commit()
    conn.close()
    return jsonify({'message':'message sent'}),200


@app.route('/api/inbox', methods=['GET'])
def inbox():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'invalid token , please re-login'}), 401
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]
    
    # Corrected query to get sender's avatar
    c.execute('''
        SELECT im.id, im.sender, im.recipient, im.message, im.created_at,
               u.avatar_url AS sender_avatar
        FROM inbox_messages im
        LEFT JOIN users u ON im.sender = u.username
        WHERE im.recipient=?
        ORDER BY im.created_at DESC
    ''', (username,))
    
    messages = c.fetchall()
    conn.close()
    
    inbox_data = []
    for msg in messages:
        inbox_data.append({
            'id': msg[0],
            'sender': msg[1],
            'recipient': msg[2],
            'message': msg[3],
            'created_at': msg[4],
            'avatar_url': msg[5] or "https://i.pinimg.com/736x/20/da/fa/20dafa83d38f2277472e132bf1f21c22.jpg"
        })
    
    return jsonify({'messages': inbox_data}), 200

@app.route('/api/delete_inbox_message',methods=['POST'])
def delete_inbox_message():
    data = request.get_json()
    token = request.headers.get('Authorization')
    message_id = data.get('message_id')

    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    if not message_id:
        return jsonify({'error': 'missing message ID'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    
    username = user[0]
    
    # Check if the message exists and belongs to the user
    c.execute('SELECT * FROM inbox_messages WHERE id=? AND recipient=?', (message_id, username))
    msg = c.fetchone()
    
    if not msg:
        conn.close()
        return jsonify({'error': 'message not found or unauthorized access'}), 404
    
    # Delete the message
    c.execute('DELETE FROM inbox_messages WHERE id=?', (message_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'message deleted successfully'}), 200

# get number of messages in inbox
@app.route('/api/inbox_count',methods=['GET'])
def inbox_count():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    
    username = user[0]
    
    c.execute('SELECT COUNT(*) FROM inbox_messages WHERE recipient=?', (username,))
    count = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({'inbox_count': count}), 200


# update 0.0.4 , now brings file sharing in rooms , return url of file by uploading it to 0x0.st 

import requests
from flask_cors import cross_origin

def file_uploader(file):
    try:
        file.stream.seek(0)
        response = requests.post(
            'https://tmpfiles.org/api/v1/upload',
            files={'file': (file.filename, file.stream, file.mimetype or 'application/octet-stream')},
            headers={
                'User-Agent': 'Mozilla/5.0'
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('url', '').strip()
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f'HTTP Error: {http_err.response.status_code} - {http_err.response.text}')
    except requests.exceptions.ConnectionError:
        raise Exception('Connection error: Could not connect to the file upload service.')
    except requests.exceptions.Timeout:
        raise Exception('Timeout error: The file upload request took too long.')
    except Exception as err:
        raise Exception(f'Unexpected error during file upload: {str(err)}')


@app.route('/api/upload_file', methods=['POST'])
@cross_origin()
def upload_file():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Invalid token or token missing'}), 401
        
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        if file.filename == '':
            return jsonify({'error': 'No file name provided'}), 400
        
        room_id = request.form.get('room_id')
        if not room_id:
            return jsonify({'error': 'No room ID provided'}), 400
        
        if file.content_length > 24 * 1024 * 1024:
            return jsonify({'error': 'File size exceeds the 24MB limit'}), 400

        
        print(f"Attempting to upload file: {file.filename} to room {room_id}")
        
        try:
            file_url = file_uploader(file)
            print(f"File uploaded successfully: {file_url}")
        except Exception as e:
            print(f"File upload failed: {str(e)}")
            return jsonify({'error': f'File upload failed: {str(e)}'}), 500
        
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT username FROM users WHERE token=?', (token,))
            user = c.fetchone()
            if not user:
                return jsonify({'error': 'Unauthorized access'}), 401
            username = user[0]
            
            c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, username))
            if not c.fetchone():
                return jsonify({'error': 'You are not a member of this room'}), 403
            
            message_data = {
                'username': username,
                'message': f'{file_url}',
                'created_at': time.time(),
                'room_id': room_id
            }
            messages.append(message_data)
            
            now = time.time()
            messages[:] = [m for m in messages if now - m['created_at'] < MESSAGE_LIFESPAN]
            
            if len(messages) > MAX_MESSAGES:
                messages.pop(0)
            
            save_messages(messages)
            
        return jsonify({
            'message': 'File uploaded successfully',
            'file_url': file_url
        }), 200
        
    except Exception as e:
        print(f"Unexpected error in upload_file: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)

