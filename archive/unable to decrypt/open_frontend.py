import os
import webbrowser
import sys
from pathlib import Path

def open_frontend():
    """Open the frontend in a web browser"""
    # Get the absolute path to the frontend/index.html file
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "index.html")
    frontend_url = Path(frontend_path).as_uri()
    
    print(f"Opening frontend at: {frontend_url}")
    
    # Open the frontend in the default web browser
    webbrowser.open(frontend_url)

if __name__ == "__main__":
    open_frontend() 