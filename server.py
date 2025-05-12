from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3
import os
from werkzeug.security import generate_password_hash,check_password_hash


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



@app.route('/')
def index():
    return " hello world "


@app.route('/api/login',methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error':"I can't see a single field you filled"}),400
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username=?',(username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error':'user not found'}),404
    
    stored_password = row[0]
    if not check_password_hash(stored_password,password):
        return jsonify({'error':'wrong password'}),401
    
    return jsonify({'message':"login successful"}),200


@app.route('/api/usercount', methods=['GET'])
def user_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return str(count), 200  # plain text





if __name__ == '__main__':
    app.run(debug=True)

