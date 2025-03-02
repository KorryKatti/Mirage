import os
import uuid
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from mirage.auth import create_access_token, get_password_hash, verify_password, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import re
from mirage.database import get_db_connection, row_to_dict

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

class User(BaseModel):
    username: str
    password: str

class Message(BaseModel):
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

@app.get("/")
async def read_root():
    return {"message": "Welcome to Mirage!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/signup")
async def signup(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    
    # Insert new user
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, hashed_password)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find user
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    db_user = cursor.fetchone()
    
    conn.close()
    
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/send-message")
async def send_message(message: Message, current_user: str = Depends(get_current_user)):
    # Verify that the sender is the current user
    if message.sender != current_user:
        raise HTTPException(status_code=403, detail="You can only send messages as yourself")
    
    # Calculate expiration time
    created_at = datetime.now(UTC).isoformat()
    expiration_time = (datetime.now(UTC) + timedelta(hours=message.expiration_hours)).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert message
    cursor.execute(
        "INSERT INTO messages (sender, receiver, content, file_url, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (message.sender, message.receiver, message.content, message.file_url, created_at, expiration_time)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Message sent successfully"}

@app.get("/receive-messages/{username}")
async def receive_messages(username: str, current_user: str = Depends(get_current_user)):
    # Verify that the user is requesting their own messages
    if username != current_user:
        raise HTTPException(status_code=403, detail="You can only access your own messages")
    
    # Get current time
    now = datetime.now(UTC).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find messages for the user that haven't expired
    cursor.execute(
        "SELECT * FROM messages WHERE receiver = ? AND expires_at > ? ORDER BY created_at DESC LIMIT 100",
        (username, now)
    )
    
    messages = [row_to_dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return messages

@app.post("/create-blog")
async def create_blog(blog_post: BlogPost, current_user: str = Depends(get_current_user)):
    # Verify that the author is the current user
    if blog_post.author != current_user:
        raise HTTPException(status_code=403, detail="You can only create blogs as yourself")
    
    created_at = datetime.now(UTC).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert blog post
    cursor.execute(
        "INSERT INTO blogs (title, content, author, created_at) VALUES (?, ?, ?, ?)",
        (blog_post.title, blog_post.content, blog_post.author, created_at)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Blog post created successfully"}

@app.get("/blogs")
async def get_blogs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM blogs ORDER BY created_at DESC LIMIT 100")
    blogs = [row_to_dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return blogs

@app.put("/update-blog/{blog_id}")
async def update_blog(blog_id: int, blog_post: BlogPost, current_user: str = Depends(get_current_user)):
    # Verify that the author is the current user
    if blog_post.author != current_user:
        raise HTTPException(status_code=403, detail="You can only update your own blogs")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find the blog post
    cursor.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,))
    blog = cursor.fetchone()
    
    if not blog:
        conn.close()
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Verify that the user is the author
    if blog["author"] != current_user:
        conn.close()
        raise HTTPException(status_code=403, detail="You can only update your own blogs")
    
    # Update the blog post
    cursor.execute(
        "UPDATE blogs SET title = ?, content = ? WHERE id = ?",
        (blog_post.title, blog_post.content, blog_id)
    )
    
    conn.commit()
    conn.close()
    
    return {"message": "Blog post updated successfully"}

@app.delete("/delete-blog/{blog_id}")
async def delete_blog(blog_id: int, current_user: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find the blog post
    cursor.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,))
    blog = cursor.fetchone()
    
    if not blog:
        conn.close()
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Verify that the user is the author
    if blog["author"] != current_user:
        conn.close()
        raise HTTPException(status_code=403, detail="You can only delete your own blogs")
    
    # Delete the blog post
    cursor.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))
    
    conn.commit()
    conn.close()
    
    return {"message": "Blog post deleted successfully"}

@app.get("/jitsi-link")
async def get_jitsi_link():
    meeting_id = str(uuid.uuid4())
    jitsi_link = f"https://meet.jit.si/{meeting_id}"
    return {"jitsi_link": jitsi_link} 