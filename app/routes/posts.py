
from flask import Blueprint, request, jsonify
import sqlite3
from app.db import get_db_connection

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/api/create_post',methods=['POST'])
def create_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    content = data.get('content','')

    if not token:
        return jsonify({'error':'invalid token , please re-login'}),401
    
    if not content:
        return jsonify({'error':'nothing to post'}),400
    
    if len(content) > 512:
        return jsonify({'error':'post content cannot exceed 512 characters'}),400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    
    c.execute('INSERT INTO posts (username,content) VALUES (?,?)',(username,content))
    
    # Update user's post count
    c.execute('UPDATE user_profile SET posts = posts + 1 WHERE username=?', (username,))

    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return jsonify({'message':'post created'}),201


@posts_bp.route('/api/get_posts/<username>',methods=['GET'])
def get_posts(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username=? ORDER BY created_at DESC',(username,))
    rows = c.fetchall()
    conn.close()
    
    posts = []
    for row in rows:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        posts.append(post_data)
    
    return jsonify({'posts': posts}), 200

@posts_bp.route('/api/vote_post',methods=['POST'])
def vote_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    post_id = data.get('post_id')
    vote_type = data.get('vote_type')

    if not token:
        return jsonify({'error':'login to vote'}),401
    if not post_id or not vote_type:
        return jsonify({'error':'missing post_id or vote_type'}),400
    
    if vote_type not in ['up','down']:
        return jsonify({'error':'you can only upvote or downvote'}),400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    
    # check if post exists
    c.execute('SELECT username FROM posts WHERE id=?',(post_id,))
    post = c.fetchone()
    if not post:
        conn.close()
        return jsonify({'error':'post not found'}),404
        
    post_author = post[0]
    if post_author == username:
        conn.close()
        return jsonify({'error':'cannot vote on your own post'}),403
    
    # Check if user already voted
    c.execute('SELECT vote_type FROM post_votes WHERE post_id=? AND username=?', (post_id, username))
    existing_vote = c.fetchone()
    
    if existing_vote:
        # User already voted - handle vote change
        if existing_vote[0] == vote_type:
            conn.close()
            return jsonify({'error':'already voted this way'}), 400
        else:
            # Reverse previous vote
            if existing_vote[0] == 'up':
                c.execute('UPDATE posts SET upvotes = upvotes - 1 WHERE id=?', (post_id,))
                c.execute('UPDATE user_profile SET upvotes = upvotes - 1 WHERE username=?', (post_author,))
            else:
                c.execute('UPDATE posts SET downvotes = downvotes - 1 WHERE id=?', (post_id,))
                c.execute('UPDATE user_profile SET downvotes = downvotes - 1 WHERE username=?', (post_author,))
            
            # Update the vote record
            c.execute('UPDATE post_votes SET vote_type=? WHERE post_id=? AND username=?', 
                      (vote_type, post_id, username))
    else:
        # Record the new vote
        c.execute('INSERT INTO post_votes (post_id, username, vote_type) VALUES (?,?,?)',
                 (post_id, username, vote_type))
    
    # Update vote counts
    if vote_type == 'up':
        c.execute('UPDATE posts SET upvotes = upvotes + 1 WHERE id=?', (post_id,))
        c.execute('UPDATE user_profile SET upvotes = upvotes + 1 WHERE username=?', (post_author,))
    else:
        c.execute('UPDATE posts SET downvotes = downvotes + 1 WHERE id=?', (post_id,))
        c.execute('UPDATE user_profile SET downvotes = downvotes + 1 WHERE username=?', (post_author,))
    
    conn.commit()
    conn.close()
    return jsonify({'message':'vote counted'}),200

@posts_bp.route('/api/reply_to_post', methods=['POST'])
def reply_to_post():
    data = request.get_json()
    token = request.headers.get('Authorization')
    post_id = data.get('post_id')
    content = data.get('content', '')

    if not token:
        return jsonify({'error': 'invalid token, please re-login'}), 401
    
    if not post_id or not content:
        return jsonify({'error': 'missing post_id or content'}), 400
    
    if len(content) > 512:
        return jsonify({'error': 'reply content cannot exceed 512 characters'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?', (token,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 401
    username = user[0]
    
    # Check if post exists
    c.execute('SELECT id FROM posts WHERE id=?', (post_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'post not found'}), 404
    
    # Insert reply into replies table
    c.execute('INSERT INTO replies (post_id, username, content) VALUES (?, ?, ?)', (post_id, username, content))
    
    # Update user's reply count (wait, the original code updated 'posts' count for replies too??)
    # Original code: c.execute('UPDATE user_profile SET posts = posts + 1 WHERE username=?', (username,))
    # Yes, it seems replies count as posts in user_profile stats in the original code.
    c.execute('UPDATE user_profile SET posts = posts + 1 WHERE username=?', (username,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'reply created'}), 201

@posts_bp.route('/api/get_replies/<int:post_id>', methods=['GET'])
def get_replies(post_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if post exists
    c.execute('SELECT id FROM posts WHERE id=?', (post_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'post not found'}), 404
    
    # Get replies for the post
    c.execute('''
        SELECT r.id, r.username, r.content, r.created_at, u.avatar_url 
        FROM replies r
        JOIN users u ON r.username = u.username
        WHERE r.post_id=?
        ORDER BY r.created_at DESC
    ''', (post_id,))
    
    replies = []
    for row in c.fetchall():
        reply_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'avatar_url': row[4] or 'default.png'
        }
        replies.append(reply_data)
    
    conn.close()
    
    return jsonify({'replies': replies}), 200

@posts_bp.route('/api/get_post_by_id/<int:post_id>',methods=['GET'])
def get_post_by_id(post_id):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE id=?', (post_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error':'post not found'}),404
    post_data = {
        'id': row[0],
        'username': row[1],
        'content': row[2],
        'created_at': row[3],
        'upvotes': row[4],
        'downvotes': row[5]
    }

    return jsonify(post_data), 200
