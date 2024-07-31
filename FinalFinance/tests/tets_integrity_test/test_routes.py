import pytest
from FinalFinance import db
from FinalFinance.models import FundData


def test_fund_search_empty_query(test_client, init_database):
    response = test_client.get('/fund_search?query=')
    assert response.status_code == 200
    assert b'Please enter a company name or CIK.' in response.data


def test_fund_search_valid_cik(test_client, init_database):
    fund1 = FundData(cik='0001234567', fund_name='Test Fund A')
    db.session.add(fund1)
    db.session.commit()

    response = test_client.get('/fund_search?query=0001234567')
    assert response.status_code == 200
    assert b'Test Fund A' in response.data


def test_fund_search_valid_fund_name(test_client, init_database):
    fund1 = FundData(cik='0001234568', fund_name='Test Fund A')
    db.session.add(fund1)
    db.session.commit()

    response = test_client.get('/fund_search?query=Test Fund A')
    assert response.status_code == 200
    assert b'Test Fund A' in response.data
