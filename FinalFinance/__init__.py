from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from typing import Optional
import os
import uuid

from .routes import routes
from .config import Config
from .database import init_db
from .models import User, AdminUser
from .admin import init_admin

import logging
import logging.config


def create_app() -> Flask:
    """
    Create and configure an instance of the Flask application.

    This function:
    - Loads environment variables from a .env file.
    - Configures logging.
    - Initializes the Flask app with configuration settings.
    - Sets up the database and login manager.
    - Registers blueprints and admin interface.
    - Loads the ADMIN_PIN from environment variables.

    Returns:
        Flask: The configured Flask application instance.
    """
    # Load environment variables from a .env file
    load_dotenv()

    try:
        # Configure logging from the logging configuration file
        logging.config.fileConfig('../logging.conf')
        logging.info('Logging configured successfully')
    except Exception as e:
        # Fall back to basic logging if configuration fails
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Error configuring logging: {e}")

    # Create a new Flask application instance
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)  # Load configuration from Config class

    # Initialize the database with the Flask app
    init_db(app)

    # Set up Flask-Login for user session management
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'  # Set the login view endpoint

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """
        Load a user from the database by their user ID.

        Args:
            user_id (str): The UUID of the user to load.

        Returns:
            Optional[User]: The user if found, otherwise None.
        """
        try:
            uid = uuid.UUID(user_id)  # Convert user_id to UUID
        except ValueError:
            return None  # Return None if user_id is not a valid UUID
        user = User.query.get(uid)  # Query for a User object
        if user:
            return user
        return AdminUser.query.get(uid)  # Query for an AdminUser object if User not found

    # Register the application routes
    app.register_blueprint(routes)

    # Initialize the admin interface
    init_admin(app)

    # Load the ADMIN_PIN from environment variables
    app.config['ADMIN_PIN'] = os.getenv('ADMIN_PIN')

    # Log that the application has started
    logger = logging.getLogger('sLogger')
    logger.info('Application started')

    return app
