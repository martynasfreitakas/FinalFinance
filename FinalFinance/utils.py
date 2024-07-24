from typing import Optional, Dict, Any, List

from feedparser import FeedParserDict
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms.fields.simple import StringField

from models import Submission, FundHoldings, FundData
from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader
from dotenv import load_dotenv
import requests
from database import db
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
from models import User
from werkzeug.security import check_password_hash
from flask_login import current_user

load_dotenv()


def setup_logging(default_path='logging.conf', default_level=logging.INFO):
    """Setup logging configuration."""
    path = default_path
    if os.path.exists(path):
        try:
            logging.config.fileConfig(path)
        except Exception as e:
            print(f"Failed to load logging configuration: {e}")
            logging.basicConfig(level=default_level)
    else:
        print(f"Logging configuration file {path} not found. Using default configuration.")
        logging.basicConfig(level=default_level)


setup_logging()

logger = logging.getLogger('sLogger')


def get_user_agent() -> Optional[str]:
    """
        Retrieve the user agent from the environment variable.
    """
    return os.environ.get('EMAIL_FOR_AUTHORIZATION', 'USER_AGENT')


def download_and_store_all_companies_names_and_cik_from_edgar() -> None:
    """
    Download and store all company names and CIKs from the SEC's Edgar database.

    """
    logger.info('Starting downloading data from Edgar.')

    url = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"

    headers = {"User-Agent": get_user_agent()}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        logger.info('Connected succesfully.')
        data_line = response.text.splitlines()
        all_lines_in_document = len(data_line)
        data = [(line.split(":")[0], line.split(":")[1].rstrip(':')) for line in data_line if ":" in line]

        for number_downloaded, (fund_name, fund_cik) in enumerate(data, start=1):
            fund_data = FundData(fund_name=fund_name, cik=fund_cik)
            db.session.add(fund_data)
            if number_downloaded % 1000 == 0:
                logging.info(f"Processed {number_downloaded} of {all_lines_in_document} lines.")
        db.session.commit()

        results = db.session.query(
            FundData.cik,
            func.group_concat(FundData.fund_name, ', ').label('fund_names')
        ).group_by(FundData.cik).having(func.count(FundData.cik) > 1).all()

        for number_dublicates, result in enumerate(results, start=1):
            fund_cik, fund_names = result

            fund_data = FundData.query.filter_by(cik=fund_cik).first()

            fund_data.fund_name = fund_names

            FundData.query.filter(FundData.cik == fund_cik, FundData.id != fund_data.id).delete()

            if number_dublicates % 1000 == 0:
                logging.info(f"Processed {number_dublicates} of {all_lines_in_document} updates.")

        db.session.commit()
    else:
        print(f"Error: {response.status_code}")


def edgar_downloader_from_sec(fund_cik: str,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> None:
    """
    Download SEC filings for a given fund CIK between specified dates and store them locally.
    """

    filing_types = ['NPORT-P', '13F-HR']

    if start_date is None:
        start_date = datetime(2022, 2, 1)
    if end_date is None:
        end_date = datetime(2024, 7, 24)

    # Should be as it is, because downloader can break
    dir_path = 'sec-edgar-filings'

    for filing_type in filing_types:
        filings_path = os.path.join(dir_path, fund_cik, filing_type)
        if os.path.exists(filings_path):
            shutil.rmtree(filings_path)
        os.makedirs(filings_path)

        try:
            dl = Downloader(dir_path, os.environ['EMAIL_FOR_AUTHORIZATION'])
            dl.get(filing_type, fund_cik, after=start_date, before=end_date)
        except HTTPError as e:
            if e.response.status_code == 404:
                print(f"404 Error for URL: {e.request.url}. CIK may be incorrect or data not available.")
            else:
                print(f"HTTP error occurred: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        if not os.listdir(filings_path):
            os.rmdir(filings_path)

        add_filing_to_db(fund_cik)


def add_filing_to_db(fund_cik: str) -> None:
    """
    Process and add SEC filings for a given fund CIK to the database.
    """
    directory_path = os.path.join('sec-edgar-filings', fund_cik)
    if not os.path.exists(directory_path):
        print(f"Directory does not exist: {directory_path}")
        return

    subdirectories = [directory for directory in os.listdir(directory_path) if
                      os.path.isdir(os.path.join(directory_path, directory))]
    for subdirectory in subdirectories:
        subdirectory_path = os.path.join(directory_path, subdirectory)
        sub_subdirectories = [directory for directory in os.listdir(subdirectory_path) if
                              os.path.isdir(os.path.join(subdirectory_path, directory))]

        for sub_subdirectory in sub_subdirectories:
            sub_subdirectory_path = os.path.join(subdirectory_path, sub_subdirectory)
            files = os.listdir(sub_subdirectory_path)
            if not files:
                continue

            for file in files:
                file_path = os.path.join(sub_subdirectory_path, file)
                extract_holdings_from_file(file_path)


def extract_holdings_from_file(path_to_file: str) -> None:
    """
    Extract holdings from a given file and add them to the database.
    """
    with open(path_to_file, 'r') as file:
        data = file.read()

    soup = BeautifulSoup(data, 'lxml')
    tags = soup.find_all(['infotable', 'ns1:infotable', 'invstorsec'])

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

    fund_data = FundData.query.filter_by(cik=owner_cik).first()
    if not fund_data:
        print(f"No FundData found for CIK: {owner_cik}")
        return

    existing_submission = Submission.query.filter_by(accession_number=accession_number).first()
    if existing_submission:
        submission = existing_submission
        submission.cik = owner_cik
        submission.company_name = company_conformed_name
        submission.submission_type = submission_type
        submission.filed_of_date = filed_of_date
        submission.period_of_portfolio = period_of_portfolio
        submission.fund_data_id = fund_data.id
    else:
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

            existing_fund_holding = FundHoldings.query.filter_by(company_name=nameofissuer,
                                                                 accession_number=accession_number).first()
            if existing_fund_holding:
                existing_fund_holding.value_usd = value
                existing_fund_holding.share_amount = sshprnamt
                existing_fund_holding.cusip = cusip
                existing_fund_holding.cik = owner_cik
                existing_fund_holding.period_of_portfolio = period_of_portfolio
                existing_fund_holding.fund_data_id = fund_data.id
            else:
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
    Manually set Funds.
    """
    well_known_funds = {
        'Berkshire Hathaway': '0001067983',
        'Sequoia Fund': '0000089043',
        'Third Avenue Management LLC': '0001099281',
        'Longleaf Partners Funds Trust': '0000806636',
        'Mairs & Power Inc: ': '0001070134',
    }
    return well_known_funds


# def get_plot_base64(ticker_symbol='spy', period='1y', interval='1d'):
#     # Period
#     # 1d, 5d: Data for the last 1 or 5 days.
#     # 1mo, 3mo, 6mo: Data for the last 1, 3, or 6 months.
#     # 1y, 2y, 5y, 10y, ytd: Data for the last 1, 2, 5, 10 years, or year to date.
#     # max: All available data.
#
#     # Interval
#     # 1m, 2m, 5m, 15m, 30m, 60m, 90m: Intraday data at 1, 2, 5, 15, 30, 60,
#     #   or 90-minute intervals. Intraday data might not be available for
#     #    all periods.
#     # 1h: Hourly data.
#     # 1d, 5d: Daily or weekly data.
#     # 1wk: Weekly data.
#     # 1mo, 3mo: Monthly or quarterly data.
#     buf = None  # Initialize buf variable
#
#     try:
#         ticker = Ticker(ticker_symbol)
#         hist = ticker.history(period=period, interval=interval)
#
#         fig = Figure(figsize=(10, 5))
#         ax = fig.subplots()
#         ax.plot(hist.index, hist['Close'], label=ticker_symbol)
#         ax.set_xlabel('Date')
#         ax.set_ylabel('Close Price')
#         ax.set_title(f'{ticker_symbol} Historical Data ({period} period)')
#         ax.legend()
#         ax.grid(True)
#
#         buf = BytesIO()
#         fig.savefig(buf, format='png')
#         buf.seek(0)
#         base64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
#         plt.close(fig)
#
#         return base64_img
#
#     except Exception as e:
#         print(f"Error generating plot for {ticker_symbol}: {str(e)}")
#         return None
#
#     finally:
#         if buf:
#             buf.close()


def save_plot_to_file(
        ticker_symbol: str = 'SPY',
        period: str = '1y',
        interval: str = '1d',
        filename: Optional[str] = None) -> Optional[str]:
    """
    Generate a plot of historical stock prices for a given ticker symbol and save it to a file.

    ticker_symbol (str): The ticker symbol for the stock. Defaults to 'SPY'.
    period (str): The period of the data to retrieve. Defaults to '1y'.
                    Possible values include '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'.
    interval (str): The interval between data points. Defaults to '1d'.
                    Possible values include '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d',
                    '1wk', '1mo', '3mo'.
    """
    try:
        ticker = Ticker(ticker_symbol)
        hist = ticker.history(period=period, interval=interval)

        fig = Figure(figsize=(10, 5))
        ax = fig.subplots()
        ax.plot(hist.index, hist['Close'], label=ticker_symbol)
        ax.set_xlabel('Date')
        ax.set_ylabel('Close Price')
        ax.set_title(f'{ticker_symbol} Historical Data ({period} period)')
        ax.legend()
        ax.grid(True)

        if filename:
            fig.savefig(filename)
            plt.close(fig)
            return filename

        plt.close(fig)
        return None

    except Exception as e:
        print(f"Error generating plot for {ticker_symbol}: {str(e)}")
        return None


def fetch_rss_feed(url: str) -> Any:
    """
    Fetch and parse an RSS feed from the specified URL.
    """
    headers = {"User-Agent": get_user_agent()}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return feedparser.parse(response.content)


def parse_rss_feed_entry(entry: FeedParserDict) -> Optional[Dict[str, str]]:
    """
    Parse an RSS feed entry to extract company information and filing details.
    """
    title_parts = entry.title.split(" - ")
    form_type, company_info = title_parts[0], title_parts[1]
    company_name, cik = company_info.split(" (")[0], company_info.split(" (")[1].split(")")[0]
    filed_date = re.search(r"<b>Filed:</b> (\d{4}-\d{2}-\d{2})", entry.summary).group(1)
    acc_no = re.search(r"<b>AccNo:</b> ([\d-]+)", entry.summary).group(1)
    return {
        "company_name": company_name,
        "form_type": form_type,
        "cik": cik,
        "filed_date": filed_date,
        "acc_no": acc_no
    }


def get_rss_feed_entries() -> List[Optional[Dict[str, str]]]:
    """
    Fetch RSS feed entries from predefined URLs and parse each entry.
    """
    urls = [
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=13f-hr&owner=include&count=20&output=atom",
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=nport-p&owner=include&count=20&output"
        "=atom"
    ]
    entries = []
    for url in urls:
        feed = fetch_rss_feed(url)
        for entry in feed.entries:
            parsed_entry = parse_rss_feed_entry(entry)
            entries.append(parsed_entry)
    return entries


def validate_unique_email(form: FlaskForm, field: StringField) -> None:
    """
    Validate that the email address provided in the form is unique and not already in use.
    """
    if field.data != form.email.default and User.query.filter_by(email=field.data).first():
        raise ValidationError('Email already in use.')


def validate_unique_phone_number(form, field):
    """
    Validates that the phone number is unique in the database, if provided and changed.
    """
    if field.data:  # Check if phone number field is not empty
        existing_user = User.query.filter_by(phone_number=field.data).first()
        if existing_user and existing_user.id != current_user.id:
            raise ValidationError('Phone number already in use.')


def validate_phone_format(form, field):
    """
    Validates that the input matches the expected phone number format.
    """
    phone_regex = re.compile(r'^\+\d{9,14}$')
    if field.data and not phone_regex.match(field.data):  # Check only if field has data
        raise ValidationError("Invalid phone number. It must start with + and be 10 to 15 characters long.")


def validate_name_surname_format_only_str(form, field):
    """
    Validates that the input for name and surname fields contains only letters.
    """
    if field.data and not re.match(r"^[A-Za-z]+$", field.data):  # Check only if field has data
        raise ValidationError("Field must contain only letters.")


def validate_match(form, field1, field2):
    """
    Validator to ensure that two fields in a WTForms form match.

    Args:
        form (FlaskForm): The form object.
        field1 (str): Name of the first field to compare.
        field2 (str): Name of the second field to compare.

    Raises:
        ValidationError: If the fields do not match.
    """
    if form[field1].data != form[field2].data:
        raise ValidationError(f"{field1.capitalize()}s must match.")


def validate_current_password(form, field) -> None:
    """
    Validator to validate the current password.

    """
    if form.current_password.data and not check_password_hash(form.user.password, form.current_password.data):
        raise ValidationError('Invalid current password.')


def validate_password_strong_password(form: FlaskForm, field: StringField) -> None:
    """
    Validate that the provided password meets the strength criteria.
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
    """

    if admin_pin.data != os.getenv('ADMIN_PIN'):
        raise ValidationError('Invalid admin PIN.')
