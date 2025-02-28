import requests
import json
import time

BASE_URL = 'http://localhost:5000'

# Register a new user
def register(username, password):
    response = requests.post(f'{BASE_URL}/register', json={'username': username, 'password': password})
    return response.json()

# Login a user
def login(username, password):
    response = requests.post(f'{BASE_URL}/login', json={'username': username, 'password': password})
    return response.json()

# Send a message
def send_message(user_id, message):
    response = requests.post(f'{BASE_URL}/send_message', json={'user_id': user_id, 'message': message})
    return response.json()

# Get messages
def get_messages():
    response = requests.get(f'{BASE_URL}/get_messages')
    return response.json()

# Get list of users (contacts)
def get_users():
    response = requests.get(f'{BASE_URL}/users')
    return response.json()

# Main function to run the client
def run_client():
    print("Welcome to BasicChat!")
    while True:
        print("1. Register")
        print("2. Login")
        choice = input("Choose an option: ")

        if choice == '1':
            username = input("Enter username: ")
            password = input("Enter password: ")
            print(register(username, password))
        elif choice == '2':
            username = input("Enter username: ")
            password = input("Enter password: ")
            login_response = login(username, password)
            print(login_response)

            if 'user_id' in login_response:
                user_id = login_response['user_id']
                print("Login successful!")
                while True:
                    print("1. View Contacts")
                    print("2. Send Message")
                    print("3. View Messages")
                    print("4. Logout")
                    action = input("Choose an action: ")

                    if action == '1':
                        users = get_users()
                        print("Contacts:")
                        for user in users.get('users', []):
                            print(user)
                    elif action == '2':
                        recipient_id = input("Enter recipient user ID: ")
                        message = input("Enter your message: ")
                        print(send_message(recipient_id, message))
                    elif action == '3':
                        messages = get_messages()
                        print("Messages:")
                        for msg in messages.get('messages', []):
                            print(f"[{msg['timestamp']}] {msg['username']}: {msg['message']}")
                    elif action == '4':
                        print("Logging out...")
                        break
                    else:
                        print("Invalid action. Please try again.")
            else:
                print("Login failed. Please try again.")
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    run_client() 