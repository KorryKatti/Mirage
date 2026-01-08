
from flask import Blueprint, request, jsonify
import sqlite3
from app.db import get_db_connection

inbox_bp = Blueprint('inbox', __name__)

@inbox_bp.route('/api/send_inbox_message',methods=['POST'])
def send_inbox_message():
    data = request.get_json()
    token = request.headers.get('Authorization')
    recipient_username = data.get('recipient')
    message = data.get('message','')
    # do the message sending and storing
    if not token:
        return jsonify({'error':'invalid token , please re-login'}),401
    
    if not recipient_username or not message:
        return jsonify({'error':'missing recipient or message'}),400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    sender = user[0]
    
    c.execute('SELECT username FROM users WHERE username=?',(recipient_username,))
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


@inbox_bp.route('/api/inbox', methods=['GET'])
def inbox():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'invalid token , please re-login'}), 401
    
    conn = get_db_connection()
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
    
    messages_rows = c.fetchall()
    conn.close()
    
    inbox_data = []
    for msg in messages_rows:
        inbox_data.append({
            'id': msg[0],
            'sender': msg[1],
            'recipient': msg[2],
            'message': msg[3],
            'created_at': msg[4],
            'avatar_url': msg[5] or "https://i.pinimg.com/736x/20/da/fa/20dafa83d38f2277472e132bf1f21c22.jpg"
        })
    
    return jsonify({'messages': inbox_data}), 200

@inbox_bp.route('/api/delete_inbox_message',methods=['POST'])
def delete_inbox_message():
    data = request.get_json()
    token = request.headers.get('Authorization')
    message_id = data.get('message_id')

    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    if not message_id:
        return jsonify({'error': 'missing message ID'}), 400

    conn = get_db_connection()
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
@inbox_bp.route('/api/inbox_count',methods=['GET'])
def inbox_count():
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
    
    username = user[0]
    
    c.execute('SELECT COUNT(*) FROM inbox_messages WHERE recipient=?', (username,))
    count = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({'inbox_count': count}), 200
