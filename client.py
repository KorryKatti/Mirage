import sys
import json
import socket
import threading
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QStackedWidget, QMessageBox,
    QScrollArea, QButtonGroup, QDialog, QFormLayout
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject, QTimer, QThread
from PyQt6.QtGui import QIcon, QDesktopServices

class ChatClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.avatar_url = None
        self.bio = None

    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            return False

    def send_message(self, message):
        try:
            self.socket.send(message.encode())
        except:
            return False
        return True

    def close(self):
        self.socket.close()

class MessageReceiver(QObject):
    message_received = pyqtSignal(str)
    room_changed = pyqtSignal(str)
    
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.running = True
        
    def receive_messages(self):
        while self.running:
            try:
                message = self.socket.recv(1024).decode()
                if not message:
                    continue
                    
                # Try to parse as JSON first
                try:
                    data = json.loads(message)
                    # Handle different types of JSON messages
                    if data.get('action') == 'room_changed':
                        self.room_changed.emit(data['room'])
                    elif data.get('action') == 'chat_message':
                        self.message_received.emit(data['message'])
                    # Ignore other JSON messages (like settings responses)
                except json.JSONDecodeError:
                    # If it's not JSON, treat as plain chat message
                    self.message_received.emit(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
                
    def stop(self):
        self.running = False

    def run(self):
        self.receive_messages()

class SettingsUpdater(QObject):
    update_finished = pyqtSignal(bool, str, dict)

    def __init__(self, client, data):
        super().__init__()
        self.client = client
        self.data = data

    def update_settings(self):
        try:
            self.client.send_message(json.dumps(self.data))
            response = json.loads(self.client.socket.recv(1024).decode())
            print("Settings update response:", response)
            
            if response['success']:
                user_data = {
                    'avatar_url': response.get('avatar_url', ''),
                    'bio': response.get('bio', '')
                }
                self.update_finished.emit(True, response['message'], user_data)
            else:
                self.update_finished.emit(False, response['message'], {})
        except Exception as e:
            print("Error in settings update:", str(e))
            self.update_finished.emit(False, str(e), {})

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = ChatClient()
        self.message_receiver = None
        self.receiver_thread = None
        self.settings_thread = None
        
        # Create messages directory if it doesn't exist
        self.messages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'messages')
        os.makedirs(self.messages_dir, exist_ok=True)
        
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Mirage v0.0.2")
        self.setWindowIcon(QIcon("assets/img/icon.png"))

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_welcome_screen()
        self.create_login_screen()
        self.create_register_screen()
        self.create_chat_screen()

        self.stacked_widget.setCurrentWidget(self.welcome_screen)

    def create_welcome_screen(self):
        self.welcome_screen = QWidget()
        layout = QVBoxLayout(self.welcome_screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Mirage")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: #e0def4;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Your go-to chat app")
        subtitle.setStyleSheet("font-size: 18px; color: #9ccfd8;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet(self.get_button_style())
        login_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.login_screen))
        layout.addWidget(login_btn)

        register_btn = QPushButton("Register")
        register_btn.setStyleSheet(self.get_button_style())
        register_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.register_screen))
        layout.addWidget(register_btn)

        self.welcome_screen.setStyleSheet("background-color: #191724;")
        self.stacked_widget.addWidget(self.welcome_screen)

    def create_login_screen(self):
        self.login_screen = QWidget()
        layout = QVBoxLayout(self.login_screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Login")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0def4;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_username.setStyleSheet(self.get_input_style())
        layout.addWidget(self.login_username)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setStyleSheet(self.get_input_style())
        layout.addWidget(self.login_password)

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet(self.get_button_style())
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(self.get_button_style())
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.welcome_screen))
        layout.addWidget(back_btn)

        self.login_screen.setStyleSheet("background-color: #191724;")
        self.stacked_widget.addWidget(self.login_screen)

    def create_register_screen(self):
        self.register_screen = QWidget()
        layout = QVBoxLayout(self.register_screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Register")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e0def4;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Username")
        self.register_username.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_username)

        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("Email")
        self.register_email.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_email)

        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Password")
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_password)

        self.register_confirm_password = QLineEdit()
        self.register_confirm_password.setPlaceholderText("Confirm Password")
        self.register_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_confirm_password.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_confirm_password)

        self.register_avatar = QLineEdit()
        self.register_avatar.setPlaceholderText("Avatar URL (optional)")
        self.register_avatar.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_avatar)

        self.register_bio = QLineEdit()
        self.register_bio.setPlaceholderText("Bio (optional)")
        self.register_bio.setStyleSheet(self.get_input_style())
        layout.addWidget(self.register_bio)

        register_btn = QPushButton("Register")
        register_btn.setStyleSheet(self.get_button_style())
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(register_btn)

        back_btn = QPushButton("Back")
        back_btn.setStyleSheet(self.get_button_style())
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.welcome_screen))
        layout.addWidget(back_btn)

        self.register_screen.setStyleSheet("background-color: #191724;")
        self.stacked_widget.addWidget(self.register_screen)

    def create_chat_screen(self):
        self.chat_screen = QWidget()
        layout = QVBoxLayout(self.chat_screen)

        h_layout = QHBoxLayout()
        layout.addLayout(h_layout)

        room_widget = QWidget()
        room_widget.setFixedWidth(200)
        room_widget.setStyleSheet("""
            QWidget {
                background-color: #1f1d2e;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        room_layout = QVBoxLayout(room_widget)

        room_label = QLabel("Rooms")
        room_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0def4; margin-bottom: 10px;")
        room_layout.addWidget(room_label)

        self.room_buttons = {}
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        h_layout.addWidget(room_widget)

        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)

        self.current_room_label = QLabel("global")
        self.current_room_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0def4; margin-bottom: 10px;")
        chat_layout.addWidget(self.current_room_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1f1d2e;
                color: #e0def4;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
        """)
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.setStyleSheet(self.get_input_style())
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(self.get_button_style())
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        chat_layout.addLayout(input_layout)
        h_layout.addWidget(chat_widget)

        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(60)
        sidebar_widget.setStyleSheet("""
            QWidget {
                background-color: #1f1d2e;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setSpacing(10)

        all_rooms_btn = QPushButton("🏠")
        create_room_btn = QPushButton("➕")
        search_room_btn = QPushButton("🔍")
        settings_btn = QPushButton("⚙️")

        sidebar_button_style = """
            QPushButton {
                background-color: #26233a;
                color: #e0def4;
                border: none;
                font-size: 20px;
                padding: 10px;
                border-radius: 4px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #2d2a41;
            }
            QPushButton:pressed {
                background-color: #9ccfd8;
            }
        """

        for btn in [all_rooms_btn, create_room_btn, search_room_btn]:
            btn.setStyleSheet(sidebar_button_style)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        settings_btn.setStyleSheet(sidebar_button_style)
        settings_btn.clicked.connect(self.show_settings_dialog)
        sidebar_layout.addWidget(settings_btn)

        h_layout.addWidget(sidebar_widget)

        self.chat_screen.setStyleSheet("background-color: #191724;")
        self.stacked_widget.addWidget(self.chat_screen)

    def create_room_buttons(self, rooms):
        for btn in self.room_buttons.values():
            btn.setParent(None)
        self.room_buttons.clear()
        self.button_group.setExclusive(False)
        for button in self.button_group.buttons():
            self.button_group.removeButton(button)
        self.button_group.setExclusive(True)

        room_widget = self.chat_screen.layout().itemAt(0).layout().itemAt(0).widget()
        room_layout = room_widget.layout()

        for room in rooms:
            btn = QPushButton(room)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #26233a;
                    color: #e0def4;
                    border: none;
                    padding: 10px;
                    border-radius: 4px;
                    text-align: left;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #2d2a41;
                }
                QPushButton:checked {
                    background-color: #9ccfd8;
                    color: #191724;
                }
            """)
            btn.setCheckable(True)
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, r=room: self.join_room(r))
            self.room_buttons[room] = btn
            room_layout.addWidget(btn)

        if 'general' in self.room_buttons:
            self.room_buttons['general'].setChecked(True)

        room_layout.addStretch()

    def load_room_messages(self, room):
        """Load messages for a specific room"""
        try:
            # Clean room name to be safe for filenames
            safe_room = "".join(x for x in room if x.isalnum() or x in (' ', '-', '_')).strip()
            filename = os.path.join(self.messages_dir, f"{safe_room}.txt")
            
            if os.path.exists(filename):
                print(f"Loading messages from {filename}")  # Debug print
                with open(filename, 'r', encoding='utf-8') as f:
                    messages = f.readlines()
                    # Only show last 100 messages to avoid overwhelming the display
                    messages = [msg.strip() for msg in messages if msg.strip()]  # Remove empty lines
                    if messages:
                        self.chat_display.clear()
                        for msg in messages[-100:]:
                            self.chat_display.append(msg)
                        # Scroll to bottom
                        self.chat_display.verticalScrollBar().setValue(
                            self.chat_display.verticalScrollBar().maximum()
                        )
                        print(f"Loaded {len(messages[-100:])} messages")  # Debug print
                    else:
                        print("No messages found in file")  # Debug print
            else:
                print(f"No message file found at {filename}")  # Debug print
        except Exception as e:
            print(f"Error loading room messages: {e}")

    def update_current_room(self, room):
        """Update the current room label and chat display"""
        old_room = self.current_room_label.text()
        if old_room != room:  # Only update if actually changing rooms
            print(f"Changing room from {old_room} to {room}")  # Debug print
            self.current_room_label.setText(room)
            self.chat_display.clear()
            self.load_room_messages(room)

    def join_room(self, room):
        """Join a new room"""
        if room != self.current_room_label.text():  # Only join if not already in the room
            print(f"Joining room: {room}")  # Debug print
            self.client.send_message(json.dumps({
                'action': 'join_room',
                'username': self.client.username,
                'room': room
            }))

    def handle_login(self):
        if not self.client.connect():
            QMessageBox.critical(self, "Error", "Could not connect to server")
            return

        data = {
            'action': 'login',
            'username': self.login_username.text().strip(),
            'password': self.login_password.text().strip()
        }

        self.client.send_message(json.dumps(data))
        response = json.loads(self.client.socket.recv(1024).decode())

        if response['success']:
            # Store user data
            self.client.username = data['username']
            self.client.avatar_url = response.get('avatar_url', '')
            self.client.bio = response.get('bio', '')
            print("Logged in with data:", {
                'username': self.client.username,
                'avatar_url': self.client.avatar_url,
                'bio': self.client.bio
            })
            
            # Get room list from server
            room_data = json.loads(self.client.socket.recv(1024).decode())
            if room_data['action'] == 'room_list':
                self.create_room_buttons(room_data['rooms'])
            
            self.stacked_widget.setCurrentWidget(self.chat_screen)
            # Load initial room messages
            print("Loading initial room messages")  # Debug print
            self.load_room_messages('global')
            self.start_message_receiver()
            QMessageBox.information(self, "Success", "Login successful!")
        else:
            QMessageBox.warning(self, "Login Failed", response['message'])
            self.client.close()

    def handle_register(self):
        if self.register_password.text() != self.register_confirm_password.text():
            QMessageBox.warning(self, "Error", "Passwords do not match!")
            return

        if not self.client.connect():
            QMessageBox.critical(self, "Error", "Could not connect to server")
            return

        data = {
            'action': 'register',
            'username': self.register_username.text().strip(),
            'email': self.register_email.text().strip(),
            'password': self.register_password.text().strip(),
            'avatar_url': self.register_avatar.text().strip() or "default_avatar.png",
            'bio': self.register_bio.text().strip() or "No bio provided"
        }

        self.client.send_message(json.dumps(data))
        response = json.loads(self.client.socket.recv(1024).decode())

        if response['success']:
            self.client.username = data['username']
            self.client.avatar_url = data['avatar_url']
            self.client.bio = data['bio']
            print("Registered with data:", {
                'username': self.client.username,
                'avatar_url': self.client.avatar_url,
                'bio': self.client.bio
            })
            
            room_data = json.loads(self.client.socket.recv(1024).decode())
            if room_data['action'] == 'room_list':
                self.create_room_buttons(room_data['rooms'])
            
            self.stacked_widget.setCurrentWidget(self.chat_screen)
            self.start_message_receiver()
            QMessageBox.information(self, "Success", "Registration successful!")
        else:
            QMessageBox.warning(self, "Registration Failed", response['message'])
            self.client.close()

    def send_message(self):
        """Send a message"""
        message = self.message_input.text().strip()
        if message:
            data = {
                'action': 'send_message',
                'username': self.client.username,
                'message': message,
                'room': self.current_room_label.text()
            }
            try:
                self.client.send_message(json.dumps(data))
                self.message_input.clear()
                # No need to save here as we'll receive our own message back
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to send message: {str(e)}")

    def display_message(self, message):
        """Display and save received message"""
        # Only append if it's not already the last message
        last_message = self.chat_display.toPlainText().split('\n')[-1] if self.chat_display.toPlainText() else ''
        if message != last_message:
            self.chat_display.append(message)
            self.save_message_to_file(message, self.current_room_label.text())
            # Scroll to bottom
            self.chat_display.verticalScrollBar().setValue(
                self.chat_display.verticalScrollBar().maximum()
            )

    def save_message_to_file(self, message, room):
        """Save message to room-specific file"""
        try:
            # Clean room name to be safe for filenames
            safe_room = "".join(x for x in room if x.isalnum() or x in (' ', '-', '_')).strip()
            filename = os.path.join(self.messages_dir, f"{safe_room}.txt")
            
            # Check if message already exists in last line
            last_line = ''
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    # Move to the last line
                    try:
                        f.seek(-2, 2)  # Go to 2nd last byte
                        while f.read(1) != '\n':  # Until EOL is found
                            try:
                                f.seek(-2, 1)  # Go back 2 bytes and read
                            except:
                                f.seek(0)  # Go to start of file
                                break
                        last_line = f.readline().strip()
                    except:
                        f.seek(0)  # If file is too small, start from beginning
                        last_line = f.readline().strip()
            
            # Only write if it's not a duplicate of the last line
            if message.strip() != last_line:
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                
                # Append message to file
                with open(filename, 'a', encoding='utf-8') as f:
                    f.write(f"{message}\n")
        except Exception as e:
            print(f"Error saving message to file: {e}")

    def get_button_style(self):
        return """
            QPushButton {
                background-color: #9ccfd8;
                color: #191724;
                border: none;
                font-size: 16px;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #7fbcc5;
            }
        """

    def get_input_style(self):
        return """
            QLineEdit {
                background-color: #1f1d2e;
                color: #e0def4;
                border: 1px solid #9ccfd8;
                padding: 8px;
                border-radius: 4px;
                margin: 5px;
            }
        """

    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #191724;
            }
            QLabel {
                color: #e0def4;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #1f1d2e;
                color: #e0def4;
                border: 1px solid #9ccfd8;
                padding: 8px;
                border-radius: 4px;
                margin: 5px;
            }
            QPushButton {
                background-color: #9ccfd8;
                color: #191724;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #7fbcc5;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        notice = QLabel("Note: Username and email cannot be changed after registration.")
        notice.setStyleSheet("color: #eb6f92; margin-bottom: 10px;")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        current_password = QLineEdit()
        current_password.setEchoMode(QLineEdit.EchoMode.Password)
        current_password.setPlaceholderText("Required for any changes")
        form_layout.addRow("Current Password:", current_password)

        new_password = QLineEdit()
        new_password.setEchoMode(QLineEdit.EchoMode.Password)
        new_password.setPlaceholderText("Leave blank to keep current password")
        form_layout.addRow("New Password:", new_password)

        confirm_password = QLineEdit()
        confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_password.setPlaceholderText("Confirm new password")
        form_layout.addRow("Confirm Password:", confirm_password)

        avatar_url = QLineEdit()
        avatar_url.setObjectName("avatar_url")
        avatar_url.setText(self.client.avatar_url if hasattr(self.client, 'avatar_url') else "")
        avatar_url.setPlaceholderText("Enter avatar URL")
        form_layout.addRow("Avatar URL:", avatar_url)

        bio = QLineEdit()
        bio.setObjectName("bio")
        bio.setText(self.client.bio if hasattr(self.client, 'bio') else "")
        bio.setPlaceholderText("Enter bio")
        form_layout.addRow("Bio:", bio)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        cancel_btn.clicked.connect(dialog.reject)
        save_btn.clicked.connect(lambda: self.save_settings(
            dialog,
            current_password.text(),
            new_password.text(),
            confirm_password.text(),
            avatar_url.text(),
            bio.text()
        ))

        dialog.exec()

    def save_settings(self, dialog, current_password, new_password, confirm_password, avatar_url, bio):
        if not current_password:
            QMessageBox.warning(self, "Error", "Current password is required")
            return

        if new_password:
            if new_password != confirm_password:
                QMessageBox.warning(self, "Error", "New passwords do not match")
                return
            if len(new_password) < 6:
                QMessageBox.warning(self, "Error", "New password must be at least 6 characters")
                return

        data = {
            'action': 'update_settings',
            'username': self.client.username,
            'current_password': current_password,
            'new_password': new_password if new_password else None,
            'new_avatar_url': avatar_url,
            'new_bio': bio
        }

        print("Sending settings update:", data)

        if self.settings_thread is not None:
            self.settings_thread.quit()
            self.settings_thread.wait()

        self.settings_updater = SettingsUpdater(self.client, data)
        self.settings_thread = QThread()
        self.settings_updater.moveToThread(self.settings_thread)
        
        self.settings_thread.started.connect(self.settings_updater.update_settings)
        self.settings_updater.update_finished.connect(
            lambda success, message, user_data: self.on_settings_update_finished(success, message, user_data, dialog)
        )
        self.settings_updater.update_finished.connect(self.settings_thread.quit)
        self.settings_thread.finished.connect(lambda: self.cleanup_settings_thread())
        
        dialog.setEnabled(False)
        
        self.settings_thread.start()

    def cleanup_settings_thread(self):
        if self.settings_thread is not None:
            self.settings_thread.deleteLater()
            self.settings_thread = None
            self.settings_updater = None

    def on_settings_update_finished(self, success, message, user_data, dialog):
        dialog.setEnabled(True)
        
        if success:
            self.client.avatar_url = user_data.get('avatar_url', '')
            self.client.bio = user_data.get('bio', '')
            
            print("Updated client data:", {
                'username': self.client.username,
                'avatar_url': self.client.avatar_url,
                'bio': self.client.bio
            })
                
            QMessageBox.information(self, "Success", "Settings updated successfully")
            dialog.close()
        else:
            QMessageBox.warning(self, "Error", message)

    def closeEvent(self, event):
        if self.message_receiver:
            self.message_receiver.stop()
        if self.settings_thread is not None:
            self.settings_thread.quit()
            self.settings_thread.wait()
        if hasattr(self, 'client'):
            self.client.close()
        event.accept()

    def start_message_receiver(self):
        self.message_receiver = MessageReceiver(self.client.socket)
        self.message_receiver.message_received.connect(self.display_message)
        self.message_receiver.room_changed.connect(self.update_current_room)
        
        self.receiver_thread = threading.Thread(target=self.message_receiver.run)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())
