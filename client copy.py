import tkinter as tk
from tkinter import scrolledtext, simpledialog
import requests
import json
import os

# Load user info from JSON file
with open('userinfoo.json', 'r') as file:
    user_info = json.load(file)

username = user_info['username']
email = user_info['email']
secret_key = user_info['secret_key']

# Server URL
server_url = 'http://127.0.0.1:5000'

current_room = None
last_message_id = 0

# Create rooms directory if it doesn't exist
if not os.path.exists('rooms'):
    os.makedirs('rooms')

# Function to save a message to a room file
def save_message_to_file(room_name, message):
    with open(f'rooms/{room_name}.txt', 'a') as file:
        file.write(f'{message}\n')

# Function to send a chat message
def send_chat_message():
    global current_room
    message = chat_message_entry.get()
    if current_room and message:
        response = requests.post(f'{server_url}/send_message', json={
            'username': username,
            'room_name': current_room,
            'message': message
        })
        if response.status_code == 200:
            chat_message_entry.delete(0, tk.END)
            chat_text.config(state=tk.NORMAL)
            formatted_message = f'{username}: {message}'
            chat_text.insert(tk.END, f'{formatted_message}\n')
            chat_text.config(state=tk.DISABLED)
            save_message_to_file(current_room, formatted_message)
        else:
            print(f"Error sending message: {response.json()['message']}")
    elif message:
        chat_text.config(state=tk.NORMAL)
        formatted_message = f'{username} (self): {message}'
        chat_text.insert(tk.END, f'{formatted_message}\n')
        chat_text.config(state=tk.DISABLED)
        chat_message_entry.delete(0, tk.END)

# Function to load rooms from server
def load_rooms():
    for widget in rooms_canvas_frame.winfo_children():
        widget.destroy()
    response = requests.get(f'{server_url}/get_rooms')
    if response.status_code == 200:
        rooms = response.json()
        for room in rooms:
            room_button = tk.Button(rooms_canvas_frame, text=room, command=lambda r=room: select_room(r))
            room_button.pack(fill=tk.X)

# Function to select a room
def select_room(room_name):
    global current_room
    current_room = room_name
    room_label.config(text=f'Current Room: {room_name}')
    response = requests.post(f'{server_url}/join_room', json={
        'username': username,
        'room_name': room_name
    })
    if response.status_code == 200:
        load_users_in_room(room_name)
        load_chat_history(room_name)
        poll_messages()
    else:
        print(f"Error joining room: {response.json()['message']}")

# Function to load users in a room
def load_users_in_room(room_name):
    response = requests.get(f'{server_url}/get_users_in_room', params={'room_name': room_name})
    if response.status_code == 200:
        users = response.json()
        user_list.delete(0, tk.END)
        for user in users:
            user_list.insert(tk.END, user)

# Function to load chat history from a room file
def load_chat_history(room_name):
    chat_text.config(state=tk.NORMAL)
    chat_text.delete(1.0, tk.END)
    try:
        with open(f'rooms/{room_name}.txt', 'r') as file:
            chat_history = file.readlines()
            for line in chat_history:
                chat_text.insert(tk.END, line)
    except FileNotFoundError:
        pass
    chat_text.config(state=tk.DISABLED)

# Function to create a new room
def create_room():
    room_name = simpledialog.askstring("Create Room", "Enter room name:")
    if room_name:
        response = requests.post(f'{server_url}/create_room', json={'room_name': room_name})
        if response.status_code == 201:
            load_rooms()
        else:
            print(f"Error creating room: {response.json()['message']}")

# Function to poll for new messages
def poll_messages():
    global last_message_id
    if current_room:
        response = requests.get(f'{server_url}/get_messages', params={
            'room_name': current_room,
            'last_message_id': last_message_id
        })
        if response.status_code == 200:
            messages = response.json()
            if messages:
                chat_text.config(state=tk.NORMAL)
                for message in messages:
                    chat_text.insert(tk.END, f"{message['username']}: {message['message']}\n")
                    save_message_to_file(current_room, f"{message['username']}: {message['message']}")
                    last_message_id = message['message_id']
                chat_text.config(state=tk.DISABLED)
        root.after(2000, poll_messages)  # Poll every 2 seconds

# Initialize Tkinter window
root = tk.Tk()
root.title("Chat Application")

# Frame for room selection
rooms_frame = tk.Frame(root, bg='#333')
rooms_frame.pack(side=tk.LEFT, fill=tk.Y)

# Canvas for scrollable room list
rooms_canvas = tk.Canvas(rooms_frame, bg='#333')
rooms_canvas.pack(side=tk.LEFT, fill=tk.Y)

# Scrollbar for room selection
rooms_scrollbar = tk.Scrollbar(rooms_frame, orient=tk.VERTICAL, command=rooms_canvas.yview)
rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Configure canvas
rooms_canvas.config(yscrollcommand=rooms_scrollbar.set)
rooms_canvas.bind('<Configure>', lambda e: rooms_canvas.config(scrollregion=rooms_canvas.bbox("all")))

# Frame inside canvas for room buttons
rooms_canvas_frame = tk.Frame(rooms_canvas, bg='#333')
rooms_canvas.create_window((0, 0), window=rooms_canvas_frame, anchor='nw')

# Button for creating a new room
create_room_button = tk.Button(rooms_frame, text="Create Room", command=create_room)
create_room_button.pack(fill=tk.X)

# Frame for chat messages and input
chat_frame = tk.Frame(root, bg='#444')
chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Label for current room
room_label = tk.Label(chat_frame, text="Select a room or talk to yourself", bg='#444', fg='white')
room_label.pack()

# Text widget for chat messages
chat_text = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, bg='#222', fg='white', wrap=tk.WORD)
chat_text.pack(fill=tk.BOTH, expand=True)

# Entry widget for chat message input
chat_message_entry = tk.Entry(chat_frame, bg='#333', fg='white')
chat_message_entry.pack(fill=tk.X, pady=5)

# Send message button
send_button = tk.Button(chat_frame, text="Send", command=send_chat_message)
send_button.pack(pady=5)

# Button for talking to yourself
talk_to_yourself_button = tk.Button(chat_frame, text="Talk to Yourself", command=send_chat_message)
talk_to_yourself_button.pack(pady=5)

# Frame for user list
user_list_frame = tk.Frame(root, bg='#333')
user_list_frame.pack(side=tk.RIGHT, fill=tk.Y)

# Listbox for user list
user_list = tk.Listbox(user_list_frame, bg='#222', fg='white')
user_list.pack(fill=tk.BOTH, expand=True)

# Load rooms when starting the client
load_rooms()

# Start the Tkinter event loop
root.mainloop()
