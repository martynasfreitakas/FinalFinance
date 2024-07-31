from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from typing import Optional
import os
import uuid

from .routes import routes
from .config import get_config
from .database import init_db, db
from .models import User, AdminUser, FundData, Submission, FundHoldings, AddFundToFavorites
from .admin import init_admin

import logging
import logging.config


def create_app(config_name=None) -> Flask:
    """
    Create and configure an instance of the Flask application.
    """
    # Load environment variables from a .env file
    load_dotenv()

    # Print the FLASK_ENV variable to verify its value
    print("FLASK_ENV:", os.getenv('FLASK_ENV'))

    logging_conf_path = os.path.join(os.path.dirname(__file__), '..', 'logging.conf')
    logging_conf_path = os.path.abspath(logging_conf_path)

    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        try:
            logging.config.fileConfig(logging_conf_path)
            logging.info('Logging configured successfully')
        except Exception as e:
            logging.basicConfig(level=logging.INFO)
            logging.error(f"Error configuring logging: {e}")

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(get_config(config_name))

    logger = logging.getLogger('sLogger')
    logger.info(f"Application started in {app.config['ENV']} mode")

    init_db(app)

    migrate = Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        user = User.query.get(uid)
        if user:
            return user
        return AdminUser.query.get(uid)

    app.register_blueprint(routes)
    init_admin(app)
    app.config['ADMIN_PIN'] = os.getenv('ADMIN_PIN')

    logger.info('Application started')

    return app
