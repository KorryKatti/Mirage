import os
import uuid
import threading
import json
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, Query, WebSocket, WebSocketDisconnect, Cookie, status
from pydantic import BaseModel
from mirage.auth import create_access_token, get_password_hash, verify_password, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import re
from mirage.database import get_db_connection, row_to_dict
from mirage.websocket import manager

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware to allow requests from any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Custom CORS middleware to allow specific patterns
class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        if origin and (re.match(r"https?://.*\.github\.io", origin) or re.match(r"https?://.*\.is-a\.dev", origin) or origin == "null"):
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            return response
        return await call_next(request)

app.add_middleware(CustomCORSMiddleware)

# Thread-local storage for database connections
thread_local = threading.local()

def get_thread_db_connection():
    """Get a database connection for the current thread"""
    if not hasattr(thread_local, "conn"):
        thread_local.conn = get_db_connection()
    return thread_local.conn

class User(BaseModel):
    username: str
    password: str

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    file_url: str = None
    expiration_hours: int = 24

class WebSocketMessage(BaseModel):
    type: str
    sender: str
    receiver: str
    content: str
    file_url: str = None
    expiration_hours: int = 24

class BlogPost(BaseModel):
    title: str
    content: str
    author: str

# Authentication dependency
async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    scheme, token = authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload["sub"]

# WebSocket authentication
async def get_token_from_cookie(websocket: WebSocket):
    try:
        token = websocket.cookies.get("token")
        if not token:
            # Try to get from query params
            token = websocket.query_params.get("token")
            
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
            
        payload = decode_access_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
            
        return payload["sub"]
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

@app.get("/")
async def read_root():
    return {"message": "Welcome to Mirage!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/signup")
async def signup(user: User):
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    
    # Insert new user
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, hashed_password)
    )
    
    conn.commit()
    
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user: User):
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    # Find user
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    db_user = cursor.fetchone()
    
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    # Create a response with a cookie
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=os.getenv("ENVIRONMENT", "development") == "production"  # Secure in production
    )
    
    return response

@app.post("/send-message")
async def send_message(message: Message, current_user: str = Depends(get_current_user)):
    # Verify that the sender is the current user
    if message.sender != current_user:
        raise HTTPException(status_code=403, detail="You can only send messages as yourself")
    
    # Calculate expiration time
    created_at = datetime.now(UTC).isoformat()
    expiration_time = (datetime.now(UTC) + timedelta(hours=message.expiration_hours)).isoformat()
    
    # Use a thread to handle database operations
    def db_operation():
        conn = get_thread_db_connection()
        cursor = conn.cursor()
        
        # Insert message
        cursor.execute(
            "INSERT INTO messages (sender, receiver, content, file_url, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (message.sender, message.receiver, message.content, message.file_url, created_at, expiration_time)
        )
        
        conn.commit()
    
    # Run database operation in a thread
    thread = threading.Thread(target=db_operation)
    thread.start()
    thread.join()
    
    # Try to send message via WebSocket if receiver is online
    ws_message = {
        "type": "new_message",
        "sender": message.sender,
        "receiver": message.receiver,
        "content": message.content,
        "file_url": message.file_url,
        "created_at": created_at,
        "expires_at": expiration_time
    }
    
    # This is non-blocking and will store the message if user is offline
    await manager.send_personal_message(ws_message, message.receiver)
    
    return {"message": "Message sent successfully"}

@app.get("/receive-messages/{username}")
async def receive_messages(
    username: str, 
    current_user: str = Depends(get_current_user),
    sent: bool = Query(False, description="If true, return messages sent by the user instead of received"),
    since: float = Query(0, description="Timestamp to get messages since (in seconds since epoch)")
):
    # Verify that the user is requesting their own messages
    if username != current_user:
        raise HTTPException(status_code=403, detail="You can only access your own messages")
    
    # Get current time
    now = datetime.now(UTC).isoformat()
    
    # Convert since to ISO format if provided
    since_iso = datetime.fromtimestamp(since, UTC).isoformat() if since > 0 else "1970-01-01T00:00:00+00:00"
    
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    if sent:
        # Find messages sent by the user that haven't expired and are newer than since
        cursor.execute(
            "SELECT * FROM messages WHERE sender = ? AND expires_at > ? AND created_at > ? ORDER BY created_at DESC LIMIT 100",
            (username, now, since_iso)
        )
    else:
        # Find messages received by the user that haven't expired and are newer than since
        cursor.execute(
            "SELECT * FROM messages WHERE receiver = ? AND expires_at > ? AND created_at > ? ORDER BY created_at DESC LIMIT 100",
            (username, now, since_iso)
        )
    
    messages = [row_to_dict(row) for row in cursor.fetchall()]
    
    return messages

@app.get("/users")
async def get_users(current_user: str = Depends(get_current_user)):
    """Get a list of all users except the current user"""
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM users WHERE username != ? ORDER BY username", (current_user,))
    users = [row["username"] for row in cursor.fetchall()]
    
    return users

@app.get("/online-users")
async def get_online_users(current_user: str = Depends(get_current_user)):
    """Get a list of currently online users"""
    return {"online_users": list(manager.online_users)}

@app.post("/create-blog")
async def create_blog(blog_post: BlogPost, current_user: str = Depends(get_current_user)):
    # Verify that the author is the current user
    if blog_post.author != current_user:
        raise HTTPException(status_code=403, detail="You can only create blogs as yourself")
    
    created_at = datetime.now(UTC).isoformat()
    
    # Use a thread to handle database operations
    def db_operation():
        conn = get_thread_db_connection()
        cursor = conn.cursor()
        
        # Insert blog post
        cursor.execute(
            "INSERT INTO blogs (title, content, author, created_at) VALUES (?, ?, ?, ?)",
            (blog_post.title, blog_post.content, blog_post.author, created_at)
        )
        
        conn.commit()
    
    # Run database operation in a thread
    thread = threading.Thread(target=db_operation)
    thread.start()
    thread.join()
    
    return {"message": "Blog post created successfully"}

@app.get("/blogs")
async def get_blogs():
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM blogs ORDER BY created_at DESC LIMIT 100")
    blogs = [row_to_dict(row) for row in cursor.fetchall()]
    
    return blogs

@app.put("/update-blog/{blog_id}")
async def update_blog(blog_id: int, blog_post: BlogPost, current_user: str = Depends(get_current_user)):
    # Verify that the author is the current user
    if blog_post.author != current_user:
        raise HTTPException(status_code=403, detail="You can only update your own blogs")
    
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    # Check if blog exists and belongs to the user
    cursor.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,))
    blog = cursor.fetchone()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    if blog["author"] != current_user:
        raise HTTPException(status_code=403, detail="You can only update your own blogs")
    
    # Update blog
    cursor.execute(
        "UPDATE blogs SET title = ?, content = ? WHERE id = ?",
        (blog_post.title, blog_post.content, blog_id)
    )
    
    conn.commit()
    
    return {"message": "Blog updated successfully"}

@app.delete("/delete-blog/{blog_id}")
async def delete_blog(blog_id: int, current_user: str = Depends(get_current_user)):
    conn = get_thread_db_connection()
    cursor = conn.cursor()
    
    # Check if blog exists and belongs to the user
    cursor.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,))
    blog = cursor.fetchone()
    
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    if blog["author"] != current_user:
        raise HTTPException(status_code=403, detail="You can only delete your own blogs")
    
    # Delete blog
    cursor.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
    
    conn.commit()
    
    return {"message": "Blog deleted successfully"}

@app.get("/jitsi-link")
async def get_jitsi_link():
    # Generate a random room ID
    room_id = str(uuid.uuid4())
    
    # Get Jitsi domain from environment variable or use default
    jitsi_domain = os.getenv("JITSI_DOMAIN", "meet.jit.si")
    
    # Create Jitsi link
    jitsi_link = f"https://{jitsi_domain}/{room_id}"
    
    return {"jitsi_link": jitsi_link}

# WebSocket endpoint for real-time messaging
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    # Authenticate the user
    authenticated_user = await get_token_from_cookie(websocket)
    
    if not authenticated_user or authenticated_user != username:
        # Authentication failed
        return
    
    # Connect to the WebSocket manager
    await manager.connect(websocket, username)
    
    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            
            try:
                # Parse the message
                message_data = json.loads(data)
                
                # Validate message
                if not isinstance(message_data, dict) or "type" not in message_data:
                    continue
                
                # Handle different message types
                if message_data["type"] == "message":
                    # Ensure sender is the authenticated user
                    if message_data.get("sender") != username:
                        continue
                    
                    receiver = message_data.get("receiver")
                    content = message_data.get("content")
                    file_url = message_data.get("file_url")
                    expiration_hours = message_data.get("expiration_hours", 24)
                    
                    if not receiver or not content:
                        continue
                    
                    # Save message to database
                    created_at = datetime.now(UTC).isoformat()
                    expiration_time = (datetime.now(UTC) + timedelta(hours=expiration_hours)).isoformat()
                    
                    conn = get_thread_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "INSERT INTO messages (sender, receiver, content, file_url, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, receiver, content, file_url, created_at, expiration_time)
                    )
                    
                    conn.commit()
                    
                    # Forward message to receiver
                    ws_message = {
                        "type": "new_message",
                        "sender": username,
                        "receiver": receiver,
                        "content": content,
                        "file_url": file_url,
                        "created_at": created_at,
                        "expires_at": expiration_time
                    }
                    
                    # Send to receiver (will be stored if offline)
                    await manager.send_personal_message(ws_message, receiver)
                    
                    # Send confirmation to sender
                    await manager.send_personal_message({
                        "type": "message_sent",
                        "receiver": receiver,
                        "timestamp": created_at
                    }, username)
                
                elif message_data["type"] == "ping":
                    # Respond with pong to keep connection alive
                    await manager.send_personal_message({"type": "pong"}, username)
                
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                pass
            except Exception as e:
                # Log error but don't crash
                print(f"Error processing WebSocket message: {e}")
    
    except WebSocketDisconnect:
        # Handle disconnection
        manager.disconnect(username) 