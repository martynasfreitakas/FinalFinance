from wtforms import StringField, PasswordField, SubmitField, EmailField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Optional, EqualTo
from .utils import (validate_phone_format, validate_name_surname_format_only_str, validate_unique_phone_number,
                    validate_password_strong_password, validate_admin_pin, validate_passwords_match)


class SignUpForm(FlaskForm):
    """
    Form for user sign up.

    This form collects information for new user registration, including username, email,
    name, surname, phone number, and password.

    Attributes:
        username (StringField): Field for entering the username, required.
        email (EmailField): Field for entering the email address, required.
        name (StringField): Optional field for entering the user's first name.
        surname (StringField): Optional field for entering the user's last name.
        phone_number (StringField): Field for entering the phone number, validated for format and uniqueness.
        password (PasswordField): Field for entering the password, required and validated for strength.
        submit (SubmitField): Submit button for the form.
    """
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[Optional(), validate_name_surname_format_only_str])
    surname = StringField('Surname', validators=[Optional(), validate_name_surname_format_only_str])
    phone_number = StringField('Phone Number', validators=[validate_phone_format, validate_unique_phone_number])
    password = PasswordField('Password', validators=[DataRequired(), validate_password_strong_password])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), validate_passwords_match])
    submit = SubmitField('Submit')


class LoginForm(FlaskForm):
    """
    Form for user login.

    This form collects information for user login, including username and password.

    Attributes:
        username (StringField): Field for entering the username, required.
        password (PasswordField): Field for entering the password, required.
        submit (SubmitField): Submit button for the form.
    """
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UpdateProfileForm(FlaskForm):
    """
    Form for updating user profile.

    This form collects information for updating the user's profile details, including name,
    surname, email, phone number, current password, new password, and confirmation of new password.

    Attributes:
        name (StringField): Optional field for entering the user's first name.
        surname (StringField): Optional field for entering the user's last name.
        email (EmailField): Field for entering the email address, required.
        phone_number (StringField): Field for entering the phone number, validated for format and uniqueness.
        current_password (PasswordField): Field for entering the current password.
        new_password (PasswordField): Optional field for entering a new password, validated for strength.
        confirm_new_password (PasswordField): Optional field for confirming the new password.
        submit_details (SubmitField): Submit button for updating profile details.
        submit_password (SubmitField): Submit button for updating the password.
    """
    name = StringField('First Name', validators=[Optional(), validate_name_surname_format_only_str])
    surname = StringField('Last Name', validators=[Optional(), validate_name_surname_format_only_str])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[validate_phone_format, validate_unique_phone_number])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', validators=[Optional(), validate_password_strong_password])
    confirm_new_password = PasswordField('Confirm New Password', validators=[Optional()])
    submit_details = SubmitField('Update Profile Details')
    submit_password = SubmitField('Update Password')


class AdminSignUpForm(FlaskForm):
    """
    Form for admin sign up.

    This form collects information for new admin registration, including username, email,
    password, confirmation of password, and admin PIN.

    Attributes:
        username (StringField): Field for entering the username, required.
        email (EmailField): Field for entering the email address, required.
        password (PasswordField): Field for entering the password, required.
        confirm_password (PasswordField): Field for confirming the password, required and must match password.
        admin_pin (StringField): Field for entering the admin PIN, required and validated.
        submit (SubmitField): Submit button for the form.
    """
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    admin_pin = StringField('Admin PIN', validators=[DataRequired(), validate_admin_pin])
    submit = SubmitField('Create Admin')
