from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

users_file = 'userserverinfo.json'
rooms_file = 'rooms.json'

# Load user data
with open(users_file, 'r') as f:
    user_data = json.load(f)
users = {user['username']: user for user in user_data['users']}

# Load or initialize rooms data
if os.path.exists(rooms_file):
    with open(rooms_file, 'r') as f:
        rooms = json.load(f)
else:
    rooms = {}

# Save rooms data to file
def save_rooms():
    with open(rooms_file, 'w') as f:
        json.dump(rooms, f)

@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.json['room_name']
    if room_name not in rooms:
        rooms[room_name] = {'messages': [], 'users': []}
        save_rooms()
        return jsonify({'message': 'Room created successfully'}), 201
    else:
        return jsonify({'message': 'Room already exists'}), 400

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    return jsonify(list(rooms.keys()))

@app.route('/join_room', methods=['POST'])
def join_room():
    username = request.json['username']
    room_name = request.json['room_name']
    if room_name in rooms and username in users:
        if username not in rooms[room_name]['users']:
            rooms[room_name]['users'].append(username)
            save_rooms()
        return jsonify({'message': 'Joined room successfully'}), 200
    else:
        return jsonify({'message': 'Room or user not found'}), 400

@app.route('/send_message', methods=['POST'])
def send_message():
    username = request.json['username']
    room_name = request.json['room_name']
    message = request.json['message']
    if room_name in rooms and username in users:
        message_id = len(rooms[room_name]['messages']) + 1
        rooms[room_name]['messages'].append({
            'message_id': message_id,
            'username': username,
            'message': message
        })
        save_rooms()
        return jsonify({'message': 'Message sent successfully'}), 200
    else:
        return jsonify({'message': 'Room or user not found'}), 400

@app.route('/get_users_in_room', methods=['GET'])
def get_users_in_room():
    room_name = request.args.get('room_name')
    if room_name in rooms:
        return jsonify(rooms[room_name]['users'])
    else:
        return jsonify([]), 400

@app.route('/get_messages', methods=['GET'])
def get_messages():
    room_name = request.args.get('room_name')
    last_message_id = int(request.args.get('last_message_id', 0))
    if room_name in rooms:
        new_messages = [msg for msg in rooms[room_name]['messages'] if msg['message_id'] > last_message_id]
        return jsonify(new_messages)
    else:
        return jsonify([]), 400

if __name__ == '__main__':
    app.run(debug=True)
