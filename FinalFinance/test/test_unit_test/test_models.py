import unittest
from FinalFinance import create_app, db
from FinalFinance.models import User, FundData, Submission, FundHoldings, AddFundToFavorites
from datetime import date


class ModelsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        user = User(username='astest', email='test@as.lt')
        user.surname = 'labas'
        user.phone_number = '888'
        user.password = 'slaptazodis'
        db.session.add(user)
        db.session.commit()
        self.assertEqual(user.username, 'astest')
        self.assertEqual(user.surname, 'labas')
        self.assertNotEqual(user.phone_number, '777')
        self.assertTrue(user.check_password('slaptazodis'))

    def test_fund_data_creation(self):
        fund = FundData(fund_name='Berskhire Fund', cik='0000000088')
        db.session.add(fund)
        db.session.commit()
        self.assertEqual(fund.fund_name, 'Berskhire Fund')
        self.assertEqual(fund.cik, '0000000088')

    def test_submission_creation(self):
        fund = FundData(fund_name='Test Fund', cik='0000000000')
        db.session.add(fund)
        db.session.commit()

        submission = Submission(
            cik='0000000000',
            company_name='Best Company',
            submission_type='NPORT-P',
            filed_of_date=date.today(),
            accession_number='0000000000-21-000000',
            period_of_portfolio='2021-12-31',
            fund_data_id=fund.id
        )
        db.session.add(submission)
        db.session.commit()
        self.assertEqual(submission.company_name, 'Best Company')

    def test_fund_holdings_creation(self):
        fund = FundData(fund_name='Test Fund', cik='0000000000')
        db.session.add(fund)
        db.session.commit()

        holding = FundHoldings(
            company_name='Test Holding',
            value_usd=1000000.0,
            share_amount=10000.0,
            cusip='123456789',
            cik='0000000000',
            accession_number='0000000000-21-000000',
            period_of_portfolio='2021-12-31',
            fund_data_id=fund.id
        )
        db.session.add(holding)
        db.session.commit()
        self.assertEqual(holding.company_name, 'Test Holding')

    def test_add_fund_to_favorites(self):
        user = User(username='testuser', email='test@example.com')
        user.password = 'testpassword'
        db.session.add(user)
        db.session.commit()

        fund = FundData(fund_name='Test Fund', cik='0000000000')
        db.session.add(fund)
        db.session.commit()

        favorite = AddFundToFavorites(user_id=user.id, fund_id=fund.id)
        db.session.add(favorite)
        db.session.commit()
        self.assertEqual(favorite.user_id, user.id)
        self.assertEqual(favorite.fund_id, fund.id)


if __name__ == '__main__':
    unittest.main()
