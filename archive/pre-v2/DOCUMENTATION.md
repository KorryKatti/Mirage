# Mirage IRC API Documentation

## Overview
Mirage IRC is a modern IRC server with HTTP polling and load balancing capabilities. This document describes the API endpoints and how to interact with them to build clients and bots.

## Server Configuration
The server configuration is stored in `servers.json`:
```json
{
    "servers": [
        {
            "id": "server1",
            "host": "127.0.0.1",
            "port": 6667,
            "max_users": 100
        }
    ],
    "health_check_interval": 30
}
```

## Authentication

### Register
- **Endpoint**: `/api/register`
- **Method**: POST
- **Body**:
```json
{
    "username": "string",
    "password": "string"
}
```
- **Response**:
```json
{
    "message": "Registration successful"
}
```
- **Error Response** (409):
```json
{
    "error": "Username already exists"
}
```

### Login
- **Endpoint**: `/api/login`
- **Method**: POST
- **Body**:
```json
{
    "username": "string",
    "password": "string"
}
```
- **Response**:
```json
{
    "token": "string",
    "username": "string",
    "channels": ["string"],
    "server": {
        "id": "string",
        "host": "string",
        "port": number
    }
}
```

## Messaging

### Send Message
- **Endpoint**: `/api/message`
- **Method**: POST
- **Headers**: `Authorization: <token>`
- **Body**:
```json
{
    "type": "message|command",
    "content": "string",
    "channel": "string"
}
```
- **Response**:
```json
{
    "status": "ok"
}
```

### Poll Messages
- **Endpoint**: `/api/poll`
- **Method**: GET
- **Headers**: `Authorization: <token>`
- **Response**:
```json
{
    "messages": ["string"],
    "users": {
        "channel_name": ["username"]
    }
}
```

## Server Information

### Server Stats
- **Endpoint**: `/api/server/stats`
- **Method**: GET
- **Response**:
```json
{
    "id": "string",
    "host": "string",
    "port": number,
    "stats": {
        "start_time": number,
        "total_messages": number,
        "active_users_count": number,
        "cpu_usage": number,
        "memory_usage": number,
        "last_updated": number
    },
    "uptime": number
}
```

## Commands
The following commands can be sent as messages with type "command":

### /nick
Change nickname
```
/nick <new_nickname>
```

### /join
Join a channel
```
/join <channel>
```

### /part
Leave current channel
```
/part
```

### /me
Send an action
```
/me <action>
```

## Building a Bot

Here's a simple example of how to create a bot in Python:

```python
import requests
import time

class MirageBot:
    def __init__(self, host, port, username, password):
        self.base_url = f"http://{host}:{port}/api"
        self.token = None
        self.username = username
        self.password = password
    
    def login(self):
        response = requests.post(
            f"{self.base_url}/login",
            json={
                "username": self.username,
                "password": self.password
            }
        )
        data = response.json()
        self.token = data["token"]
    
    def send_message(self, channel, content):
        requests.post(
            f"{self.base_url}/message",
            headers={"Authorization": self.token},
            json={
                "type": "message",
                "content": content,
                "channel": channel
            }
        )
    
    def poll_messages(self):
        response = requests.get(
            f"{self.base_url}/poll",
            headers={"Authorization": self.token}
        )
        return response.json()
    
    def run(self):
        self.login()
        while True:
            try:
                data = self.poll_messages()
                for message in data["messages"]:
                    # Handle messages here
                    print(message)
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(1)

# Usage
bot = MirageBot("127.0.0.1", 6667, "bot", "password")
bot.run()
```

## Error Handling
The API uses standard HTTP status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 409: Conflict
- 500: Server Error

All error responses include an "error" field with a description of the error.

## Rate Limiting
- Message polling is limited to once per second
- Users are automatically disconnected after 30 seconds of inactivity
- Server stats are updated every 5 seconds

## WebSocket Support (Future)
WebSocket support is planned for future releases to provide real-time updates without polling. 