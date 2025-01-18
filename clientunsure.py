import requests
import threading
import time
import os
import uuid
import json
import hmac
import hashlib
from datetime import datetime
import sys
import itertools
from threading import Lock

class SecurityManager:
    def __init__(self):
        self.client_secret = os.urandom(32)
        self.server_token = None
    
    def generate_signature(self, client_id, timestamp):
        message = f"{client_id}:{timestamp}".encode()
        return hmac.new(self.client_secret, message, 
                       hashlib.sha256).hexdigest()
    
    def calculate_file_checksum(self, filepath):
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

class Message:
    def __init__(self, username, content, msg_type='text', file_path=None):
        self.id = str(uuid.uuid4())
        self.username = username
        self.content = content
        self.timestamp = time.time()
        self.type = msg_type
        self.file_path = file_path
        self.checksum = None  # For file messages
    
    def to_dict(self):
        data = {
            'id': self.id,
            'username': self.username,
            'content': self.content,
            'timestamp': self.timestamp,
            'type': self.type,
            'file_path': self.file_path
        }
        if self.checksum:
            data['checksum'] = self.checksum
        return data

class ChatClient:
    def __init__(self, server_url, username):
        self.server_url = server_url
        self.username = username
        self.client_id = str(uuid.uuid4())
        self.security = SecurityManager()
        self.messages = {}
        self.message_file = f"messages_{username}.json"
        self.downloads_dir = 'downloads'
        self.uploads_dir = 'uploads'
        self.animator = AnimatedText()
        
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        self.load_messages()
        self.register_with_server()

    def register_with_server(self):
        self.animator.animate("Connecting to server")
        try:
            timestamp = str(int(time.time()))
            signature = self.security.generate_signature(self.client_id, timestamp)
            
            response = requests.post(f"{self.server_url}/register", json={
                'client_id': self.client_id,
                'timestamp': timestamp,
                'signature': signature,
                'last_msg_id': max((msg.id for msg in self.messages.values()), 
                                 default=''),
                'available_files': [f for f in os.listdir(self.uploads_dir)]
            })
            
            if response.ok:
                data = response.json()
                self.security.server_token = data['token']
                active_clients = data['active_clients']
                self.sync_with_peers(active_clients)
            else:
                print("\nServer registration failed:", response.json().get('error'))
                sys.exit(1)
        except Exception as e:
            print(f"\nError registering with server: {e}")
            sys.exit(1)
        finally:
            self.animator.stop()

    def upload_file(self, filepath, msg_id):
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        if file_size > 8 * 1024 * 1024:
            print(f"\nError: File size ({file_size/1024/1024:.1f}MB) exceeds limit (8MB)")
            return False

        self.animator.animate(f"Uploading {filename}")
        try:
            # Calculate checksum before upload
            checksum = self.security.calculate_file_checksum(filepath)
            
            with open(filepath, 'rb') as f:
                files = {'file': f}
                data = {
                    'client_id': self.client_id,
                    'token': self.security.server_token,
                    'msg_id': msg_id,
                    'checksum': checksum
                }
                response = requests.post(f"{self.server_url}/upload",
                                       files=files, data=data)
                
                if not response.ok:
                    error_msg = response.json().get('error', 'Unknown error')
                    print(f"\nUpload failed: {error_msg}")
                    return False
                
                # Store checksum for later verification
                return response.json().get('checksum') == checksum
                
        except Exception as e:
            print(f"\nError uploading file: {e}")
            return False
        finally:
            self.animator.stop()

    def download_file(self, filename):
        try:
            params = {
                'client_id': self.client_id,
                'token': self.security.server_token
            }
            response = requests.get(f"{self.server_url}/download/{filename}",
                                  params=params)
            
            if response.ok:
                filepath = os.path.join(self.downloads_dir, 
                                      filename.split('_', 1)[1])
                
                # Save file temporarily
                temp_path = filepath + '.tmp'
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify checksum
                actual_checksum = self.security.calculate_file_checksum(temp_path)
                expected_checksum = response.headers.get('X-File-Checksum')
                
                if actual_checksum != expected_checksum:
                    os.remove(temp_path)
                    print("\nFile integrity check failed")
                    return False
                
                # Move to final location
                os.rename(temp_path, filepath)
                print(f"\nFile downloaded: {filepath}")
                return True
                
            elif response.status_code == 404:
                print(f"\nFile expired or not found: {filename}")
                self.animator.animate(f"Requesting {filename} from peers")
                # Peer file request logic can be implemented here
            return False
            
        except Exception as e:
            print(f"\nError downloading file: {e}")
            return False
        finally:
            self.animator.stop()

    def load_messages(self):
        try:
            if os.path.exists(self.message_file):
                with open(self.message_file, 'r') as f:
                    messages = json.load(f)
                    for msg_data in messages:
                        msg = Message(**msg_data)
                        self.messages[msg.id] = msg
        except Exception as e:
            print(f"\nError loading messages: {e}")

    def sync_with_peers(self, active_clients):
        try:
            self.animator.animate("Syncing with peers")
            for client_id in active_clients:
                response = requests.get(f"{self.server_url}/sync/{client_id}", params={
                    'client_id': self.client_id,
                    'token': self.security.server_token
                })
                if response.ok:
                    peer_messages = response.json().get('messages', [])
                    for msg_data in peer_messages:
                        msg = Message(**msg_data)
                        if msg.id not in self.messages:
                            self.messages[msg.id] = msg
                            self.save_message(msg)
        except Exception as e:
            print(f"\nError syncing with peers: {e}")
        finally:
            self.animator.stop()

    def save_message(self, message):
        try:
            self.messages[message.id] = message
            with open(self.message_file, 'w') as f:
                json.dump([msg.to_dict() for msg in self.messages.values()], f)
        except Exception as e:
            print(f"\nError saving message: {e}")

class AnimatedText:
    def __init__(self):
        self.running = False
        self.lock = Lock()
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])

    def animate(self, text):
        def run():
            while self.running:
                with self.lock:
                    sys.stdout.write(f"\r{text} {next(self.spinner)}")
                    sys.stdout.flush()
                time.sleep(0.1)

        with self.lock:
            self.running = True
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        with self.lock:
            self.running = False
            sys.stdout.write("\r")
            sys.stdout.flush()

if __name__ == "__main__":
    server_url = input("Enter server URL (e.g., http://localhost:5000): ")
    username = input("Enter your username: ")
    
    client = ChatClient(server_url, username)
    client.animator.animate("Starting client")
    # Add main interaction loop or client.start() as needed
    client.animator.stop()
