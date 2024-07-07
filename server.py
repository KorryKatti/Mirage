from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

if not os.path.exists('rooms.json'):
    with open('rooms.json', 'w') as f:
        json.dump({}, f)

if not os.path.exists('userserverinfo.json'):
    with open('userserverinfo.json', 'w') as f:
        json.dump({"users": []}, f)

@app.route('/get_rooms', methods=['GET'])
def get_rooms():
    with open('rooms.json', 'r') as f:
        rooms = json.load(f)
    return jsonify(list(rooms.keys()))

@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.json.get('room_name')
    with open('rooms.json', 'r+') as f:
        rooms = json.load(f)
        if room_name not in rooms:
            rooms[room_name] = []
            f.seek(0)
            json.dump(rooms, f)
            f.truncate()
    return jsonify({"message": "Room created"}), 201

@app.route('/join_room', methods=['POST'])
def join_room():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    with open('rooms.json', 'r+') as f:
        rooms = json.load(f)
        if room_name in rooms and username not in rooms[room_name]:
            rooms[room_name].append(username)
            f.seek(0)
            json.dump(rooms, f)
            f.truncate()
    return jsonify({"message": "Joined room"}), 200

@app.route('/leave_room', methods=['POST'])
def leave_room():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    with open('rooms.json', 'r+') as f:
        rooms = json.load(f)
        if room_name in rooms and username in rooms[room_name]:
            rooms[room_name].remove(username)
            f.seek(0)
            json.dump(rooms, f)
            f.truncate()
    return jsonify({"message": "Left room"}), 200

@app.route('/get_users_in_room', methods=['GET'])
def get_users_in_room():
    room_name = request.args.get('room_name')
    with open('rooms.json', 'r') as f:
        rooms = json.load(f)
    return jsonify(rooms.get(room_name, []))

@app.route('/send_message', methods=['POST'])
def send_message():
    username = request.json.get('username')
    room_name = request.json.get('room_name')
    message = request.json.get('message')
    print(f"Message from {username} in {room_name}: {message}")
    return jsonify({"message": "Message sent"}), 200

if __name__ == '__main__':
    app.run(debug=True)
