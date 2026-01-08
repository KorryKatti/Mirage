
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import sqlite3
import time
from app.db import get_db_connection
from app.utils import file_uploader
from app.store import messages, save_messages
from app.config import MAX_MESSAGES, MESSAGE_LIFESPAN

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/api/upload_file', methods=['POST'])
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
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE token=?', (token,))
        user = c.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'Unauthorized access'}), 401
        username = user[0]
        
        c.execute('SELECT id FROM room_members WHERE room_id=? AND username=?', (room_id, username))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'You are not a member of this room'}), 403
        
        conn.close()

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
