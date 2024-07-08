from flask import Flask, request, jsonify
import json
import os
from collections import defaultdict

app = Flask(__name__)

# Initialize rooms and user info files if they don't exist
rooms_file = 'rooms.json'
users_file = 'userserverinfo.json'

if not os.path.exists(rooms_file):
    with open(rooms_file, 'w') as f:
        json.dump({}, f)

# Function to load rooms from JSON file
def load_rooms():
    with open(rooms_file, 'r') as f:
        return json.load(f)

# Function to save rooms to JSON file
def save_rooms(rooms):
    with open(rooms_file, 'w') as f:
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

# Dictionary to store messages for each room
messages = defaultdict(list)
message_counter = defaultdict(int)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    username = data.get('username')
    room_name = data.get('room_name')
    message = data.get('message')

    if username and room_name and message:
        # Store the message with a unique ID
        message_id = message_counter[room_name]
        messages[room_name].append({'id': message_id, 'username': username, 'message': message})
        message_counter[room_name] += 1
        return jsonify({'message': 'Message sent successfully'}), 200
    else:
        return jsonify({'message': 'Missing username, room_name, or message'}), 400

@app.route('/get_new_messages', methods=['GET'])
def get_new_messages():
    room_name = request.args.get('room_name')
    last_message_id = int(request.args.get('last_message_id', -1))
    if room_name in messages:
        # Retrieve messages with IDs greater than last_message_id
        room_messages = [msg for msg in messages[room_name] if msg['id'] > last_message_id]
        return jsonify(room_messages), 200
    else:
        return jsonify([]), 200

if __name__ == '__main__':
    app.run(debug=True)
