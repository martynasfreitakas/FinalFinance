import pytest
from FinalFinance import db
from FinalFinance.models import FundData, AddFundToFavorites


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


@pytest.mark.usefixtures("mock_sec_requests")
def test_monitor_no_favorites(test_client, init_database, login_test_user):
    """Test the monitor route when no favorites are added."""
    response = test_client.get('/monitor')
    # Debugging information
    print("Monitor No Favorites Response Status Code:", response.status_code)
    print("Monitor No Favorites Response Data:", response.get_data(as_text=True))

    assert response.status_code == 200
    assert 'Add Fund to favorites to get stats.' in response.get_data(as_text=True)


@pytest.mark.usefixtures("mock_sec_requests")
def test_monitor_with_favorites(test_client, init_database, login_test_user):
    """Test the monitor route with favorites."""
    # Setup a fund and add it to favorites
    fund = FundData(fund_name='Test Fund A', cik='0001234567')
    db.session.add(fund)
    db.session.commit()

    favorite = AddFundToFavorites(user_id=login_test_user.id, fund_id=fund.id)
    db.session.add(favorite)
    db.session.commit()

    response = test_client.get('/monitor')

    # Debugging information
    print("Monitor With Favorites Response Status Code:", response.status_code)
    print("Monitor With Favorites Response Data:", response.get_data(as_text=True))

    assert response.status_code == 200, f"Expected 200 but got {response.status_code} with data: {response.get_data(as_text=True)}"
    assert 'Test Fund A' in response.get_data(as_text=True)
