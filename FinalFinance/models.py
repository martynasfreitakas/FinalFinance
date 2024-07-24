from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import UUID
import uuid


class FundData(db.Model):
    __tablename__ = 'fund_data'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_name = db.Column(db.String(80), nullable=False)
    cik = db.Column(db.String(10), nullable=False)
    submissions = db.relationship('Submission', back_populates='fund_data', cascade="all, delete-orphan")
    fund_holdings = db.relationship('FundHoldings', back_populates='fund_data', cascade="all, delete-orphan")
    favorites = db.relationship('AddFundToFavorites', back_populates='fund', cascade="all, delete-orphan")


class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cik = db.Column(db.String(10), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    submission_type = db.Column(db.String(10), nullable=False)
    filed_of_date = db.Column(db.Date, nullable=False)
    accession_number = db.Column(db.String(20), nullable=False)
    period_of_portfolio = db.Column(db.String(50), nullable=False)
    fund_data_id = db.Column(UUID(as_uuid=True), db.ForeignKey('fund_data.id'))
    fund_data = db.relationship('FundData', back_populates='submissions')
    fund_portfolio_value = db.Column(db.Float, nullable=True)
    fund_owns_companies = db.Column(db.Integer, nullable=True)

    def __init__(self, cik, company_name, submission_type, filed_of_date, accession_number, period_of_portfolio,
                 fund_data_id, fund_portfolio_value=None, fund_owns_companies=None):
        self.cik = cik
        self.company_name = company_name
        self.submission_type = submission_type
        self.filed_of_date = filed_of_date
        self.accession_number = accession_number
        self.period_of_portfolio = period_of_portfolio
        self.fund_data_id = fund_data_id
        self.fund_portfolio_value = fund_portfolio_value
        self.fund_owns_companies = fund_owns_companies


class FundHoldings(db.Model):
    __tablename__ = 'fund_holdings'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = db.Column(db.String(200), nullable=False)
    value_usd = db.Column(db.Float, nullable=False)
    share_amount = db.Column(db.Float, nullable=False)
    cusip = db.Column(db.String(9), nullable=False)
    cik = db.Column(db.String(10), nullable=False)
    accession_number = db.Column(db.String(20), nullable=False)
    period_of_portfolio = db.Column(db.String(50), nullable=False)
    fund_data_id = db.Column(UUID(as_uuid=True), db.ForeignKey('fund_data.id'), nullable=False)
    fund_data = db.relationship('FundData', back_populates='fund_holdings')


class AddFundToFavorites(db.Model):
    __tablename__ = 'add_fund_to_favorites'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    fund_id = db.Column(UUID(as_uuid=True), db.ForeignKey('fund_data.id'), nullable=False)
    fund = db.relationship('FundData', back_populates='favorites')
    user = db.relationship('User', back_populates='favorite_funds')
    __table_args__ = (db.UniqueConstraint('user_id', 'fund_id', name='unique_favorite'),)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=True)
    surname = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    _password = db.Column(db.String(225), nullable=False)
    favorite_funds = db.relationship('AddFundToFavorites', back_populates='user', cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint('phone_number', name='unique_phone_number'),
    )

    # Flask-Login’s UserMixin and to provide a unique identifier for each user object:
    def get_id(self):
        return str(self.id)

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, plaintext_password):
        self._password = generate_password_hash(plaintext_password)

    @property
    def is_admin(self):
        return False

    def check_password(self, plaintext_password):
        return check_password_hash(self._password, plaintext_password)


class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_user'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    admin_rights = db.Column(db.Boolean, default=False)
    admin_pin = db.Column(db.String(255), nullable=False)

    def __init__(self, username, email, password, admin_pin, admin_rights=False):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.admin_rights = admin_rights
        self.admin_pin = admin_pin

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def check_admin_pin(self, pin):
        return self.admin_pin == pin

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.admin_rights
