from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import uuid

from .routes import routes
from config import Config
from database import init_db
from models import User, AdminUser
from admin import init_admin

import logging
import logging.config


def create_app():
    load_dotenv()

    try:
        logging.config.fileConfig('../logging.conf')
        logging.info('Logging configured successfully')
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Error configuring logging: {e}")

    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)

    init_db(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'

    @login_manager.user_loader
    def load_user(user_id):
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

    logger = logging.getLogger('sLogger')
    logger.info('Application started')

    return app
