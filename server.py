# server.py

from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Initialize rooms and user info files if they don't exist
if not os.path.exists('rooms.json'):
    with open('rooms.json', 'w') as f:
        json.dump({}, f)

if not os.path.exists('userserverinfo.json'):
    with open('userserverinfo.json', 'w') as f:
        json.dump({"users": []}, f)

# Function to load rooms from JSON file
def load_rooms():
    with open('rooms.json', 'r') as f:
        return json.load(f)

# Function to save rooms to JSON file
def save_rooms(rooms):
    with open('rooms.json', 'w') as f:
        json.dump(rooms, f)

# Function to get users in a room
def get_users_in_room(room_name):
    rooms = load_rooms()
    return rooms.get(room_name, [])

# Function to join a room
def join_room(username, room_name):
    rooms = load_rooms()
    if room_name in rooms and username not in rooms[room_name]:
        rooms[room_name].append(username)
        save_rooms(rooms)

# Function to leave a room
def leave_room(username, room_name):
    rooms = load_rooms()
    if room_name in rooms and username in rooms[room_name]:
        rooms[room_name].remove(username)
        save_rooms(rooms)

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    rooms = load_rooms()
    return jsonify(list(rooms.keys()))

@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.json.get('room_name')
    if not room_name:
        return jsonify({"error": "Room name not provided"}), 400
    
    rooms = load_rooms()
    if room_name in rooms:
        return jsonify({"error": "Room already exists"}), 400
    
    rooms[room_name] = []
    save_rooms(rooms)
    return jsonify({"message": "Room created"}), 201

@app.route('/join_room', methods=['POST'])
def join_room_route():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    if not username or not room_name:
        return jsonify({"error": "Username or room name not provided"}), 400
    
    join_room(username, room_name)
    return jsonify({"message": "Joined room"}), 200

@app.route('/leave_room', methods=['POST'])
def leave_room_route():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    if not username or not room_name:
        return jsonify({"error": "Username or room name not provided"}), 400
    
    leave_room(username, room_name)
    return jsonify({"message": "Left room"}), 200

@app.route('/get_users_in_room', methods=['GET'])
def get_users_in_room_route():
    room_name = request.args.get('room_name')
    if not room_name:
        return jsonify({"error": "Room name not provided"}), 400
    
    users = get_users_in_room(room_name)
    return jsonify(users)

@app.route('/send_message', methods=['POST'])
def send_message():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    message = request.json.get('message')
    
    if not username or not room_name or not message:
        return jsonify({"error": "Username, room name, or message not provided"}), 400
    
    # Broadcast message to all clients in the room
    rooms = load_rooms()
    if room_name in rooms:
        for user in rooms[room_name]:
            # Assuming each user has a unique identifier (like username)
            # Send message to the user (you can use WebSocket for real-time updates)
            print(f"Sending message to {user}: {message}")
            # Example: send_message_to_client(user, message)
    
    return jsonify({"message": "Message sent"}), 200

if __name__ == '__main__':
    app.run(debug=True)
