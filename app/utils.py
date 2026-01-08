
import hashlib
import markdown
from bleach.sanitizer import Cleaner
import requests
import time
from app.config import UPLOAD_URL, ALLOWED_TAGS, ALLOWED_ATTRIBUTES

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def safe_markdown(text):
    """Convert markdown to sanitized HTML"""
    html = markdown.markdown(text)
    cleaner = Cleaner(tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return cleaner.clean(html)

def file_uploader(file):
    try:
        file.stream.seek(0)
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/octet-stream'
        }

        response = requests.post(
            UPLOAD_URL,
            data=file.stream,
            headers=headers
        )
        response.raise_for_status()
        return response.text.strip()  # assuming server returns the URL or file ID as plain text

    except requests.exceptions.HTTPError as http_err:
        raise Exception(f'HTTP Error: {http_err.response.status_code} - {http_err.response.text}')
    except requests.exceptions.ConnectionError:
        raise Exception('Connection error: Could not connect to the file upload service.')
    except requests.exceptions.Timeout:
        raise Exception('Timeout error: The file upload request took too long.')
    except Exception as err:
        raise Exception(f'Unexpected error during file upload: {str(err)}')

def ping_server(interval=60):
    while True:
        try:
            res = requests.get('https://cpp-webserver.onrender.com', timeout=5)
            print(f'Ping: {res.status_code} - {res.reason}')
        except Exception as e:
            print(f'Ping failed: {e}')
        time.sleep(interval)
