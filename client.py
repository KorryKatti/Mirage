import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from ttkbootstrap import Style
import requests
import json
import os
import random
import hashlib
from datetime import datetime

# Load user info from JSON file
with open("userinfo.json", "r") as file:
    user_info = json.load(file)

username = user_info["username"]
email = user_info["email"]
secret_key = user_info["secret_key"]

# Server URL
server_url = "http://127.0.0.1:5000"

current_room = None
last_message_id = -1

# Create messages directory if it doesn't exist
os.makedirs("messages", exist_ok=True)

def generate_message_id(username, message, timestamp):
    """Generate a unique message ID."""
    return hashlib.md5(f"{username}:{message}:{timestamp}".encode()).hexdigest()

def save_message_to_file(room_name, username, message, timestamp):
    """Save a message to the corresponding room's text file."""
    message_id = generate_message_id(username, message, timestamp)
    with open(f"messages/{room_name}.txt", "a") as file:
        file.write(f"{message_id},{timestamp},{username},{message}\n")

def generate_user_color(username):
    """Generate a color based on the username."""
    random.seed(username)
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def send_chat_message():
    """Send a chat message to the server."""
    global current_room, last_message_id
    message = chat_message_entry.get().strip()
    if current_room and message:
        timestamp = datetime.now().isoformat()
        response = requests.post(
            f"{server_url}/send_message",
            json={"username": username, "room_name": current_room, "message": message},
        )
        if response.status_code == 200:
            chat_message_entry.delete(0, tk.END)
            save_message_to_file(current_room, username, message, timestamp)
            formatted_message = f"{username}: {message}"
            user_color = generate_user_color(username)
            chat_text.config(state=tk.NORMAL)
            chat_text.insert(tk.END, f"{formatted_message}\n", ("username",))
            chat_text.tag_config("username", foreground=user_color)
            chat_text.config(state=tk.DISABLED)
            chat_text.see(tk.END)
            last_message_id = max(last_message_id, int(generate_message_id(username, message, timestamp), 16))
        else:
            messagebox.showerror("Error", f"Error sending message: {response.json().get('message', 'Unknown error')}")
    elif message:
        messagebox.showerror("Error", "Select a room first.")

def load_rooms():
    """Load chat rooms from the server and display them."""
    for widget in rooms_canvas_frame.winfo_children():
        widget.destroy()
    response = requests.get(f"{server_url}/get_rooms")
    if response.status_code == 200:
        rooms = response.json()
        for room in rooms:
            room_button = tk.Button(
                rooms_canvas_frame,
                text=room,
                command=lambda r=room: select_room(r),
                bg="blue",
                fg="white",
            )
            room_button.pack(fill=tk.X, pady=2)

def select_room(room_name):
    """Select a chat room."""
    global current_room, last_message_id
    if current_room == room_name:
        return
    current_room = room_name
    last_message_id = -1
    room_label.config(text=f"Current Room: {room_name}")
    response = requests.post(f"{server_url}/join_room", json={"username": username, "room_name": room_name})
    if response.status_code == 200:
        load_users_in_room(room_name)
        load_chat_history(room_name)
        check_for_new_messages()
    else:
        messagebox.showerror("Error", f"Error joining room: {response.json().get('message', 'Unknown error')}")

def leave_room():
    """Leave the current chat room."""
    global current_room, last_message_id
    if current_room:
        response = requests.post(f"{server_url}/leave_room", json={"username": username, "room_name": current_room})
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

def load_users_in_room(room_name):
    """Load the list of users in the current room."""
    response = requests.get(f"{server_url}/get_users_in_room", params={"room_name": room_name})
    if response.status_code == 200:
        users = response.json()
        user_list.delete(0, tk.END)
        for user in users:
            user_list.insert(tk.END, user)

def load_chat_history(room_name):
    """Load chat history from the file and server."""
    global last_message_id
    chat_text.config(state=tk.NORMAL)
    chat_text.delete(1.0, tk.END)

    displayed_messages = set()

    # Load messages from the file
    try:
        with open(f"messages/{room_name}.txt", "r") as file:
            for line in file:
                try:
                    message_id, timestamp, username, message = line.strip().split(",", 3)
                    if message_id not in displayed_messages:
                        formatted_message = f"{username}: {message}"
                        user_color = generate_user_color(username)
                        chat_text.insert(tk.END, f"{formatted_message}\n", ("username",))
                        chat_text.tag_config("username", foreground=user_color)
                        displayed_messages.add(message_id)
                        last_message_id = max(last_message_id, int(message_id, 16))
                except ValueError:
                    continue  # Skip malformed lines
                
    except FileNotFoundError:
        print(f"No existing chat history for room {room_name}")

    # Load messages from the server
    try:
        response = requests.get(f"{server_url}/get_all_messages", params={"room_name": room_name})
        if response.status_code == 200:
            messages = response.json()
            for msg in messages:
                message_id = generate_message_id(msg['username'], msg['message'], msg['timestamp'])
                if message_id not in displayed_messages:
                    formatted_message = f"{msg['username']}: {msg['message']}"
                    save_message_to_file(room_name, msg['username'], msg['message'], msg['timestamp'])
                    user_color = generate_user_color(msg['username'])
                    chat_text.insert(tk.END, f"{formatted_message}\n", ("username",))
                    chat_text.tag_config("username", foreground=user_color)
                    displayed_messages.add(message_id)
                    last_message_id = max(last_message_id, int(message_id, 16))
    except Exception as e:
        print(f"Error loading messages from server: {e}")

    chat_text.config(state=tk.DISABLED)
    chat_text.see(tk.END)

def check_for_new_messages():
    """Check for new messages in the current room."""
    global last_message_id
    if current_room:
        response = requests.get(f"{server_url}/get_new_messages", params={"room_name": current_room, "last_message_id": last_message_id})
        if response.status_code == 200:
            new_messages = response.json()
            if new_messages:
                chat_text.config(state=tk.NORMAL)
                for msg in new_messages:
                    message_id = generate_message_id(msg['username'], msg['message'], msg['timestamp'])
                    if int(message_id, 16) > last_message_id:
                        formatted_message = f"{msg['username']}: {msg['message']}"
                        save_message_to_file(current_room, msg['username'], msg['message'], msg['timestamp'])
                        user_color = generate_user_color(msg['username'])
                        chat_text.insert(tk.END, f"{formatted_message}\n", ("username",))
                        chat_text.tag_config("username", foreground=user_color)
                        last_message_id = int(message_id, 16)
                chat_text.config(state=tk.DISABLED)
                chat_text.see(tk.END)
        root.after(1700, check_for_new_messages)

def refresh_user_list():
    """Refresh the user list in the current room."""
    if current_room:
        load_users_in_room(current_room)
    root.after(2000, refresh_user_list)

def create_new_room():
    """Create a new chat room."""
    new_room_name = simpledialog.askstring("Create New Room", "Enter the name for the new room:")
    if new_room_name:
        response = requests.post(f"{server_url}/create_room", json={"username": username, "room_name": new_room_name})
        if response.status_code == 200:
            messagebox.showinfo("Success", f"Room '{new_room_name}' created.")
            load_rooms()
        else:
            messagebox.showerror("Error", f"Error creating room '{new_room_name}': {response.json().get('message', 'Unknown error')}")

# Initialize main Tkinter window
root = tk.Tk()
root.title("Chat App")

# Initialize ttkbootstrap
style = Style(theme="cyborg")  # Choose 'cyborg' theme for retro neon look

# Main container frame
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# Left frame (chat area)
left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Chat display area
chat_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 12))
chat_text.pack(pady=10, fill=tk.BOTH, expand=True)

# Entry for chat messages
chat_message_entry = tk.Entry(left_frame, font=("Arial", 12))
chat_message_entry.pack(pady=10, fill=tk.X)

# Send message button
send_button = tk.Button(left_frame, text="Send", command=send_chat_message)
send_button.pack(pady=10)

# Right frame (room and user list)
right_frame = tk.Frame(main_frame)
right_frame.pack(side=tk.RIGHT, fill=tk.Y)

# Rooms canvas frame
rooms_frame = tk.LabelFrame(right_frame, text="Chat Rooms")
rooms_frame.pack(fill=tk.BOTH, expand=True)

rooms_canvas_frame = tk.Frame(rooms_frame)
rooms_canvas_frame.pack(fill=tk.BOTH, expand=True)

load_rooms()

# Current room label
room_label = tk.Label(right_frame, text="Select a room or talk to yourself", font=("Arial", 12))
room_label.pack(pady=10)

# User list
user_list = tk.Listbox(right_frame, font=("Arial", 12))
user_list.pack(fill=tk.Y, pady=10)

# Leave room button
leave_button = tk.Button(right_frame, text="Leave Room", command=leave_room)
leave_button.pack(pady=10)

# Create room button
create_room_button = tk.Button(right_frame, text="Create Room", command=create_new_room)
create_room_button.pack(pady=10)

# Refresh user list and check for new messages
root.after(2000, refresh_user_list)
root.after(2000, check_for_new_messages)

# Start the Tkinter main loop
root.mainloop()
