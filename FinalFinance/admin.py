from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from models import User, FundData, Submission, FundHoldings, AddFundToFavorites, AdminUser
from database import db


class AdminModelView(ModelView):
    def is_accessible(self):
        if hasattr(current_user, 'admin_rights'):
            return current_user.is_authenticated and current_user.admin_rights
        return False


def init_admin(app):
    admin = Admin(app, name='FinalFinance Admin', template_mode='bootstrap3')
    admin.add_view(AdminModelView(User, db.session))
    admin.add_view(AdminModelView(FundData, db.session))
    admin.add_view(AdminModelView(Submission, db.session))
    admin.add_view(AdminModelView(FundHoldings, db.session))
    admin.add_view(AdminModelView(AddFundToFavorites, db.session))
    admin.add_view(AdminModelView(AdminUser, db.session))
