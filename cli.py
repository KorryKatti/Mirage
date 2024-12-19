import socketio
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from datetime import datetime
import os
import time
import sys

console = Console()
sio = socketio.Client()
current_user = None
current_room = None
chat_messages = []
is_in_chat_mode = False

# Ensure messages folder exists
os.makedirs("messages", exist_ok=True)

# Enhanced event handlers
@sio.on('login_response')
def on_login_response(data):
    global current_user
    if data['status'] == 'success':
        current_user = data.get('username')
        rprint(f"[green]Login successful! Active users in last 24h: {data['unique_logins_count']}[/green]")
    else:
        rprint(f"[red]Login failed: {data['message']}[/red]")

@sio.on('message_response')
def on_message_response(data):
    if data['status'] == 'success':
        rprint("[green]Message sent[/green]")
    else:
        rprint(f"[red]Message failed: {data['message']}[/red]")

@sio.on('chat_message')
def on_chat_message(data):
    global chat_messages
    timestamp = datetime.now().strftime("%H:%M:%S")
    sender = data.get('username', 'Unknown')
    message = data.get('message', '')
    room = data.get('room', '')

    if room == current_room:
        # Avoid duplicates by checking the message doesn't already exist
        formatted_message = f"[{timestamp}] {sender}: {message}"
        if formatted_message not in chat_messages:
            chat_messages.append(formatted_message)
            save_message_to_file(current_room, formatted_message)
            if is_in_chat_mode:
                display_chat()

def save_message_to_file(room_name, message):
    # Save message to a file named after the room
    folder = 'messages'
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{room_name}.txt")
    with open(filepath, 'a') as file:
        file.write(message + '\n')

def load_messages_from_file(room_name):
    # Load messages from the file for the current room
    filepath = os.path.join('messages', f"{room_name}.txt")
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            return file.readlines()
    return []

def display_chat():
    """Displays the chat from the room's file."""
    console.clear()
    rprint(Panel(f"Chat Room: {current_room} (Press Ctrl+C to exit chat mode)", title="Chat Window"))

    messages = load_messages_from_file(current_room)
    for msg in messages[-20:]:  # Display the last 20 messages
        rprint(msg.strip())

    rprint("\n" + "-" * console.width)
    rprint("[yellow]Type your message and press Enter to send (or /exit to leave chat mode)[/yellow]")


def chat_mode():
    global is_in_chat_mode, chat_messages
    is_in_chat_mode = True
    chat_messages = load_messages_from_file(current_room)  # Load messages from the file initially

    try:
        while is_in_chat_mode:
            display_chat()
            message = input("> ")

            if message.lower() == '/exit':
                is_in_chat_mode = False
                break

            if message.strip():
                sio.emit('send_message', {
                    'username': current_user,
                    'room_name': current_room,
                    'message': message
                })
    except KeyboardInterrupt:
        is_in_chat_mode = False
        console.clear()

def connect_to_server():
    try:
        sio.connect('http://localhost:5000', headers={'Connection': 'Upgrade'})
        rprint("[green]Connected to server[/green]")
        return True
    except Exception as e:
        rprint(f"[red]Connection failed: {str(e)}[/red]")
        return False

def send_message():
    global current_room
    if not current_user:
        rprint("[red]Please login first![/red]")
        return

    room_name = Prompt.ask("Enter room name")
    current_room = room_name

    if Prompt.ask("Do you want to enter chat mode?", choices=["y", "n"], default="y") == "y":
        chat_mode()
    else:
        message = Prompt.ask("Enter your message")
        sio.emit('send_message', {
            'username': current_user,
            'room_name': room_name,
            'message': message
        })
        time.sleep(0.5)

def show_menu():
    console.clear()
    rprint(Panel(
        "Chat Client Menu\n" +
        ("Logged in as: " + current_user if current_user else "Not logged in") +
        (f"\nCurrent room: {current_room}" if current_room else ""),
        title="Status"
    ))
    
    menu_items = {
        "1": "Login",
        "2": "Register",
        "3": "Create Room",
        "4": "Join Room",
        "5": "Send Message/Enter Chat",
        "6": "Update Profile",
        "7": "Exit"
    }
    
    for key, value in menu_items.items():
        rprint(f"{key}. {value}")
    
    choice = Prompt.ask(
        "Choose an option",
        choices=list(menu_items.keys()),
        default="1"
    )
    return choice


def login():
    username = Prompt.ask("Enter username")
    password = Prompt.ask("Enter password", password=True)
    sio.emit('login', {
        'username': username,
        'password': password
    })
    time.sleep(0.5)  # Wait for response
    return username

def register():
    username = Prompt.ask("Enter new username")
    password = Prompt.ask("Enter password", password=True)
    confirm_password = Prompt.ask("Confirm password", password=True)
    
    if password != confirm_password:
        rprint("[red]Passwords do not match![/red]")
        return
    
    sio.emit('register', {
        'username': username,
        'password': password
    })
    time.sleep(0.5)

def create_room():
    if not current_user:
        rprint("[red]Please login first![/red]")
        return
    
    room_name = Prompt.ask("Enter room name")
    password = Prompt.ask("Enter room password (optional)", password=True, default="")
    
    sio.emit('create_room', {
        'username': current_user,
        'room_name': room_name,
        'password': password
    })
    time.sleep(0.5)

def join_room():
    if not current_user:
        rprint("[red]Please login first![/red]")
        return
    
    room_name = Prompt.ask("Enter room name")
    password = Prompt.ask("Enter room password (if required)", password=True, default="")
    
    sio.emit('join_room', {
        'username': current_user,
        'room_name': room_name,
        'password': password
    })
    time.sleep(0.5)

def update_profile():
    if not current_user:
        rprint("[red]Please login first![/red]")
        return
    
    bio = Prompt.ask("Enter your bio")
    avatar = Prompt.ask("Enter avatar URL")
    
    sio.emit('update_profile', {
        'username': current_user,
        'bio': bio,
        'avatar': avatar
    })
    time.sleep(0.5)

def main():
    if not connect_to_server():
        return
    
    while True:
        choice = show_menu()
        
        actions = {
            "1": login,
            "2": register,
            "3": create_room,
            "4": join_room,
            "5": send_message,
            "6": update_profile,
            "7": lambda: None
        }
        
        if choice == "7":
            if Confirm.ask("Are you sure you want to exit?"):
                sio.disconnect()
                rprint("[yellow]Disconnected from server. Goodbye![/yellow]")
                break
        else:
            actions[choice]()
        
        if not is_in_chat_mode:
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        rprint("\n[yellow]Caught interrupt signal. Disconnecting...[/yellow]")
        try:
            sio.disconnect()
        except:
            pass
        sys.exit(0)
