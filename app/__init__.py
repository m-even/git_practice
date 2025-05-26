from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login' # The name of the route for logging in

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from flask_dance.contrib.google import make_google_blueprint
    google_bp = make_google_blueprint(
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_to="main.google_login_callback" 
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    from flask_dance.contrib.facebook import make_facebook_blueprint
    facebook_bp = make_facebook_blueprint(
        client_id=os.environ.get("FACEBOOK_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("FACEBOOK_OAUTH_CLIENT_SECRET"),
        scope=["email", "public_profile"],
        redirect_to="main.facebook_login_callback"
    )
    app.register_blueprint(facebook_bp, url_prefix="/login") # Flask-Dance handles /facebook internally

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Make sure models are imported before trying to create tables or run migrations
    from app import models 

    # Integrate Whitenoise for serving static files
    from whitenoise import WhiteNoise
    # Assuming app.static_folder is correctly set to 'static' relative to the app's root path
    # For a typical Flask structure where __init__.py is in 'app/' and static is 'app/static/',
    # app.static_folder would resolve correctly.
    # If static files are in 'app/static' and this __init__.py is in 'app/',
    # then app.static_folder should point to '.../your_project_root/app/static'
    # WhiteNoise(app.wsgi_app, root=app.static_folder) is the standard way.
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=app.static_folder)
    # Add prefix for static files if they are served under /static/
    # Example: app.wsgi_app.add_files(app.static_folder, prefix='static/')
    # This is often handled by Flask's static_url_path, WhiteNoise respects this.

    return app
