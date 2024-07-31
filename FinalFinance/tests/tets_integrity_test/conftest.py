import pytest
from unittest.mock import patch, Mock
from FinalFinance import create_app, db
from FinalFinance.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='module')
def test_client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope='function', autouse=True)
def init_database():
    db.create_all()
    yield db
    db.session.remove()
    db.drop_all()


@pytest.fixture(scope='function')
def login_test_user(test_client):
    user = User(email='testuser@example.com', username='testuser', _password=generate_password_hash('password'))
    db.session.add(user)
    db.session.commit()

    response = test_client.post('/login', data={
        'username': 'testuser',
        'password': 'password'
    }, follow_redirects=True)

    assert response.status_code == 200

    return user


@pytest.fixture
def mock_sec_requests():
    with patch('FinalFinance.utils.fetch_rss_feed') as mock_fetch:
        mock_fetch.return_value = Mock(entries=[])
        yield mock_fetch
