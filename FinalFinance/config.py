import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()


class Config(object):
    """
    Base configuration class for the Flask application.

    This class uses environment variables to configure various aspects of the Flask app,
    including the database URI, session management, and user agent settings.

    Attributes:
        SQLALCHEMY_DATABASE_URI (str): The URI for the database connection.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Flag to disable Flask-SQLAlchemy's event system.
        SECRET_KEY (str): Secret key for session management and cryptographic operations.
        USER_AGENT (str): User agent string for making HTTP requests.
    """
    # Swich between ENV: $env:FLASK_ENV="enviroment"
    # Check ENV: echo $env:FLASK_ENV

    ENV = 'development'  # Default to development

    # The URI for the database connection, fetched from the environment variable 'DATABASE_URL'
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL')

    # Disable Flask-SQLAlchemy event system to reduce overhead
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Secret key for session management and cryptographic operations, fetched from 'SECRET_KEY'
    SECRET_KEY: str = os.environ.get('SECRET_KEY')

    # User agent string for making HTTP requests, fetched from 'USER_AGENT'
    USER_AGENT: str = os.environ.get('USER_AGENT')


class DevelopmentConfig(Config):
    """
    Development configuration class for the Flask application.
    """
    DEBUG = True


class TestingConfig(Config):
    """
    Testing configuration class for the Flask application.

    This class overrides the default configuration with settings suitable for testing,
    such as using a dedicated PostgreSQL database.
    """
    ENV = 'testing'
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')  # Dedicated PostgreSQL test database
    WTF_CSRF_ENABLED = False  # Disable CSRF protection for easier testing
    DEBUG = True


class ProductionConfig(Config):
    """
    Production configuration class for the Flask application.

    This class overrides the default configuration with settings suitable for production,
    including a production database URI, disabling debug mode, and enabling secure settings.
    """
    ENV = 'production'
    DEBUG = False  # Disable debug mode in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URL')  # Production database URL
    SECRET_KEY = os.environ.get('PRODUCTION_SECRET_KEY')  # Production secret key
    USER_AGENT = os.environ.get('USER_AGENT')  # You may keep the same User-Agent


def get_config(env=None):
    """
    Get the appropriate configuration class based on the environment.

    Args:
        env (str): The environment string (e.g., 'development', 'testing', 'production').

    Returns:
        Config: The configuration class for the specified environment.
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')  # Default to development
    config_mapping = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }
    return config_mapping.get(env, Config)
