import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from datetime import datetime
import threading
import time
import requests
import json

HOST = '127.0.0.1'
PORT = 6667
BASE_URL = f'http://{HOST}:{PORT}/api'

class LoginWindow:
    def __init__(self):
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
    
    def register(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        try:
            response = requests.post(f'{BASE_URL}/register', json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "Registration successful! You can now login.")
            else:
                messagebox.showerror("Error", response.json().get('error', 'Registration failed'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")
    
    def login(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        try:
            response = requests.post(f'{BASE_URL}/login', json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.root.destroy()
                MirageClient(data['token'], data['username'], data['channels'])
            else:
                messagebox.showerror("Error", response.json().get('error', 'Login failed'))
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {str(e)}")

class MirageClient:
    def __init__(self, token, username, channels):
        self.token = token
        self.username = username
        self.current_channel = '#general'
        
        self.root = tk.Tk()
        self.root.title(f"Mirage IRC - {username}")
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
        
        # Create channel list
        self.channels_frame = tk.Frame(
            self.main_frame,
            bg=self.colors['input_bg'],
            width=150
        )
        self.channels_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        
        # Channel list label
        tk.Label(
            self.channels_frame,
            text="CHANNELS",
            fg=self.colors['accent'],
            bg=self.colors['input_bg'],
            font=('Consolas', 10, 'bold')
        ).pack(padx=10, pady=10, anchor='w')
        
        self.channels_list = tk.Listbox(
            self.channels_frame,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            selectbackground=self.colors['accent'],
            selectforeground=self.colors['fg'],
            relief='flat',
            font=('Consolas', 10),
            width=20
        )
        self.channels_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat area container
        chat_container = tk.Frame(self.main_frame, bg=self.colors['bg'])
        chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Channel label
        self.channel_label = tk.Label(
            chat_container,
            text="#general",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 10, 'bold')
        )
        self.channel_label.pack(anchor='w')
        
        # Chat area
        self.text_area = scrolledtext.ScrolledText(
            chat_container,
            state='disabled',
            wrap='word',
            height=20,
            bg=self.colors['input_bg'],
            fg=self.colors['fg'],
            font=('Consolas', 10),
            insertbackground=self.colors['fg']
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Input frame
        input_frame = tk.Frame(chat_container, bg=self.colors['bg'])
        input_frame.pack(fill=tk.X, pady=10)
        
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
        
        # Status bar
        self.status_bar = tk.Label(
            chat_container,
            text="Connected to server",
            fg=self.colors['fg'],
            bg=self.colors['bg'],
            font=('Consolas', 8),
            anchor='w'
        )
        self.status_bar.pack(fill=tk.X)
        
        # Initialize channels
        for channel in channels:
            self.channels_list.insert(tk.END, channel)
        
        # Start polling thread
        self.polling = True
        threading.Thread(target=self.poll_messages, daemon=True).start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.geometry("1000x600")
        self.root.mainloop()
    
    def add_message(self, message):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, f"{message}\n")
        self.text_area.config(state='disabled')
        self.text_area.yview(tk.END)
    
    def send_message(self, event=None):
        message = self.entry.get().strip()
        if not message:
            return
        
        headers = {'Authorization': self.token}
        
        if message.startswith('/'):
            # Handle commands
            data = {
                'type': 'command',
                'content': message,
                'channel': self.current_channel
            }
        else:
            data = {
                'type': 'message',
                'content': message,
                'channel': self.current_channel
            }
        
        try:
            response = requests.post(f'{BASE_URL}/message', 
                                   headers=headers,
                                   json=data)
            if response.status_code == 200:
                self.entry.delete(0, tk.END)
            else:
                self.add_message(f"Error sending message: {response.json().get('error')}")
        except Exception as e:
            self.add_message(f"Error sending message: {str(e)}")
    
    def poll_messages(self):
        while self.polling:
            try:
                response = requests.get(f'{BASE_URL}/poll',
                                      headers={'Authorization': self.token})
                
                if response.status_code == 200:
                    data = response.json()
                    for message in data['messages']:
                        self.add_message(message)
                    
                    # Update user lists for channels
                    # Implementation for user list updates would go here
                
                elif response.status_code == 401:
                    self.polling = False
                    messagebox.showerror("Error", "Session expired")
                    self.root.destroy()
                    return
            except Exception as e:
                print(f"Polling error: {str(e)}")
            
            time.sleep(1)
    
    def on_closing(self):
        self.polling = False
        self.root.destroy()

if __name__ == "__main__":
    LoginWindow()
