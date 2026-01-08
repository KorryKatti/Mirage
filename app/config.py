
# Configuration

DB_FILE = "db.sqlite"
MAX_MESSAGES = 100
MESSAGE_LIFESPAN = 60 * 30 * 30  
MESSAGES_FILE = "messages.txt"

UPLOAD_URL = 'https://cpp-webserver.onrender.com/upload'

# Configure allowed HTML tags/attributes for Markdown
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 
    'i', 'li', 'ol', 'strong', 'ul', 'p', 'br', 'img',
    'h1', 'h2', 'h3', 'h4', 'pre'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title']
}
