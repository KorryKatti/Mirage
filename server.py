# server.py
from flask import Flask, request, jsonify, send_file
import os
import time
import threading
import hashlib
import hmac
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB
FILE_RETENTION_TIME = 3600  # 1 hour
SERVER_SECRET = os.urandom(32)  # Generate random server secret on startup

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_clients = {}
file_metadata = {}  # filename -> (upload_time, checksum)

def verify_signature(client_id, timestamp, signature):
    try:
        message = f"{client_id}:{timestamp}".encode()
        expected_sig = hmac.new(SERVER_SECRET, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    except:
        return False

def calculate_file_checksum(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def cleanup_files():
    while True:
        current_time = time.time()
        files_to_remove = []
        
        for filename, (upload_time, _) in file_metadata.items():
            if current_time - upload_time > FILE_RETENTION_TIME:
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                try:
                    os.remove(filepath)
                    files_to_remove.append(filename)
                except:
                    pass
        
        for filename in files_to_remove:
            del file_metadata[filename]
        
        time.sleep(300)

cleanup_thread = threading.Thread(target=cleanup_files, daemon=True)
cleanup_thread.start()

@app.route('/register', methods=['POST'])
def register_client():
    data = request.json
    client_id = data['client_id']
    timestamp = data.get('timestamp')
    signature = data.get('signature')
    
    if not verify_signature(client_id, timestamp, signature):
        return jsonify({'error': 'Invalid client signature'}), 403
    
    # Generate client token
    token = hmac.new(SERVER_SECRET, 
                     f"{client_id}:{timestamp}".encode(),
                     hashlib.sha256).hexdigest()
    
    active_clients[client_id] = {
        'token': token,
        'last_msg_id': data.get('last_msg_id', ''),
        'available_files': data.get('available_files', [])
    }
    
    return jsonify({
        'token': token,
        'active_clients': {
            cid: info for cid, info in active_clients.items() 
            if cid != client_id
        }
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    client_id = request.form['client_id']
    token = request.form['token']
    
    # Verify client token
    if (client_id not in active_clients or 
        active_clients[client_id]['token'] != token):
        return jsonify({'error': 'Invalid token'}), 403
    
    file = request.files['file']
    msg_id = request.form['msg_id']
    provided_checksum = request.form['checksum']
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return jsonify({
            'error': 'File too large',
            'max_size_mb': MAX_FILE_SIZE / 1024 / 1024
        }), 413
    
    if file:
        # Save file temporarily to verify checksum
        temp_path = os.path.join(UPLOAD_FOLDER, 'temp_' + secure_filename(file.filename))
        file.save(temp_path)
        
        # Verify checksum
        actual_checksum = calculate_file_checksum(temp_path)
        if actual_checksum != provided_checksum:
            os.remove(temp_path)
            return jsonify({'error': 'File checksum mismatch'}), 400
        
        # Move to final location
        filename = f"{msg_id}_{secure_filename(file.filename)}"
        final_path = os.path.join(UPLOAD_FOLDER, filename)
        os.rename(temp_path, final_path)
        
        file_metadata[filename] = (time.time(), actual_checksum)
        return jsonify({
            'status': 'ok',
            'filename': filename,
            'checksum': actual_checksum
        })

@app.route('/download/<filename>')
def download_file(filename):
    client_id = request.args.get('client_id')
    token = request.args.get('token')
    
    # Verify client token
    if (client_id not in active_clients or 
        active_clients[client_id]['token'] != token):
        return jsonify({'error': 'Invalid token'}), 403
    
    if filename in file_metadata:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            # Verify file hasn't been tampered with
            current_checksum = calculate_file_checksum(file_path)
            stored_checksum = file_metadata[filename][1]
            
            if current_checksum != stored_checksum:
                return jsonify({'error': 'File integrity check failed'}), 500
                
            return send_file(file_path)
    
    return jsonify({'error': 'File expired or not found'}), 404

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    client_id = data['client_id']
    token = data['token']
    
    if (client_id not in active_clients or 
        active_clients[client_id]['token'] != token):
        return jsonify({'error': 'Invalid token'}), 403
    
    active_clients[client_id].update({
        'last_msg_id': data['last_msg_id'],
        'available_files': data['available_files']
    })
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)