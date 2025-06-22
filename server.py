from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
import time
import json
import hashlib
import markdown
from bleach.sanitizer import Cleaner


app = Flask(__name__)
CORS(app, 
     supports_credentials=True,
     resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"], "allow_headers": ["Authorization", "Content-Type"]}}
)


DB_FILE = "db.sqlite"

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def migrate_existing_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Ensure all columns exist in user_profile
    try:
        c.execute('ALTER TABLE user_profile ADD COLUMN upvotes INTEGER DEFAULT 0')
        print("Added upvotes column to user_profile ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print(f"Error adding upvotes to user_profile: {str(e)}")

    try:
        c.execute('ALTER TABLE user_profile ADD COLUMN downvotes INTEGER DEFAULT 0')
        print("Added downvotes column to user_profile ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print(f"Error adding downvotes to user_profile: {str(e)}")

    # Get all existing users
    c.execute('SELECT username FROM users')
    users = c.fetchall()
    
    for (username,) in users:
        # Check if user exists in user_profile
        c.execute('SELECT 1 FROM user_profile WHERE username=?', (username,))
        if not c.fetchone():
            # Initialize stats for user
            c.execute('''
                INSERT INTO user_profile (username, followers, following, posts, upvotes, downvotes)
                VALUES (?, 0, 0, 0, 0, 0)
            ''', (username,))
            
        # Update stats based on actual data
        # Update post count
        c.execute('SELECT COUNT(*) FROM posts WHERE username=?', (username,))
        post_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET posts=? WHERE username=?', (post_count, username))
        
        # Update follower count
        c.execute('SELECT COUNT(*) FROM following WHERE following=?', (username,))
        follower_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET followers=? WHERE username=?', (follower_count, username))
        
        # Update following count
        c.execute('SELECT COUNT(*) FROM following WHERE follower=?', (username,))
        following_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET following=? WHERE username=?', (following_count, username))
        
        # Update upvotes/downvotes (sum of all votes on user's posts)
        c.execute('SELECT SUM(upvotes), SUM(downvotes) FROM posts WHERE username=?', (username,))
        up, down = c.fetchone()
        up = up or 0
        down = down or 0
        c.execute('UPDATE user_profile SET upvotes=?, downvotes=? WHERE username=?', (up, down, username))
    
    conn.commit()
    conn.close()


# init db
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Create tables if they don't exist (without failing if they do)
    tables = {
        'users': '''CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    avatar_url TEXT,
                    description TEXT,
                    password TEXT NOT NULL,
                    token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''',
        'rooms': '''CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_private INTEGER DEFAULT 0,
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''',
        'room_members': '''CREATE TABLE IF NOT EXISTS room_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(room_id) REFERENCES rooms(id),
                    FOREIGN KEY(username) REFERENCES users(username)
                  )''',
        'inbox_messages': '''CREATE TABLE IF NOT EXISTS inbox_messages(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(sender) REFERENCES users(username),
                  FOREIGN KEY(recipient) REFERENCES users(username)
                  )''',
        'user_profile': '''CREATE TABLE IF NOT EXISTS user_profile (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  followers INTEGER DEFAULT 0,
                  following INTEGER DEFAULT 0,
                  posts INTEGER DEFAULT 0,
                  upvotes INTEGER DEFAULT 0,
                  downvotes INTEGER DEFAULT 0,
                  FOREIGN KEY(username) REFERENCES users(username)
                  )''',
        'posts': '''CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upvotes INTEGER DEFAULT 0,
                downvotes INTEGER DEFAULT 0,
                FOREIGN KEY(username) REFERENCES users(username)
                )''',
        'post_votes': '''CREATE TABLE IF NOT EXISTS post_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(username) REFERENCES users(username),
                UNIQUE(post_id, username)
                )''',
        'following': '''CREATE TABLE IF NOT EXISTS following (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower TEXT NOT NULL,
                following TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(follower) REFERENCES users(username),
                FOREIGN KEY(following) REFERENCES users(username),
                UNIQUE(follower, following)
                )''',
        'replies': '''CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(username) REFERENCES users(username)
                )'''
    }

    # Create all tables
    for table_name, create_stmt in tables.items():
        c.execute(create_stmt)
        print(f"Ensured {table_name} table exists")

    # Now safely add columns if they don't exist
    try:
        c.execute('ALTER TABLE posts ADD COLUMN upvotes INTEGER DEFAULT 0')
        print("Added upvotes column to posts table ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("upvotes column already exists in posts table")
        else:
            print(f"Error adding upvotes column: {str(e)}")

    try:
        c.execute('ALTER TABLE posts ADD COLUMN downvotes INTEGER DEFAULT 0')
        print("Added downvotes column to posts table ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("downvotes column already exists in posts table")
        else:
            print(f"Error adding downvotes column: {str(e)}")

    conn.commit()
    conn.close()
    print("Database initialization completed")

init_db()

migrate_existing_users()

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
    
    # hash password
    hashed_pw = generate_password_hash(password)

    c.execute('''
    INSERT INTO users (username,email,avatar_url,description,password)
              VALUES (?,?,?,?,?)             
''',(username,email,avatar_url,description,hashed_pw))
    
    # Initialize all stats to 0
    c.execute('''
    INSERT INTO user_profile (username, followers, following, posts, upvotes, downvotes)
    VALUES (?, 0, 0, 0, 0, 0)
    ''', (username,))
    
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
    ping_thread = threading.Thread(target=ping_server, args=(60,), daemon=True)
    ping_thread.start()
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

UPLOAD_URL = 'https://cpp-webserver.onrender.com/upload'

def file_uploader(file):
    try:
        file.stream.seek(0)
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/octet-stream'
        }

        response = requests.post(
            UPLOAD_URL,
            data=file.stream,
            headers=headers
        )
        response.raise_for_status()
        return response.text.strip()  # assuming server returns the URL or file ID as plain text

    except requests.exceptions.HTTPError as http_err:
        raise Exception(f'HTTP Error: {http_err.response.status_code} - {http_err.response.text}')
    except requests.exceptions.ConnectionError:
        raise Exception('Connection error: Could not connect to the file upload service.')
    except requests.exceptions.Timeout:
        raise Exception('Timeout error: The file upload request took too long.')
    except Exception as err:
        raise Exception(f'Unexpected error during file upload: {str(err)}')
    
def ping_server(interval=60):
    while True:
        try:
            res = requests.get('https://cpp-webserver.onrender.com', timeout=5)
            print(f'Ping: {res.status_code} - {res.reason}')
        except Exception as e:
            print(f'Ping failed: {e}')
        time.sleep(interval)

# in a separaate thread we start the pinging
import threading



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
    

# post 0.0.4 additions to shift to 0.0.5 , now adding profile and posts ; to add in 0.0.6 : fyp


@app.route('/api/create_post',methods=['POST'])
def create_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    content = data.get('content','')

    if not token:
        return jsonify({'error':'invalid token , please re-login'}),401
    
    if not content:
        return jsonify({'error':'nothing to post'}),400
    
    if len(content) > 512:
        return jsonify({'error':'post content cannot exceed 512 characters'}),400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    
    c.execute('INSERT INTO posts (username,content) VALUES (?,?)',(username,content))
    
    # Update user's post count
    c.execute('UPDATE user_profile SET posts = posts + 1 WHERE username=?', (username,))

    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return jsonify({'message':'post created'}),201


@app.route('/api/user/<username>',methods=['GET'])
def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get basic user info
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error':'user not found'}),404
    
    # Get profile stats from user_profile table
    c.execute('SELECT followers, following, posts, upvotes, downvotes FROM user_profile WHERE username=?', (username,))
    profile_stats = c.fetchone()
    
    conn.close()
    
    user_data = {
        'username': row[1],
        'avatar_url': row[3],
        'description': row[4],
        'created_at': row[6],
        'stats': {
            'followers': profile_stats[0] if profile_stats else 0,
            'following': profile_stats[1] if profile_stats else 0,
            'posts': profile_stats[2] if profile_stats else 0,
            'upvotes': profile_stats[3] if profile_stats else 0,
            'downvotes': profile_stats[4] if profile_stats else 0
        }
    }

    return jsonify(user_data),200

@app.route('/api/get_posts/<username>',methods=['GET'])
def get_posts(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username=? ORDER BY created_at DESC',(username,))
    rows = c.fetchall()
    conn.close()
    
    posts = []
    for row in rows:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        posts.append(post_data)
    
    return jsonify({'posts': posts}), 200

@app.route('/api/vote_post',methods=['POST'])
def vote_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    post_id = data.get('post_id')
    vote_type = data.get('vote_type')

    if not token:
        return jsonify({'error':'login to vote'}),401
    if not post_id or not vote_type:
        return jsonify({'error':'missing post_id or vote_type'}),400
    
    if vote_type not in ['up','down']:
        return jsonify({'error':'you can only upvote or downvote'}),400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    
    # check if post exists
    c.execute('SELECT username FROM posts WHERE id=?',(post_id,))
    post = c.fetchone()
    if not post:
        conn.close()
        return jsonify({'error':'post not found'}),404
        
    post_author = post[0]
    if post_author == username:
        conn.close()
        return jsonify({'error':'cannot vote on your own post'}),403
    
    # check if user already voted (optional - prevents multiple votes)
        # Check if user already voted
    c.execute('SELECT vote_type FROM post_votes WHERE post_id=? AND username=?', (post_id, username))
    existing_vote = c.fetchone()
    
    if existing_vote:
        # User already voted - handle vote change
        if existing_vote[0] == vote_type:
            conn.close()
            return jsonify({'error':'already voted this way'}), 400
        else:
            # Reverse previous vote
            if existing_vote[0] == 'up':
                c.execute('UPDATE posts SET upvotes = upvotes - 1 WHERE id=?', (post_id,))
                c.execute('UPDATE user_profile SET upvotes = upvotes - 1 WHERE username=?', (post_author,))
            else:
                c.execute('UPDATE posts SET downvotes = downvotes - 1 WHERE id=?', (post_id,))
                c.execute('UPDATE user_profile SET downvotes = downvotes - 1 WHERE username=?', (post_author,))
            
            # Update the vote record
            c.execute('UPDATE post_votes SET vote_type=? WHERE post_id=? AND username=?', 
                      (vote_type, post_id, username))
    else:
        # Record the new vote
        c.execute('INSERT INTO post_votes (post_id, username, vote_type) VALUES (?,?,?)',
                 (post_id, username, vote_type))
    
    # Update vote counts
    if vote_type == 'up':
        c.execute('UPDATE posts SET upvotes = upvotes + 1 WHERE id=?', (post_id,))
        c.execute('UPDATE user_profile SET upvotes = upvotes + 1 WHERE username=?', (post_author,))
    else:
        c.execute('UPDATE posts SET downvotes = downvotes + 1 WHERE id=?', (post_id,))
        c.execute('UPDATE user_profile SET downvotes = downvotes + 1 WHERE username=?', (post_author,))
    
    conn.commit()
    conn.close()
    return jsonify({'message':'vote counted'}),200

# Follow/Unfollow endpoints
@app.route('/api/follow', methods=['POST'])
def follow_user():
    data = request.get_json()
    token = request.headers.get('Authorization')
    target_username = data.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Check if target exists
    c.execute('SELECT username FROM users WHERE username=?', (target_username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    # Check if already following
    c.execute('SELECT * FROM following WHERE follower=? AND following=?', (username, target_username))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'already following'}), 400

    # Create follow relationship
    c.execute('INSERT INTO following (follower, following) VALUES (?, ?)', (username, target_username))
    
    # Update follower counts
    c.execute('UPDATE user_profile SET following = following + 1 WHERE username=?', (username,))
    c.execute('UPDATE user_profile SET followers = followers + 1 WHERE username=?', (target_username,))

    conn.commit()
    conn.close()
    return jsonify({'message': f'now following {target_username}'}), 200

@app.route('/api/unfollow', methods=['POST'])
def unfollow_user():
    data = request.get_json()
    token = request.headers.get('Authorization')
    target_username = data.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Remove follow relationship
    c.execute('DELETE FROM following WHERE follower=? AND following=?', (username, target_username))
    
    if c.rowcount == 0:
        conn.close()
        return jsonify({'error': 'not following this user'}), 400

    # Update follower counts
    c.execute('UPDATE user_profile SET following = following - 1 WHERE username=?', (username,))
    c.execute('UPDATE user_profile SET followers = followers - 1 WHERE username=?', (target_username,))

    conn.commit()
    conn.close()
    return jsonify({'message': f'unfollowed {target_username}'}), 200

@app.route('/api/check_follow', methods=['GET'])
def check_follow():
    token = request.headers.get('Authorization')
    target_username = request.args.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Check if following
    c.execute('SELECT * FROM following WHERE follower=? AND following=?', (username, target_username))
    is_following = bool(c.fetchone())

    conn.close()
    return jsonify({'is_following': is_following}), 200


@app.route('/api/get_followers/<username>', methods=['GET'])
def get_followers(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404
    
    # Get followers with their avatars
    c.execute('''
        SELECT u.username, u.avatar_url 
        FROM following f
        JOIN users u ON f.follower = u.username
        WHERE f.following = ?
        ORDER BY f.created_at DESC
    ''', (username,))
    
    followers = [{'username': row[0], 'avatar_url': row[1] or 'default.png'} for row in c.fetchall()]
    conn.close()
    
    return jsonify({'followers': followers}), 200

@app.route('/api/get_following/<username>', methods=['GET'])
def get_following(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404
    
    # Get following with their avatars
    c.execute('''
        SELECT u.username, u.avatar_url 
        FROM following f
        JOIN users u ON f.following = u.username
        WHERE f.follower = ?
        ORDER BY f.created_at DESC
    ''', (username,))
    
    following = [{'username': row[0], 'avatar_url': row[1] or 'default.png'} for row in c.fetchall()]
    conn.close()
    
    return jsonify({'following': following}), 200

@app.route('/api/reply_to_post', methods=['POST'])
def reply_to_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    post_id = data.get('post_id')
    content = data.get('content', '')

    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    if not post_id or not content:
        return jsonify({'error': 'missing post_id or content'}), 400
    
    if len(content) > 512:
        return jsonify({'error': 'reply content cannot exceed 512 characters'}), 400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]
    
    # Check if post exists
    c.execute('SELECT id FROM posts WHERE id=?', (post_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'post not found'}), 404
    
    # Insert reply into replies table
    c.execute('INSERT INTO replies (post_id, username, content) VALUES (?, ?, ?)', (post_id, username, content))
    
    # Update user's reply count
    c.execute('UPDATE user_profile SET posts = posts + 1 WHERE username=?', (username,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'reply created'}), 201

@app.route('/api/get_replies/<int:post_id>', methods=['GET'])
def get_replies(post_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if post exists
    c.execute('SELECT id FROM posts WHERE id=?', (post_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'post not found'}), 404
    
    # Get replies for the post
    c.execute('''
        SELECT r.id, r.username, r.content, r.created_at, u.avatar_url 
        FROM replies r
        JOIN users u ON r.username = u.username
        WHERE r.post_id=?
        ORDER BY r.created_at DESC
    ''', (post_id,))
    
    replies = []
    for row in c.fetchall():
        reply_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'avatar_url': row[4] or 'default.png'
        }
        replies.append(reply_data)
    
    conn.close()
    
    return jsonify({'replies': replies}), 200

@app.route('/api/get_post_by_id/<int:post_id>',methods=['GET'])
def get_post_by_id(post_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE id=?', (post_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error':'post not found'}),404
    post_data = {
        'id': row[0],
        'username': row[1],
        'content': row[2],
        'created_at': row[3],
        'upvotes': row[4],
        'downvotes': row[5]
    }

    return jsonify(post_data), 200


# Configure allowed HTML tags/attributes for Markdown
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 
    'i', 'li', 'ol', 'strong', 'ul', 'p', 'br', 'img',
    'h1', 'h2', 'h3', 'h4', 'pre'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title']
}

def safe_markdown(text):
    """Convert markdown to sanitized HTML"""
    html = markdown.markdown(text)
    cleaner = Cleaner(tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return cleaner.clean(html)

# fyp basic design
# get peole who the username follows and get the id of the last post made on the database
# feed suggestion = some posts from following list + some posts from last some posts and 1-2 very old posts , random on each request , send max 30 at a time
# also return most used hashtag beginning words in the past 20 posts , return top 3 as trending topics
# extract hashtags from past 20 global posts (recent ones only)
# for trending: break hashtags into root words (e.g. #code_tips → "code")
# return top 3 most common roots as trending topics
# build the final feed as:
#   - ~40% from followed users
#   - ~40% from recent global posts
#   - ~20% from old/random archive
# then shuffle them to make it feel fresh
import random , re
from collections import Counter

@app.route('/api/fyp',methods=['GET'])
def fyp():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error':'invalid token , please login again'}),401
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    followed_users = []
    c.execute('SELECT following FROM following WHERE follower=?',(username,))
    followed = c.fetchall()
    if followed:
        followed_users = [f[0] for f in followed]
    else:
        conn.close()
        return jsonify({'message':'no users being followed , yet'}),200
    
    recent_posts = []
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username IN ({}) ORDER BY created_at DESC LIMIT 20'.format(','.join(['?'] * len(followed_users))), followed_users)
    recent_posts = c.fetchall()
    if not recent_posts:
        conn.close()
        return jsonify({'message':'no recent posts from followed users'}),200
    recent_posts_data = []
    for row in recent_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        recent_posts_data.append(post_data)
    # Get global posts (not from followed users)
    global_posts = []
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username NOT IN ({}) ORDER BY created_at DESC LIMIT 20'.format(','.join(['?'] * len(followed_users))), followed_users)
    global_posts = c.fetchall()
    global_posts_data = []
    for row in global_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        global_posts_data.append(post_data)
    # Get old/random posts (from the last 100 posts)
    old_posts = []
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts ORDER BY created_at ASC LIMIT 100')
    old_posts = c.fetchall()
    old_posts_data = []
    for row in old_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        old_posts_data.append(post_data)
    conn.close()
    # Combine and shuffle the posts
    combined_posts = recent_posts_data + global_posts_data + old_posts_data
    random.shuffle(combined_posts)
    # Limit to 30 posts
    combined_posts = combined_posts[:30]
    # Extract hashtags from recent global posts
    hashtags = []
    for post in global_posts_data:
        if 'content' in post:
            found_hashtags = re.findall(r'#(\w+)', post['content'])
            hashtags.extend(found_hashtags)
    # Get top 3 trending hashtags
    hashtag_counts = Counter(hashtags)
    trending_hashtags = hashtag_counts.most_common(3)
    trending_topics = [f'#{tag}' for tag, count in trending_hashtags]
    return jsonify({
        'posts': combined_posts,
        'trending_topics': trending_topics
    }), 200

# upto now 0.0.6 has been released , will continue ahead later
# planned things : profile editing option , deletion of post option and building a inbuilt bot to send system messages to user in inbox/notifications
# later


if __name__ == '__main__':
    app.run(debug=True)

