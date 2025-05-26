import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for session management and CSRF protection
    # It's crucial to set this in your environment variables for production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_strong_default_secret_key_for_dev_only'

    # Database configuration
    # Defaults to SQLite in a 'site.db' file in the instance folder if DATABASE_URL is not set
    # The instance folder is outside the app package and can hold instance-specific data like the database file
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '..', 'instance', 'site.db') # Changed path to instance folder

    # Disable modification tracking for SQLAlchemy, as it's not needed and adds overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False
