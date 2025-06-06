import sys
sys.path.append('/home/korry/Documents/github/mirage')

from web_server import WebServer

import socket
import threading
import json
import logging
from datetime import datetime
import os
import bcrypt
import uuid

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
                'public': True
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
            
            # Check if room already exists
            with open(self.rooms_file, 'r') as f:
                rooms_data = json.load(f)
            
            if room_name in rooms_data:
                client_socket.send(json.dumps({
                    'action': 'error',
                    'message': f"Room '{room_name}' already exists"
                }).encode())
                return False, f"Room '{room_name}' already exists"
            
            # Create the room
            self.rooms[room_name] = set()
            
            # Save to rooms.json
            rooms_data[room_name] = {
                'created_at': datetime.now().isoformat(),
                'description': '',
                'creator': username,
                'public': True
            }
            
            with open(self.rooms_file, 'w') as f:
                json.dump(rooms_data, f, indent=4)
            
            # Update room members
            self.room_members[room_name] = {
                'members': [username],
                'public': True
            }
            self.save_room_members()
            
            # Send room list update only to the creator
            room_list_message = json.dumps({
                'action': 'room_list',
                'rooms': list(rooms_data.keys())
            })
            client_socket.send(room_list_message.encode())
            
            # Send success response to creator (not as a chat message)
            client_socket.send(json.dumps({
                'action': 'create_room_response',
                'success': True,
                'message': f"Room '{room_name}' created successfully"
            }).encode())
            
            return True, f"Room '{room_name}' created successfully"
            
        except Exception as e:
            logger.error(f"Error creating room: {e}")
            client_socket.send(json.dumps({
                'action': 'error',
                'message': f"Server error creating room: {str(e)}"
            }).encode())
            return False, "Server error creating room"

    def handle_join_room(self, client_socket, data):
        """Handle room joining logic"""
        try:
            username = data.get('username')
            new_room = data.get('room')
            
            if not username or not new_room:
                client_socket.send(json.dumps({
                    'action': 'error',
                    'message': 'Invalid room or username'
                }).encode())
                return False
            
            # Check if room exists
            with open(self.rooms_file, 'r') as f:
                rooms_data = json.load(f)
            
            room_info = rooms_data.get(new_room, {})
            
            # Check if room exists
            if not room_info:
                client_socket.send(json.dumps({
                    'action': 'error',
                    'message': f'Room {new_room} does not exist'
                }).encode())
                return False
            
            # Remove from old room
            if client_socket in self.clients:
                old_room = self.clients[client_socket]['room']
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
            
            # Update client's current room
            if client_socket not in self.clients:
                self.clients[client_socket] = {}
            self.clients[client_socket]['room'] = new_room
            
            # Add to room members if not already there
            if new_room not in self.room_members:
                self.room_members[new_room] = {'members': []}
            
            if username not in self.room_members[new_room]['members']:
                self.room_members[new_room]['members'].append(username)
                self.save_room_members()
            
            # Send confirmation to client
            client_socket.send(json.dumps({
                'action': 'room_changed',
                'room': new_room
            }).encode())
            
            # Broadcast join message
            self.broadcast(json.dumps({
                'action': 'chat_message',
                'message': f"{username} has joined the room"
            }), room=new_room)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling room join: {e}")
            client_socket.send(json.dumps({
                'action': 'error',
                'message': f"Server error: {str(e)}"
            }).encode())
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

    def handle_client_message(self, client_socket, message):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'join_room':
                return self.handle_join_room(client_socket, data)
            
            elif action == 'register':
                success, message = self.register_user(data)
                response = {'success': success, 'message': message}
                client_socket.send(json.dumps(response).encode())
                if success:
                    # Initialize client data
                    username = data.get('username')
                    self.clients[client_socket] = {'username': username, 'room': 'global'}
                    self.rooms['global'].add(client_socket)
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
                    
                    # Send room list
                    available_rooms = self.get_user_rooms(username)
                    room_list = {
                        'action': 'room_list',
                        'rooms': available_rooms
                    }
                    client_socket.send(json.dumps(room_list).encode())
                else:
                    client_socket.send(json.dumps({
                        'success': False,
                        'message': response
                    }).encode())
                return
            
            elif action == 'update_settings':
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
                client_socket.send(json.dumps(response).encode())
                return

            elif action == 'send_message':
                self.broadcast_message(data)
                return

            elif action == 'create_room':
                success, message = self.create_room(data.get('room_name'), client_socket)
                response = {
                    'action': 'create_room_response',
                    'success': success,
                    'message': message
                }
                client_socket.send(json.dumps(response).encode())
                return

            elif action == 'explore_rooms':
                self.handle_explore_rooms(client_socket)
                return

            elif action == 'get_room_members':
                self.get_room_members(client_socket, data.get('room'))
                return

            elif action == 'add_profile_comment':
                self.handle_profile_comment(client_socket, data)
                return

            elif action == 'get_user_profile':
                self.get_user_profile(client_socket, data)
                return

            elif action == 'file_transfer':
                self.handle_file_transfer(client_socket, data)
                return

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

    def handle_file_transfer(self, client_socket, data):
        """
        Handle incoming file transfer
        
        :param client_socket: Socket of the client sending the file
        :param data: Dictionary containing file transfer metadata
        """
        try:
            # Validate file transfer data
            filename = data.get('filename')
            filesize = data.get('filesize')
            sender = data.get('sender')
            room = data.get('room', 'global')
            
            if not all([filename, filesize, sender]):
                self.send_error(client_socket, "Invalid file transfer metadata")
                return
            
            # Create directory for file transfers if it doesn't exist
            import os
            transfer_dir = os.path.join(os.path.dirname(__file__), 'file_transfers')
            os.makedirs(transfer_dir, exist_ok=True)
            
            # Generate unique filename to prevent overwriting
            import uuid
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(transfer_dir, unique_filename)
            
            # Prepare to receive file
            with open(file_path, 'wb') as f:
                bytes_received = 0
                while bytes_received < filesize:
                    chunk = client_socket.recv(min(4096, filesize - bytes_received))
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
            
            # Broadcast file transfer to room
            file_message = {
                'action': 'file_received',
                'filename': filename,
                'unique_filename': unique_filename,
                'sender': sender,
                'filesize': filesize,
                'room': room
            }
            
            # Broadcast to all clients in the room
            self.broadcast(json.dumps(file_message), room=room)
            
            # Send success response to sender
            response = {
                'action': 'file_transfer_complete',
                'filename': filename,
                'unique_filename': unique_filename
            }
            client_socket.send(json.dumps(response).encode())
        
        except Exception as e:
            logging.error(f"Error handling file transfer: {e}")
            self.send_error(client_socket, "File transfer failed")

    def handle_profile_comment(self, client_socket, data):
        try:
            # Validate comment data
            username = data.get('username')
            target_user = data.get('target_user')
            comment_text = data.get('comment')
            
            logging.info(f"Received comment: username={username}, target_user={target_user}, comment={comment_text}")
            
            if not all([username, target_user, comment_text]):
                logging.error("Invalid comment data: missing fields")
                self.send_error(client_socket, "Invalid comment data")
                return
            
            # Validate that the commenting user exists
            if username not in self.users:
                logging.error(f"Sender user not found: {username}")
                self.send_error(client_socket, "Sender user not found")
                return
            
            # Validate target user exists
            if target_user not in self.users:
                logging.error(f"Target user not found: {target_user}")
                self.send_error(client_socket, "Target user not found")
                return
            
            # Sanitize comment length
            if len(comment_text) > 500:
                logging.error("Comment too long")
                self.send_error(client_socket, "Comment too long (max 500 characters)")
                return
            
            # Generate a unique comment ID
            comment_id = str(uuid.uuid4())
            
            # Store comment in user's profile comments
            comment_data = {
                'id': comment_id,
                'username': username,
                'comment': comment_text,
                'timestamp': datetime.now().isoformat()
            }
            
            # Ensure comments collection exists for the user
            if 'comments' not in self.users[target_user]:
                self.users[target_user]['comments'] = []
            
            # Add comment to user's profile
            self.users[target_user]['comments'].insert(0, comment_data)
            
            # Limit comments to last 50
            self.users[target_user]['comments'] = self.users[target_user]['comments'][:50]
            
            # Save updated user data IMMEDIATELY
            try:
                with open(self.users_file, 'r') as f:
                    all_users = json.load(f)
                
                # Update the specific user's comments
                all_users[target_user]['comments'] = self.users[target_user]['comments']
                
                # Write back to file
                with open(self.users_file, 'w') as f:
                    json.dump(all_users, f, indent=4)
                
                logging.info(f"Successfully saved comment for user {target_user}")
            except Exception as save_error:
                logging.error(f"Error saving comments: {save_error}")
                logging.error(f"Current users data: {self.users}")
                logging.error(f"Target user data: {self.users.get(target_user, 'Not found')}")
            
            # Send success response
            response = {
                'action': 'profile_comment_added',
                'success': True,
                'comment': comment_data,
                'target_user': target_user
            }
            client_socket.send(json.dumps(response).encode())
        
        except Exception as e:
            logging.error(f"Unexpected error handling profile comment: {e}")
            self.send_error(client_socket, "Failed to add comment")

    def get_user_profile(self, client_socket, data):
        """
        Retrieve and send user profile data
        
        :param client_socket: Socket to send the response
        :param data: Dictionary containing profile request data
        """
        try:
            # Extract username from request
            username = data.get('username')
            
            # Validate username
            if not username or username not in self.users:
                self.send_error(client_socket, f"User {username} not found")
                return
            
            # Retrieve user data
            user_data = self.users[username]
            
            # Render the profile page
            self.render_profile_page(client_socket, username)
        
        except Exception as e:
            logging.error(f"Error getting user profile: {e}")
            self.send_error(client_socket, "Failed to retrieve user profile")

    def render_profile_page(self, client_socket, username):
        """
        Render an HTML profile page for a given user
        
        :param client_socket: Socket to send the response
        :param username: Username of the profile to render
        """
        try:
            # Retrieve user data
            if username not in self.users:
                self.send_error(client_socket, f"User {username} not found")
                return
            
            user_data = self.users[username]
            
            # Determine the current user's username from the client socket
            current_username = self.clients.get(client_socket, {}).get('username', 'Anonymous')
            
            # Prepare comments HTML
            comments_html = ''
            comments = user_data.get('comments', [])
            for comment in comments:
                comments_html += f'''
                <div class="comment">
                    <strong>{comment['username']}</strong>
                    <p>{comment['comment']}</p>
                    <small>{comment['timestamp']}</small>
                </div>
                '''
            
            # Create full HTML profile page
            profile_html = f'''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>{username}'s Profile</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f4f4f4;
                    }}
                    .profile-container {{
                        background-color: white;
                        border-radius: 8px;
                        padding: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        text-align: center;
                    }}
                    .avatar {{
                        width: 150px;
                        height: 150px;
                        border-radius: 50%;
                        object-fit: cover;
                        margin-bottom: 15px;
                    }}
                    .comments-section {{
                        margin-top: 20px;
                        background-color: white;
                        border-radius: 8px;
                        padding: 15px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .comment {{
                        border-bottom: 1px solid #eee;
                        padding: 10px 0;
                    }}
                    .comment:last-child {{
                        border-bottom: none;
                    }}
                    #comment-form {{
                        margin-top: 15px;
                    }}
                    #comment-input {{
                        width: 100%;
                        padding: 10px;
                        margin-bottom: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }}
                    #submit-comment {{
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 10px 15px;
                        border-radius: 4px;
                        cursor: pointer;
                    }}
                </style>
            </head>
            <body>
                <div class="profile-container">
                    <img src="{user_data.get('avatar_url', 'https://via.placeholder.com/150')}" alt="Profile Avatar" class="avatar">
                    <h1 class="username">{username}</h1>
                    <p class="bio">{user_data.get('bio', 'No bio provided')}</p>
                </div>
                
                <div class="comments-section">
                    <h2>Activity Board</h2>
                    <form id="comment-form">
                        <textarea id="comment-input" placeholder="Leave a comment..." rows="4" maxlength="500"></textarea>
                        <button type="submit" id="submit-comment">Post Comment</button>
                    </form>
                    <div id="comments-container">
                        {comments_html}
                    </div>
                </div>
                
                <script>
                    const currentUsername = "{current_username}";
                    const targetUsername = "{username}";
                    
                    document.getElementById('comment-form').addEventListener('submit', function(e) {{
                        e.preventDefault();
                        const commentInput = document.getElementById('comment-input');
                        const comment = commentInput.value.trim();
                        
                        if (comment) {{
                            // Prepare comment data
                            const commentData = {{
                                action: 'add_profile_comment',
                                username: currentUsername,
                                target_user: targetUsername,
                                comment: comment
                            }};
                            
                            // Send comment via WebSocket
                            const socket = new WebSocket('ws://localhost:12345');
                            
                            socket.onopen = function() {{
                                socket.send(JSON.stringify(commentData));
                            }};
                            
                            socket.onmessage = function(event) {{
                                const response = JSON.parse(event.data);
                                
                                if (response.action === 'profile_comment_added') {{
                                    // Add comment to UI
                                    const commentsContainer = document.getElementById('comments-container');
                                    const newComment = document.createElement('div');
                                    newComment.className = 'comment';
                                    newComment.innerHTML = `
                                        <strong>${{response.comment.username}}</strong>
                                        <p>${{response.comment.comment}}</p>
                                        <small>${{response.comment.timestamp}}</small>
                                    `;
                                    commentsContainer.insertBefore(newComment, commentsContainer.firstChild);
                                    commentInput.value = '';
                                }}
                                
                                socket.close();
                            }};
                            
                            socket.onerror = function(error) {{
                                console.error('WebSocket Error:', error);
                                alert('Failed to send comment. Please try again.');
                            }};
                        }}
                    }});
                </script>
            </body>
            </html>
            '''
            
            # Prepare HTTP-like response
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(profile_html)}\r\n"
                "\r\n"
                f"{profile_html}"
            )
            
            # Send the response
            client_socket.send(response.encode())
        
        except Exception as e:
            logging.error(f"Error rendering profile page: {e}")
            self.send_error(client_socket, "Failed to render profile page")

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

    def start_server(self):
        """Start the server and listen for client connections"""
        try:
            # Start the web server in a separate thread
            web_server = WebServer()
            web_server.start_in_thread()
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"Server listening on {self.host}:{self.port}")

            while True:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Connection from {address}")
                
                # Start a new thread to handle client connection
                client_thread = threading.Thread(
                    target=self.handle_client_connection, 
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()

        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.server_socket.close()

    def handle_client_connection(self, client_socket):
        """Handle individual client connection"""
        try:
            while True:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    logger.info(f"Received data: {data}")
                    self.handle_client_message(client_socket, data)

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    client_socket.send(json.dumps({
                        'success': False,
                        'message': 'Invalid JSON format'
                    }).encode())
                except Exception as e:
                    logger.error(f"Client connection error: {e}")
                    break

        except Exception as e:
            logger.error(f"Client connection error: {e}")
        finally:
            self.remove_client(client_socket)
            client_socket.close()

    def send_error(self, client_socket, message):
        client_socket.send(json.dumps({
            'action': 'error',
            'message': message
        }).encode())

if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
