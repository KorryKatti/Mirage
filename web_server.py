import os
import json
import threading
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

class WebServer:
    def __init__(self, users_file='/home/korry/Documents/github/mirage/users.json'):
        self.app = Flask(__name__, template_folder='/home/korry/Documents/github/mirage/templates')
        CORS(self.app)
        self.users_file = users_file
        self.setup_routes()
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_users(self, users):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)
    
    def setup_routes(self):
        """Set up Flask routes"""
        @self.app.route('/profile/<username>')
        def profile(username):
            # Load users
            users = self.load_users()
            
            # Check if user exists
            if username not in users:
                return "User not found", 404
            
            # Get user data
            user_data = users[username]
            
            # Prepare comments (most recent first)
            comments = user_data.get('comments', [])
            comments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return render_template(
                'profile.html', 
                username=username, 
                avatar_url=user_data.get('avatar_url', 'https://via.placeholder.com/150'),
                bio=user_data.get('bio', 'No bio provided'),
                comments=comments
            )
        
        @self.app.route('/add_comment', methods=['POST'])
        def add_comment():
            # Get comment data
            data = request.json
            
            # Validate input
            if not all(key in data for key in ['username', 'target_user', 'comment']):
                return jsonify({'success': False, 'message': 'Invalid input'}), 400
            
            # Load users
            users = self.load_users()
            
            # Validate users
            if data['username'] not in users or data['target_user'] not in users:
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Prepare comment
            import uuid
            from datetime import datetime
            
            comment_data = {
                'id': str(uuid.uuid4()),
                'username': data['username'],
                'comment': data['comment'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Add comment to user's profile
            if 'comments' not in users[data['target_user']]:
                users[data['target_user']]['comments'] = []
            
            users[data['target_user']]['comments'].insert(0, comment_data)
            
            # Limit comments to last 50
            users[data['target_user']]['comments'] = users[data['target_user']]['comments'][:50]
            
            # Save updated users
            self.save_users(users)
            
            return jsonify({
                'success': True, 
                'comment': comment_data
            })
    
    def run(self, host='localhost', port=5000):
        """Run the Flask server"""
        self.app.run(host=host, port=port, debug=True, use_reloader=False)
    
    def start_in_thread(self, host='localhost', port=5000):
        """Start the server in a separate thread"""
        server_thread = threading.Thread(target=self.run, kwargs={'host': host, 'port': port}, daemon=True)
        server_thread.start()
        return server_thread

# Create templates directory if it doesn't exist
os.makedirs('/home/korry/Documents/github/mirage/templates', exist_ok=True)
