import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from ttkbootstrap import Style
from customtkinter import CTkButton, CTkEntry, CTkLabel, CTkFrame
import requests
import json
import os
import random

# Initialize ttkbootstrap with a modern theme
style = Style(theme='cosmo')  # Choose a modern theme like 'cosmo' or 'litera'

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
def load_rooms():
    for widget in rooms_canvas_frame.winfo_children():
        widget.destroy()
    response = requests.get(f'{server_url}/get_rooms')
    if response.status_code == 200:
        rooms = response.json()
        for room in rooms:
            room_button = CTkButton(rooms_canvas_frame, text=room, command=lambda r=room: select_room(r), fg_color='#4CAF50', hover_color='#45A049')
            room_button.pack(fill=tk.X, pady=5, padx=10)

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
        check_for_new_messages()
    else:
        messagebox.showerror("Error", f"Error joining room: {response.json().get('message', 'Unknown error')}")

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
        root.after(1500, check_for_new_messages)

# Initialize main Tkinter window
root = tk.Tk()
root.title("Mirage Chat App")
root.geometry("700x500")
root.config(bg='#1a1a1a')

# Left frame for chat
chat_frame = CTkFrame(root)
chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# Room label
room_label = CTkLabel(chat_frame, text="Select a room", text_color='white')
room_label.pack(fill=tk.X, pady=10)

# Chat display
chat_text = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, bg='#2b2b2b', fg='#EDEDED', insertbackground='white')
chat_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Chat entry and send button
chat_message_entry = CTkEntry(chat_frame, placeholder_text="Type your message...", width=300)
chat_message_entry.pack(side=tk.LEFT, fill=tk.X, padx=10, pady=10, expand=True)
send_button = CTkButton(chat_frame, text="Send", command=send_chat_message, width=80)
send_button.pack(side=tk.RIGHT)

# Right frame for rooms and users
sidebar_frame = CTkFrame(root, width=150)
sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

# Rooms list
rooms_label = CTkLabel(sidebar_frame, text="Rooms", text_color='white')
rooms_label.pack(fill=tk.X)
rooms_canvas = tk.Canvas(sidebar_frame, bg='#2b2b2b', highlightthickness=0)
rooms_canvas.pack(side=tk.LEFT, fill=tk.Y)
rooms_scrollbar = tk.Scrollbar(sidebar_frame, orient='vertical', command=rooms_canvas.yview)
rooms_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
rooms_canvas_frame = tk.Frame(rooms_canvas, bg='#2b2b2b')
rooms_canvas.create_window((0, 0), window=rooms_canvas_frame, anchor='nw')
rooms_canvas.config(yscrollcommand=rooms_scrollbar.set)

# Users list
users_label = CTkLabel(sidebar_frame, text="Users", text_color='white')
users_label.pack(fill=tk.X, pady=10)
user_list = tk.Listbox(sidebar_frame, bg='#2b2b2b', fg='white')
user_list.pack(fill=tk.Y, expand=True)

# Create new room button
create_room_button = CTkButton(sidebar_frame, text="Create Room", command=create_new_room)
create_room_button.pack(padx=10, pady=10)

# Load rooms
load_rooms()

# Start refreshing
check_for_new_messages()

root.mainloop()
