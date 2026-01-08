
from flask import Blueprint, request, jsonify
import sqlite3
import random
import re
from collections import Counter
from app.db import get_db_connection

feed_bp = Blueprint('feed', __name__)

@feed_bp.route('/api/fyp',methods=['GET'])
def fyp():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error':'invalid token , please login again'}),401
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE token=?',(token,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error':'unauthorized'}),401
    username = user[0]
    
    followed_users = []
    c.execute('SELECT following FROM following WHERE follower=?',(username,))
    followed = c.fetchall()
    if followed:
        followed_users = [f[0] for f in followed]
    else:
        conn.close()
        return jsonify({'message':'no users being followed , yet'}),200
    
    # Get recent posts from followed users
    recent_posts = []
    # format replacement is necessary for IN clause with dynamic list
    placeholders = ','.join(['?'] * len(followed_users))
    query = 'SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username IN ({}) ORDER BY created_at DESC LIMIT 20'.format(placeholders)
    c.execute(query, followed_users)
    recent_posts = c.fetchall()
    
    if not recent_posts:
        conn.close()
        return jsonify({'message':'no recent posts from followed users'}),200
    
    recent_posts_data = []
    for row in recent_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        recent_posts_data.append(post_data)
        
    # Get global posts (not from followed users)
    global_posts = []
    query_global = 'SELECT id, username, content, created_at, upvotes, downvotes FROM posts WHERE username NOT IN ({}) ORDER BY created_at DESC LIMIT 20'.format(placeholders)
    c.execute(query_global, followed_users)
    global_posts = c.fetchall()
    
    global_posts_data = []
    for row in global_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        global_posts_data.append(post_data)
        
    # Get old/random posts (from the last 100 posts)
    old_posts = []
    c.execute('SELECT id, username, content, created_at, upvotes, downvotes FROM posts ORDER BY created_at ASC LIMIT 100')
    old_posts = c.fetchall()
    
    old_posts_data = []
    for row in old_posts:
        post_data = {
            'id': row[0],
            'username': row[1],
            'content': row[2],
            'created_at': row[3],
            'upvotes': row[4],
            'downvotes': row[5]
        }
        old_posts_data.append(post_data)
    
    conn.close()
    
    # Combine and shuffle the posts
    combined_posts = recent_posts_data + global_posts_data + old_posts_data
    random.shuffle(combined_posts)
    
    # Limit to 30 posts
    combined_posts = combined_posts[:30]
    
    # Extract hashtags from recent global posts
    hashtags = []
    for post in global_posts_data:
        if 'content' in post:
            found_hashtags = re.findall(r'#(\w+)', post['content'])
            hashtags.extend(found_hashtags)
            
    # Get top 3 trending hashtags
    hashtag_counts = Counter(hashtags)
    trending_hashtags = hashtag_counts.most_common(3)
    trending_topics = [f'#{tag}' for tag, count in trending_hashtags]
    
    return jsonify({
        'posts': combined_posts,
        'trending_topics': trending_topics
    }), 200
