from wtforms import StringField, PasswordField, SubmitField, EmailField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Optional, EqualTo
from .utils import (validate_phone_format, validate_name_surname_format_only_str, validate_unique_phone_number,
                   validate_password_strong_password, validate_admin_pin)


class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[Optional(), validate_name_surname_format_only_str])
    surname = StringField('Surname', validators=[Optional(), validate_name_surname_format_only_str])
    phone_number = StringField('Phone Number', validators=[validate_phone_format, validate_unique_phone_number])
    password = PasswordField('Password', validators=[DataRequired(), validate_password_strong_password])
    submit = SubmitField('Submit')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UpdateProfileForm(FlaskForm):
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
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    admin_pin = StringField('Admin PIN', validators=[DataRequired(), validate_admin_pin])

    submit = SubmitField('Create Admin')
