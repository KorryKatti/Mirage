from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
import time

app = Flask(__name__)
CORS(app,supports_credentials=True)


DB_FILE = "db.sqlite"


# init db
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
                  CREATE TABLE users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  avatar_url TEXT,
                  description TEXT,
                  password TEXT NOT NULL,
                  token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )'''
        )
        conn.commit()
        conn.close()
        print(" da database is uh now initi uh lized")

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
MESSAGE_LIFESPAN = 60 * 30 # 30 minutes since i don't expect much traffic yet

messages = []

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    username = data.get('username')
    message = data.get('message')
    token = request.headers.get('Authorization')

    if not username or not message or not token:
        return jsonify({'error': "Missing fields or token"}), 400

    # token validation
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE token=?", (token,))
    row = c.fetchone()
    conn.close()

    if not row or row[0] != username:
        return jsonify({'error': "Unauthorized"}), 401

    if not message.strip():
        return jsonify({'error': "Empty message"}), 400

    # everything's clean, accept message
    current_time = time.time()
    message_data = {
        'username': username,
        'message': message,
        'created_at': current_time
    }

    messages.append(message_data)


    messages[:] = [m for m in messages if current_time - m['created_at'] < MESSAGE_LIFESPAN]
    if len(messages) > MAX_MESSAGES:
        messages.pop(0)

    return jsonify({'message': "sent"}), 200

@app.route('/api/get_messages', methods=['GET'])
def get_messages():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'no token provided'}), 401

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token = ?', (token,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'invalid token'}), 401

    return jsonify({'messages': messages}), 200


# @app.route('/')
# def index():
#     return " hello world "


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


if __name__ == '__main__':
    app.run(debug=True)

