# client.py
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

class AnimatedText:
    def __init__(self):
        self.lock = Lock()
        self.current_animation = None
        self.stop_animation = False

    def animate(self, text, animation_chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'):
        with self.lock:
            self.stop_animation = True
            if self.current_animation:
                self.current_animation.join()
            
            self.stop_animation = False
            self.current_animation = threading.Thread(
                target=self._animate, 
                args=(text, animation_chars)
            )
            self.current_animation.start()

    def _animate(self, text, animation_chars):
        for char in itertools.cycle(animation_chars):
            if self.stop_animation:
                sys.stdout.write('\r' + ' ' * (len(text) + 2) + '\r')
                sys.stdout.flush()
                return
            
            sys.stdout.write(f'\r{char} {text}')
            sys.stdout.flush()
            time.sleep(0.1)

    def stop(self):
        with self.lock:
            self.stop_animation = True
            if self.current_animation:
                self.current_animation.join()
                sys.stdout.write('\r' + ' ' * 50 + '\r')
                sys.stdout.flush()

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

    def load_messages(self):
        self.animator.animate("Loading message history")
        try:
            if os.path.exists(self.message_file):
                with open(self.message_file, 'r') as f:
                    saved_messages = json.load(f)
                    for msg_data in saved_messages:
                        self.messages[msg_data['id']] = Message(**msg_data)
        except Exception as e:
            print(f"\nError loading messages: {e}")
        finally:
            self.animator.stop()

    def sync_with_peers(self, active_clients):
        if not active_clients:
            return

        self.animator.animate("Syncing with peers")
        try:
            for client_id, info in active_clients.items():
                try:
                    response = requests.get(f"{self.server_url}/download/{client_id}_messages.json")
                    if response.ok:
                        peer_messages = response.json()
                        for msg_data in peer_messages:
                            if msg_data['id'] not in self.messages:
                                self.messages[msg_data['id']] = Message(**msg_data)
                                
                                if msg_data['type'] == 'file':
                                    self.animator.animate(f"Downloading file: {msg_data['content']}")
                                    self.download_file(msg_data['content'])
                
                except Exception as e:
                    print(f"\nError syncing with peer {client_id}: {e}")
            
            self.save_messages()
        finally:
            self.animator.stop()

    def save_messages(self):
        try:
            with open(self.message_file, 'w') as f:
                json.dump([msg.to_dict() for msg in self.messages.values()], f)
        except Exception as e:
            print(f"Error saving messages: {e}")

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
        
        if file_size > MAX_FILE_SIZE:
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
                # ... (implement peer file request logic)
            return False
            
        except Exception as e:
            print(f"\nError downloading file: {e}")
            return False
        finally:
            self.animator.stop()

    def send_message(self, content, msg_type='text', file_path=None):
        message = Message(self.username, content, msg_type, file_path)
        self.messages[message.id] = message
        self.save_messages()
        
        if msg_type == 'file':
            self.upload_file(file_path, message.id)
        
        return message

    def display_messages(self):
        sorted_messages = sorted(self.messages.values(), key=lambda x: x.timestamp)
        for msg in sorted_messages:
            timestamp = datetime.fromtimestamp(msg.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            if msg.type == 'file':
                print(f"\n[{timestamp}] {msg.username} shared a file: {msg.content}")
            else:
                print(f"\n[{timestamp}] {msg.username}: {msg.content}")

    def heartbeat(self):
        while True:
            try:
                last_msg_id = max((msg.id for msg in self.messages.values()), default='')
                available_files = [f for f in os.listdir(self.uploads_dir)]
                
                response = requests.post(f"{self.server_url}/heartbeat", json={
                    'client_id': self.client_id,
                    'last_msg_id': last_msg_id,
                    'available_files': available_files
                })
                
                if response.ok:
                    response = requests.get(f"{self.server_url}/active_clients")
                    if response.ok:
                        active_clients = response.json().get('active_clients', {})
                        self.sync_with_peers(active_clients)
                        
            except Exception as e:
                print(f"\nError in heartbeat: {e}")
            
            time.sleep(5)

    def display_prompt(self):
        sys.stdout.write('\n> ')
        sys.stdout.flush()

    def start(self):
        heartbeat_thread = threading.Thread(target=self.heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        print("\n=== Chat History ===")
        self.display_messages()
        print("\nCommands:")
        print("  /file <filepath> - Send a file (8MB max)")
        print("  /clear - Clear screen")
        print("  /quit - Exit chat")
        
        while True:
            self.display_prompt()
            try:
                message = input()
                if message.startswith('/file '):
                    filepath = message[6:].strip()
                    if os.path.exists(filepath):
                        filename = os.path.basename(filepath)
                        msg = self.send_message(filename, 'file', filepath)
                        if msg:
                            print("File sent successfully!")
                        else:
                            print("Failed to send file.")
                    else:
                        print("File not found.")
                elif message == '/clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.display_messages()
                elif message == '/quit':
                    break
                else:
                    self.send_message(message)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    server_url = input("Enter server URL (e.g., http://localhost:5000): ")
    username = input("Enter your username: ")
    
    client = ChatClient(server_url, username)
    client.start()