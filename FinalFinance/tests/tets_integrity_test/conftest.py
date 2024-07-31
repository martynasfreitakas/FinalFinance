import pytest
from FinalFinance import create_app, db
from FinalFinance.models import FundData


@pytest.fixture(scope='module')
def test_client():
    flask_app = create_app('testing')
    testing_client = flask_app.test_client()
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client

    ctx.pop()


@pytest.fixture(scope='function', autouse=True)
def init_database():
    db.create_all()

    yield db

    db.session.remove()
    db.drop_all()
