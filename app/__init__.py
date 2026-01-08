
from flask import Flask
from flask_cors import CORS
from app.db import init_db, migrate_existing_users

def create_app():
    app = Flask(__name__)
    CORS(app, 
         supports_credentials=True,
         resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"], "allow_headers": ["Authorization", "Content-Type"]}}
    )
    
    # Initialize DB
    init_db()
    migrate_existing_users()

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.inbox import inbox_bp
    from app.routes.posts import posts_bp
    from app.routes.users import users_bp
    from app.routes.feed import feed_bp
    from app.routes.upload import upload_bp
    from app.routes.misc import misc_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(inbox_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(misc_bp)

    return app
