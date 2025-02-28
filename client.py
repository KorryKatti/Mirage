import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
from datetime import datetime
import threading
import time
import requests
import json
import os
from pathlib import Path
import re
from cryptography.fernet import Fernet
import hashlib
import base64

class ServerManager:
    def __init__(self):
        with open('servers.json', 'r') as f:
            self.config = json.load(f)
        self.servers = self.config['servers']
        self.current_server = None
    
    def get_best_server(self):
        server_loads = []
        for server in self.servers:
            try:
                response = requests.get(
                    f"http://{server['host']}:{server['port']}/api/server/stats",
                    timeout=2
                )
                if response.status_code == 200:
                    stats = response.json()
                    # Calculate load score (lower is better)
                    load_score = (
                        stats['stats']['cpu_usage'] * 0.4 +
                        stats['stats']['memory_usage'] * 0.3 +
                        (stats['stats']['active_users_count'] / server['max_users']) * 0.3
                    )
                    server_loads.append((server, load_score))
            except:
                continue
        
        if not server_loads and self.servers:
            # Fallback to first server if none respond
            return self.servers[0]
        elif not server_loads:
            raise Exception("No servers available")
        
        # Return server with lowest load
        return min(server_loads, key=lambda x: x[1])[0]
    
    def get_server_url(self, server=None):
        if not server:
            server = self.current_server
        return f"http://{server['host']}:{server['port']}/api"

class LoginWindow:
    def __init__(self):
        self.server_manager = ServerManager()
        
        self.root = tk.Tk()
        self.root.title("Mirage IRC - Login")
        self.root.configure(bg='#1a1a1a')
        self.root.geometry("300x400")
        
        self.colors = {
            'bg': '#1a1a1a',
            'fg': '#e0e0e0',
            'input_bg': '#2d2d2d',
            'highlight': '#3a3a3a',
            'accent': '#6272a4'
        }
        
        # Server status
        self.status_label = tk.Label(
            self.root,
            text="Connecting to server...",
            fg=self.colors['accent'],
            bg=self.colors['bg'],
            font=('Consolas', 8)
        )
        self.status_label.pack(pady=5)
        
        # Title
        title = tk.Label(
            self.root,
            text="Mirage IRC",
            fg=self.colors['accent'],
            bg=self.colors['bg'],
            font=('Consolas', 24, 'bold')
        )
        title.pack(pady=20)
        
        # Login Frame
        self.frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Username
        tk.Label(
            self.frame,
            text="Username:",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10)
        ).pack(anchor='w')
        
        self.username = tk.Entry(
            self.frame,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10)
        )
        self.username.pack(fill=tk.X, pady=(0, 10))
        
        # Password
        tk.Label(
            self.frame,
            text="Password:",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10)
        ).pack(anchor='w')
        
        self.password = tk.Entry(
            self.frame,
            show="•",
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10)
        )
        self.password.pack(fill=tk.X, pady=(0, 20))
        
        # Buttons
        btn_frame = tk.Frame(self.frame, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.login_btn = tk.Button(
            btn_frame,
            text="Login",
            command=self.login,
            bg=self.colors['accent'],
            fg=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10)
        )
        self.login_btn.pack(side=tk.LEFT, expand=True, padx=5)
        
        self.register_btn = tk.Button(
            btn_frame,
            text="Register",
            command=self.register,
            bg=self.colors['highlight'],
            fg=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10)
        )
        self.register_btn.pack(side=tk.LEFT, expand=True, padx=5)
        
        self.root.mainloop()
    
    def find_server(self):
        try:
            server = self.server_manager.get_best_server()
            self.server_manager.current_server = server
            self.status_label.config(
                text=f"Connected to {server['id']} ({server['host']}:{server['port']})"
            )
        except Exception as e:
            self.status_label.config(text="Error: No servers available")
            messagebox.showerror("Error", "No servers available")
    
    def register(self):
        if not self.server_manager.current_server:
            self.find_server()
            if not self.server_manager.current_server:
                return
        
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        try:
            response = requests.post(
                f"{self.server_manager.get_server_url()}/register",
                json={
                    'username': username,
                    'password': password
                }
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "Registration successful! You can now login.")
            else:
                messagebox.showerror("Error", response.json().get('error', 'Registration failed'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")
    
    def login(self):
        if not self.server_manager.current_server:
            self.find_server()
            if not self.server_manager.current_server:
                return
        
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        try:
            response = requests.post(
                f"{self.server_manager.get_server_url()}/login",
                json={
                    'username': username,
                    'password': password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.root.destroy()
                MirageClient(
                    data['token'],
                    data['username'],
                    data['channels'],
                    self.server_manager,
                    data['server']
                )
            else:
                messagebox.showerror("Error", response.json().get('error', 'Login failed'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

class MirageClient:
    def __init__(self, token, username, channels, server_manager, server):
        self.token = token
        self.username = username
        self.server_manager = server_manager
        self.server_manager.current_server = server
        self.current_channel = '#general'
        
        # Reintroduce encryption key initialization
        self.encryption_key = base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest())
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Message history storage
        self.message_history = {}
        for channel in channels:
            self.message_history[channel] = []
        
        self.root = tk.Tk()
        self.root.title(f"Mirage IRC - {username} ({server['id']})")
        self.root.configure(bg='#1a1a1a')
        
        self.colors = {
            'bg': '#1a1a1a',
            'fg': '#e0e0e0',
            'input_bg': '#2d2d2d',
            'highlight': '#3a3a3a',
            'accent': '#6272a4'
        }
        
        # Create main container
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left sidebar
        self.sidebar = tk.Frame(
            self.main_frame,
            bg=self.colors['input_bg'],
            width=200
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        
        # Server info
        self.server_frame = tk.Frame(self.sidebar, bg=self.colors['input_bg'])
        self.server_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            self.server_frame,
            text="SERVER",
            fg=self.colors['accent'],
            bg=self.colors['input_bg'],
            font=('Consolas', 10, 'bold')
        ).pack(anchor='w')
        
        self.server_label = tk.Label(
            self.server_frame,
            text=f"{server['id']} ({server['host']}:{server['port']})",
            fg=self.colors['fg'],
            bg=self.colors['input_bg'],
            font=('Consolas', 8)
        )
        self.server_label.pack(anchor='w')
        
        # Channel list
        tk.Label(
            self.sidebar,
            text="CHANNELS",
            fg=self.colors['accent'],
            bg=self.colors['input_bg'],
            font=('Consolas', 10, 'bold')
        ).pack(padx=10, pady=(10,5), anchor='w')
        
        self.channels_list = tk.Listbox(
            self.sidebar,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10),
            height=10
        )
        self.channels_list.pack(fill=tk.X, padx=10, pady=5)
        self.channels_list.bind('<<ListboxSelect>>', self.on_channel_select)
        
        # User list
        tk.Label(
            self.sidebar,
            text="USERS",
            fg=self.colors['accent'],
            bg=self.colors['input_bg'],
            font=('Consolas', 10, 'bold')
        ).pack(padx=10, pady=(10,5), anchor='w')
        
        self.users_list = tk.Listbox(
            self.sidebar,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10),
            height=10
        )
        self.users_list.pack(fill=tk.X, padx=10, pady=5)
        
        # Files list
        tk.Label(
            self.sidebar,
            text="FILES",
            fg=self.colors['accent'],
            bg=self.colors['input_bg'],
            font=('Consolas', 10, 'bold')
        ).pack(padx=10, pady=(10,5), anchor='w')
        
        self.files_list = tk.Listbox(
            self.sidebar,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10),
            height=10
        )
        self.files_list.pack(fill=tk.X, padx=10, pady=5)
        self.files_list.bind('<<ListboxSelect>>', self.on_file_select)
        
        # Chat area container
        chat_container = tk.Frame(self.main_frame, bg=self.colors['bg'])
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Channel header
        header_frame = tk.Frame(chat_container, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X)
        
        self.channel_label = tk.Label(
            header_frame,
            text="#general",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 12, 'bold')
        )
        self.channel_label.pack(side=tk.LEFT)
        
        self.topic_label = tk.Label(
            header_frame,
            text="Welcome to Mirage IRC",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10)
        )
        self.topic_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Chat area
        self.text_area = scrolledtext.ScrolledText(
            chat_container,
            wrap=tk.WORD,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            font=('Consolas', 10),
            insertbackground=self.colors['fg']
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.text_area.config(state='disabled')
        
        # Configure text tags for different message types
        self.text_area.tag_configure('timestamp', foreground='#666666')
        self.text_area.tag_configure('username', foreground=self.colors['accent'])
        self.text_area.tag_configure('system', foreground='#888888', font=('Consolas', 10, 'italic'))
        self.text_area.tag_configure('file_info', background=self.colors['highlight'])
        
        # Input area
        input_frame = tk.Frame(chat_container, bg=self.colors['bg'])
        input_frame.pack(fill=tk.X, pady=10)
        
        # File upload button
        self.upload_btn = tk.Button(
            input_frame,
            text="📎",
            command=self.upload_file,
            bg=self.colors['input_bg'],
            fg=self.colors['accent'],
            relief='flat',
            font=('Consolas', 12)
        )
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Nickname label
        self.nick_label = tk.Label(
            input_frame,
            text=f"{username} >",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10)
        )
        self.nick_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Message entry
        self.entry = tk.Entry(
            input_frame,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10)
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self.send_message)
        
        # Initialize channels
        for channel in channels:
            self.channels_list.insert(tk.END, channel)
        
        # Start polling thread
        self.polling = True
        threading.Thread(target=self.poll_messages, daemon=True).start()
        
        # Load files for current channel
        self.load_channel_files()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.geometry("1200x800")
        self.root.mainloop()
    
    def on_channel_select(self, event):
        selection = self.channels_list.curselection()
        if selection:
            channel = self.channels_list.get(selection[0])
            self.join_channel(channel)
    
    def join_channel(self, channel):
        self.current_channel = channel
        self.channel_label.config(text=channel)
        
        # Load message history for the channel
        self.load_message_history()
        
        # Load channel files
        self.load_channel_files()
        
        self.send_message(None, f"/join {channel}")
    
    def on_file_select(self, event):
        selection = self.files_list.curselection()
        if selection:
            # Extract file ID from the first part of the listbox item
            file_id = self.files_list.get(selection[0]).split()[0]
            self.download_file(file_id)
    
    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            if file_size > 16 * 1024 * 1024:  # 16MB limit
                messagebox.showerror("Error", "File size exceeds 16MB limit")
                return
            
            # Check file extension
            file_ext = os.path.splitext(file_path)[1].lower()[1:]
            allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'zip', 'doc', 'docx'}
            if file_ext not in allowed_extensions:
                messagebox.showerror("Error", f"File type .{file_ext} is not allowed")
                return
            
            # Create multipart form data
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                response = requests.post(
                    f"{self.server_manager.get_server_url()}/upload",
                    headers={'Authorization': self.token},
                    data={'channel': self.current_channel},
                    files=files
                )
            
            if response.status_code == 200:
                self.load_channel_files()
                messagebox.showinfo("Success", "File uploaded successfully")
            else:
                error_msg = response.json().get('error', 'Failed to upload file')
                messagebox.showerror("Error", error_msg)
        except Exception as e:
            messagebox.showerror("Error", f"Upload failed: {str(e)}")
    
    def download_file(self, file_id):
        try:
            response = requests.get(
                f"{self.server_manager.get_server_url()}/download/{file_id}",
                headers={'Authorization': self.token},
                stream=True  # Stream the response to handle large files
            )
            
            if response.status_code == 200:
                # Get original filename from headers
                content_disposition = response.headers.get('Content-Disposition', '')
                filename = content_disposition.split('filename=')[-1].strip('"')
                
                # Ask user where to save the file
                save_path = filedialog.asksaveasfilename(
                    defaultextension=os.path.splitext(filename)[1],
                    initialfile=filename
                )
                
                if save_path:
                    # Download file in chunks
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    messagebox.showinfo("Success", "File downloaded successfully")
            else:
                error_msg = response.json().get('error', 'Failed to download file')
                messagebox.showerror("Error", error_msg)
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {str(e)}")
    
    def load_channel_files(self):
        try:
            response = requests.get(
                f"{self.server_manager.get_server_url()}/files/{self.current_channel}",
                headers={'Authorization': self.token}
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.files_list.delete(0, tk.END)
                    
                    if not data or 'files' not in data:
                        return
                    
                    for file in data['files']:
                        size = self.format_size(file['size'])
                        # Format: "ID filename (size) - uploader"
                        self.files_list.insert(tk.END, f"{file['id']} {file['name']} ({size}) - {file['uploader']}")
                except json.JSONDecodeError:
                    print("Error: Invalid JSON response from server")
            else:
                print(f"Error loading files: {response.status_code}")
        except Exception as e:
            print(f"Error loading files: {str(e)}")
    
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"
    
    def on_file_click(self, file_id):
        # Create a context menu
        menu = tk.Menu(self.root, tearoff=0, bg=self.colors['input_bg'], fg=self.colors['fg'])
        menu.add_command(
            label="📥 Download",
            command=lambda: self.download_file(file_id),
            font=('Consolas', 9)
        )
        menu.add_command(
            label="👁 Preview",
            command=lambda url=download_url, fname=filename: self.preview_file(url.split('/')[-1], fname),
            font=('Consolas', 9)
        )
        
        # Show the menu at current mouse position
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()
    
    def preview_file(self, file_id, filename):
        try:
            # Download the file to a temporary location
            response = requests.get(
                f"{self.server_manager.get_server_url()}/download/{file_id}",
                headers={'Authorization': self.token},
                stream=True
            )
            
            if response.status_code == 200:
                import tempfile
                import os
                import subprocess
                
                # Create temp file with correct extension
                ext = os.path.splitext(filename)[1]
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp_path = tmp.name
                
                # Try to open the file with the default system application
                if os.name == 'nt':  # Windows
                    os.startfile(tmp_path)
                elif os.name == 'posix':  # macOS and Linux
                    try:
                        subprocess.run(['xdg-open', tmp_path])  # Linux
                    except FileNotFoundError:
                        subprocess.run(['open', tmp_path])  # macOS
            else:
                messagebox.showerror("Error", "Failed to preview file")
        except Exception as e:
            messagebox.showerror("Error", f"Preview failed: {str(e)}")
    
    def poll_messages(self):
        while self.polling:
            try:
                response = requests.get(
                    f"{self.server_manager.get_server_url()}/poll",
                    headers={'Authorization': self.token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for message in data['messages']:
                        try:
                            # Handle system messages (join/part/etc)
                            if isinstance(message, str) and (message.startswith('[') and '] *' in message):
                                self.add_message_to_history(message)
                                continue

                            # Handle encrypted messages
                            if isinstance(message, str) and message.startswith('gAAAAA'):
                                try:
                                    decrypted = self.cipher_suite.decrypt(message.encode()).decode()
                                    self.add_message_to_history(decrypted)
                                except Exception as e:
                                    print(f"Failed to decrypt message: {e}")
                                    self.add_message_to_history(f"[Error] Failed to decrypt message")
                                    continue
                            elif isinstance(message, dict):
                                if message.get('encrypted'):
                                    try:
                                        decrypted = self.cipher_suite.decrypt(message['content'].encode()).decode()
                                        timestamp = message.get('timestamp', datetime.now().strftime('%H:%M'))
                                        sender = message.get('sender', 'unknown')
                                        formatted_msg = f"[{timestamp}] <{sender}> {decrypted}"
                                        self.add_message_to_history(formatted_msg)
                                    except Exception as e:
                                        print(f"Failed to decrypt message: {e}")
                                        self.add_message_to_history(f"[Error] Failed to decrypt message from {sender}")
                                        continue
                                else:
                                    # System message or command response
                                    content = message.get('content', str(message))
                                    self.add_message_to_history(content)
                        except Exception as e:
                            print(f"Failed to process message: {e}")
                            continue
                    
                    # Update user lists for channels
                    if self.current_channel in data['users']:
                        self.update_user_list(data['users'][self.current_channel])
                    
                    # Reload files list periodically
                    self.load_channel_files()
                    
                    # Refresh display from history
                    self.refresh_display()
                
                elif response.status_code == 401:
                    self.polling = False
                    messagebox.showerror("Error", "Session expired")
                    self.root.destroy()
                    return
            except Exception as e:
                print(f"Polling error: {str(e)}")
            
            time.sleep(1)

    def add_message_to_history(self, message):
        # Store message in history if it's not already there
        if self.current_channel in self.message_history:
            if message not in self.message_history[self.current_channel]:
                self.message_history[self.current_channel].append(message)
        else:
            self.message_history[self.current_channel] = [message]
        
        # Save message history to file
        self.save_message_history()

    def refresh_display(self):
        # Clear and redisplay all messages from history
        self.text_area.config(state='normal')
        self.text_area.delete(1.0, tk.END)
        if self.current_channel in self.message_history:
            for msg in self.message_history[self.current_channel]:
                self.display_message(msg)
        self.text_area.config(state='disabled')
        self.text_area.yview(tk.END)

    def send_message(self, event=None, content=None):
        message = content or self.entry.get().strip()
        if not message:
            return
        
        headers = {'Authorization': self.token}
        timestamp = datetime.now().strftime('%H:%M')
        
        if message.startswith('/'):
            # Handle commands
            data = {
                'type': 'command',
                'content': message,
                'channel': self.current_channel
            }
            try:
                response = requests.post(
                    f"{self.server_manager.get_server_url()}/message",
                    headers=headers,
                    json=data
                )
                if response.status_code == 200:
                    if not content:
                        self.entry.delete(0, tk.END)
                else:
                    self.add_message_to_history(f"Error sending message: {response.json().get('error')}")
                    self.refresh_display()
            except Exception as e:
                self.add_message_to_history(f"Error sending message: {str(e)}")
                self.refresh_display()
            return
        
        # For regular messages, encrypt and send
        try:
            # Encrypt message
            encrypted_message = self.cipher_suite.encrypt(message.encode()).decode()
            
            # Prepare message data
            data = {
                'type': 'message',
                'content': encrypted_message,
                'channel': self.current_channel,
                'encrypted': True,
                'sender': self.username,
                'timestamp': timestamp
            }
            
            # Add message to local history immediately (unencrypted)
            local_message = f"[{timestamp}] <{self.username}> {message}"
            self.add_message_to_history(local_message)
            self.refresh_display()
            
            # Send to server
            response = requests.post(
                f"{self.server_manager.get_server_url()}/message",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                if not content:
                    self.entry.delete(0, tk.END)
            else:
                self.add_message_to_history(f"Error sending message: {response.json().get('error')}")
                self.refresh_display()
        except Exception as e:
            self.add_message_to_history(f"Error sending message: {str(e)}")
            self.refresh_display()

    def on_closing(self):
        self.polling = False
        self.root.destroy()

    def save_message_history(self):
        # Create directory if it doesn't exist
        os.makedirs('message_history', exist_ok=True)
        
        # Save history for current channel
        history_file = os.path.join('message_history', f'{self.current_channel.replace("#", "")}.json')
        try:
            with open(history_file, 'w') as f:
                json.dump(self.message_history[self.current_channel], f)
        except Exception as e:
            print(f"Error saving message history: {e}")

    def load_message_history(self):
        try:
            history_file = os.path.join('message_history', f'{self.current_channel.replace("#", "")}.json')
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.message_history[self.current_channel] = json.load(f)
                    
                    # Display loaded messages
                    self.text_area.config(state='normal')
                    self.text_area.delete(1.0, tk.END)
                    for msg in self.message_history[self.current_channel]:
                        self.display_message(msg)
                    self.text_area.config(state='disabled')
        except Exception as e:
            print(f"Error loading message history: {e}")

    def display_message(self, message):
        self.text_area.config(state='normal')
        
        # Check if this is a file share message
        if ' shared a file: ' in message and '[Preview/Download:' in message:
            # Extract file information using regex
            match = re.match(r'\[(.*?)\] \* (.*?) shared a file: (.*?) \((.*?)\) - \[Preview/Download: (.*?)\]', message)
            if match:
                timestamp, username, filename, size, download_url = match.groups()
                
                # Add the message header
                self.text_area.insert(tk.END, f'[{timestamp}] * {username} shared a file:\n', 'timestamp')
                
                # Create a frame for the file info and buttons
                frame = tk.Frame(self.text_area, bg=self.colors['input_bg'])
                
                # File info
                info_frame = tk.Frame(frame, bg=self.colors['input_bg'])
                info_frame.pack(fill=tk.X, padx=10, pady=5)
                
                # Add appropriate file icon
                ext = os.path.splitext(filename)[1].lower()
                icon = '📄'  # Default icon
                if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                    icon = '🖼️'
                elif ext in ['.mp3', '.wav']:
                    icon = '🎵'
                elif ext in ['.zip', '.rar']:
                    icon = '📦'
                elif ext in ['.pdf']:
                    icon = '📕'
                elif ext in ['.doc', '.docx']:
                    icon = '📝'
                
                tk.Label(
                    info_frame,
                    text=icon,
                    bg=self.colors['input_bg'],
                    font=('Consolas', 10)
                ).pack(side=tk.LEFT, padx=(0, 5))
                
                tk.Label(
                    info_frame,
                    text=filename,
                    fg=self.colors['accent'],
                    bg=self.colors['input_bg'],
                    font=('Consolas', 10, 'bold')
                ).pack(side=tk.LEFT)
                
                tk.Label(
                    info_frame,
                    text=f'({size})',
                    fg=self.colors['fg'],
                    bg=self.colors['input_bg'],
                    font=('Consolas', 9)
                ).pack(side=tk.LEFT, padx=(5, 0))
                
                # Buttons frame
                btn_frame = tk.Frame(frame, bg=self.colors['input_bg'])
                btn_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
                
                # Download button
                download_btn = tk.Button(
                    btn_frame,
                    text='📥 Download',
                    command=lambda url=download_url: self.download_file(url.split('/')[-1]),
                    bg=self.colors['input_bg'],
                    fg=self.colors['accent'],
                    relief='flat',
                    font=('Consolas', 9),
                    cursor='hand2'
                )
                download_btn.pack(side=tk.LEFT, padx=(0, 10))
                
                # Preview button
                preview_btn = tk.Button(
                    btn_frame,
                    text='👁 Preview',
                    command=lambda url=download_url, fname=filename: self.preview_file(url.split('/')[-1], fname),
                    bg=self.colors['input_bg'],
                    fg=self.colors['accent'],
                    relief='flat',
                    font=('Consolas', 9),
                    cursor='hand2'
                )
                preview_btn.pack(side=tk.LEFT)
                
                # Insert the frame into the text area
                self.text_area.window_create(tk.END, window=frame)
                self.text_area.insert(tk.END, '\n')
            else:
                # Check for URLs in the message
                words = message.split()
                current_pos = 0
                
                for word in words:
                    # Simple URL detection
                    if word.startswith(('http://', 'https://', 'www.')):
                        # Add text before the URL
                        before_url = message[current_pos:message.find(word, current_pos)]
                        if before_url:
                            self.text_area.insert(tk.END, before_url)
                        
                        # Add the URL as a clickable link
                        self.text_area.insert(tk.END, word, 'link')
                        self.text_area.tag_bind('link', '<Button-1>', lambda e, url=word: self.open_url(url))
                        self.text_area.tag_configure('link', foreground=self.colors['accent'], underline=True)
                        
                        current_pos = message.find(word, current_pos) + len(word)
                    
                # Add any remaining text
                remaining_text = message[current_pos:]
                if remaining_text:
                    self.text_area.insert(tk.END, remaining_text)
                
                self.text_area.insert(tk.END, '\n')
        else:
            self.text_area.insert(tk.END, f"{message}\n")
        
        self.text_area.config(state='disabled')
        self.text_area.yview(tk.END)

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def show_user_profile(self, username):
        # Create profile popup window
        profile_window = tk.Toplevel(self.root)
        profile_window.title(f"User Profile - {username}")
        profile_window.configure(bg=self.colors['bg'])
        profile_window.geometry("300x400")
        
        # Profile picture (placeholder)
        profile_frame = tk.Frame(profile_window, bg=self.colors['bg'])
        profile_frame.pack(pady=20)
        
        # Create a canvas for the circular profile picture
        canvas_size = 150
        canvas = tk.Canvas(
            profile_frame,
            width=canvas_size,
            height=canvas_size,
            bg=self.colors['bg'],
            highlightthickness=0
        )
        canvas.pack()
        
        # Draw circular background
        canvas.create_oval(
            2, 2, canvas_size-2, canvas_size-2,
            fill=self.colors['accent'],
            width=2
        )
        
        # Draw placeholder initials
        initials = username[0].upper()
        canvas.create_text(
            canvas_size/2,
            canvas_size/2,
            text=initials,
            fill=self.colors['bg'],
            font=('Consolas', 48, 'bold')
        )
        
        # Username
        tk.Label(
            profile_window,
            text=username,
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 16, 'bold')
        ).pack(pady=10)
        
        # Member since
        tk.Label(
            profile_window,
            text="Member since: " + datetime.now().strftime("%Y-%m-%d"),
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10)
        ).pack()
        
        # Center the window
        profile_window.update_idletasks()
        x = (profile_window.winfo_screenwidth() - profile_window.winfo_width()) // 2
        y = (profile_window.winfo_screenheight() - profile_window.winfo_height()) // 2
        profile_window.geometry(f"+{x}+{y}")

    def update_user_list(self, users):
        self.users_list.delete(0, tk.END)
        for user in users:
            # Create a frame for each user
            user_item = tk.Frame(self.users_list, bg=self.colors['input_bg'])
            
            # Username button
            btn = tk.Button(
                user_item,
                text=user,
                fg=self.colors['fg'],
                bg=self.colors['input_bg'],
                relief='flat',
                font=('Consolas', 10),
                command=lambda u=user: self.show_user_profile(u),
                cursor='hand2'
            )
            btn.pack(fill=tk.X, padx=2, pady=1)
            
            # Add the user to the listbox
            self.users_list.insert(tk.END, user)

if __name__ == "__main__":
    LoginWindow()
