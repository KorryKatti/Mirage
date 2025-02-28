import socket
import threading
import sys
import logging
import json
from datetime import datetime
from getpass import getpass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None

    def connect(self):
        """Connect to the chat server"""
        try:
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def register(self):
        """Register a new user"""
        print("\n=== Registration ===")
        data = {
            'action': 'register',
            'username': input("Username: ").strip(),
            'email': input("Email: ").strip(),
            'password': getpass("Password: ").strip(),  # Hide password input
            'avatar_url': input("Avatar URL (optional, press enter to skip): ").strip() or "default_avatar.png",
            'bio': input("Bio (optional, press enter to skip): ").strip() or "No bio provided"
        }
        
        # Confirm password
        confirm_password = getpass("Confirm Password: ").strip()
        if confirm_password != data['password']:
            print("\nPasswords do not match!")
            return False

        self.socket.send(json.dumps(data).encode())
        response = json.loads(self.socket.recv(1024).decode())
        
        if response['success']:
            print("\nRegistration successful!")
            self.username = data['username']
            return True
        else:
            print(f"\nRegistration failed: {response['message']}")
            return False

    def login(self):
        """Login existing user"""
        print("\n=== Login ===")
        data = {
            'action': 'login',
            'username': input("Username: ").strip(),
            'password': getpass("Password: ").strip()  # Hide password input
        }
        
        self.socket.send(json.dumps(data).encode())
        response = json.loads(self.socket.recv(1024).decode())
        
        if response['success']:
            print("\nLogin successful!")
            self.username = data['username']
            return True
        else:
            print(f"\nLogin failed: {response['message']}")
            return False

    def start(self):
        """Start the chat client"""
        if not self.connect():
            return

        print("\nWelcome to Mirage Chat!")
        print("1. Login")
        print("2. Register")
        choice = input("Choose an option (1/2): ").strip()

        success = False
        if choice == '1':
            success = self.login()
        elif choice == '2':
            success = self.register()
        else:
            print("Invalid choice")
            return

        if not success:
            return

        print("\nSuccessfully connected to server. Please start typing now!")

        # Start receiving messages in a separate thread
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

        # Main loop for sending messages
        try:
            while True:
                message = input()
                if message.lower() == '/quit':
                    break
                if message:
                    self.socket.send(message.encode())
        except KeyboardInterrupt:
            pass
        finally:
            self.socket.close()
            logger.info("Disconnected from server")

    def receive_messages(self):
        """Receive and display messages from the server"""
        while True:
            try:
                message = self.socket.recv(1024).decode()
                if not message:
                    break
                print(message)
            except:
                break

def print_help():
    """Print available commands"""
    print("\nAvailable commands:")
    print("/quit - Exit the chat")
    print("Just type your message and press Enter to send\n")

if __name__ == "__main__":
    client = ChatClient()
    try:
        client.start()
    except KeyboardInterrupt:
        logger.info("Client shutting down...")
    except Exception as e:
        logger.error(f"Client error: {e}")
    finally:
        sys.exit(0)
