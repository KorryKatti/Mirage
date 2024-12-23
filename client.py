import sys
import json
import socket
import threading
import os
import base64
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QStackedWidget, QMessageBox,
    QScrollArea, QButtonGroup, QDialog, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QProgressBar, QProgressDialog
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject, QTimer, QThread, Qt
from PyQt6.QtGui import QIcon, QDesktopServices, QPixmap, QTextCursor
import requests
from requests_toolbelt.multipart import MultipartEncoder, MultipartEncoderMonitor

class ChatClient:
    def __init__(self):
        self.socket = None
        self.username = None
        self.avatar_url = None
        self.bio = None
        self.server_url = 'localhost:12345'  # Changed to use full URL format

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host, port = self.server_url.split(':')
            self.socket.connect((host, int(port)))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def send_message(self, message):
        try:
            self.socket.send(message.encode())
        except:
            return False
        return True

    def close(self):
        self.socket.close()

    def send_file(self, room, file_path):
        """
        Send file link to room (deprecated, now handled by FileUploader)
        """
        try:
            # Validate file size (limit to 50MB)
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                print("File too large")
                return False
            
            # Prepare file transfer message
            file_info = {
                'type': 'file_transfer',
                'room': room,
                'filename': os.path.basename(file_path)
            }
            
            # Send file info via socket
            self.socket.send(json.dumps(file_info).encode('utf-8'))
            return True
        except Exception as e:
            print(f"File transfer error: {e}")
            return False

    def upload_file(self, file_path):
        """
        Deprecated method, now handled by FileUploader
        """
        return None

    def receive_file(self, file_info):
        """
        Receive and save a file from another user.
        
        :param file_info: Dictionary containing file transfer information
        :return: Path to saved file or None
        """
        try:
            # Download file from transfer.sh
            response = requests.get(file_info['download_link'])
            
            if response.status_code == 200:
                # Create downloads directory if it doesn't exist
                downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
                os.makedirs(downloads_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(downloads_dir, file_info['filename'])
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                
                return file_path
            else:
                print(f"File download failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"File receive error: {e}")
            return None

class MessageReceiver(QObject):
    message_received = pyqtSignal(str)
    room_changed = pyqtSignal(str)
    room_list_updated = pyqtSignal(list)
    room_created = pyqtSignal(bool, str)
    explore_rooms_response = pyqtSignal(list)
    member_list_response = pyqtSignal(list)
    
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
                    elif data.get('action') == 'room_list':
                        self.room_list_updated.emit(data['rooms'])
                    elif data.get('action') == 'create_room_response':
                        self.room_created.emit(data['success'], data['message'])
                    elif data.get('action') == 'explore_rooms_response':
                        self.explore_rooms_response.emit(data['rooms'])
                    elif data.get('action') == 'get_room_members_response':
                        self.member_list_response.emit(data['members'])
                    elif data.get('action') == 'error':
                        QMessageBox.warning(None, "Error", data['message'])
                    elif data.get('type') == 'file_transfer':
                        # Handle file transfer
                        file_path = self.socket.recv(1024).decode()
                        file_data = self.socket.recv(int(file_path)).decode()
                        file_info = json.loads(file_data)
                        file_path = self.socket.recv(int(file_info['filesize'])).decode()
                        print(f"Received file: {file_info['filename']}")
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

class FileUploader(QThread):
    """
    Threaded file uploader with progress tracking
    """
    upload_progress = pyqtSignal(int)
    upload_complete = pyqtSignal(str, str)  # filename, download_link
    upload_error = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        """
        Upload file in a separate thread
        """
        try:
            # Open file in binary mode
            file_size = os.path.getsize(self.file_path)
            filename = os.path.basename(self.file_path)

            # Track upload progress
            def progress_callback(monitor):
                progress = int((monitor.bytes_read / file_size) * 100)
                self.upload_progress.emit(progress)

            # Use requests with streaming to track progress
            with open(self.file_path, 'rb') as file:
                # Create a MultipartEncoder for progress tracking
                encoder = MultipartEncoder(
                    fields={'file': (filename, file)}
                )
                
                # Create a MultipartEncoderMonitor to track progress
                monitor = MultipartEncoderMonitor(encoder, progress_callback)

                # Use a different, more reliable file sharing service
                response = requests.post(
                    'https://file.io', 
                    data=monitor,
                    headers={'Content-Type': monitor.content_type},
                    timeout=60
                )

            if response.status_code == 200:
                # Parse download link from response
                download_link = response.json().get('link')
                self.upload_complete.emit(filename, download_link)
            else:
                self.upload_error.emit(f"Upload failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            self.upload_error.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.upload_error.emit(f"Upload error: {str(e)}")

class DownloadableFileButton(QPushButton):
    """
    Custom button for downloadable files with embedded download link
    """
    def __init__(self, filename, download_link, parent=None):
        super().__init__(f"📥 Download: {filename}", parent)
        self.filename = filename
        self.download_link = download_link
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                text-align: left;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.clicked.connect(self.download_file)

    def download_file(self):
        """
        Download the file when button is clicked
        """
        try:
            # Open file save dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Downloaded File", 
                self.filename, 
                "All Files (*.*)"
            )
            
            if not save_path:
                return  # User cancelled
            
            # Download file in a thread
            self.downloader = FileDownloader(self.download_link, save_path)
            self.downloader.download_complete.connect(self.on_download_complete)
            self.downloader.download_error.connect(self.on_download_error)
            self.downloader.start()
        except Exception as e:
            QMessageBox.warning(self, "Download Error", str(e))

    def on_download_complete(self, save_path):
        """
        Show success message when download is complete
        """
        QMessageBox.information(
            self, 
            "Download Complete", 
            f"File saved to: {save_path}"
        )

    def on_download_error(self, error):
        """
        Show error message if download fails
        """
        QMessageBox.warning(
            self, 
            "Download Failed", 
            str(error)
        )

class FileDownloader(QThread):
    """
    Threaded file downloader
    """
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, download_url, save_path):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path

    def run(self):
        """
        Download file in a separate thread
        """
        try:
            # Download file
            response = requests.get(self.download_url, timeout=30)
            
            if response.status_code == 200:
                # Save file
                with open(self.save_path, 'wb') as file:
                    file.write(response.content)
                
                # Emit success signal
                self.download_complete.emit(self.save_path)
            else:
                self.download_error.emit(f"Download failed: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            self.download_error.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.download_error.emit(f"Download error: {str(e)}")

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
        self.room_buttons = {}  # Initialize room_buttons dictionary
        self.button_group = QButtonGroup()  # Initialize button group
        self.button_group.setExclusive(True)
        
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
        layout = QHBoxLayout()

        # Left panel for room list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Room list label
        room_label = QLabel("Your Rooms")
        room_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0def4;")
        left_layout.addWidget(room_label)
        
        # Room list
        self.room_list = QVBoxLayout()
        left_layout.addLayout(self.room_list)
        left_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.show_settings_dialog)
        left_layout.addWidget(settings_btn)
        
        # Member list button
        member_list_btn = QPushButton("Member List")
        member_list_btn.clicked.connect(self.show_member_list)
        left_layout.addWidget(member_list_btn)
        
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(200)
        layout.addWidget(left_panel)

        # Center chat area
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        
        # Current room label
        self.current_room_label = QLabel("global")
        self.current_room_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        center_layout.addWidget(self.current_room_label)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        center_layout.addWidget(self.chat_display)
        
        # Message input
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        file_transfer_btn = QPushButton("📁 Send File")
        file_transfer_btn.setStyleSheet(self.get_button_style())
        file_transfer_btn.clicked.connect(self.send_file_dialog)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)
        input_layout.addWidget(file_transfer_btn)
        center_layout.addLayout(input_layout)
        
        center_panel.setLayout(center_layout)
        layout.addWidget(center_panel)

        # Right panel for room management
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Room management label
        manage_label = QLabel("Room Management")
        manage_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0def4;")
        right_layout.addWidget(manage_label)
        
        # Create room button
        create_room_btn = QPushButton("Create New Room")
        create_room_btn.clicked.connect(self.create_room_dialog)
        right_layout.addWidget(create_room_btn)
        
        # Explore rooms button
        explore_rooms_btn = QPushButton("Explore Rooms")
        explore_rooms_btn.clicked.connect(self.explore_rooms_dialog)
        right_layout.addWidget(explore_rooms_btn)
        
        right_layout.addStretch()
        right_panel.setLayout(right_layout)
        right_panel.setFixedWidth(200)
        layout.addWidget(right_panel)

        self.chat_screen.setLayout(layout)
        self.stacked_widget.addWidget(self.chat_screen)

    def create_room_buttons(self, rooms):
        """Create buttons for each room"""
        # Clear existing buttons first
        while self.room_list.count():
            item = self.room_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for btn in self.room_buttons.values():
            self.button_group.removeButton(btn)
        self.room_buttons.clear()
        
        # Create new buttons
        for room in sorted(set(rooms)):  # Use set to remove duplicates
            btn = QPushButton(room)
            btn.setCheckable(True)
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, r=room: self.join_room(r))
            self.room_buttons[room] = btn
            self.room_list.addWidget(btn)
            
            # Set button style
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
        
        # Select global room by default if no room is selected
        if not self.button_group.checkedButton() and 'global' in self.room_buttons:
            self.room_buttons['global'].setChecked(True)
            
        self.room_list.addStretch()

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
            try:
                self.client.send_message(json.dumps({
                    'action': 'join_room',
                    'username': self.client.username,
                    'room': room
                }))
            except Exception as e:
                QMessageBox.warning(self, "Room Join Error", f"Failed to join room: {str(e)}")
                print(f"Room join error: {e}")

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
            'avatar_url': self.register_avatar.text().strip() or "https://i.pinimg.com/736x/0c/da/40/0cda4058d21f8101ffcc223eec55c18f.jpg",
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
        self.message_receiver.room_list_updated.connect(self.create_room_buttons)
        self.message_receiver.room_created.connect(self.handle_room_created)
        self.message_receiver.explore_rooms_response.connect(self.update_room_list)
        self.message_receiver.member_list_response.connect(self.update_member_list)
        
        self.receiver_thread = threading.Thread(target=self.message_receiver.run)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()

    def create_room_dialog(self):
        """Show dialog to create a new room"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Room")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Room name input
        name_label = QLabel("Room Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter room name")
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_button = QPushButton("Create")
        cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(create_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        create_button.clicked.connect(lambda: self.handle_room_creation(name_input.text(), dialog))
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()

    def handle_room_creation(self, room_name, dialog):
        """Handle room creation request"""
        if not room_name.strip():
            QMessageBox.warning(self, "Error", "Room name cannot be empty")
            return
        
        data = {
            'action': 'create_room',
            'room_name': room_name.strip()
        }
        
        try:
            self.client.send_message(json.dumps(data))
            # Response will be handled by message receiver
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create room: {str(e)}")

    def handle_room_created(self, success, message):
        """Handle room creation response"""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)

    def explore_rooms_dialog(self):
        """Show dialog to explore available rooms"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Explore Rooms")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Room list widget
        self.room_list_widget = QTableWidget()
        self.room_list_widget.setColumnCount(5)
        self.room_list_widget.setHorizontalHeaderLabels(["Room Name", "Creator", "Members", "Status", "Action"])
        header = self.room_list_widget.horizontalHeader()
        for i in range(5):  # Set each section to be stretched
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.room_list_widget)
        
        # Request rooms from server
        self.client.send_message(json.dumps({
            'action': 'explore_rooms'
        }))
        
        dialog.setLayout(layout)
        dialog.exec()

    def update_room_list(self, rooms_data):
        """Update the room exploration dialog with room data"""
        if not hasattr(self, 'room_list_widget'):
            return
            
        self.room_list_widget.setRowCount(len(rooms_data))
        
        for i, room in enumerate(rooms_data):
            # Room name
            name_item = QTableWidgetItem(room['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.room_list_widget.setItem(i, 0, name_item)
            
            # Creator
            creator_item = QTableWidgetItem(room.get('creator', 'Unknown'))
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.room_list_widget.setItem(i, 1, creator_item)
            
            # Members count
            member_count = len(room.get('members', []))
            members_item = QTableWidgetItem(str(member_count))
            members_item.setFlags(members_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.room_list_widget.setItem(i, 2, members_item)
            
            # Status
            status_item = QTableWidgetItem("Public" if room.get('public', False) else "Private")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.room_list_widget.setItem(i, 3, status_item)
            
            # Action buttons container
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 4, 4, 4)
            
            # Join button
            join_btn = QPushButton("Join")
            join_btn.setStyleSheet("""
                QPushButton {
                    background-color: #31748f;
                    color: #e0def4;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #3e8fb0;
                }
            """)
            join_btn.clicked.connect(lambda checked, r=room['name']: self.join_room(r))
            action_layout.addWidget(join_btn)
            
            action_widget.setLayout(action_layout)
            self.room_list_widget.setCellWidget(i, 4, action_widget)

    def show_member_list(self):
        """Show list of members in current room"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Room Members")
        dialog.setModal(True)
        dialog.resize(300, 400)
        
        layout = QVBoxLayout()
        
        # Request member list from server
        self.client.send_message(json.dumps({
            'action': 'get_room_members',
            'room': self.current_room_label.text()
        }))
        
        # Create scrollable member list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.member_list_layout = QVBoxLayout(scroll_content)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        dialog.setLayout(layout)
        dialog.exec()
        
    def update_member_list(self, members_data):
        """Update member list with received data"""
        # Clear existing members
        while self.member_list_layout.count():
            item = self.member_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for member in members_data:
            # Create member button
            btn = QPushButton(member['username'])
            btn.clicked.connect(lambda checked, m=member: self.show_member_profile(m))
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
            """)
            self.member_list_layout.addWidget(btn)
            
        self.member_list_layout.addStretch()

    def show_member_profile(self, member_data):
        """Show member profile dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Profile: {member_data['username']}")
        dialog.setModal(True)
        dialog.resize(300, 400)
        
        layout = QVBoxLayout()
        
        # Avatar
        avatar_label = QLabel()
        avatar_pixmap = QPixmap()
        avatar_pixmap.loadFromData(requests.get(member_data['avatar_url']).content)
        avatar_label.setPixmap(avatar_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar_label)
        
        # Username
        username_label = QLabel(f"Username: {member_data['username']}")
        username_label.setStyleSheet("color: #e0def4; font-size: 14px;")
        username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(username_label)
        
        # Bio
        bio_label = QLabel(f"Bio: {member_data['bio']}")
        bio_label.setStyleSheet("color: #e0def4; font-size: 12px;")
        bio_label.setWordWrap(True)
        bio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bio_label)
        
        # Open Profile button
        open_profile_btn = QPushButton("Open Profile")
        open_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #31748f;
                color: #e0def4;
                border: none;
                padding: 10px;
                border-radius: 4px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #3e8fb0;
            }
        """)
        layout.addWidget(open_profile_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def send_file_dialog(self):
        """
        Open a file dialog to select and send a file.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if file_path:
            # Create and start the file uploader in a separate thread
            self.file_uploader = FileUploader(file_path)
            self.file_uploader.upload_progress.connect(self.update_upload_progress)
            self.file_uploader.upload_complete.connect(self.on_upload_complete)
            self.file_uploader.upload_error.connect(self.on_upload_error)
            
            # Create a progress dialog
            self.upload_progress_dialog = QProgressDialog("Uploading file...", "Cancel", 0, 100, self)
            self.upload_progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.upload_progress_dialog.setAutoClose(True)
            self.upload_progress_dialog.setAutoReset(True)
            self.upload_progress_dialog.canceled.connect(self.file_uploader.terminate)
            
            # Start the upload thread
            self.file_uploader.start()
            self.upload_progress_dialog.show()

    def update_upload_progress(self, progress):
        """
        Update the upload progress dialog
        """
        if hasattr(self, 'upload_progress_dialog'):
            self.upload_progress_dialog.setValue(progress)

    def on_upload_complete(self, filename, download_link):
        """
        Handle successful file upload
        """
        # Close the progress dialog
        if hasattr(self, 'upload_progress_dialog'):
            self.upload_progress_dialog.close()
        
        # Simulate sending a message with the download link
        self.message_input.setText(f"Download Link for {filename}: {download_link}")
        self.send_message()  # Call the existing send_message method
        
        # Display the file in local chat
        self.display_downloadable_file(filename, download_link)

    def on_upload_error(self, error):
        """
        Handle file upload error
        """
        # Close the progress dialog
        if hasattr(self, 'upload_progress_dialog'):
            self.upload_progress_dialog.close()
        
        # Show error message
        QMessageBox.warning(self, "Upload Error", str(error))

    def display_downloadable_file(self, filename, download_link):
        """
        Display a downloadable file link in the chat
        
        :param filename: Name of the file
        :param download_link: URL to download the file
        """
        # Insert the file information into the chat display
        file_message = f"📁 File Uploaded: {filename}\nDownload Link: {download_link}"
        self.chat_display.append(file_message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())
