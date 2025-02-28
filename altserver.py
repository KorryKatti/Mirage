from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

db_file = 'chat.db'

# Initialize the database
if not os.path.exists(db_file):
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
        c.execute('''CREATE TABLE messages (id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return jsonify({'message': 'Registration successful'}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username already exists'}), 409

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        if user:
            return jsonify({'message': 'Login successful', 'user_id': user[0]}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    
    if not user_id or not message:
        return jsonify({'error': 'User ID and message are required'}), 400
    
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO messages (user_id, message) VALUES (?, ?)', (user_id, message))
        conn.commit()
        return jsonify({'message': 'Message sent'}), 201

@app.route('/get_messages', methods=['GET'])
def get_messages():
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        c.execute('SELECT users.username, messages.message, messages.timestamp FROM messages JOIN users ON messages.user_id = users.id ORDER BY messages.timestamp DESC')
        messages = [{'username': row[0], 'message': row[1], 'timestamp': row[2]} for row in c.fetchall()]
        return jsonify({'messages': messages}), 200

if __name__ == '__main__':
    app.run(debug=True) 