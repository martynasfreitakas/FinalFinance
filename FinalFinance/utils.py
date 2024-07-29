from collections import defaultdict
from typing import Optional, Dict, Any, List

import pandas as pd
from feedparser import FeedParserDict
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms.fields.simple import StringField

from .models import Submission, FundHoldings, FundData
from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader
from dotenv import load_dotenv
import requests
from .database import db
import shutil
from datetime import datetime
import os
import re
import logging.config
from requests.exceptions import HTTPError
from yfinance import Ticker

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

import base64
from io import BytesIO

import feedparser
from wtforms.validators import ValidationError
from .models import User
from werkzeug.security import check_password_hash
from flask_login import current_user

# Load environment variables from a .env file
load_dotenv()


def setup_logging(default_path: str = 'logging.conf', default_level: int = logging.INFO) -> None:
    """
    Setup logging configuration.

    This function sets up logging based on the configuration provided in the logging configuration file.
    If the file does not exist or fails to load, it defaults to basic logging configuration.

    Args:
        default_path (str): The path to the logging configuration file.
        default_level (int): The default logging level if the configuration file is not found or fails to load.
    """
    path = default_path

    # Check if the logging configuration file exists
    if os.path.exists(path):
        try:
            # Load the logging configuration from the file
            logging.config.fileConfig(path)
        except Exception as e:
            # If loading fails, print the error and use the default logging configuration
            print(f"Failed to load logging configuration: {e}")
            logging.basicConfig(level=default_level)
    else:
        # If the logging configuration file is not found, use the default logging configuration
        print(f"Logging configuration file {path} not found. Using default configuration.")
        logging.basicConfig(level=default_level)


# Initialize logging
setup_logging()

# Create a logger instance
logger = logging.getLogger('sLogger')


def get_user_agent() -> Optional[str]:
    """
        Retrieve the user agent from the environment variable.
    """
    return os.environ.get('EMAIL_FOR_AUTHORIZATION', 'USER_AGENT')


def download_and_store_all_companies_names_and_cik_from_edgar() -> None:
    """
    Download and store all company names and CIKs from the SEC's Edgar database.

    This function retrieves the data from the SEC Edgar database, processes it,
    and stores the company names and CIKs in the database. It also handles merging
    duplicate CIK entries.

    Raises:
        requests.RequestException: If the request to the SEC Edgar database fails.
    """
    logger.info('Starting downloading data from Edgar.')

    # URL for the SEC Edgar CIK lookup data
    url = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
    headers = {"User-Agent": get_user_agent()}

    try:
        # Send a GET request to the SEC Edgar database
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        # Log an error if the request fails
        logger.error(f"Error during HTTP request: {e}")
        return

    if response.status_code == 200:
        logger.info('Connected successfully.')
        data_line = response.text.splitlines()
        all_lines_in_document = len(data_line)
        data = [(line.split(":")[0], line.split(":")[1].rstrip(':')) for line in data_line if ":" in line]

        # Process and store each company name and CIK in the database
        for number_downloaded, (fund_name, fund_cik) in enumerate(data, start=1):
            fund_data = FundData(fund_name=fund_name, cik=fund_cik)
            db.session.add(fund_data)
            if number_downloaded % 1000 == 0:
                logger.info(f"Processed {number_downloaded} of {all_lines_in_document} lines.")
        db.session.commit()

        # Handle merging of duplicate CIK entries
        results = db.session.query(
            FundData.cik,
            func.string_agg(FundData.fund_name, ', ').label('fund_names')
        ).group_by(FundData.cik).having(func.count(FundData.cik) > 1).all()

        for number_duplicates, result in enumerate(results, start=1):
            fund_cik, fund_names = result
            fund_data = FundData.query.filter_by(cik=fund_cik).first()
            fund_data.fund_name = fund_names
            FundData.query.filter(FundData.cik == fund_cik, FundData.id != fund_data.id).delete()

            if number_duplicates % 1000 == 0:
                logger.info(f"Processed {number_duplicates} of {all_lines_in_document} updates.")

        db.session.commit()
    else:
        logger.error(f"Error: {response.status_code}")


def edgar_downloader_from_sec(fund_cik: str,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> None:
    """
    Download SEC filings for a given fund CIK between specified dates and store them locally.

    This function downloads SEC filings of specified types for a given fund CIK within the date range
    and stores them in the local file system. If the filing type directory exists, it is cleared before
    downloading new filings.

    Args:
        fund_cik (str): The Central Index Key (CIK) of the fund.
        start_date (Optional[datetime]): The start date for the filings to be downloaded. Defaults to 2022-02-01.
        end_date (Optional[datetime]): The end date for the filings to be downloaded. Defaults to 2024-07-24.

    Raises:
        HTTPError: If an HTTP error occurs during the download process.
        Exception: If any other error occurs during the download process.
    """
    filing_types = ['NPORT-P', '13F-HR']

    if start_date is None:
        start_date = datetime(2022, 2, 1)
    if end_date is None:
        end_date = datetime(2024, 7, 24)

    # Base directory path for storing SEC filings
    dir_path = 'sec-edgar-filings'

    for filing_type in filing_types:
        # Path to store filings of a specific type for the given fund CIK
        filings_path = os.path.join(dir_path, fund_cik, filing_type)
        if os.path.exists(filings_path):
            # Clear the existing directory if it exists
            shutil.rmtree(filings_path)
        os.makedirs(filings_path)

        try:
            # Initialize the downloader with the base directory path and email for authorization
            dl = Downloader(dir_path, os.environ['EMAIL_FOR_AUTHORIZATION'])
            # Download filings of the specified type for the given CIK within the date range
            dl.get(filing_type, fund_cik, after=start_date, before=end_date)
        except HTTPError as e:
            if e.response.status_code == 404:
                print(f"404 Error for URL: {e.request.url}. CIK may be incorrect or data not available.")
            else:
                print(f"HTTP error occurred: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        # Remove the directory if no filings were downloaded
        if not os.listdir(filings_path):
            os.rmdir(filings_path)

        # Add downloaded filings to the database
        add_filing_to_db(fund_cik)


def add_filing_to_db(fund_cik: str) -> None:
    """
    Process and add SEC filings for a given fund CIK to the database.

    This function processes the downloaded SEC filings for a given fund CIK by extracting
    relevant holdings information and storing it in the database.

    Args:
        fund_cik (str): The Central Index Key (CIK) of the fund.
    """
    directory_path = os.path.join('sec-edgar-filings', fund_cik)
    if not os.path.exists(directory_path):
        print(f"Directory does not exist: {directory_path}")
        return

    # Iterate through subdirectories for each filing type
    subdirectories = [directory for directory in os.listdir(directory_path) if
                      os.path.isdir(os.path.join(directory_path, directory))]
    for subdirectory in subdirectories:
        subdirectory_path = os.path.join(directory_path, subdirectory)
        # Iterate through subdirectories for each filing date
        sub_subdirectories = [directory for directory in os.listdir(subdirectory_path) if
                              os.path.isdir(os.path.join(subdirectory_path, directory))]

        for sub_subdirectory in sub_subdirectories:
            sub_subdirectory_path = os.path.join(subdirectory_path, sub_subdirectory)
            files = os.listdir(sub_subdirectory_path)
            if not files:
                continue

            # Process each file in the sub_subdirectory
            for file in files:
                file_path = os.path.join(sub_subdirectory_path, file)
                extract_holdings_from_file(file_path)


def extract_holdings_from_file(path_to_file: str) -> None:
    """
    Extract holdings from a given file and add them to the database.

    This function reads an SEC filing file, parses its content to extract relevant holdings information,
    and stores the extracted data in the database. It handles updates to existing records and adds new records as needed.

    Args:
        path_to_file (str): The path to the SEC filing file.
    """
    with open(path_to_file, 'r') as file:
        data = file.read()

    # Parse the file content with BeautifulSoup
    soup = BeautifulSoup(data, 'lxml')
    tags = soup.find_all(['infotable', 'ns1:infotable', 'invstorsec'])

    # Regular expressions to extract various metadata from the file
    cik_tag_line = re.compile(r'CENTRAL INDEX KEY:\s+(\d+)')
    owner_cik = cik_tag_line.search(data).group(1) if cik_tag_line.search(data) else None

    accession_number_line = re.compile(r'ACCESSION NUMBER:\s+(.+)')
    accession_number = accession_number_line.search(data).group(1).strip() if accession_number_line.search(
        data) else None

    company_conformed_name_line = re.compile(r'COMPANY CONFORMED NAME:\s+(.+)')
    company_conformed_name = company_conformed_name_line.search(data).group(
        1).strip() if company_conformed_name_line.search(data) else None

    conformed_submission_type_line = re.compile(r'CONFORMED SUBMISSION TYPE:\s+(.+)')
    submission_type = conformed_submission_type_line.search(data).group(
        1).strip() if conformed_submission_type_line.search(data) else None

    filed_of_date_line = re.compile(r'FILED AS OF DATE:\s+(.+)')
    filed_of_date_format = filed_of_date_line.search(data).group(1).strip() if filed_of_date_line.search(data) else None
    filed_of_date = datetime.strptime(filed_of_date_format, '%Y%m%d') if filed_of_date_format else None

    period_of_portfolio_line = re.compile(r'CONFORMED PERIOD OF REPORT:\s+(.+)')
    period_of_portfolio_format = period_of_portfolio_line.search(data).group(
        1).strip() if period_of_portfolio_line.search(data) else None
    period_of_portfolio_date = datetime.strptime(period_of_portfolio_format,
                                                 '%Y%m%d') if period_of_portfolio_format else None

    if period_of_portfolio_date:
        year = period_of_portfolio_date.year
        quarter = (period_of_portfolio_date.month - 1) // 3 + 1
        quarter_str = f'Q{quarter}'
        period_of_portfolio = f'{year} {quarter_str}'
    else:
        period_of_portfolio = None

    # Retrieve the fund data from the database
    fund_data = FundData.query.filter_by(cik=owner_cik).first()
    if not fund_data:
        print(f"No FundData found for CIK: {owner_cik}")
        return

    # Check if the submission already exists in the database
    existing_submission = Submission.query.filter_by(accession_number=accession_number).first()
    if existing_submission:
        # Update the existing submission
        submission = existing_submission
        submission.cik = owner_cik
        submission.company_name = company_conformed_name
        submission.submission_type = submission_type
        submission.filed_of_date = filed_of_date
        submission.period_of_portfolio = period_of_portfolio
        submission.fund_data_id = fund_data.id
    else:
        # Add a new submission to the database
        submission = Submission(
            cik=owner_cik,
            company_name=company_conformed_name,
            submission_type=submission_type,
            filed_of_date=filed_of_date,
            accession_number=accession_number,
            period_of_portfolio=period_of_portfolio,
            fund_data_id=fund_data.id
        )
        db.session.add(submission)

    fund_portfolio_value = 0
    fund_owns_companies = 0

    for tag in tags:
        try:
            # Extract holdings information based on the tag type
            if tag.name in ['infotable', 'ns1:infotable']:
                nameofissuer = tag.find(['nameofissuer', 'ns1:nameofissuer']).text.strip() if tag.find(
                    ['nameofissuer', 'ns1:nameofissuer']) else None
                cusip = tag.find(['cusip', 'ns1:cusip']).text.strip() if tag.find(['cusip', 'ns1:cusip']) else None
                value = int(tag.find(['value', 'ns1:value']).text.strip()) if tag.find(['value', 'ns1:value']) else 0
                sshprnamt = int(tag.find(['sshprnamt', 'ns1:sshprnamt']).text.strip()) if tag.find(
                    ['sshprnamt', 'ns1:sshprnamt']) else 0
            elif tag.name == 'invstorsec':
                nameofissuer = tag.find('name').text.strip() if tag.find('name') else None
                cusip = tag.find('cusip').text.strip() if tag.find('cusip') else None
                value = float(tag.find('valusd').text.strip()) if tag.find('valusd') else 0
                sshprnamt = float(tag.find('balance').text.strip()) if tag.find('balance') else 0

            if value:
                fund_portfolio_value += value
            if nameofissuer:
                fund_owns_companies += 1

            # Check if the fund holding already exists in the database
            existing_fund_holding = FundHoldings.query.filter_by(company_name=nameofissuer,
                                                                 accession_number=accession_number).first()
            if existing_fund_holding:
                # Update the existing fund holding
                existing_fund_holding.value_usd = value
                existing_fund_holding.share_amount = sshprnamt
                existing_fund_holding.cusip = cusip
                existing_fund_holding.cik = owner_cik
                existing_fund_holding.period_of_portfolio = period_of_portfolio
                existing_fund_holding.fund_data_id = fund_data.id
            else:
                # Add a new fund holding to the database
                fund_holding = FundHoldings(
                    company_name=nameofissuer,
                    value_usd=value,
                    share_amount=sshprnamt,
                    cusip=cusip,
                    cik=owner_cik,
                    accession_number=accession_number,
                    period_of_portfolio=period_of_portfolio,
                    fund_data_id=fund_data.id
                )
                db.session.add(fund_holding)

        except Exception as e:
            print(f"Error processing tag: {e}")

    # Update the submission with portfolio value and number of owned companies
    submission.fund_portfolio_value = fund_portfolio_value
    submission.fund_owns_companies = fund_owns_companies

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error committing to the database: {e}")


def get_fund_lists() -> Dict[str, str]:
    """
    Retrieve a dictionary of well-known funds and their Central Index Keys (CIKs).

    This function returns a manually set dictionary containing the names of well-known funds
    and their corresponding CIKs. These CIKs are used to identify the funds in the SEC database.

    Returns:
        Dict[str, str]: A dictionary where the keys are fund names and the values are their CIKs.
    """
    # Manually set dictionary of well-known funds and their CIKs
    well_known_funds = {
        'Berkshire Hathaway': '0001067983',
        'Sequoia Fund': '0000089043',
        'Third Avenue Management LLC': '0001099281',
        'Longleaf Partners Funds Trust': '0000806636',
        'Mairs & Power Inc: ': '0001070134',
    }
    return well_known_funds


def save_plot_to_file(ticker_symbol: str = 'SPY', period: str = '1y', interval: str = '1d',
                      filename: Optional[str] = None) -> Optional[str]:
    """
    Generate a plot of historical stock prices for a given ticker symbol and save it to a file.

    This function retrieves historical stock price data for a given ticker symbol, generates a plot of the closing prices,
    and saves the plot to a specified file.

    Args:
        ticker_symbol (str): The ticker symbol for the stock. Defaults to 'SPY'.
        period (str): The period of the data to retrieve. Defaults to '1y'.
                      Possible values include '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'.
        interval (str): The interval between data points. Defaults to '1d'.
                        Possible values include '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d',
                        '1wk', '1mo', '3mo'.
        filename (Optional[str]): The path to the file where the plot will be saved. If None, the plot is not saved.

    Returns:
        Optional[str]: The filename where the plot is saved, or None if the plot is not saved.
    """
    try:
        print(f"Generating plot for {ticker_symbol} with period {period} and interval {interval}")

        # Retrieve historical stock price data
        ticker = Ticker(ticker_symbol)
        hist = ticker.history(period=period, interval=interval)
        print(f"Retrieved historical data for {ticker_symbol}")

        # Create the plot
        fig = Figure(figsize=(10, 5))
        ax = fig.subplots()
        ax.plot(hist.index, hist['Close'], label=ticker_symbol)
        ax.set_xlabel('Date')
        ax.set_ylabel('Close Price')
        ax.set_title(f'{ticker_symbol} Historical Data ({period} period, {interval} interval)')
        ax.legend()
        ax.grid(True)

        # Save the plot to a file if a filename is provided
        if filename:
            print(f"Saving plot to file: {filename}")
            fig.savefig(filename)
            plt.close(fig)
            print(f"Plot saved successfully to {filename}")
            return filename

        plt.close(fig)
        print("No filename provided; plot not saved")
        return None

    except Exception as e:
        print(f"Error generating plot for {ticker_symbol}: {str(e)}")
        return None


def fetch_rss_feed(url: str) -> Any:
    """
    Fetch and parse an RSS feed from the specified URL.

    This function sends a GET request to the provided URL, retrieves the RSS feed content,
    and parses it using the feedparser library.

    Args:
        url (str): The URL of the RSS feed to fetch.

    Returns:
        Any: The parsed RSS feed.
    """
    headers = {"User-Agent": get_user_agent()}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return feedparser.parse(response.content)


def parse_rss_feed_entry(entry: FeedParserDict) -> Optional[Dict[str, str]]:
    """
    Parse an RSS feed entry to extract company information and filing details.

    This function takes an RSS feed entry, extracts the form type, company name, CIK, filed date,
    and accession number, and returns them in a dictionary.

    Args:
        entry (FeedParserDict): A single RSS feed entry to parse.

    Returns:
        Optional[Dict[str, str]]: A dictionary containing parsed information, or None if parsing fails.
    """
    try:
        title_parts = entry.title.split(" - ")
        form_type, company_info = title_parts[0], title_parts[1]
        company_name = company_info.split(" (")[0]
        cik = company_info.split(" (")[1].split(")")[0]
        filed_date = re.search(r"<b>Filed:</b> (\d{4}-\d{2}-\d{2})", entry.summary).group(1)
        acc_no = re.search(r"<b>AccNo:</b> ([\d-]+)", entry.summary).group(1)
        return {
            "company_name": company_name,
            "form_type": form_type,
            "cik": cik,
            "filed_date": filed_date,
            "acc_no": acc_no
        }
    except (IndexError, AttributeError) as e:
        print(f"Error parsing entry: {e}")
        return None


def get_rss_feed_entries() -> List[Optional[Dict[str, str]]]:
    """
    Fetch RSS feed entries from predefined URLs and parse each entry.

    This function retrieves RSS feeds from predefined SEC URLs, parses each entry to extract relevant information,
    and returns a list of parsed entries.

    Returns:
        List[Optional[Dict[str, str]]]: A list of dictionaries containing parsed RSS feed entries.
    """
    urls = [
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=13f-hr&owner=include&count=20&output=atom",
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=nport-p&owner=include&count=20&output"
        "=atom"
    ]
    entries = []
    for url in urls:
        # Fetch and parse the RSS feed
        feed = fetch_rss_feed(url)
        for entry in feed.entries:
            # Parse each RSS feed entry
            parsed_entry = parse_rss_feed_entry(entry)
            entries.append(parsed_entry)
    return entries


def validate_unique_email(form: FlaskForm, field: StringField) -> None:
    """
    Validate that the email address provided in the form is unique and not already in use.

    Args:
        form (FlaskForm): The form containing the email field to validate.
        field (StringField): The email field to validate.

    Raises:
        ValidationError: If the email is already in use by another user.
    """
    # Check if the email is different from the default (indicating a change) and already exists in the database
    if field.data != form.email.default and User.query.filter_by(email=field.data).first():
        raise ValidationError('Email already in use.')


def validate_unique_phone_number(form: FlaskForm, field: StringField) -> None:
    """
    Validate that the phone number is unique in the database, if provided and changed.

    Args:
        form (FlaskForm): The form containing the phone number field to validate.
        field (StringField): The phone number field to validate.

    Raises:
        ValidationError: If the phone number is already in use by another user.
    """
    # Check if phone number field is not empty
    if field.data:
        existing_user = User.query.filter_by(phone_number=field.data).first()
        # Ensure the phone number is not in use by another user (not the current user)
        if existing_user and existing_user.id != current_user.id:
            raise ValidationError('Phone number already in use.')


def validate_phone_format(form: FlaskForm, field: StringField) -> None:
    """
    Validates that the input matches the expected phone number format.

    Args:
        form (FlaskForm): The form containing the phone number field to validate.
        field (StringField): The phone number field to validate.

    Raises:
        ValidationError: If the phone number does not match the expected format.
    """
    phone_regex = re.compile(r'^\+\d{9,14}$')
    # Check if the phone number field has data and matches the expected format
    if field.data and not phone_regex.match(field.data):
        raise ValidationError("Invalid phone number. It must start with + and be 10 to 15 characters long.")


def validate_name_surname_format_only_str(form: FlaskForm, field: StringField) -> None:
    """
    Validates that the input for name and surname fields contains only letters.

    Args:
        form (FlaskForm): The form containing the name or surname field to validate.
        field (StringField): The name or surname field to validate.

    Raises:
        ValidationError: If the field contains non-letter characters.
    """
    # Check if the name or surname field has data and contains only letters
    if field.data and not re.match(r"^[A-Za-z]+$", field.data):
        raise ValidationError("Field must contain only letters.")


def validate_match(form: FlaskForm, field1: str, field2: str) -> None:
    """
    Validator to ensure that two fields in a WTForms form match.

    Args:
        form (FlaskForm): The form object.
        field1 (str): Name of the first field to compare.
        field2 (str): Name of the second field to compare.

    Raises:
        ValidationError: If the fields do not match.
    """
    # Check if the values of the two fields match
    if form[field1].data != form[field2].data:
        raise ValidationError(f"{field1.capitalize()}s must match.")


def validate_current_password(form: FlaskForm, field: StringField) -> None:
    """
    Validator to validate the current password.

    This function checks if the provided current password matches the user's existing password in the database.

    Args:
        form (FlaskForm): The form containing the current password field to validate.
        field (StringField): The current password field to validate.

    Raises:
        ValidationError: If the current password is invalid.
    """
    if form.current_password.data and not check_password_hash(current_user.password, form.current_password.data):
        raise ValidationError('Invalid current password.')


def validate_password_strong_password(form: FlaskForm, field: StringField) -> None:
    """
    Validate that the provided password meets the strength criteria.

    This function checks if the provided password meets the following strength criteria:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character

    Args:
        form (FlaskForm): The form containing the password field to validate.
        field (StringField): The password field to validate.

    Raises:
        ValidationError: If the password does not meet the strength criteria.
    """
    password = field.data

    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('Password must contain at least one digit.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character.')


def validate_admin_pin(form: FlaskForm, admin_pin: StringField) -> None:
    """
    Validate that the provided admin PIN matches the expected PIN from environment variables.

    This function checks if the provided admin PIN matches the expected PIN stored in the environment variables.

    Args:
        form (FlaskForm): The form containing the admin PIN field to validate.
        admin_pin (StringField): The admin PIN field to validate.

    Raises:
        ValidationError: If the admin PIN is invalid.
    """
    if admin_pin.data != os.getenv('ADMIN_PIN'):
        raise ValidationError('Invalid admin PIN.')


def fetch_and_process_holdings(cik, start_date=None, end_date=None):
    """
    Fetch and process holdings data for a given CIK.
    """
    # Fetch the fund and its submissions from the database
    fund = Submission.query.filter_by(cik=cik).first()

    if not fund:
        # If no fund found, fetch from SEC EDGAR and update the database
        edgar_downloader_from_sec(cik, start_date=start_date, end_date=end_date)
        fund = Submission.query.filter_by(cik=cik).first()
        if not fund:
            return None, [], []

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

    # Create a dictionary to track the count of reports for each quarter
    submissions_by_date = defaultdict(list)
    for submission in all_submissions:
        submissions_by_date[submission.filed_of_date].append(submission)

    processed_submissions = []
    for date in sorted(submissions_by_date.keys(), reverse=True):
        submissions = submissions_by_date[date]
        for i, submission in enumerate(submissions, start=1):
            period_with_suffix = f"{submission.period_of_portfolio}_{i}"
            processed_submissions.append({
                'filed_of_date': submission.filed_of_date,
                'period_of_portfolio': period_with_suffix,
                'submission_type': submission.submission_type,
                'accession_number': submission.accession_number,
                'fund_portfolio_value': submission.fund_portfolio_value
            })

    # Sort processed_submissions by Accession Number in descending order
    processed_submissions.sort(key=lambda x: x['accession_number'], reverse=True)

    # Sort DataFrame by Company Name and Accession Number
    holdings_df.sort_values(by=['Company Name', 'Accession Number'], ascending=[True, False], inplace=True)

    return fund, processed_submissions, holdings_df


def process_holdings_dataframe(holdings_df, all_submissions):
    """
    Process the holdings DataFrame to compare current and previous holdings.
    """
    most_recent_accession = all_submissions[0]['accession_number'] if all_submissions else None
    previous_accession = all_submissions[1]['accession_number'] if len(all_submissions) > 1 else None

    if not most_recent_accession:
        return []

    current_holdings_df = holdings_df[holdings_df['Accession Number'] == most_recent_accession].copy()
    if previous_accession:
        previous_holdings_df = holdings_df[holdings_df['Accession Number'] == previous_accession].copy()

        try:
            merged_holdings_df = pd.merge(
                current_holdings_df,
                previous_holdings_df[['Company Name', 'Share Amount']],
                on='Company Name',
                how='left',
                suffixes=('', '_Previous')
            )
            merged_holdings_df.rename(columns={'Share Amount_Previous': 'Previous Share Amount'}, inplace=True)

            previous_companies = previous_holdings_df['Company Name'].unique()
            merged_holdings_df['New Company'] = ~merged_holdings_df['Company Name'].isin(previous_companies)

            merged_holdings_df['Change Amount'] = merged_holdings_df['Share Amount'] - merged_holdings_df[
                'Previous Share Amount'].fillna(0)

            def calculate_change_percentage(row):
                if pd.isna(row['Previous Share Amount']) or row['Previous Share Amount'] == 0:
                    if row['Share Amount'] > 0:
                        return 100.0
                    else:
                        return 0.0
                else:
                    return (row['Change Amount'] / row['Previous Share Amount']) * 100

            merged_holdings_df['Change Percentage'] = merged_holdings_df.apply(calculate_change_percentage, axis=1)

            merged_holdings_df['Change Status'] = 'No Change'
            merged_holdings_df.loc[merged_holdings_df['Share Amount'] > merged_holdings_df[
                'Previous Share Amount'], 'Change Status'] = 'Increased'
            merged_holdings_df.loc[merged_holdings_df['Share Amount'] < merged_holdings_df[
                'Previous Share Amount'], 'Change Status'] = 'Decreased'
            merged_holdings_df.loc[
                merged_holdings_df['Previous Share Amount'].isna(), 'Change Status'] = 'New Investment'

            previous_holdings_not_in_current = previous_holdings_df[
                ~previous_holdings_df['Company Name'].isin(current_holdings_df['Company Name'])].copy()

            previous_holdings_not_in_current['Share Amount'] = 0
            previous_holdings_not_in_current['Change Status'] = 'Position Closed'
            previous_holdings_not_in_current['New Company'] = False
            previous_holdings_not_in_current['Change Amount'] = -previous_holdings_not_in_current['Share Amount']
            previous_holdings_not_in_current['Change Percentage'] = -100

            merged_holdings_df = pd.concat([merged_holdings_df, previous_holdings_not_in_current],
                                           ignore_index=True)

        except KeyError:
            current_holdings_df['Previous Share Amount'] = 0
            current_holdings_df['New Company'] = True
            current_holdings_df['Change Status'] = 'New Investment'
            current_holdings_df['Change Amount'] = current_holdings_df['Share Amount']
            current_holdings_df['Change Percentage'] = 100.0
            merged_holdings_df = current_holdings_df

    else:
        current_holdings_df['Previous Share Amount'] = 0
        current_holdings_df['New Company'] = True
        current_holdings_df['Change Status'] = 'New Investment'
        current_holdings_df['Change Amount'] = current_holdings_df['Share Amount']
        current_holdings_df['Change Percentage'] = 100.0
        merged_holdings_df = current_holdings_df

    merged_holdings_df['Value (USD)'] = merged_holdings_df['Value (USD)'].fillna(0).astype(int)
    merged_holdings_df['Share Amount'] = merged_holdings_df['Share Amount'].fillna(0).astype(int)
    merged_holdings_df['Previous Share Amount'] = merged_holdings_df['Previous Share Amount'].fillna(0).astype(int)
    merged_holdings_df['Change Amount'] = merged_holdings_df['Change Amount'].fillna(0).astype(int)
    merged_holdings_df['Change Percentage'] = merged_holdings_df['Change Percentage'].fillna(0).round(1)

    return merged_holdings_df.to_dict(orient='records')


def process_monitor_holdings_dataframe(holdings_df, all_submissions):
    """
    Process the holdings DataFrame specifically for the monitor view.

    This function merges multiple holdings submissions into a single DataFrame, organizing
    the data by company name and submission period. It also ensures that the periods are
    uniquely identified even if multiple submissions exist within the same period.

    Args:
        holdings_df (pd.DataFrame): DataFrame containing holdings data.
        all_submissions (list): List of dictionaries containing submission details.

    Returns:
        tuple: A tuple containing:
            - list: List of dictionaries representing the processed holdings data.
            - list: List of column headers for the merged DataFrame.
    """
    # Extract accession numbers and periods from all_submissions
    accession_numbers = [submission['accession_number'] for submission in all_submissions]
    periods = [submission['period_of_portfolio'] for submission in all_submissions]

    # Initialize the merged DataFrame with 'Company Name' column
    merged_holdings_df = pd.DataFrame(columns=['Company Name'])

    # Dictionary to keep track of period suffixes
    period_counts = {}

    # Loop through accession numbers and periods to merge data
    if accession_numbers:
        for i, (accession_number, period) in enumerate(zip(accession_numbers, periods)):
            # Increment the period count for unique suffix
            period_counts[period] = period_counts.get(period, 0) + 1
            period_suffix = period_counts[period]

            # Create the column name with or without suffix
            column_name = f'{period}_{period_suffix}' if period_suffix > 1 else period

            # Filter and rename columns in the temporary DataFrame
            temp_df = holdings_df[holdings_df['Accession Number'] == accession_number].copy()
            temp_df.rename(columns={'Share Amount': column_name}, inplace=True)

            # Merge the temporary DataFrame with the merged DataFrame
            merged_holdings_df = pd.merge(
                merged_holdings_df,
                temp_df[['Company Name', column_name]],
                on='Company Name',
                how='outer'
            )

    # Fill NaN values with 0
    merged_holdings_df.fillna(0, inplace=True)

    # Convert all columns except 'Company Name' to integers
    for col in merged_holdings_df.columns[1:]:
        merged_holdings_df[col] = merged_holdings_df[col].astype(int)

    # Reorder columns to place 'Company Name' first and reverse the order of other columns
    columns_order = ['Company Name'] + [col for col in merged_holdings_df.columns if col != 'Company Name'][::-1]
    merged_holdings_df = merged_holdings_df[columns_order]

    # Convert the merged DataFrame to a dictionary and return it along with the column order
    return merged_holdings_df.to_dict(orient='records'), columns_order

