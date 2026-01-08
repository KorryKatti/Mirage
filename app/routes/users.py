
from flask import Blueprint, request, jsonify
import sqlite3
from app.db import get_db_connection

users_bp = Blueprint('users', __name__)

@users_bp.route('/api/user/<username>',methods=['GET'])
def get_user(username):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get basic user info
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error':'user not found'}),404
    
    # Get profile stats from user_profile table
    c.execute('SELECT followers, following, posts, upvotes, downvotes FROM user_profile WHERE username=?', (username,))
    profile_stats = c.fetchone()
    
    conn.close()
    
    user_data = {
        'username': row[1],
        'avatar_url': row[3],
        'description': row[4],
        'created_at': row[6],
        'stats': {
            'followers': profile_stats[0] if profile_stats else 0,
            'following': profile_stats[1] if profile_stats else 0,
            'posts': profile_stats[2] if profile_stats else 0,
            'upvotes': profile_stats[3] if profile_stats else 0,
            'downvotes': profile_stats[4] if profile_stats else 0
        }
    }

    return jsonify(user_data),200

# Follow/Unfollow endpoints
@users_bp.route('/api/follow', methods=['POST'])
def follow_user():
    data = request.get_json()
    token = request.headers.get('Authorization')
    target_username = data.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Check if target exists
    c.execute('SELECT username FROM users WHERE username=?', (target_username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    # Check if already following
    c.execute('SELECT * FROM following WHERE follower=? AND following=?', (username, target_username))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'already following'}), 400

    # Create follow relationship
    c.execute('INSERT INTO following (follower, following) VALUES (?, ?)', (username, target_username))
    
    # Update follower counts
    c.execute('UPDATE user_profile SET following = following + 1 WHERE username=?', (username,))
    c.execute('UPDATE user_profile SET followers = followers + 1 WHERE username=?', (target_username,))

    conn.commit()
    conn.close()
    return jsonify({'message': f'now following {target_username}'}), 200

@users_bp.route('/api/unfollow', methods=['POST'])
def unfollow_user():
    data = request.get_json()
    token = request.headers.get('Authorization')
    target_username = data.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Remove follow relationship
    c.execute('DELETE FROM following WHERE follower=? AND following=?', (username, target_username))
    
    if c.rowcount == 0:
        conn.close()
        return jsonify({'error': 'not following this user'}), 400

    # Update follower counts
    c.execute('UPDATE user_profile SET following = following - 1 WHERE username=?', (username,))
    c.execute('UPDATE user_profile SET followers = followers - 1 WHERE username=?', (target_username,))

    conn.commit()
    conn.close()
    return jsonify({'message': f'unfollowed {target_username}'}), 200

@users_bp.route('/api/check_follow', methods=['GET'])
def check_follow():
    token = request.headers.get('Authorization')
    target_username = request.args.get('username')

    if not token or not target_username:
        return jsonify({'error': 'missing fields'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # Get current user
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]

    # Check if following
    c.execute('SELECT * FROM following WHERE follower=? AND following=?', (username, target_username))
    is_following = bool(c.fetchone())

    conn.close()
    return jsonify({'is_following': is_following}), 200


@users_bp.route('/api/get_followers/<username>', methods=['GET'])
def get_followers(username):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404
    
    # Get followers with their avatars
    c.execute('''
        SELECT u.username, u.avatar_url 
        FROM following f
        JOIN users u ON f.follower = u.username
        WHERE f.following = ?
        ORDER BY f.created_at DESC
    ''', (username,))
    
    followers = [{'username': row[0], 'avatar_url': row[1] or 'default.png'} for row in c.fetchall()]
    conn.close()
    
    return jsonify({'followers': followers}), 200

@users_bp.route('/api/get_following/<username>', methods=['GET'])
def get_following(username):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT 1 FROM users WHERE username=?', (username,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404
    
    # Get following with their avatars
    c.execute('''
        SELECT u.username, u.avatar_url 
        FROM following f
        JOIN users u ON f.following = u.username
        WHERE f.follower = ?
        ORDER BY f.created_at DESC
    ''', (username,))
    
    following = [{'username': row[0], 'avatar_url': row[1] or 'default.png'} for row in c.fetchall()]
    conn.close()
    
    return jsonify({'following': following}), 200
