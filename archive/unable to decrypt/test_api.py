import requests
import json
import time
import sys

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_api():
    """Test the API endpoints"""
    print("Testing API endpoints...")
    
    # Test health check
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Make sure the server is running.")
        print("Run 'python run.py' in a separate terminal to start the server.")
        sys.exit(1)
    
    # Test signup
    signup_data = {
        "username": "testuser",
        "password": "testpassword"
    }
    try:
        response = requests.post(f"{BASE_URL}/signup", json=signup_data)
        print(f"Signup: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Signup failed: {e}")
    
    # Test login
    login_data = {
        "username": "testuser",
        "password": "testpassword"
    }
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        print(f"Login: {response.status_code} - {response.json()}")
        
        # Get access token
        access_token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test send message
        message_data = {
            "sender": "testuser",
            "receiver": "recipient",
            "content": "Hello, this is a test message!",
            "expiration_hours": 24
        }
        response = requests.post(f"{BASE_URL}/send-message", json=message_data, headers=headers)
        print(f"Send message: {response.status_code} - {response.json()}")
        
        # Test receive messages
        response = requests.get(f"{BASE_URL}/receive-messages/testuser", headers=headers)
        print(f"Receive messages: {response.status_code}")
        if response.status_code == 200:
            messages = response.json()
            print(f"Number of messages: {len(messages)}")
            if messages:
                print(f"First message: {messages[0]}")
        
        # Test create blog
        blog_data = {
            "title": "Test Blog",
            "content": "This is a test blog post",
            "author": "testuser"
        }
        response = requests.post(f"{BASE_URL}/create-blog", json=blog_data, headers=headers)
        print(f"Create blog: {response.status_code} - {response.json()}")
        
        # Test get blogs
        response = requests.get(f"{BASE_URL}/blogs")
        print(f"Get blogs: {response.status_code}")
        if response.status_code == 200:
            blogs = response.json()
            print(f"Number of blogs: {len(blogs)}")
            if blogs:
                blog_id = blogs[0]["id"]
                print(f"First blog: {blogs[0]}")
                
                # Test update blog
                update_blog_data = {
                    "title": "Updated Test Blog",
                    "content": "This is an updated test blog post",
                    "author": "testuser"
                }
                response = requests.put(f"{BASE_URL}/update-blog/{blog_id}", json=update_blog_data, headers=headers)
                print(f"Update blog: {response.status_code} - {response.json()}")
                
                # Test delete blog
                response = requests.delete(f"{BASE_URL}/delete-blog/{blog_id}", headers=headers)
                print(f"Delete blog: {response.status_code} - {response.json()}")
        
        # Test Jitsi link
        response = requests.get(f"{BASE_URL}/jitsi-link")
        print(f"Jitsi link: {response.status_code} - {response.json()}")
    
    except Exception as e:
        print(f"Test failed: {e}")
    
    print("API test completed!")

if __name__ == "__main__":
    test_api() 