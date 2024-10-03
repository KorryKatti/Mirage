from flask import Flask, request, jsonify
from collections import defaultdict
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# File paths
rooms_file = 'rooms.json'
stats_file = 'stats.json'
users_file = 'userinfo.json'

pings = []

# Initialize rooms and stats files if don't exist
if not os.path.exists(rooms_file):
    with open(rooms_file, 'w') as f:
        json.dump({}, f)
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump({'today': 0, 'total': 0}, f)

# Load rooms from JSON file
def load_rooms():
    with open(rooms_file, 'r') as f:
        return json.load(f)

# Load stats from JSON file
def load_stats() -> dict:
    with open(stats_file, 'r') as f:
        return json.load(f)

# Save rooms to JSON file
def save_rooms(rooms):
    with open(rooms_file, 'w') as f:
        json.dump(rooms, f)

# Save stats to JSON file
def save_stats(stats):
    with open(stats_file, 'w') as f:
        json.dump(stats, f)

def get_username():
    with open(users_file, 'r') as f:
        user_info = json.load(f)
        return user_info['username']
# Function to get users in a room
def get_users_in_room(room_name):
    rooms = load_rooms()
    return rooms.get(room_name, [])

# Function to add user to a room
def join_room(username, room_name):
    rooms = load_rooms()
    if room_name in rooms and username not in rooms[room_name]:
        rooms[room_name].append(username)
        save_rooms(rooms)

# Function to remove user from a room
def leave_room(username, room_name):
    rooms = load_rooms()
    if room_name in rooms and username in rooms[room_name]:
        rooms[room_name].remove(username)
        save_rooms(rooms)

def delete_old_messages(messages, room_name):
    time_to_delete = datetime.now() - timedelta(hours=1)
    messages[room_name] = [
        msg for msg in messages[room_name]
        if isinstance(msg['timestamp'], datetime) and msg['timestamp'] > time_to_delete or
           isinstance(msg['timestamp'], str) and datetime.fromisoformat(msg['timestamp']) > time_to_delete
    ]

def increment_stats(username: str):
    """
    Updates today and total counts if the user did not made a request in last 24.5 hours.
    """
    review_stats()
    stats = load_stats()

    if any(ping.get('username') == username for ping in pings):
        pass
    else:
        stats['today'] = stats.get('today', 0) + 1
        stats['total'] = stats.get('total', 0) + 1
        pings.append({'username': username, 'timestamp': datetime.now()})
        save_stats(stats)

# Function to update statistics
def review_stats():
    stats = load_stats()
    threshold = timedelta(hours=24, minutes=30)

    expired_count = 0
    current_time = datetime.now()

    for i, ping in enumerate(pings):
        if current_time - ping.get('timestamp') > threshold:
            expired_count += 1
            del pings[i]
        else:
            break  # Stop iterating if a non-expired ping is found

    if expired_count > 0:
        stats['today'] = max(stats.get('today', 0) - expired_count, 0)
        save_stats(stats)

# Route to get all rooms
@app.route('/get_rooms', methods=['GET'])
def get_rooms(): #only returns room of the specefic user
    rooms = load_rooms()
    username = get_username()
    user_rooms = {room_id: users for room_id, users in rooms.items() if username in users}
    return jsonify(list(user_rooms.keys()))

# Route to create a new room
@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.json.get('room_name')
    if not room_name:
        return jsonify({"error": "Room name not provided"}), 400

    rooms = load_rooms()
    if room_name in rooms:
        return jsonify({"error": "Room already exists"}), 400

    username = request.json.get('username') #add the current loggedin username to the cretaed room
    rooms[room_name] = [username]

    save_rooms(rooms)
    return jsonify({"message": "Room created"}), 201

# Route to join a room
@app.route('/join_room', methods=['POST'])
def join_room_route():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    if not username or not room_name:
        return jsonify({"error": "Username or room name not provided"}), 400

    join_room(username, room_name)
    return jsonify({"message": "Joined room"}), 200

# Route to leave a room
@app.route('/leave_room', methods=['POST'])
def leave_room_route():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    if not username or not room_name:
        return jsonify({"error": "Username or room name not provided"}), 400

    leave_room(username, room_name)
    return jsonify({"message": "Left room"}), 200

# Route to get users in a specific room
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

# Route to send a message to a room
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    username = data.get('username')
    room_name = data.get('room_name')
    message = data.get('message')

    increment_stats(username=username)

    if username and room_name and message:
        # Store the message with a unique ID
        message_id = message_counter[room_name]
        timestamp = datetime.now().isoformat()

        messages[room_name].append({'id': message_id, 'username': username, 'message': message, 'timestamp': timestamp})
        message_counter[room_name] += 1
        
        delete_old_messages(messages, room_name) # Delete old messages
        return jsonify({'message': 'Message sent successfully'}), 200
    else:
        return jsonify({'error': 'Missing username, room_name, or message'}), 400

# Route to get new messages since a given message ID
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



@app.route('/get_all_messages', methods=['GET'])
def get_all_messages():
    room_name = request.args.get('room_name')
    if room_name in messages:
        return jsonify(messages[room_name]), 200
    return jsonify([]), 200

if __name__ == '__main__':
    app.run(debug=True)

# Route to get statistics of the service
@app.route('/metrics', methods=['GET'])
def get_metrics():
    review_stats()

    return jsonify(load_stats()), 200
