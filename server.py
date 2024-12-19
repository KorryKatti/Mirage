import json
import time
from datetime import datetime, timedelta
from flask import Flask
from flask_socketio import SocketIO
from cryptography.fernet import Fernet
import hashlib

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow CORS for testing

# Load the key
with open("secret.key", "rb") as key_file:
    key = key_file.read()

cipher_suite = Fernet(key)

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load existing users from JSON file
def load_users():
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save users to JSON file
def save_users(users):
    with open("users.json", "w") as file:
        json.dump(users, file)

# Load existing login data from JSON file
def load_logins():
    try:
        with open("logins.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save login data to JSON file
def save_logins(logins):
    with open("logins.json", "w") as file:
        json.dump(logins, file)

# Load existing room data from JSON file
def load_rooms():
    try:
        with open("rooms.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save room data to JSON file
def save_rooms(rooms):
    with open("rooms.json", "w") as file:
        json.dump(rooms, file)

# In-memory storage
users = load_users()
logins = load_logins()
rooms = load_rooms()

# Function to count unique logins in the past 24 hours
def count_unique_logins():
    current_time = time.time()
    unique_logins = set()
    for username, timestamp in logins.items():
        if current_time - timestamp <= 86400:  # 24 hours = 86400 seconds
            unique_logins.add(username)
    return len(unique_logins)

# Basic route
@app.route('/')
def index():
    return "Welcome to the SocketIO Server!"

# Event handler for user login
# Event handler for user login
@socketio.on('login')
def handle_login(data):
    username = data.get('username')
    password = data.get('password')
    
    print(f"Login attempt for username: {username}")  # Debug print
    print(f"Current users in system: {users}")  # Debug print
    
    try:
        # Hash the password
        hashed_password = hash_password(password)
        print(f"Hashed password: {hashed_password}")  # Debug print
        
        # Check if user exists (try both encrypted and unencrypted)
        user_found = False
        user_data = None
        
        # First try direct lookup (for testing)
        if username in users:
            user_found = True
            user_data = users[username]
        else:
            # Try encrypted lookup
            encrypted_username = cipher_suite.encrypt(username.encode()).decode()
            print(f"Encrypted username: {encrypted_username}")  # Debug print
            if encrypted_username in users:
                user_found = True
                user_data = users[encrypted_username]
        
        print(f"User found: {user_found}")  # Debug print
        if user_found:
            print(f"Stored password hash: {user_data['password']}")  # Debug print
        
        if user_found and user_data['password'] == hashed_password:
            # Record the login time
            logins[username] = time.time()
            save_logins(logins)
            
            socketio.emit('login_response', {
                'status': 'success',
                'message': 'Login successful',
                'username': username,
                'unique_logins_count': len(logins)
            })
            print(f"Login successful for {username}")  # Debug print
        else:
            socketio.emit('login_response', {
                'status': 'error',
                'message': 'Invalid username or password'
            })
            print(f"Login failed for {username}")  # Debug print
    
    except Exception as e:
        print(f"Error during login: {e}")  # Debug print
        socketio.emit('login_response', {
            'status': 'error',
            'message': f'Login error: {str(e)}'
        })

# Event handler for user registration
@socketio.on('register')
def handle_register(data):
    username = data.get('username')
    password = data.get('password')
    
    print(f"Registration attempt for username: {username}")  # Debug print
    
    try:
        # Hash password
        hashed_password = hash_password(password)
        
        # Store with unencrypted username for now (for testing)
        if username in users:
            socketio.emit('register_response', {
                'status': 'error',
                'message': 'Username already taken'
            })
            print(f"Registration failed - username taken: {username}")  # Debug print
            return
        
        # Register the user
        users[username] = {
            'password': hashed_password,
            'profile': {'bio': '', 'avatar': ''},
            'rooms': []
        }
        save_users(users)
        
        print(f"Registration successful for {username}")  # Debug print
        print(f"Updated users: {users}")  # Debug print
        
        socketio.emit('register_response', {
            'status': 'success',
            'message': 'User registered successfully'
        })
        
    except Exception as e:
        print(f"Error during registration: {e}")  # Debug print
        socketio.emit('register_response', {
            'status': 'error',
            'message': f'Registration error: {str(e)}'
        })

# Event handler for creating a room
@socketio.on('create_room')
def handle_create_room(data):
    username = data.get('username')
    room_name = data.get('room_name')
    password = data.get('password', None)

    if username not in users:
        socketio.emit('room_response', {'status': 'error', 'message': 'User not found'})
        return

    if room_name in rooms:
        socketio.emit('room_response', {'status': 'error', 'message': 'Room already exists'})
        return

    rooms[room_name] = {'password': password, 'users': [username], 'messages': []}
    users[username]['rooms'].append(room_name)
    save_users(users)
    save_rooms(rooms)

    socketio.emit('room_response', {'status': 'success', 'message': 'Room created successfully'})

# Event handler for joining a room
@socketio.on('join_room')
def handle_join_room(data):
    username = data.get('username')
    room_name = data.get('room_name')
    password = data.get('password', None)

    if username not in users:
        socketio.emit('room_response', {'status': 'error', 'message': 'User not found'})
        return

    if room_name not in rooms:
        socketio.emit('room_response', {'status': 'error', 'message': 'Room does not exist'})
        return

    room = rooms[room_name]
    
    if room['password'] and room['password'] != password:
        socketio.emit('room_response', {'status': 'error', 'message': 'Incorrect room password'})
        return

    if username in room['users']:
        socketio.emit('room_response', {'status': 'error', 'message': 'User already in room'})
        return

    room['users'].append(username)
    users[username]['rooms'].append(room_name)
    save_users(users)
    save_rooms(rooms)

    socketio.emit('room_response', {'status': 'success', 'message': 'Joined room successfully'})

# Event handler for sending messages in a room
@socketio.on('send_message')
def handle_send_message(data):
    username = data.get('username')
    room_name = data.get('room_name')
    message = data.get('message')

    if username not in users:
        socketio.emit('message_response', {'status': 'error', 'message': 'User not found'})
        return

    if room_name not in rooms:
        socketio.emit('message_response', {'status': 'error', 'message': 'Room does not exist'})
        return

    room = rooms[room_name]
    if username not in room['users']:
        socketio.emit('message_response', {'status': 'error', 'message': 'User not in room'})
        return

    # Store the message
    room['messages'].append({'username': username, 'message': message})
    save_rooms(rooms)

    # Broadcast the message to all users
    socketio.emit('chat_message', {
        'username': username,
        'message': message,
        'room': room_name
    })
    
    socketio.emit('message_response', {'status': 'success', 'message': 'Message sent successfully'})

# Event handler for updating the user profile (bio and avatar)
@socketio.on('update_profile')
def handle_update_profile(data):
    username = data.get('username')
    bio = data.get('bio', '')
    avatar = data.get('avatar', '')  # Avatar URL passed by the user

    # Encrypt the username
    encrypted_username = cipher_suite.encrypt(username.encode()).decode()

    if encrypted_username not in users:
        socketio.emit('profile_update', {'status': 'error', 'message': 'User not found'})
        return

    # Update the profile with bio and avatar URL
    users[encrypted_username]['profile'] = {'bio': bio, 'avatar': avatar}
    save_users(users)

    socketio.emit('profile_update', {'status': 'success', 'message': 'Profile updated successfully'})

# Run the app
if __name__ == '__main__':
    socketio.run(app, debug=True)
