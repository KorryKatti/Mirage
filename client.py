import tkinter as tk
from tkinter import scrolledtext, simpledialog
import requests
import json
import os
import random

# Load user info from JSON file
with open('userinfo.json', 'r') as file:
    user_info = json.load(file)

username = user_info['username']
email = user_info['email']
secret_key = user_info['secret_key']

# Server URL
server_url = 'http://127.0.0.1:5000'

current_room = None

# Create rooms directory if it doesn't exist
if not os.path.exists('rooms'):
    os.makedirs('rooms')

# Function to save a message to a room file
def save_message_to_file(room_name, message):
    with open(f'rooms/{room_name}.txt', 'a') as file:
        file.write(f'{message}\n')

# Function to generate a color based on the username
def generate_user_color(username):
    random.seed(username)
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

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
            user_color = generate_user_color(username)
            formatted_message = f'{username}: {message}'
            chat_text.insert(tk.END, f'{formatted_message}\n', ('username',))
            chat_text.tag_config('username', foreground=user_color)
            chat_text.config(state=tk.DISABLED)
            save_message_to_file(current_room, formatted_message)
        else:
            print(f"Error sending message: {response.json()['message']}")
    elif message:
        chat_text.config(state=tk.NORMAL)
        formatted_message = f'{username} (self): {message}'
        chat_text.insert(tk.END, f'{formatted_message}\n', ('username',))
        user_color = generate_user_color(username)
        chat_text.tag_config('username', foreground=user_color)
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
            room_button = tk.Button(rooms_canvas_frame, text=room, command=lambda r=room: select_room(r), bg='#444', fg='white', relief='flat', bd=0)
            room_button.pack(fill=tk.X, pady=2)

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
        # Start checking for new messages
        check_for_new_messages()
    else:
        print(f"Error joining room: {response.json()['message']}")

# Function to leave a room
def leave_room():
    global current_room
    if current_room:
        response = requests.post(f'{server_url}/leave_room', json={
            'username': username,
            'room_name': current_room
        })
        if response.status_code == 200:
            current_room = None
            room_label.config(text="Select a room or talk to yourself")
            chat_text.config(state=tk.NORMAL)
            chat_text.delete(1.0, tk.END)
            chat_text.config(state=tk.DISABLED)
            user_list.delete(0, tk.END)
        else:
            print(f"Error leaving room: {response.json()['message']}")

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
                user, message = line.split(': ', 1)
                user_color = generate_user_color(user)
                chat_text.insert(tk.END, f'{line}', ('username',))
                chat_text.tag_config('username', foreground=user_color)
    except FileNotFoundError:
        pass
    chat_text.config(state=tk.DISABLED)

# Function to check for new messages periodically
def check_for_new_messages():
    global current_room
    if current_room:
        try:
            with open(f'rooms/{current_room}.txt', 'r') as file:
                chat_history = file.readlines()
                chat_text.config(state=tk.NORMAL)
                chat_text.delete(1.0, tk.END)
                for line in chat_history:
                    user, message = line.split(': ', 1)
                    user_color = generate_user_color(user)
                    chat_text.insert(tk.END, f'{line}', ('username',))
                    chat_text.tag_config('username', foreground=user_color)
                chat_text.config(state=tk.DISABLED)
        except FileNotFoundError:
            pass
    # Schedule this function to run again after 2 seconds (2000 milliseconds)
    root.after(2000, check_for_new_messages)

# Function to create a new room
def create_room():
    room_name = simpledialog.askstring("Create Room", "Enter room name:")
    if room_name:
        response = requests.post(f'{server_url}/create_room', json={'room_name': room_name})
        if response.status_code == 201:
            load_rooms()
        else:
            print(f"Error creating room: {response.json()['message']}")

# Function to style buttons
def style_button(button):
    button.configure(
        bg='#555',
        fg='white',
        activebackground='#666',
        activeforeground='white',
        relief='flat',
        bd=0,
        padx=10,
        pady=5
    )

# Create the main window
root = tk.Tk()
root.title("Mirage Chat")
root.geometry("800x600")

# Create the chat frame
chat_frame = tk.Frame(root)
chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create the chat text widget
chat_text = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, wrap=tk.WORD, bg='#333', fg='white', insertbackground='white')
chat_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Create the chat message entry
chat_message_entry = tk.Entry(chat_frame, bg='#444', fg='white', insertbackground='white')
chat_message_entry.pack(padx=10, pady=10, fill=tk.X)

# Create the send button
send_button = tk.Button(chat_frame, text="Send", command=send_chat_message)
send_button.pack(padx=10, pady=5, side=tk.LEFT)
style_button(send_button)

# Create the leave room button
leave_room_button = tk.Button(chat_frame, text="Leave Room", command=leave_room)
leave_room_button.pack(padx=10, pady=5, side=tk.RIGHT)
style_button(leave_room_button)

# Create the rooms frame
rooms_frame = tk.Frame(root, width=200, bg='#222')
rooms_frame.pack(side=tk.LEFT, fill=tk.Y)

# Create the room label
room_label = tk.Label(rooms_frame, text="Select a room or talk to yourself", bg='#222', fg='white', padx=10, pady=5)
room_label.pack(fill=tk.X)

# Create the create room button
create_room_button = tk.Button(rooms_frame, text="Create Room", command=create_room)
create_room_button.pack(fill=tk.X, pady=5)
style_button(create_room_button)

# Create the rooms canvas and frame
rooms_canvas = tk.Canvas(rooms_frame, bg='#222', bd=0, highlightthickness=0)
rooms_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
rooms_scrollbar = tk.Scrollbar(rooms_frame, orient=tk.VERTICAL, command=rooms_canvas.yview)
rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
rooms_canvas_frame = tk.Frame(rooms_canvas, bg='#222')
rooms_canvas.create_window((0, 0), window=rooms_canvas_frame, anchor='nw')
rooms_canvas.configure(yscrollcommand=rooms_scrollbar.set)

# Create the users list box
user_list = tk.Listbox(root, bg='#333', fg='white', bd=0)
user_list.pack(side=tk.RIGHT, fill=tk.Y)

# Load rooms when the app starts
load_rooms()

# Start the Tkinter main loop
root.mainloop()