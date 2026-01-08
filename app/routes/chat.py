
from flask import Blueprint, request, jsonify
import sqlite3
import threading
import time
from app.db import get_db_connection
from app.utils import hash_pw, ping_server
from app.store import messages, save_messages
from app.config import MAX_MESSAGES, MESSAGE_LIFESPAN

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    room_name = data.get('room_name', '').strip()
    is_private = int(data.get('is_private', 0))
    password = data.get('password', '').strip() if is_private else None
    token = request.headers.get('Authorization')

    if not room_name or not token or (is_private and not password):
        return jsonify({'error': "invalid fields received"}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # validate token
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': "unauthorized"}), 401

    # ensure name is a clean string
    if isinstance(room_name, (list, tuple)):
        room_name = room_name[0]
    elif not isinstance(room_name, str):
        conn.close()
        return jsonify({'error': "room_name must be a string"}), 400

    # check if room exists
    c.execute('SELECT id FROM rooms WHERE name=?', (room_name,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': "room already exists"}), 400

    # hash pw if private
    pw_hash = hash_pw(password) if is_private else None

    # don't allow creationn of more thann n5 public rooms , if attempt at making send a message
    if not is_private:
        c.execute('SELECT COUNT(*) FROM rooms WHERE is_private=0')
        public_room_count = c.fetchone()[0]
        if public_room_count >= 5:
            conn.close()
            return jsonify({'error': 'maximum number of public rooms reached (5). Please create a private room to continue the conversation with the people you would like to'}), 400

    # create room
    c.execute('''
        INSERT INTO rooms (name, is_private, password_hash)
        VALUES (?, ?, ?)
    ''', (room_name, is_private, pw_hash))
    room_id = c.lastrowid

    # add creator to members
    c.execute('INSERT INTO room_members (room_id, username) VALUES (?, ?)', (room_id, user[0]))
    conn.commit()
    conn.close()

    return jsonify({'message': f'room "{room_name}" created', 'room_id': room_id}), 201


@chat_bp.route('/api/join_room', methods=['POST'])
def join_room():
    data = request.get_json()
    room_name = data.get('name', '').strip()
    password = data.get('password', '').strip()
    token = request.headers.get('Authorization')

    if not room_name or not token:
        return jsonify({'error': 'missing room name or token'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # validate token
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401

    # fetch room + pw hash
    c.execute('SELECT id, is_private, password_hash FROM rooms WHERE name=?', (room_name,))
    room = c.fetchone()
    if not room:
        conn.close()
        return jsonify({'error': 'room not found'}), 404

    room_id, is_private, stored_hash = room

    # check password if private
    if is_private:
        if not password:
            conn.close()
            return jsonify({'error': 'password required'}), 403
        if stored_hash != hash_pw(password):
            conn.close()
            return jsonify({'error': 'wrong password'}), 403

    # Add or update membership
    c.execute('''
        INSERT OR REPLACE INTO room_members (room_id, username, joined_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (room_id, user[0]))
    
    conn.commit()
    conn.close()

    return jsonify({
        'message': f'{user[0]} joined room "{room_name}"',
        'room_id': room_id,
        'room_name': room_name
    }), 200

@chat_bp.route('/api/send_room_message', methods=['POST'])
def send_room_message():
    ping_thread = threading.Thread(target=ping_server, args=(60,), daemon=True)
    ping_thread.start()
    data = request.get_json()
    token = request.headers.get('Authorization')
    room_id = data.get('room_id')
    message = data.get('message', '').strip()

    if not token or not room_id or not message:
        return jsonify({'error': 'missing fields'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401

    c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, user[0]))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'you are not in this room'}), 403
    
    conn.close()

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

@chat_bp.route('/api/get_room_messages', methods=['GET'])
def get_room_messages():
    token = request.headers.get('Authorization')
    room_id = request.args.get('room_id')

    if not token or not room_id:
        return jsonify({'error': 'missing token or room id'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401

    c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, user[0]))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'you are not in this room'}), 403
    
    conn.close()

    filtered = [m for m in messages if str(m.get('room_id')) == str(room_id)]
    return jsonify({'messages': filtered}), 200

@chat_bp.route('/api/rooms', methods=['GET'])
def list_rooms():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'missing token'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401

    c.execute('SELECT id, name FROM rooms WHERE is_private=0')
    rooms = c.fetchall()

    c.execute('SELECT room_id FROM room_members WHERE username=?', (user[0],))
    user_rooms_set = {r[0] for r in c.fetchall()}

    conn.close()

    data = []
    for room_id, name in rooms:
        data.append({
            'room_id': room_id,
            'name': name,
            'joined': room_id in user_rooms_set
        })

    return jsonify({'rooms': data}), 200

@chat_bp.route('/api/room_members/<int:room_id>', methods=['GET'])
def get_room_members(room_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    
    c.execute('SELECT username FROM room_members WHERE room_id=?', (room_id,))
    members = c.fetchall()
    if not members:
        conn.close()
        return jsonify({'error': 'no members in this room'}), 404
    
    members_list = [m[0] for m in members]
    conn.close()
    
    return jsonify({'members': members_list}), 200

@chat_bp.route('/api/user_rooms', methods=['GET'])
def user_rooms():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error':'invalid token, please re-login'}), 401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    
    username = user[0]
    
    # Get all rooms the user is a member of
    c.execute('SELECT r.id, r.name, r.is_private FROM rooms r JOIN room_members rm ON r.id = rm.room_id WHERE rm.username=?', (username,))
    rooms = c.fetchall()
    conn.close()
    
    room_list = []
    for room in rooms:
        room_data = {
            'room_id': room[0],
            'name': room[1],
            'is_private': room[2]
        }
        room_list.append(room_data)
    return jsonify({'rooms': room_list}), 200
