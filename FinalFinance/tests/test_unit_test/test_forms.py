import os
import unittest
from FinalFinance import create_app, db
from FinalFinance.forms import SignUpForm, LoginForm, UpdateProfileForm, AdminSignUpForm


class TestForms(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_sign_up_form_valid(self):
        form = SignUpForm(data={
            'username': 'testuser',
            'email': 'test@as.com',
            'name': 'as',
            'surname': 'mano',
            'phone_number': '+198767890',
            'password': 'Password123!'
        })
        self.assertTrue(form.validate())

    def test_sign_up_form_invalid_email(self):
        form = SignUpForm(data={
            'username': 'testuser',
            'email': 'invalid-email',
            'name': 'Test',
            'surname': 'User',
            'phone_number': '+12345678909',
            'password': 'Password123!'
        })
        self.assertFalse(form.validate())

    def test_login_form_valid(self):
        form = LoginForm(data={
            'username': 'testuser',
            'password': 'Password123!'
        })
        self.assertTrue(form.validate())

    def test_login_form_missing_username(self):
        form = LoginForm(data={
            'password': 'Password123!'
        })
        self.assertFalse(form.validate())

    def test_update_profile_form_valid(self):
        form = UpdateProfileForm(data={
            'email': 'test@example.com',
            'phone_number': '+1234567890',
            'current_password': 'Password123!',
            'new_password': 'NewPassword123!',
            'confirm_new_password': 'NewPassword123!'
        })
        self.assertTrue(form.validate())

    def test_update_profile_form_password_mismatch(self):
        form = UpdateProfileForm(data={
            'email': 'test@example.com',
            'phone_number': '1234567890',
            'current_password': 'Password123!',
            'new_password': 'NewPassword123!',
            'confirm_new_password': 'MismatchPassword!'
        })
        self.assertFalse(form.validate())

    def test_admin_sign_up_form_valid(self):
        form = AdminSignUpForm(data={
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'AdminPassword123!',
            'confirm_password': 'AdminPassword123!',
            'admin_pin': '1515'
        })
        self.assertTrue(form.validate())

    def test_admin_sign_up_form_invalid_pin(self):
        form = AdminSignUpForm(data={
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'AdminPassword123!',
            'confirm_password': 'AdminPassword123!',
            'admin_pin': 'invalid'
        })
        self.assertFalse(form.validate())


if __name__ == '__main__':
    unittest.main()
