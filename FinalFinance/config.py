import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()


class Config(object):
    """
    Configuration class for the Flask application.

    This class uses environment variables to configure various aspects of the Flask app,
    including the database URI, session management, and user agent settings.

    Attributes:
        SQLALCHEMY_DATABASE_URI (str): The URI for the database connection.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Flag to disable Flask-SQLAlchemy's event system.
        SECRET_KEY (str): Secret key for session management and cryptographic operations.
        USER_AGENT (str): User agent string for making HTTP requests.
    """

    # The URI for the database connection, fetched from the environment variable 'DATABASE_URL'
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL')

    # Disable Flask-SQLAlchemy event system to reduce overhead
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Secret key for session management and cryptographic operations, fetched from 'SECRET_KEY'
    SECRET_KEY: str = os.environ.get('SECRET_KEY')

    # User agent string for making HTTP requests, fetched from 'USER_AGENT'
    USER_AGENT: str = os.environ.get('USER_AGENT')
