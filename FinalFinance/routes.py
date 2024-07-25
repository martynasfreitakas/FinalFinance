import uuid
from datetime import datetime

import numpy as np

from .database import db
from flask import render_template, flash, redirect, url_for, request, Blueprint, send_from_directory, current_app
from .forms import SignUpForm, LoginForm, UpdateProfileForm, AdminSignUpForm
from .models import User, FundData, Submission, AddFundToFavorites, FundHoldings, AdminUser
import pandas as pd
from .utils import edgar_downloader_from_sec, get_fund_lists, save_plot_to_file, get_rss_feed_entries
from flask_login import login_user, logout_user, current_user, login_required
import re
import os
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

# Define the blueprint for routes
routes = Blueprint('routes', __name__)


@routes.route('/')
def home() -> str:
    """
    Route for the home page.

    This function renders the home page, displaying well-known funds, RSS feed entries, and a plot image.
    The plot image is generated and saved if it does not already exist for the current day.

    Returns:
        str: The rendered HTML template for the home page.
    """
    # Retrieve a list of well-known funds
    well_known_funds = get_fund_lists()

    # Retrieve RSS feed entries
    rss_feed_entries = get_rss_feed_entries()

    # Define the ticker symbol and current date
    ticker_symbol = 'spy'
    today_date = datetime.now().strftime('%Y-%m-%d')
    image_filename = f'plot_{ticker_symbol}_{today_date}.png'
    image_path = os.path.join('FinalFinance', 'static', 'images', image_filename)
    print(f"Saving plot to: {image_path}")

    # Ensure the static/images directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    # Check if the image for today already exists
    if not os.path.exists(image_path):
        # Generate and save the plot image
        save_plot_to_file(ticker_symbol=ticker_symbol, period='1y', interval='1d', filename=image_path)

    # Render the home page template with the required context variables
    return render_template('home.html', well_known_funds=well_known_funds,
                           rss_feed_entries=rss_feed_entries, image_filename=image_filename, year=datetime.now().year)


@routes.route('/static/images/<path:filename>')
def custom_static(filename: str) -> object:
    """
    Route for serving static image files.

    This function serves static image files from the 'static/images' directory.
    It logs whether the requested file is found or not.

    Args:
        filename (str): The filename of the requested image.

    Returns:
        Response: The static file if found, otherwise a 404 error.
    """
    file_path = os.path.join('static', 'images', filename)
    if os.path.exists(file_path):
        print(f"Serving file: {file_path}")
    else:
        print(f"File not found: {file_path}")
    return send_from_directory(os.path.join('static', 'images'), filename)


@routes.route('/about')
def about() -> str:
    """
    Route for the about page.

    This function renders the about page, displaying information about the site.

    Returns:
        str: The rendered HTML template for the about page.
    """
    return render_template('about.html', year=datetime.now().year)


@routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            print(f'User {user.username} logged in successfully.')
            login_user(user)
            flash('Logged in successfully.')

            return redirect(url_for('routes.home'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html', year=datetime.now().year, form=form)


@routes.route('/logout')
def logout() -> object:
    """
    Route for logging out the user.

    This function logs out the current user, flashes a logout message,
    and redirects to the home page.

    Returns:
        Response: Redirects to the home page.
    """
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('routes.home'))


@routes.route('/fund_search', methods=['GET'])
def fund_search() -> str:
    """
    Route for searching funds.

    This function handles the GET request for searching funds by company name or CIK.
    It flashes a message if no query is provided and renders the search results if a query is given.

    Returns:
        str: The rendered HTML template for the fund search results.
    """
    query = request.args.get('query', default='', type=str)

    if not query:
        flash('Please enter a company name or CIK.')
        return render_template('fund_search.html', year=datetime.now().year)

    # Check if the query is a digit (CIK) or a string (fund name)
    if query.isdigit():
        funds = FundData.query.filter(FundData.cik.like(f'%{query}%')).all()
    else:
        funds = FundData.query.filter(FundData.fund_name.ilike(f'%{query}%')).all()

    # Render the fund search results page
    return render_template('fund_search.html', funds=funds, year=datetime.now().year)


@routes.route('/fund_details/add_more_submissions/<cik>', methods=['GET', 'POST'])
@login_required
def add_more_submissions(cik: str) -> object:
    """
    Route for adding more submissions for a fund.

    This function handles both GET and POST requests for adding more submissions to a fund.
    It fetches new submissions from the SEC EDGAR database for the given CIK and date range.

    Args:
        cik (str): The CIK of the fund.

    Returns:
        Response: The rendered HTML template for the fund details page or redirects to it after adding submissions.
    """
    if request.method == 'POST':
        # Get the start and end dates from the form
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']

        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Fetch new submissions from SEC EDGAR
        edgar_downloader_from_sec(cik, start_date=start_date, end_date=end_date)

        flash('Submissions added successfully.')

        # Redirect to the fund details page
        return redirect(url_for('routes.fund_details', cik=cik))

    # Fetch the fund and its submissions from the database
    fund = Submission.query.filter_by(cik=cik).first()
    all_submissions = Submission.query.filter_by(cik=cik).all()

    # Render the fund details page
    return render_template('fund_details.html',
                           fund=fund, submissions=all_submissions, year=datetime.now().year)


@routes.route('/fund_favorites')
@login_required
def fund_favorites() -> str:
    """
    Route for displaying the user's favorite funds.

    This function renders a page showing all the funds that the current user has marked as favorite.

    Returns:
        str: The rendered HTML template for the favorite funds page.
    """
    favorite_funds = current_user.favorite_funds

    # Render the favorite funds page
    return render_template('fund_favorites.html', favorite_funds=favorite_funds, year=datetime.now().year)


@routes.route('/add_to_favorites/<cik>', methods=['POST'])
@login_required
def add_to_favorites(cik: str) -> object:
    """
    Route for adding a fund to the user's favorites.

    This function handles the POST request to add a fund to the user's favorites list.
    It checks if the user and fund exist and if the fund is already in the user's favorites.

    Args:
        cik (str): The CIK of the fund to be added to favorites.

    Returns:
        Response: Redirects to the fund search page.
    """
    # Retrieve the current user
    user = User.query.filter_by(id=current_user.id).first()
    if not user:
        flash('User not found.')
        return redirect(url_for('routes.login'))

    # Retrieve the fund by CIK
    fund = FundData.query.filter_by(cik=cik).first()
    if not fund:
        flash('Fund not found.')
        return redirect(url_for('routes.fund_search'))

    # Check if the fund is already in the user's favorites
    favorite = AddFundToFavorites.query.filter_by(user_id=user.id, fund_id=fund.id).first()
    if favorite:
        flash('Fund is already in favorites.')
    else:
        # Add the fund to the user's favorites
        favorite = AddFundToFavorites(user_id=user.id, fund_id=fund.id)
        db.session.add(favorite)
        db.session.commit()
        flash('Fund added to favorites.')

    return redirect(url_for('routes.fund_search'))


@routes.route('/remove_from_favorites/<uuid:fund_id>', methods=['POST'])
@login_required
def remove_from_favorites(fund_id: uuid.UUID) -> object:
    """
    Route for removing a fund from the user's favorites.

    This function handles the POST request to remove a fund from the user's favorites list.
    It checks if the user exists and if the fund is in the user's favorites.

    Args:
        fund_id (uuid.UUID): The ID of the fund to be removed from favorites.

    Returns:
        Response: Redirects to the fund favorites page.
    """
    # Retrieve the current user
    user = User.query.filter_by(id=current_user.id).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('routes.login'))

    # Retrieve the favorite entry for the fund
    favorite_entry = AddFundToFavorites.query.filter_by(
        user_id=user.id,
        fund_id=fund_id
    ).first()

    if favorite_entry:
        # Remove the fund from the user's favorites
        db.session.delete(favorite_entry)
        db.session.commit()
        flash('Fund removed from favorites successfully!', 'success')
    else:
        flash('Fund not found in favorites.', 'error')

    return redirect(url_for('routes.fund_favorites'))


@routes.route('/submission_details/<accession_number>')
@login_required
def submission_details(accession_number: str) -> str:
    """
    Route for displaying the details of a submission.

    This function renders the submission details page for a given accession number.
    It retrieves the submission, fund, and holdings associated with the accession number.

    Args:
        accession_number (str): The accession number of the submission.

    Returns:
        str: The rendered HTML template for the submission details page.
    """
    # Retrieve the submission by accession number
    submission = Submission.query.filter_by(accession_number=accession_number).first()
    if not submission:
        flash('No submission found with the given accession number.')
        return redirect(url_for('routes.fund_search'))

    # Retrieve the fund and holdings associated with the submission
    fund = Submission.query.filter_by(cik=submission.cik).first()
    holdings = FundHoldings.query.filter_by(accession_number=accession_number).all()

    # Render the submission details page
    return render_template('submission_details.html', submission=submission, holdings=holdings, fund=fund,
                           year=datetime.now().year)


@routes.route('/fund_details/<cik>', methods=['GET', 'POST'])
def fund_details(cik: str) -> str:
    """
    Route for displaying and managing fund details.

    This function handles both GET and POST requests for the fund details page. It fetches
    submissions and holdings for a fund identified by its CIK. Users can add more submissions
    for a specific date range. The function also compares the most recent and previous holdings.

    Args:
        cik (str): The CIK of the fund.

    Returns:
        str: The rendered HTML template for the fund details page.
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        start_date = None
        end_date = None

    if request.method == 'POST':
        # Get the start and end dates from the form
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']

        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Fetch new submissions from SEC EDGAR
        edgar_downloader_from_sec(cik, start_date=start_date, end_date=end_date)

        flash('Submissions added successfully.')

        # Redirect to the fund details page
        return redirect(url_for('routes.fund_details', cik=cik))

    # Fetch the fund and its submissions from the database
    fund = Submission.query.filter_by(cik=cik).first()

    if not fund:
        # If no fund found, fetch from SEC EDGAR and update the database
        edgar_downloader_from_sec(cik, start_date=start_date, end_date=end_date)
        fund = Submission.query.filter_by(cik=cik).first()
        if not fund:
            flash('This Fund does not provide holding filings.')
            return redirect(url_for('routes.fund_search'))

    # Fetch all submissions for the fund
    all_submissions = Submission.query.filter_by(cik=cik).order_by(Submission.filed_of_date.desc()).all()

    # Fetch all holdings for the fund based on submissions
    all_holdings = []
    if all_submissions:
        all_accession_numbers = [submission.accession_number for submission in all_submissions]
        all_holdings = FundHoldings.query.filter(FundHoldings.accession_number.in_(all_accession_numbers)).all()

    # Convert SQLAlchemy results to a pandas DataFrame
    holdings_df = pd.DataFrame(
        [(holding.company_name, holding.value_usd, holding.share_amount, holding.accession_number)
         for holding in all_holdings],
        columns=['Company Name', 'Value (USD)', 'Share Amount', 'Accession Number']
    )

    # Sort DataFrame by Company Name and Accession Number
    holdings_df.sort_values(by=['Company Name', 'Accession Number'], ascending=[True, False], inplace=True)

    # Get the most recent and previous accessions
    most_recent_accession = all_submissions[0].accession_number if all_submissions else None
    previous_accession = all_submissions[1].accession_number if len(all_submissions) > 1 else None

    if most_recent_accession:
        # Get current holdings
        current_holdings_df = holdings_df[holdings_df['Accession Number'] == most_recent_accession].copy()
        if previous_accession:
            # Get previous holdings
            previous_holdings_df = holdings_df[holdings_df['Accession Number'] == previous_accession].copy()

            try:
                # Merge current and previous holdings on 'Company Name'
                merged_holdings_df = pd.merge(
                    current_holdings_df,
                    previous_holdings_df[['Company Name', 'Share Amount']],
                    on='Company Name',
                    how='left',
                    suffixes=('', '_Previous')
                )
                merged_holdings_df.rename(columns={'Share Amount_Previous': 'Previous Share Amount'}, inplace=True)

                # Check for new companies
                previous_companies = previous_holdings_df['Company Name'].unique()
                merged_holdings_df['New Company'] = ~merged_holdings_df['Company Name'].isin(previous_companies)

                # Calculate change in share amount and percentage
                merged_holdings_df['Change Amount'] = merged_holdings_df['Share Amount'] - merged_holdings_df[
                    'Previous Share Amount'].fillna(0)
                merged_holdings_df['Change Percentage'] = merged_holdings_df.apply(
                    lambda row: 100 if row['Previous Share Amount'] == 0 else (row['Change Amount'] / row[
                        'Previous Share Amount']) * 100, axis=1)

                # Determine change status
                merged_holdings_df['Change Status'] = 'No Change'
                merged_holdings_df.loc[merged_holdings_df['Share Amount'] > merged_holdings_df[
                    'Previous Share Amount'], 'Change Status'] = 'Increased'
                merged_holdings_df.loc[merged_holdings_df['Share Amount'] < merged_holdings_df[
                    'Previous Share Amount'], 'Change Status'] = 'Decreased'
                merged_holdings_df.loc[
                    merged_holdings_df['Previous Share Amount'].isna(), 'Change Status'] = 'New Investment'

                # Find companies that were in previous but not in current
                previous_holdings_not_in_current = previous_holdings_df[
                    ~previous_holdings_df['Company Name'].isin(current_holdings_df['Company Name'])].copy()

                # Set share amount to 0 for these companies
                previous_holdings_not_in_current['Share Amount'] = 0
                previous_holdings_not_in_current['Change Status'] = 'Position Closed'
                previous_holdings_not_in_current['New Company'] = False
                previous_holdings_not_in_current['Change Amount'] = -previous_holdings_not_in_current['Share Amount']
                previous_holdings_not_in_current['Change Percentage'] = -100

                # Append these rows to the merged holdings DataFrame
                merged_holdings_df = pd.concat([merged_holdings_df, previous_holdings_not_in_current],
                                               ignore_index=True)

            except KeyError:
                # Handle case when 'Previous Share Amount' is missing
                current_holdings_df['Previous Share Amount'] = 0
                current_holdings_df['New Company'] = True
                current_holdings_df['Change Status'] = 'New Investment'
                current_holdings_df['Change Amount'] = current_holdings_df['Share Amount']
                current_holdings_df['Change Percentage'] = 100
                merged_holdings_df = current_holdings_df

        else:
            # Handle case when there is no previous accession
            current_holdings_df['Previous Share Amount'] = 0
            current_holdings_df['New Company'] = True
            current_holdings_df['Change Status'] = 'New Investment'
            current_holdings_df['Change Amount'] = current_holdings_df['Share Amount']
            current_holdings_df['Change Percentage'] = 100
            merged_holdings_df = current_holdings_df

        # Round necessary columns and handle new investments
        merged_holdings_df['Value (USD)'] = merged_holdings_df['Value (USD)'].fillna(0).astype(int)
        merged_holdings_df['Share Amount'] = merged_holdings_df['Share Amount'].fillna(0).astype(int)
        merged_holdings_df['Previous Share Amount'] = merged_holdings_df['Previous Share Amount'].fillna(0).astype(int)
        merged_holdings_df['Change Amount'] = merged_holdings_df['Change Amount'].fillna(0).astype(int)
        merged_holdings_df['Change Percentage'] = merged_holdings_df['Change Percentage'].fillna(0).round(1)

        holdings_df = merged_holdings_df

    # Convert DataFrame back to list of dictionaries for rendering in template
    holdings_list = holdings_df.to_dict(orient='records')

    # Render the fund details page
    return render_template('fund_details.html', fund=fund, submissions=all_submissions, newest_holdings=holdings_list,
                           year=datetime.now().year)


@routes.route('/signup', methods=['GET', 'POST'])
def signup() -> str:
    """
    Route for user signup.

    This function handles both GET and POST requests for the signup page. It collects user data
    from the signup form, checks for existing users with the same username or email, and registers
    a new user if validation passes.

    Returns:
        str: The rendered HTML template for the signup page or redirects to login page upon successful registration.
    """
    form = SignUpForm()

    if form.validate_on_submit():
        # Collect form data
        username = form.username.data
        email = form.email.data
        password = form.password.data
        name = form.name.data
        surname = form.surname.data
        phone_number = form.phone_number.data.strip() if form.phone_number.data else None

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('The username already exists. Try a different one.')
            return redirect(url_for('routes.signup'))

        # Check if the email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('The email address is already registered.')
            return redirect(url_for('routes.signup'))

        # Create a new user and add to the database
        user = User(
            username=username,
            email=email,
            name=name,
            surname=surname,
            phone_number=phone_number,
            password=password
        )

        db.session.add(user)
        db.session.commit()

        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('routes.login'))

    # Render the signup page with the form
    return render_template('signup.html', form=form)


@routes.route('/profile', methods=['GET', 'POST'])
@login_required
def profile() -> str:
    """
    Route for displaying and updating user profile.

    This function handles both GET and POST requests for the profile page. It allows users to
    update their profile information and change their password if the current password is verified.

    Returns:
        str: The rendered HTML template for the profile page.
    """
    form = UpdateProfileForm(obj=current_user)

    if form.validate_on_submit():
        # Check if the current password is provided and valid
        if form.current_password.data and not current_user.check_password(form.current_password.data):
            flash('Invalid current password. Please try again.', 'error')
            return redirect(url_for('routes.profile'))

        # Check if the new passwords match
        if form.new_password.data and form.new_password.data != form.confirm_new_password.data:
            flash('New passwords must match.', 'error')
            return redirect(url_for('routes.profile'))

        # Update the user's password if a new password is provided
        if form.new_password.data:
            current_user.password = form.new_password.data

        phone_number = form.phone_number.data.strip() if form.phone_number.data else None

        # Validate phone number format
        phone_regex = re.compile(r'^\+\d{9,14}$')
        if phone_number and not phone_regex.match(phone_number):
            flash("Invalid phone number. It must start with + and be 10 to 15 characters long.", 'error')
            return redirect(url_for('routes.profile'))

        # Check if the phone number is already in use by another user
        if phone_number:
            existing_user = User.query.filter_by(phone_number=phone_number).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Phone number already in use.', 'error')
                return redirect(url_for('routes.profile'))

        # Update the user's profile information
        current_user.name = form.name.data
        current_user.surname = form.surname.data
        current_user.email = form.email.data
        current_user.phone_number = phone_number

        try:
            db.session.commit()
            flash('Your profile has been updated successfully.', 'success')
            return redirect(url_for('routes.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'error')
            current_app.logger.error(f'Failed to update profile: {str(e)}')

    return render_template('profile.html', form=form, user=current_user)


@routes.route('/monitor', methods=['GET', 'POST'])
@login_required
def monitor() -> str:
    """
    Route for monitoring user's favorite funds.

    This function handles both GET and POST requests for the monitor page. It displays the user's favorite funds,
    retrieves the latest submissions and holdings for a selected fund, and provides analysis on holdings changes.

    Returns:
        str: The rendered HTML template for the monitor page.
    """
    favorite_funds = current_user.favorite_funds

    if not favorite_funds:
        flash('No favorite funds added yet.')
        return render_template('monitor.html', year=datetime.now().year, message='No favorite funds added yet.')

    fund_name_and_cik = [(favorite.fund.fund_name, favorite.fund.cik) for favorite in favorite_funds]

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)

    monitored_cik = request.form.get('monitored_cik', None)
    if monitored_cik is None and favorite_funds:
        monitored_cik = favorite_funds[0].fund.cik

    if request.method == 'POST':
        # Get start and end dates from the form
        start_date_str = request.form.get('start_date', '2023-01-01')
        end_date_str = request.form.get('end_date', '2023-12-31')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError as e:
            flash(f'Error parsing date: {e}')
            return redirect(url_for('routes.monitor'))

    elif request.method == 'GET':
        monitored_cik = request.args.get('cik', monitored_cik)

    # Fetch the fund and its submissions from the database
    fund = Submission.query.filter_by(cik=monitored_cik).first()

    if not fund:
        try:
            # Fetch new submissions from SEC EDGAR if fund not found
            edgar_downloader_from_sec(monitored_cik, start_date=start_date, end_date=end_date)
        except Exception as e:
            flash(f'Error downloading SEC filings: {str(e)}')
            return redirect(url_for('routes.monitor'))

        fund = Submission.query.filter_by(cik=monitored_cik).first()

        if not fund:
            flash('This Fund does not provide holding filings.')
            return redirect(url_for('routes.monitor'))

    # Fetch all submissions for the monitored CIK
    all_submissions = Submission.query.filter_by(cik=monitored_cik).order_by(Submission.filed_of_date.desc()).all()

    newest_submission = all_submissions[0] if all_submissions else None

    # Fetch all holdings based on submissions
    all_holdings = []
    if all_submissions:
        all_accession_numbers = [submission.accession_number for submission in all_submissions]
        all_holdings = FundHoldings.query.filter(FundHoldings.accession_number.in_(all_accession_numbers)).all()

    # Convert SQLAlchemy results to a pandas DataFrame
    holdings_df = pd.DataFrame(
        [(holding.company_name, holding.share_amount, holding.accession_number)
         for holding in all_holdings],
        columns=['Company Name', 'Share Amount', 'Accession Number']
    )

    # Sort DataFrame by Company Name and Accession Number
    holdings_df.sort_values(by=['Company Name', 'Accession Number'], ascending=[True, False], inplace=True)

    accession_numbers = [submission.accession_number for submission in all_submissions[:5]]

    merged_holdings_df = pd.DataFrame(columns=['Company Name'])

    if accession_numbers:
        for i, accession_number in enumerate(accession_numbers):
            temp_df = holdings_df[holdings_df['Accession Number'] == accession_number].copy()
            column_name = 'Share Amount' if i == 0 else f'Previous Share Amount +{i}'
            temp_df.rename(columns={'Share Amount': column_name}, inplace=True)
            merged_holdings_df = pd.merge(
                merged_holdings_df,
                temp_df[['Company Name', column_name]],
                on='Company Name',
                how='outer'
            )

    merged_holdings_df.fillna(0, inplace=True)

    # Ensure all share amount columns are integers
    for col in merged_holdings_df.columns[1:]:
        merged_holdings_df[col] = merged_holdings_df[col].astype(int)

    # Reorder columns to show Company Name, then Previous Share Amounts, then Share Amount
    columns_order = ['Company Name'] + [col for col in merged_holdings_df.columns if 'Previous Share Amount' in col][
                                       ::-1] + ['Share Amount']
    merged_holdings_df = merged_holdings_df[columns_order]

    # Check for companies with current Share Amount of 0 but non-zero previous amounts
    condition = (merged_holdings_df['Share Amount'] == 0) & (merged_holdings_df.iloc[:, 1:-1].sum(axis=1) != 0)
    zero_share_but_previous_non_zero = merged_holdings_df[condition]

    holdings_list = merged_holdings_df.to_dict(orient='records')

    # Render the monitor page
    return render_template('monitor.html',
                           fund=fund, newest_holdings=holdings_list,
                           year=datetime.now().year, fund_details=fund_name_and_cik,
                           favorite_funds=favorite_funds,
                           monitored_cik=monitored_cik,
                           submissions=all_submissions,
                           newest_submission=newest_submission)


@login_required
def admin_home() -> str:
    """
    Route for the admin home page.

    This function renders the admin home page if the current user is an admin. If the user is not an admin,
    access is denied and the user is redirected to the home page.

    Returns:
        str: The rendered HTML template for the admin home page or redirects to the home page for non-admin users.
    """
    if not current_user.is_admin:
        flash('Access denied. You need to be an admin to view this page.', 'error')
        return redirect(url_for('routes.home'))  # Redirect to appropriate route for regular users

    form = LoginForm()
    return render_template('admin/admin_home.html', year=datetime.now().year, form=form)


@routes.route('/admin/login', methods=['GET', 'POST'])
def admin_login() -> str:
    """
    Route for admin login.

    This function handles both GET and POST requests for the admin login page. It validates the login form
    and authenticates the admin user.

    Returns:
        str: The rendered HTML template for the admin login page or redirects to the admin dashboard upon successful login.
    """
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        try:
            admin_user = AdminUser.query.filter_by(username=username).first()
        except Exception as e:
            flash('An error occurred. Please try again later.', 'error')
            return render_template('admin/admin_login.html', title='Admin Login', form=form)

        if admin_user and check_password_hash(admin_user.password_hash, password):
            login_user(admin_user)
            flash('Login successful!', 'success')
            return redirect(url_for('routes.admin_dashboard'))
        else:
            flash('Login unsuccessful. Please check your credentials.', 'error')

    return render_template('admin/admin_login.html', title='Admin Login', form=form)


@routes.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup() -> str:
    """
    Route for admin signup.

    This function handles both GET and POST requests for the admin signup page. It validates the signup form,
    checks the admin PIN, and registers a new admin user.

    Returns:
        str: The rendered HTML template for the admin signup page or redirects to the admin login page upon successful registration.
    """
    form = AdminSignUpForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        admin_pin = form.admin_pin.data

        # Check if the PIN matches the environment variable
        if admin_pin != current_app.config['ADMIN_PIN']:
            flash('Admin PIN is incorrect. Please enter the correct PIN.', 'error')
            return render_template('admin/admin_signup.html', title='Admin Sign Up', form=form)

        existing_user = AdminUser.query.filter(
            (AdminUser.username == username) | (AdminUser.email == email)
        ).first()

        if existing_user:
            flash('Username or email already exists. Please choose another.', 'error')
            return render_template('admin/admin_signup.html', title='Admin Sign Up', form=form)

        try:
            # Adjusted to explicitly set admin_rights to True
            new_admin_user = AdminUser(username=username, email=email, password=password, admin_pin=admin_pin,
                                       admin_rights=True)
            db.session.add(new_admin_user)
            db.session.commit()

            flash('Admin user created successfully!', 'success')
            print(f"Admin user created: {new_admin_user.username} ({new_admin_user.email})")
            return redirect(url_for('routes.admin_login'))

        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists. Please choose another.', 'error')

        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again later.', 'error')
            current_app.logger.error(f"Error in admin signup: {str(e)}")

    return render_template('admin/admin_signup.html', title='Admin Sign Up', form=form)


@routes.route('/admin/logout')
@login_required
def admin_logout() -> object:
    """
    Route for admin logout.

    This function logs out the current admin user and redirects to the admin login page.

    Returns:
        Response: Redirects to the admin login page.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.admin_login'))


@routes.route('/admin/dashboard')
@login_required
def admin_dashboard() -> str:
    """
    Route for the admin dashboard.

    This function renders the admin dashboard page if the current user is an admin. If the user is not an admin,
    access is denied and the user is redirected to the admin login page.

    Returns:
        str: The rendered HTML template for the admin dashboard page or redirects to the admin login page for non-admin users.
    """
    # Check if current_user is not found or not an admin
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied. You need to be an admin to view this page.', 'error')
        return redirect(url_for('routes.admin_login'))

    return render_template('admin/admin_dashboard.html', year=datetime.now().year, current_user=current_user)
