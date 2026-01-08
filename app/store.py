
import json
import os
from app.config import MESSAGES_FILE

# Load messages from file if exists, else create file
def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    else:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f)

# Global messages list
messages = load_messages()
