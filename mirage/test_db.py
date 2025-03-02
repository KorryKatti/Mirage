import os
from mirage.database import get_db_connection, init_db
from mirage.auth import get_password_hash
from datetime import datetime, timedelta, UTC

def test_database():
    """Test the SQLite database functionality"""
    print("Testing SQLite database...")
    
    # Ensure database is initialized
    init_db()
    
    # Get connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Test user creation
    username = "testuser"
    password = "testpassword"
    hashed_password = get_password_hash(password)
    
    # Delete test user if exists
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    
    # Create test user
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, hashed_password)
    )
    
    # Verify user was created
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    print(f"User created: {user['username']}")
    
    # Test message creation
    sender = username
    receiver = "recipient"
    content = "Test message"
    created_at = datetime.now(UTC).isoformat()
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
    
    # Create test message
    cursor.execute(
        "INSERT INTO messages (sender, receiver, content, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (sender, receiver, content, created_at, expires_at)
    )
    
    # Verify message was created
    cursor.execute("SELECT * FROM messages WHERE sender = ? AND receiver = ?", (sender, receiver))
    message = cursor.fetchone()
    print(f"Message created: {message['content']}")
    
    # Test blog creation
    title = "Test Blog"
    content = "This is a test blog post"
    author = username
    created_at = datetime.now(UTC).isoformat()
    
    # Create test blog
    cursor.execute(
        "INSERT INTO blogs (title, content, author, created_at) VALUES (?, ?, ?, ?)",
        (title, content, author, created_at)
    )
    
    # Verify blog was created
    cursor.execute("SELECT * FROM blogs WHERE author = ?", (author,))
    blog = cursor.fetchone()
    print(f"Blog created: {blog['title']}")
    
    # Clean up
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    cursor.execute("DELETE FROM messages WHERE sender = ? AND receiver = ?", (sender, receiver))
    cursor.execute("DELETE FROM blogs WHERE author = ?", (author,))
    
    conn.commit()
    conn.close()
    
    print("Database test completed successfully!")

if __name__ == "__main__":
    test_database() 