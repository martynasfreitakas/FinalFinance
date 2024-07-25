from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from .models import User, FundData, Submission, FundHoldings, AddFundToFavorites, AdminUser
from .database import db
from flask import Flask


class AdminModelView(ModelView):
    """
    Custom ModelView for Flask-Admin with access control based on user authentication and admin rights.

    This class extends Flask-Admin's ModelView to include custom logic for determining
    whether the current user has access to the admin views.

    Methods:
        is_accessible: Determines if the current user has access to the admin view.
    """

    def is_accessible(self) -> bool:
        """
        Check if the current user has access to the admin view.

        Returns:
            bool: True if the user is authenticated and has admin rights, False otherwise.
        """
        if hasattr(current_user, 'admin_rights'):
            return current_user.is_authenticated and current_user.admin_rights
        return False


def init_admin(app: Flask) -> None:
    """
    Initialize Flask-Admin with model views for the application.

    Args:
        app (Flask): The Flask application instance to initialize admin views for.

    Returns:
        None
    """
    # Create an Admin instance with Bootstrap 3 template mode
    admin = Admin(app, name='FinalFinance Admin', template_mode='bootstrap3')

    # Add model views to the admin interface
    admin.add_view(AdminModelView(User, db.session))
    admin.add_view(AdminModelView(FundData, db.session))
    admin.add_view(AdminModelView(Submission, db.session))
    admin.add_view(AdminModelView(FundHoldings, db.session))
    admin.add_view(AdminModelView(AddFundToFavorites, db.session))
    admin.add_view(AdminModelView(AdminUser, db.session))