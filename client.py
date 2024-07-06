import tkinter as tk
from tkinter import scrolledtext, END
import json

def setup_gui():
    # Read username from JSON file
    with open('userinfo.json', 'r') as file:
        user_info = json.load(file)
        username = user_info.get('username', 'User123')  # Default username if not found in file

    # Dark mode colors
    bg_color = "#1e1e1e"  # Background color
    fg_color = "#ffffff"  # Foreground (text) color
    chat_bg_color = "#2e2e2e"  # Chat display background color
    listbox_bg_color = "#333333"  # Listbox background color

    root = tk.Tk()
    root.title("Mirage Chat App")

    # Main frame for the entire app
    main_frame = tk.Frame(root, bg=bg_color)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Label to display username
    username_label = tk.Label(main_frame, text=f"Logged in as: {username}", bg=bg_color, fg=fg_color)
    username_label.pack(pady=10)

    # Frame for room selection (to be implemented)
    room_frame = tk.Frame(main_frame, bg=bg_color)
    room_frame.pack(pady=10)

    # Label and listbox for room selection (example)
    tk.Label(room_frame, text="Room Selection", bg=bg_color, fg=fg_color).pack()
    room_listbox = tk.Listbox(room_frame, height=5, bg=listbox_bg_color, fg=fg_color)
    room_listbox.pack()

    # Chat display area
    chat_display = scrolledtext.ScrolledText(main_frame, width=60, height=20, bg=chat_bg_color, fg=fg_color)
    chat_display.pack(pady=10, padx=10)

    # Frame for user list
    user_list_frame = tk.Frame(main_frame, bg=bg_color)
    user_list_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

    # Label for user list
    tk.Label(user_list_frame, text="Users", bg=bg_color, fg=fg_color).pack()

    # Listbox for user list (example)
    user_listbox = tk.Listbox(user_list_frame, width=20, bg=listbox_bg_color, fg=fg_color)
    user_listbox.pack()

    # Example: Adding users to user list
    users = ["User1", "User2", "User3", "Moderator1", "User4"]
    for user in users:
        user_listbox.insert(tk.END, user)

    root.mainloop()

# Call the function to setup and run the GUI
setup_gui()
