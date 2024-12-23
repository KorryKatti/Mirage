import socket
import threading
import json
import logging
from datetime import datetime
import os
import bcrypt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.clients = {}  # socket: {'username': username, 'room': room}
        self.rooms = {'global': set()}  # room_name: set of client sockets
        self.server_socket = None
        self.users_file = 'users.json'
        self.rooms_file = 'rooms.json'
        self.room_members_file = 'room_members.json'
        self.load_users()
        self.load_rooms()
        self.load_room_members()

    def load_users(self):
        """Load users from JSON file"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
        with open(self.users_file, 'r') as f:
            self.users = json.load(f)

    def save_users(self):
        """Save users to JSON file"""
        try:
            logger.info(f"Saving users to {self.users_file}")
            logger.info(f"Current users data: {self.users}")
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=4)
            logger.info("Users data saved successfully")
        except Exception as e:
            logger.error(f"Error saving users data: {str(e)}")
            raise  # Re-raise to handle in calling function

    def load_rooms(self):
        """Load rooms from rooms.json"""
        try:
            with open(self.rooms_file, 'r') as f:
                rooms_data = json.load(f)
                # Initialize each room from the file
                for room_name, room_info in rooms_data.items():
                    if room_name not in self.rooms:
                        self.rooms[room_name] = set()
        except FileNotFoundError:
            # Create file if it doesn't exist
            self.save_rooms()
        except json.JSONDecodeError:
            # If file is corrupted, start fresh
            self.save_rooms()

    def save_rooms(self):
        """Save rooms to rooms.json"""
        try:
            rooms_data = {room: {
                'created_at': datetime.now().isoformat(),
                'description': '',  # You can add room descriptions later
                'creator': '',      # You can add creator info later
                'public': False
            } for room in self.rooms.keys()}
            
            with open(self.rooms_file, 'w') as f:
                json.dump(rooms_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving rooms: {e}")

    def load_room_members(self):
        """Load room members from JSON file"""
        try:
            with open(self.room_members_file, 'r') as f:
                self.room_members = json.load(f)
        except FileNotFoundError:
            self.room_members = {
                "global": {
                    "members": [],
                    "public": True
                }
            }
            self.save_room_members()
        except json.JSONDecodeError:
            self.room_members = {
                "global": {
                    "members": [],
                    "public": True
                }
            }
            self.save_room_members()

    def save_room_members(self):
        """Save room members to JSON file"""
        try:
            with open(self.room_members_file, 'w') as f:
                json.dump(self.room_members, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving room members: {e}")

    def hash_password(self, password):
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password, hashed):
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def register_user(self, data):
        """Register a new user"""
        try:
            username = data['username']
            email = data['email']
            password = data['password']
            avatar_url = data['avatar_url']
            bio = data['bio']

            if username in self.users:
                return False, "Username already exists"
            
            if any(user['email'] == email for user in self.users.values()):
                return False, "Email already registered"

            # Hash the password before storing
            hashed_password = self.hash_password(password)

            self.users[username] = {
                'email': email,
                'password': hashed_password,  # Store hashed password
                'avatar_url': avatar_url,
                'bio': bio
            }
            self.save_users()
            return True, "Registration successful"
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, "Registration failed"

    def login_user(self, data):
        """Login a user"""
        try:
            username = data.get('username')
            password = data.get('password')

            if username not in self.users:
                return False, "User not found"

            if bcrypt.checkpw(password.encode(), self.users[username]['password'].encode()):
                user_data = self.users[username]
                return True, {
                    'message': "Login successful",
                    'avatar_url': user_data.get('avatar_url', ''),
                    'bio': user_data.get('bio', '')
                }
            return False, "Invalid password"
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, "Login failed"

    def update_user_settings(self, data):
        """Update user settings"""
        try:
            username = data.get('username')
            new_password = data.get('new_password')
            new_avatar_url = data.get('new_avatar_url')
            new_bio = data.get('new_bio')
            current_password = data.get('current_password')

            logger.info(f"Updating settings for user: {username}")
            logger.info(f"Current data in users: {self.users.get(username)}")
            logger.info(f"New bio: {new_bio}")
            logger.info(f"New avatar URL: {new_avatar_url}")

            if username not in self.users:
                logger.error(f"User {username} not found")
                return False, "User not found"

            # Verify current password
            stored_password = self.users[username]['password']
            logger.info(f"Verifying password for {username}")
            
            try:
                password_correct = bcrypt.checkpw(current_password.encode(), stored_password.encode())
                if not password_correct:
                    logger.error(f"Password verification failed for {username}")
                    return False, "Current password is incorrect"
            except Exception as e:
                logger.error(f"Password verification error: {str(e)}")
                return False, f"Password verification error: {str(e)}"

            # Update password if provided
            if new_password:
                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                self.users[username]['password'] = hashed.decode()
                logger.info("Password updated")

            # Update avatar URL if provided
            if new_avatar_url is not None:
                self.users[username]['avatar_url'] = new_avatar_url
                logger.info(f"Avatar URL updated to: {new_avatar_url}")

            # Update bio if provided
            if new_bio is not None:
                self.users[username]['bio'] = new_bio
                logger.info(f"Bio updated to: {new_bio}")

            # Save changes
            self.save_users()
            logger.info(f"Settings updated successfully for {username}")
            logger.info(f"New user data: {self.users.get(username)}")
            return True, "Settings updated successfully"
        except Exception as e:
            logger.error(f"Error updating settings for {username}: {str(e)}")
            return False, f"Error updating settings: {str(e)}"

    def get_user_rooms(self, username):
        """Get list of rooms available to a user"""
        available_rooms = ['global']  # Global is always available
        
        for room_name, room_info in self.room_members.items():
            if room_info.get('public', False) or username in room_info.get('members', []):
                available_rooms.append(room_name)
                
        return available_rooms

    def create_room(self, room_name, client_socket):
        """Create a new room"""
        try:
            username = self.clients[client_socket]['username']
            
            # Validate room name
            if not room_name or not isinstance(room_name, str):
                return False, "Invalid room name"
            
            # Clean room name
            room_name = "".join(x for x in room_name if x.isalnum() or x in (' ', '-', '_')).strip()
            
            if not room_name:
                return False, "Room name must contain valid characters"
            
            if room_name in self.rooms:
                return False, "Room already exists"
            
            # Create the room
            self.rooms[room_name] = set()
            
            # Save to rooms.json
            with open(self.rooms_file, 'r') as f:
                rooms_data = json.load(f)
            
            rooms_data[room_name] = {
                'created_at': datetime.now().isoformat(),
                'description': '',
                'creator': username,
                'public': True  # Changed to True by default
            }
            
            with open(self.rooms_file, 'w') as f:
                json.dump(rooms_data, f, indent=4)
            
            # Update room members
            self.room_members[room_name] = {
                'members': [username],
                'public': True  # Changed to True by default
            }
            self.save_room_members()
            
            # Send updated room list to the creator
            available_rooms = self.get_user_rooms(username)
            room_update = json.dumps({
                'action': 'room_list',
                'rooms': available_rooms
            })
            client_socket.send(room_update.encode())
            
            return True, "Room created successfully"
            
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            return False, "Server error creating room"

    def handle_join_room(self, client_socket, data):
        """Handle room joining logic"""
        try:
            username = data.get('username')
            new_room = data.get('room')
            
            if not username or not new_room:
                return False
            
            # Check if user has access to the room
            user_rooms = self.get_user_rooms(username)
            room_info = self.room_members.get(new_room, {})
            is_public = room_info.get('public', False)
            
            if new_room not in user_rooms and not is_public:
                client_socket.send(json.dumps({
                    'action': 'error',
                    'message': "You don't have access to this room"
                }).encode())
                return False
            
            if client_socket not in self.clients:
                self.clients[client_socket] = {'username': username, 'room': 'global'}
            
            old_room = self.clients[client_socket]['room']
            
            # Remove from old room
            if old_room in self.rooms and client_socket in self.rooms[old_room]:
                self.rooms[old_room].remove(client_socket)
                self.broadcast(json.dumps({
                    'action': 'chat_message',
                    'message': f"{username} has left the room"
                }), room=old_room)
            
            # Add to new room
            if new_room not in self.rooms:
                self.rooms[new_room] = set()
            
            self.rooms[new_room].add(client_socket)
            self.clients[client_socket]['room'] = new_room
            
            # Add to room members if not already there
            if username not in self.room_members[new_room]['members']:
                self.room_members[new_room]['members'].append(username)
                self.save_room_members()
            
            self.broadcast(json.dumps({
                'action': 'chat_message',
                'message': f"{username} has joined the room"
            }), room=new_room)
            
            # Send confirmation to client
            client_socket.send(json.dumps({
                'action': 'room_changed',
                'room': new_room
            }).encode())
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling room join: {e}")
            return False

    def handle_explore_rooms(self, client_socket):
        """Handle room exploration request"""
        try:
            username = self.clients[client_socket]['username']
            
            # Get all rooms
            with open(self.rooms_file, 'r') as f:
                rooms_data = json.load(f)
            
            # Format room data for client
            room_list = []
            for room_name, room_info in rooms_data.items():
                room_list.append({
                    'name': room_name,
                    'creator': room_info.get('creator', ''),
                    'created_at': room_info.get('created_at', ''),
                    'description': room_info.get('description', ''),
                    'public': room_info.get('public', False),
                    'member_count': len(self.room_members.get(room_name, {}).get('members', [])),
                    'is_member': username in self.room_members.get(room_name, {}).get('members', [])
                })
            
            response = {
                'action': 'explore_rooms_response',
                'rooms': room_list
            }
            client_socket.send(json.dumps(response).encode())
            return True
            
        except Exception as e:
            logger.error(f"Error handling room exploration: {e}")
            return False

    def get_room_members(self, client_socket, room_name):
        """Get list of members in a room with their profiles"""
        try:
            # Load room members
            with open(self.room_members_file, 'r') as f:
                room_members = json.load(f)
            
            if room_name not in room_members:
                response = {
                    'action': 'error',
                    'message': 'Room not found'
                }
                client_socket.send(json.dumps(response).encode())
                return
            
            # Load user profiles
            with open(self.users_file, 'r') as f:
                users_data = json.load(f)
            
            # Get member profiles
            members_data = []
            for username in room_members[room_name]['members']:
                if username in users_data:
                    members_data.append({
                        'username': username,
                        'avatar_url': users_data[username].get('avatar_url', 'https://i.pinimg.com/736x/0c/da/40/0cda4058d21f8101ffcc223eec55c18f.jpg'),
                        'bio': users_data[username].get('bio', 'No bio provided')
                    })
            
            response = {
                'action': 'get_room_members_response',
                'members': members_data
            }
            client_socket.send(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Error getting room members: {str(e)}")
            response = {
                'action': 'error',
                'message': f"Server error: {str(e)}"
            }
            client_socket.send(json.dumps(response).encode())

    def broadcast(self, message, room='global', exclude=None):
        """Broadcast a message to all clients in a room"""
        try:
            if room not in self.rooms:
                return
            
            for client in self.rooms[room]:
                if client != exclude and client in self.clients:
                    try:
                        client.send(message.encode() if isinstance(message, str) else message)
                    except Exception as e:
                        logger.error(f"Error sending to client: {e}")
                        self.remove_client(client)
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")

    def broadcast_message(self, data):
        """Handle and broadcast chat messages"""
        try:
            username = data.get('username')
            message = data.get('message')
            room = data.get('room', 'global')
            
            if not username or not message:
                return
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Special handling for file upload messages
            if '📁 File Uploaded:' in message:
                broadcast_message = {
                    'action': 'chat_message',
                    'message': f"{message}"  # Keep the full file upload message
                }
            else:
                broadcast_message = {
                    'action': 'chat_message',
                    'message': f"[{timestamp}] {username}: {message}"
                }
            
            if room not in self.rooms:
                room = 'global'
                
            self.broadcast(json.dumps(broadcast_message), room=room)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    def remove_client(self, client_socket):
        """Remove client and clean up their data"""
        try:
            if client_socket in self.clients:
                username = self.clients[client_socket]['username']
                room = self.clients[client_socket]['room']
                
                # Remove from room
                if room in self.rooms and client_socket in self.rooms[room]:
                    self.rooms[room].remove(client_socket)
                    self.broadcast(json.dumps({
                        'action': 'chat_message',
                        'message': f"{username} has left the room"
                    }), room=room)
                
                # Remove from clients
                del self.clients[client_socket]
            
            client_socket.close()
        except Exception as e:
            logger.error(f"Error removing client: {e}")

    def handle_client(self, client_socket):
        """Handle individual client connections"""
        try:
            while True:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    logger.info(f"Received data: {data}")
                    data = json.loads(data)
                    action = data.get('action')
                    logger.info(f"Processing action: {action}")

                    if action == 'register':
                        success, message = self.register_user(data)
                        response = {'success': success, 'message': message}
                        client_socket.send(json.dumps(response).encode())
                        if success:
                            # Initialize client data
                            username = data.get('username')
                            self.clients[client_socket] = {'username': username, 'room': 'global'}
                            self.rooms['global'].add(client_socket)
                        else:
                            return
                    
                    elif action == 'login':
                        success, response = self.login_user(data)
                        if isinstance(response, dict):
                            client_socket.send(json.dumps({
                                'success': True,
                                'message': response['message'],
                                'avatar_url': response['avatar_url'],
                                'bio': response['bio']
                            }).encode())
                            # Initialize client data
                            username = data.get('username')
                            self.clients[client_socket] = {'username': username, 'room': 'global'}
                            self.rooms['global'].add(client_socket)
                        else:
                            client_socket.send(json.dumps({
                                'success': False,
                                'message': response
                            }).encode())
                        if not success:
                            return
                    
                    elif action == 'update_settings':
                        logger.info("Processing settings update")
                        success, message = self.update_user_settings(data)
                        response = {
                            'success': success,
                            'message': message
                        }
                        if success:
                            user_data = self.users[data['username']]
                            response.update({
                                'avatar_url': user_data.get('avatar_url', ''),
                                'bio': user_data.get('bio', '')
                            })
                        logger.info(f"Sending settings response: {response}")
                        client_socket.send(json.dumps(response).encode())
                        continue

                    elif action == 'send_message':
                        self.broadcast_message(data)
                        continue

                    elif action == 'join_room':
                        self.handle_join_room(client_socket, data)
                        continue

                    elif action == 'create_room':
                        success, message = self.create_room(data.get('room_name'), client_socket)
                        response = {
                            'action': 'create_room_response',
                            'success': success,
                            'message': message
                        }
                        client_socket.send(json.dumps(response).encode())
                        continue

                    elif action == 'explore_rooms':
                        self.handle_explore_rooms(client_socket)
                        continue

                    elif action == 'get_room_members':
                        self.get_room_members(client_socket, data.get('room'))
                        continue

                    # After successful login/register, send room list
                    if action in ['login', 'register']:
                        username = self.clients[client_socket]['username']
                        available_rooms = self.get_user_rooms(username)
                        room_list = {
                            'action': 'room_list',
                            'rooms': available_rooms
                        }
                        client_socket.send(json.dumps(room_list).encode())

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    client_socket.send(json.dumps({
                        'success': False,
                        'message': 'Invalid JSON format'
                    }).encode())
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    client_socket.send(json.dumps({
                        'success': False,
                        'message': f'Server error: {str(e)}'
                    }).encode())

        except Exception as e:
            logger.error(f"Client connection error: {e}")
        finally:
            logger.info("Client disconnected")
            self.remove_client(client_socket)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logger.info(f"Server started on {self.host}:{self.port}")

        while True:
            client_socket, address = self.server_socket.accept()
            logger.info(f"New connection from {address}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
