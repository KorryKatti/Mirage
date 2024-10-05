import os
import json
from datetime import datetime, timedelta
from collections import defaultdict
import socketio
import eventlet

sio = socketio.Server()
app = socketio.WSGIApp(sio)

rooms_file = 'rooms.json'
stats_file = 'stats.json'
users_file = 'userinfo.json'

pings = []

if not os.path.exists(rooms_file):
    with open(rooms_file, 'w') as f:
        json.dump({}, f)
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump({'today': 0, 'total': 0}, f)

def load_rooms():
    with open(rooms_file, 'r') as f:
        return json.load(f)

def load_stats() -> dict:
    with open(stats_file, 'r') as f:
        return json.load(f)

def save_rooms(rooms):
    with open(rooms_file, 'w') as f:
        json.dump(rooms, f)

def save_stats(stats):
    with open(stats_file, 'w') as f:
        json.dump(stats, f)

def get_username():
    with open(users_file, 'r') as f:
        user_info = json.load(f)
        return user_info['username']

def get_users_in_room(room_name):
    rooms = load_rooms()
    return rooms.get(room_name, [])

def join_room(username, room_name):
    rooms = load_rooms()
    if room_name in rooms and username not in rooms[room_name]:
        rooms[room_name].append(username)
        save_rooms(rooms)

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
    review_stats()
    stats = load_stats()

    if any(ping.get('username') == username for ping in pings):
        pass
    else:
        stats['today'] = stats.get('today', 0) + 1
        stats['total'] = stats.get('total', 0) + 1
        pings.append({'username': username, 'timestamp': datetime.now()})
        save_stats(stats)

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
            break

    if expired_count > 0:
        stats['today'] = max(stats.get('today', 0) - expired_count, 0)
        save_stats(stats)

messages = defaultdict(list)
message_counter = defaultdict(int)

@sio.event
def connect(sid, environ):
    pass

@sio.event
def disconnect(sid):
    pass

@sio.event
def get_rooms(sid):
    rooms = load_rooms()
    username = get_username()
    user_rooms = {room_id: users for room_id, users in rooms.items() if username in users}
    sio.emit('room_list', list(user_rooms.keys()), room=sid)

@sio.event
def create_room(sid, data):
    room_name = data.get('room_name')
    if not room_name:
        sio.emit('error', {'error': 'Room name not provided'}, room=sid)
        return

    rooms = load_rooms()
    if room_name in rooms:
        sio.emit('error', {'error': 'Room already exists'}, room=sid)
        return

    username = data.get('username')
    rooms[room_name] = [username]
    save_rooms(rooms)
    sio.emit('room_created', {'message': 'Room created'}, room=sid)

@sio.event
def join_room_route(sid, data):
    username = data.get('username')
    room_name = data.get('room_name')
    if not username or not room_name:
        sio.emit('error', {'error': 'Username or room name not provided'}, room=sid)
        return

    join_room(username, room_name)
    sio.emit('joined_room', {'message': 'Joined room'}, room=sid)

@sio.event
def leave_room_route(sid, data):
    username = data.get('username')
    room_name = data.get('room_name')
    if not username or not room_name:
        sio.emit('error', {'error': 'Username or room name not provided'}, room=sid)
        return

    leave_room(username, room_name)
    sio.emit('left_room', {'message': 'Left room'}, room=sid)

@sio.event
def get_users_in_room_route(sid, data):
    room_name = data.get('room_name')
    if not room_name:
        sio.emit('error', {'error': 'Room name not provided'}, room=sid)
        return

    users = get_users_in_room(room_name)
    sio.emit('room_users', users, room=sid)

@sio.event
def send_message(sid, data):
    username = data.get('username')
    room_name = data.get('room_name')
    message = data.get('message')

    increment_stats(username=username)

    if username and room_name and message:
        message_id = message_counter[room_name]
        timestamp = datetime.now().isoformat()

        messages[room_name].append({'id': message_id, 'username': username, 'message': message, 'timestamp': timestamp})
        message_counter[room_name] += 1

        delete_old_messages(messages, room_name)
        sio.emit('message_sent', {'message': 'Message sent successfully'}, room=sid)
    else:
        sio.emit('error', {'error': 'Missing username, room_name, or message'}, room=sid)

@sio.event
def get_new_messages(sid, data):
    room_name = data.get('room_name')
    last_message_id = int(data.get('last_message_id', -1))
    if room_name in messages:
        room_messages = [msg for msg in messages[room_name] if msg['id'] > last_message_id]
        sio.emit('new_messages', room_messages, room=sid)
    else:
        sio.emit('new_messages', [], room=sid)

@sio.event
def get_all_messages(sid, data):
    room_name = data.get('room_name')
    if room_name in messages:
        sio.emit('all_messages', messages[room_name], room=sid)
    else:
        sio.emit('all_messages', [], room=sid)

@sio.event
def get_metrics(sid):
    review_stats()
    sio.emit('metrics', load_stats(), room=sid)

# Start the server with host and port number
if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
