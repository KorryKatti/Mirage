import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

# Ensure the data directory exists
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)

# Database path
DB_PATH = os.path.join(data_dir, "mirage.db")

def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        content TEXT NOT NULL,
        file_url TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )
    ''')
    
    # Create blogs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

# Helper function to convert SQLite row to dict
def row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

# Initialize the database on import
init_db() 