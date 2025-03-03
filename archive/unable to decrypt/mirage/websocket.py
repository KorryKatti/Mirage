import json
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, UTC
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: {username: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user's online status
        self.online_users: Set[str] = set()
        # Store pending messages for offline users: {username: [messages]}
        self.pending_messages: Dict[str, List[dict]] = {}
        
    async def connect(self, websocket: WebSocket, username: str):
        """Connect a user to the WebSocket"""
        await websocket.accept()
        self.active_connections[username] = websocket
        self.online_users.add(username)
        
        # Send any pending messages
        if username in self.pending_messages:
            for message in self.pending_messages[username]:
                await self.send_personal_message(message, username)
            # Clear pending messages
            del self.pending_messages[username]
            
        # Notify all users about online status changes
        await self.broadcast_online_users()
        
        logger.info(f"User {username} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, username: str):
        """Disconnect a user from the WebSocket"""
        if username in self.active_connections:
            del self.active_connections[username]
        if username in self.online_users:
            self.online_users.remove(username)
            
        # Notify all users about online status changes
        self.broadcast_online_users_sync()
        
        logger.info(f"User {username} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, username: str):
        """Send a message to a specific user"""
        if username in self.active_connections:
            await self.active_connections[username].send_text(json.dumps(message))
            return True
        else:
            # Store message for when user connects
            if username not in self.pending_messages:
                self.pending_messages[username] = []
            self.pending_messages[username].append(message)
            return False
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users"""
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))
    
    async def broadcast_online_users(self):
        """Broadcast the list of online users to all connected users"""
        message = {
            "type": "online_users",
            "users": list(self.online_users),
            "timestamp": datetime.now(UTC).isoformat()
        }
        await self.broadcast(message)
    
    def broadcast_online_users_sync(self):
        """Non-async version for use in disconnect method"""
        message = {
            "type": "online_users",
            "users": list(self.online_users),
            "timestamp": datetime.now(UTC).isoformat()
        }
        for username, connection in self.active_connections.items():
            try:
                # Create a background task to send the message
                import asyncio
                asyncio.create_task(connection.send_text(json.dumps(message)))
            except Exception as e:
                logger.error(f"Error sending online users update to {username}: {e}")

# Create a global connection manager
manager = ConnectionManager() 