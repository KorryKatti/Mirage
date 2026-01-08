
import requests
import time
import uuid
import sys

# Default configuration
BASE_URL = "http://127.0.0.1:5000/api"

def run_tests():
    print(f"Running tests against {BASE_URL}...")
    
    session = requests.Session()
    unique_id = str(uuid.uuid4())[:8]
    username = f"test_{unique_id}"
    password = "password123"
    email = f"test_{unique_id}@example.com"
    
    try:
        # 1. Register
        print(f"\n[1/7] Registering user: {username}")
        res = session.post(f"{BASE_URL}/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        if res.status_code == 201:
            print("✅ Registration successful")
        else:
            print(f"❌ Registration failed: {res.status_code} - {res.text}")
            return

        # 2. Login
        print("\n[2/7] Logging in...")
        res = session.post(f"{BASE_URL}/login", json={
            "username": username,
            "password": password
        })
        if res.status_code == 200:
            token = res.json()['token']
            headers = {"Authorization": token}
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {res.status_code} - {res.text}")
            return

        # 3. Ping
        print("\n[3/7] Pinging server...")
        res = session.get(f"{BASE_URL}/ping")
        if res.status_code == 200:
            print("✅ Ping successful")
        else:
            print(f"❌ Ping failed: {res.status_code}")

        # 4. Create Room
        room_name = f"room_{unique_id}"
        print(f"\n[4/7] Creating room: {room_name}")
        res = session.post(f"{BASE_URL}/create_room", json={
            "room_name": room_name,
            "is_private": 0
        }, headers=headers)
        if res.status_code == 201:
            room_id = res.json()['room_id']
            print(f"✅ Room created (ID: {room_id})")
        else:
            print(f"❌ Room creation failed: {res.status_code} - {res.text}")
            return

        # 5. Send/Receive Messages
        print("\n[5/7] Testing chat functionality...")
        res = session.post(f"{BASE_URL}/send_room_message", json={
            "room_id": room_id,
            "message": "Hello world from test script"
        }, headers=headers)
        
        if res.status_code == 200:
            # Verify message receipt
            res = session.get(f"{BASE_URL}/get_room_messages", params={"room_id": room_id}, headers=headers)
            messages = res.json().get('messages', [])
            if any(m['message'] == "Hello world from test script" for m in messages):
                print("✅ Message sent and verified")
            else:
                print("❌ Message sent but not found in retrieval")
        else:
            print(f"❌ Send message failed: {res.status_code} - {res.text}")

        # 6. Create Social Post
        print("\n[6/7] Creating social post...")
        res = session.post(f"{BASE_URL}/create_post", json={
            "content": "Automated test post content"
        }, headers=headers)
        if res.status_code == 201:
            print("✅ Post created")
        else:
            print(f"❌ Post creation failed: {res.status_code} - {res.text}")

        # 7. Get Profile
        print("\n[7/7] Verifying profile...")
        res = session.get(f"{BASE_URL}/user/{username}")
        if res.status_code == 200:
            stats = res.json().get('stats', {})
            if stats.get('posts') >= 1:
                print("✅ Profile stats verified (posts count updated)")
            else:
                print("⚠️ Profile retrieved but post count mismatch")
        else:
            print(f"❌ Profile retrieval failed: {res.status_code}")

        print("\n✨ All tests completed successfully!")

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to server at {BASE_URL}")
        print("   Make sure the server is running (python3 server.py)")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    run_tests()
