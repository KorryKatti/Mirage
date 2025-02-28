# Mirage IRC Client

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
- [Creating an Executable](#creating-an-executable)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contribution Guidelines](#contribution-guidelines)
- [License](#license)

## Overview
Mirage IRC is a chat client application that allows users to connect to an IRC server, join channels, and communicate with other users. This client is built using Python and Tkinter for the GUI.

## Features
- Connect to multiple servers and choose the best one based on load.
- Join and switch between channels.
- Send and receive encrypted messages.
- Upload and download files.
- View user profiles and channel information.

## Requirements
- Python 3.7+
- `requests` library
- `cryptography` library
- `tkinter` (usually included with Python on Windows)
- `PyInstaller` (for creating the executable)

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd Mirage
   ```

2. **Install Dependencies**:
   Ensure you have Python 3.7+ installed. Then, install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Client**:
   ```bash
   python client.py
   ```

## Creating an Executable
To create an executable for the client, use PyInstaller:

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Create the Executable**:
   ```bash
   pyinstaller --onefile --windowed client.py
   ```
   The executable will be located in the `dist` directory.

## Creating a `servers.json` File
To create a `servers.json` file, you can use the following template as a starting point. This file should be placed in the root directory of your project.

```json
{
  "servers": [
    {
      "id": "server1",
      "host": "localhost",
      "port": 5000,
      "max_users": 100
    },
    {
      "id": "server2",
      "host": "localhost",
      "port": 5001,
      "max_users": 100
    }
  ]
}
```

- **id**: A unique identifier for the server.
- **host**: The hostname or IP address of the server.
- **port**: The port number on which the server listens.
- **max_users**: The maximum number of users that can connect to the server.

You can add more server entries as needed, adjusting the `host`, `port`, and `max_users` values to match your server configuration.

## Usage
- **Login/Register**: Use the login window to enter your credentials or register a new account.
- **Join Channels**: Select a channel from the list to join and start chatting.
- **Send Messages**: Type your message in the input field and press Enter to send.
- **Upload Files**: Click the paperclip icon to upload files to the current channel.

## Troubleshooting
- **Connection Issues**: Ensure your internet connection is active and the server is running.
- **Missing Dependencies**: Run `pip install -r requirements.txt` to install any missing libraries.
- **Executable Not Running**: Ensure all necessary files, like `servers.json`, are in the same directory as the executable.

## Contribution Guidelines
We welcome contributions! To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes and push to your fork.
4. Submit a pull request with a description of your changes.

## License
This project is licensed under the MIT License. 