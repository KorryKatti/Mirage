import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from ttkbootstrap import Style
import requests
import json
import os
import random

# Initialize ttkbootstrap
style = Style(theme='cyborg')  # Choose 'cyborg' theme for retro neon look

# Load user info from JSON file
with open('userinfo.json', 'r') as file:
    user_info = json.load(file)

username = user_info['username']
email = user_info['email']
secret_key = user_info['secret_key']

# Server URL
server_url = 'http://127.0.0.1:5000'

current_room = None
last_message_id = -1

# Create messages directory if it doesn't exist
if not os.path.exists('messages'):
    os.makedirs('messages')

# Function to save a message to a room file
def save_message_to_file(room_name, message):
    with open(f'messages/{room_name}.txt', 'a') as file:
        file.write(f'{message}\n')

# Function to generate a color based on the username
def generate_user_color(username):
    random.seed(username)
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

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
        else:
            messagebox.showerror("Error", f"Error sending message: {response.json().get('message', 'Unknown error')}")
    elif message:
        messagebox.showerror("Error", "Select a room first.")

# Function to load rooms from server
# Function to load rooms from server
def load_rooms():
    for widget in rooms_canvas_frame.winfo_children():
        widget.destroy()
    response = requests.get(f'{server_url}/get_rooms')
    if response.status_code == 200:
        rooms = response.json()
        for room in rooms:
            room_button = tk.Button(rooms_canvas_frame, text=room, command=lambda r=room: select_room(r), bg='blue', fg='white')
            room_button.pack(fill=tk.X, pady=2)


# Function to select a room
def select_room(room_name):
    global current_room, last_message_id
    current_room = room_name
    last_message_id = -1
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
        messagebox.showerror("Error", f"Error joining room: {response.json().get('message', 'Unknown error')}")

# Function to leave a room
def leave_room():
    global current_room, last_message_id
    if current_room:
        response = requests.post(f'{server_url}/leave_room', json={
            'username': username,
            'room_name': current_room
        })
        if response.status_code == 200:
            current_room = None
            last_message_id = -1
            room_label.config(text="Select a room or talk to yourself")
            chat_text.config(state=tk.NORMAL)
            chat_text.delete(1.0, tk.END)
            chat_text.config(state=tk.DISABLED)
            user_list.delete(0, tk.END)
        else:
            messagebox.showerror("Error", f"Error leaving room: {response.json().get('message', 'Unknown error')}")

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
        with open(f'messages/{room_name}.txt', 'r') as file:
            chat_history = file.read()
            chat_text.insert(tk.END, chat_history)
    except FileNotFoundError:
        pass
    chat_text.config(state=tk.DISABLED)

# Function to check for new messages
def check_for_new_messages():
    global last_message_id
    if current_room:
        response = requests.get(f'{server_url}/get_new_messages', params={
            'room_name': current_room,
            'last_message_id': last_message_id
        })
        if response.status_code == 200:
            new_messages = response.json()
            if new_messages:
                chat_text.config(state=tk.NORMAL)
                for msg in new_messages:
                    formatted_message = f"{msg['username']}: {msg['message']}"
                    save_message_to_file(current_room, formatted_message)
                    user_color = generate_user_color(msg['username'])
                    chat_text.insert(tk.END, f'{formatted_message}\n', ('username',))
                    chat_text.tag_config('username', foreground=user_color)
                    last_message_id = msg['id']
                chat_text.config(state=tk.DISABLED)
                chat_text.see(tk.END)
        root.after(1700, check_for_new_messages)

# Function to periodically refresh the user list
def refresh_user_list():
    if current_room:
        load_users_in_room(current_room)
    root.after(2000, refresh_user_list)

# Function to create a new room
def create_new_room():
    new_room_name = simpledialog.askstring("Create New Room", "Enter the name for the new room:")
    if new_room_name:
        response = requests.post(f'{server_url}/create_room', json={
            'username': username,
            'room_name': new_room_name
        })
        if response.status_code == 200:
            messagebox.showinfo("Success", f"Room '{new_room_name}' created.")
            # Add the new room button directly to the GUI
            room_button = tk.Button(rooms_canvas_frame, text=new_room_name, command=lambda r=new_room_name: select_room(r), style='primary.TButton')
            room_button.pack(fill=tk.X, pady=2)
            # Refresh the rooms list to update the GUI
            load_rooms()
        else:
            messagebox.showerror("Error", f"Error creating room '{new_room_name}': {response.json().get('message', 'Unknown error')}")
            load_rooms()

# Initialize main Tkinter window
root = tk.Tk()
root.title("Chat App")

# Main container frame
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# Left frame (chat area)
left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Room label
room_label = tk.Label(left_frame, text="Select a room or talk to yourself", bg='black', fg='cyan')
room_label.pack(fill=tk.X)

# Chat display
chat_text = scrolledtext.ScrolledText(left_frame, state=tk.DISABLED, bg='black', fg='white')
chat_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Chat message entry
chat_message_frame = tk.Frame(left_frame)
chat_message_frame.pack(fill=tk.X, padx=10, pady=10)
chat_message_entry = tk.Entry(chat_message_frame, bg='black', fg='white')
chat_message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
send_button = tk.Button(chat_message_frame, text="Send", command=send_chat_message, bg='black', fg='cyan')
send_button.pack(side=tk.RIGHT)

# Right frame (rooms and users)
right_frame = tk.Frame(main_frame, bg='#222')
right_frame.pack(side=tk.RIGHT, fill=tk.Y)

# Rooms list
rooms_label = tk.Label(right_frame, text="Rooms", bg='black', fg='cyan')
rooms_label.pack(fill=tk.X, pady=(10, 5))

rooms_canvas = tk.Canvas(right_frame, bg='#222')
rooms_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
rooms_scrollbar = tk.Scrollbar(right_frame, orient='vertical', command=rooms_canvas.yview)
rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
rooms_canvas_frame = tk.Frame(rooms_canvas, bg='#222')
rooms_canvas.create_window((0, 0), window=rooms_canvas_frame, anchor='nw')
rooms_canvas.config(yscrollcommand=rooms_scrollbar.set)
rooms_canvas.bind('<Configure>', lambda e: rooms_canvas.configure(scrollregion=rooms_canvas.bbox("all")))

# Users list
users_label = tk.Label(right_frame, text="Users", bg='black', fg='cyan')
users_label.pack(fill=tk.X, pady=(20, 5))
user_list = tk.Listbox(right_frame, bg='#222', fg='white')
user_list.pack(fill=tk.Y, expand=True)

# Create new room button
create_room_button = tk.Button(right_frame, text="Create New Room", command=create_new_room, bg='black', fg='cyan')
create_room_button.pack(side=tk.BOTTOM, padx=10, pady=10)

# Load rooms initially
load_rooms()

# Start periodic refreshes
refresh_user_list()
check_for_new_messages()

root.mainloop()
