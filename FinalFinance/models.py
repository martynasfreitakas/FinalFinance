from .database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import date


class FundData(db.Model):
    """
    Model representing fund data.

    Attributes:
        id (UUID): Primary key, unique identifier for each fund.
        fund_name (str): Name of the fund.
        cik (str): Central Index Key of the fund.
        submissions (relationship): Relationship to the Submission model.
        fund_holdings (relationship): Relationship to the FundHoldings model.
        favorites (relationship): Relationship to the AddFundToFavorites model.
    """
    __tablename__ = 'fund_data'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_name = db.Column(db.String(80), nullable=False)
    cik = db.Column(db.String(10), nullable=False)
    submissions = db.relationship('Submission', back_populates='fund_data', cascade="all, delete-orphan")
    fund_holdings = db.relationship('FundHoldings', back_populates='fund_data', cascade="all, delete-orphan")
    favorites = db.relationship('AddFundToFavorites', back_populates='fund', cascade="all, delete-orphan")


class Submission(db.Model):
    """
    Model representing a submission.

    Attributes:
        id (UUID): Primary key, unique identifier for each submission.
        cik (str): Central Index Key of the company.
        company_name (str): Name of the company.
        submission_type (str): Type of the submission.
        filed_of_date (date): Date when the submission was filed.
        accession_number (str): Accession number of the submission.
        period_of_portfolio (str): Period of the portfolio.
        fund_data_id (UUID): Foreign key linking to FundData.
        fund_data (relationship): Relationship to the FundData model.
        fund_portfolio_value (float): Value of the fund's portfolio.
        fund_owns_companies (int): Number of companies the fund owns.
    """
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

    def __init__(self, cik: str, company_name: str, submission_type: str, filed_of_date: date, accession_number: str,
                 period_of_portfolio: str,
                 fund_data_id: UUID, fund_portfolio_value: float = None, fund_owns_companies: int = None):
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
    """
    Model representing fund holdings.

    Attributes:
        id (UUID): Primary key, unique identifier for each holding.
        company_name (str): Name of the company.
        value_usd (float): Value in USD.
        share_amount (float): Amount of shares.
        cusip (str): Committee on Uniform Securities Identification Procedures number.
        cik (str): Central Index Key.
        accession_number (str): Accession number.
        period_of_portfolio (str): Period of the portfolio.
        fund_data_id (UUID): Foreign key linking to FundData.
        fund_data (relationship): Relationship to the FundData model.
    """
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
    """
    Model representing the addition of a fund to a user's favorites.

    Attributes:
        id (UUID): Primary key, unique identifier for each favorite.
        user_id (UUID): Foreign key linking to User.
        fund_id (UUID): Foreign key linking to FundData.
        fund (relationship): Relationship to the FundData model.
        user (relationship): Relationship to the User model.
    """
    __tablename__ = 'add_fund_to_favorites'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    fund_id = db.Column(UUID(as_uuid=True), db.ForeignKey('fund_data.id'), nullable=False)
    fund = db.relationship('FundData', back_populates='favorites')
    user = db.relationship('User', back_populates='favorite_funds')
    __table_args__ = (db.UniqueConstraint('user_id', 'fund_id', name='unique_favorite'),)


class User(UserMixin, db.Model):
    """
    Model representing a user.

    Attributes:
        id (UUID): Primary key, unique identifier for each user.
        name (str): First name of the user.
        surname (str): Last name of the user.
        username (str): Unique username of the user.
        email (str): Unique email address of the user.
        phone_number (str): Unique phone number of the user.
        _password (str): Hashed password of the user.
        favorite_funds (relationship): Relationship to the AddFundToFavorites model.
    """
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

    def get_id(self) -> str:
        """
        Get the unique identifier for the user.

        Returns:
            str: The user's unique identifier.
        """
        return str(self.id)

    @property
    def password(self) -> str:
        """
        Get the hashed password.

        Returns:
            str: The hashed password.
        """
        return self._password

    @password.setter
    def password(self, plaintext_password: str) -> None:
        """
        Set the hashed password.

        Args:
            plaintext_password (str): The plain text password to be hashed.
        """
        self._password = generate_password_hash(plaintext_password)

    @property
    def is_admin(self) -> bool:
        """
        Check if the user is an admin.

        Returns:
            bool: False, as this is the user model.
        """
        return False

    def check_password(self, plaintext_password: str) -> bool:
        """
        Check the password against the hashed password.

        Args:
            plaintext_password (str): The plain text password to be checked.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return check_password_hash(self._password, plaintext_password)


class AdminUser(UserMixin, db.Model):
    """
    Model representing an admin user.

    Attributes:
        id (UUID): Primary key, unique identifier for each admin user.
        username (str): Unique username of the admin user.
        email (str): Unique email address of the admin user.
        password_hash (str): Hashed password of the admin user.
        admin_rights (bool): Indicates if the user has admin rights.
        admin_pin (str): Admin PIN for additional security.
    """
    __tablename__ = 'admin_user'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    admin_rights = db.Column(db.Boolean, default=False)
    admin_pin = db.Column(db.String(255), nullable=False)

    def __init__(self, username: str, email: str, password: str, admin_pin: str, admin_rights: bool = False):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.admin_rights = admin_rights
        self.admin_pin = admin_pin

    def check_password(self, password: str) -> bool:
        """
        Check the password against the hashed password.

        Args:
            password (str): The plain text password to be checked.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return check_password_hash(self.password_hash, password)

    def check_admin_pin(self, pin: str) -> bool:
        """
        Check the provided admin PIN.

        Args:
            pin (str): The admin PIN to be checked.

        Returns:
            bool: True if the PIN matches, False otherwise.
        """
        return self.admin_pin == pin

    def get_id(self) -> str:
        """
        Get the unique identifier for the admin user.

        Returns:
            str: The admin user's unique identifier.
        """
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        """
        Check if the user has admin rights.

        Returns:
            bool: True if the user has admin rights, False otherwise.
        """
        return self.admin_rights
