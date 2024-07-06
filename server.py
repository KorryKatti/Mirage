from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# File paths
USER_INFO_FILE = 'userserverinfo.json'
ROOMS_FOLDER = 'rooms'

# Initialize server state
users = {}
rooms = {}

# Helper functions
def load_user_info():
    global users
    if os.path.exists(USER_INFO_FILE):
        with open(USER_INFO_FILE, 'r') as f:
            users = json.load(f)

def save_user_info():
    with open(USER_INFO_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def save_room_data():
    for room_name, room_data in rooms.items():
        room_file = os.path.join(ROOMS_FOLDER, f"{room_name}.json")
        os.makedirs(os.path.dirname(room_file), exist_ok=True)
        with open(room_file, 'w') as f:
            json.dump(room_data, f, indent=4)

def load_rooms():
    global rooms
    if not os.path.exists(ROOMS_FOLDER):
        os.makedirs(ROOMS_FOLDER)
    for filename in os.listdir(ROOMS_FOLDER):
        if filename.endswith('.json'):
            room_name = filename[:-5]
            with open(os.path.join(ROOMS_FOLDER, filename), 'r') as f:
                rooms[room_name] = json.load(f)

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    return jsonify(list(rooms.keys()))

@app.route('/join_room', methods=['POST'])
def join_room():
    global users, rooms

    data = request.json
    username = data.get('username')
    room_name = data.get('room_name')

    if username in users and room_name in rooms:
        if username not in rooms[room_name]['users']:
            rooms[room_name]['users'].append(username)
            save_room_data()
            return jsonify({"message": f"User '{username}' joined room '{room_name}'"}), 200
        else:
            return jsonify({"message": f"User '{username}' is already in room '{room_name}'"}), 400
    else:
        return jsonify({"message": "Room or user not found"}), 404

@app.route('/send_message', methods=['POST'])
def send_message():
    global rooms

    data = request.json
    username = data.get('username')
    room_name = data.get('room_name')
    message = data.get('message')

    if username and room_name and message:
        if room_name in rooms:
            rooms[room_name]['messages'].append({"username": username, "message": message})
            save_room_data()
            return jsonify({"message": "Message sent successfully"}), 200
        else:
            return jsonify({"message": "Room not found"}), 404
    else:
        return jsonify({"message": "Invalid request parameters"}), 400

if __name__ == '__main__':
    load_user_info()
    load_rooms()
    app.run(debug=True)
