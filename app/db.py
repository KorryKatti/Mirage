
import sqlite3
from app.config import DB_FILE

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    # Optional: conn.row_factory = sqlite3.Row
    return conn

def migrate_existing_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Ensure all columns exist in user_profile
    try:
        c.execute('ALTER TABLE user_profile ADD COLUMN upvotes INTEGER DEFAULT 0')
        print("Added upvotes column to user_profile ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print(f"Error adding upvotes to user_profile: {str(e)}")

    try:
        c.execute('ALTER TABLE user_profile ADD COLUMN downvotes INTEGER DEFAULT 0')
        print("Added downvotes column to user_profile ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print(f"Error adding downvotes to user_profile: {str(e)}")

    # Get all existing users
    c.execute('SELECT username FROM users')
    users = c.fetchall()
    
    for (username,) in users:
        # Check if user exists in user_profile
        c.execute('SELECT 1 FROM user_profile WHERE username=?', (username,))
        if not c.fetchone():
            # Initialize stats for user
            c.execute('''
                INSERT INTO user_profile (username, followers, following, posts, upvotes, downvotes)
                VALUES (?, 0, 0, 0, 0, 0)
            ''', (username,))
            
        # Update stats based on actual data
        # Update post count
        c.execute('SELECT COUNT(*) FROM posts WHERE username=?', (username,))
        post_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET posts=? WHERE username=?', (post_count, username))
        
        # Update follower count
        c.execute('SELECT COUNT(*) FROM following WHERE following=?', (username,))
        follower_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET followers=? WHERE username=?', (follower_count, username))
        
        # Update following count
        c.execute('SELECT COUNT(*) FROM following WHERE follower=?', (username,))
        following_count = c.fetchone()[0]
        c.execute('UPDATE user_profile SET following=? WHERE username=?', (following_count, username))
        
        # Update upvotes/downvotes (sum of all votes on user's posts)
        c.execute('SELECT SUM(upvotes), SUM(downvotes) FROM posts WHERE username=?', (username,))
        up, down = c.fetchone()
        up = up or 0
        down = down or 0
        c.execute('UPDATE user_profile SET upvotes=?, downvotes=? WHERE username=?', (up, down, username))
    
    conn.commit()
    conn.close()


# init db
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Create tables if they don't exist (without failing if they do)
    tables = {
        'users': '''CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    avatar_url TEXT,
                    description TEXT,
                    password TEXT NOT NULL,
                    token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''',
        'rooms': '''CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_private INTEGER DEFAULT 0,
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''',
        'room_members': '''CREATE TABLE IF NOT EXISTS room_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(room_id) REFERENCES rooms(id),
                    FOREIGN KEY(username) REFERENCES users(username)
                  )''',
        'inbox_messages': '''CREATE TABLE IF NOT EXISTS inbox_messages(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(sender) REFERENCES users(username),
                  FOREIGN KEY(recipient) REFERENCES users(username)
                  )''',
        'user_profile': '''CREATE TABLE IF NOT EXISTS user_profile (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  followers INTEGER DEFAULT 0,
                  following INTEGER DEFAULT 0,
                  posts INTEGER DEFAULT 0,
                  upvotes INTEGER DEFAULT 0,
                  downvotes INTEGER DEFAULT 0,
                  FOREIGN KEY(username) REFERENCES users(username)
                  )''',
        'posts': '''CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upvotes INTEGER DEFAULT 0,
                downvotes INTEGER DEFAULT 0,
                FOREIGN KEY(username) REFERENCES users(username)
                )''',
        'post_votes': '''CREATE TABLE IF NOT EXISTS post_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(username) REFERENCES users(username),
                UNIQUE(post_id, username)
                )''',
        'following': '''CREATE TABLE IF NOT EXISTS following (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower TEXT NOT NULL,
                following TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(follower) REFERENCES users(username),
                FOREIGN KEY(following) REFERENCES users(username),
                UNIQUE(follower, following)
                )''',
        'replies': '''CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(post_id) REFERENCES posts(id),
                FOREIGN KEY(username) REFERENCES users(username)
                )'''
    }

    # Create all tables
    for table_name, create_stmt in tables.items():
        c.execute(create_stmt)
        print(f"Ensured {table_name} table exists")

    # Now safely add columns if they don't exist
    try:
        c.execute('ALTER TABLE posts ADD COLUMN upvotes INTEGER DEFAULT 0')
        print("Added upvotes column to posts table ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("upvotes column already exists in posts table")
        else:
            print(f"Error adding upvotes column: {str(e)}")

    try:
        c.execute('ALTER TABLE posts ADD COLUMN downvotes INTEGER DEFAULT 0')
        print("Added downvotes column to posts table ✅")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("downvotes column already exists in posts table")
        else:
            print(f"Error adding downvotes column: {str(e)}")

    conn.commit()
    conn.close()
    print("Database initialization completed")
