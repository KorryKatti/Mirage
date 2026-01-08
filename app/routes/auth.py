
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import sqlite3
from app.db import get_db_connection
from app.config import DB_FILE

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/register',methods=['POST'])
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
    
    conn = get_db_connection()
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

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': "I can't see a single field you filled"}), 400

    conn = get_db_connection()
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

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    data = request.get_json()
    token = data.get('token')

    if not token:
        return jsonify({'error': 'no token provided'}), 400

    conn = get_db_connection()
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

@auth_bp.route('/api/usercount', methods=['GET'])
def user_count():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    count = c.fetchone()[0]
    conn.close()
    return str(count), 200  # plain text
