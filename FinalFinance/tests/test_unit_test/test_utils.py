import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from FinalFinance import create_app, db
from FinalFinance.utils import get_user_agent, download_and_store_all_companies_names_and_cik_from_edgar, \
    save_plot_to_file, extract_holdings_from_file
from FinalFinance.models import FundData
import tempfile
import shutil


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        shutil.rmtree(self.temp_dir)

    def test_get_user_agent(self):
        os.environ['EMAIL_FOR_AUTHORIZATION'] = 'test_user_agent'
        user_agent = get_user_agent()
        self.assertEqual(user_agent, 'test_user_agent')

    @patch('FinalFinance.utils.requests.get')
    def test_download_and_store_all_companies_names_and_cik_from_edgar(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Example Fund:0001234567\nAnother Fund:0002345678"
        mock_get.return_value = mock_response

        download_and_store_all_companies_names_and_cik_from_edgar()

        fund_data = FundData.query.all()
        self.assertEqual(len(fund_data), 2)
        self.assertEqual(fund_data[0].fund_name, 'Example Fund')
        self.assertEqual(fund_data[0].cik, '0001234567')
        self.assertEqual(fund_data[1].fund_name, 'Another Fund')
        self.assertEqual(fund_data[1].cik, '0002345678')

    @patch('FinalFinance.utils.Ticker')
    def test_save_plot_to_file(self, mock_ticker):

        data = {
            'Close': [100, 200],
            'Date': pd.to_datetime(['2021-01-01', '2021-01-02'])
        }
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)

        mock_ticker.return_value.history.return_value = df

        filename = os.path.join(self.temp_dir, 'test_plot.png')
        result = save_plot_to_file('SPY', '1d', '1d', filename)
        self.assertEqual(result, filename)
        self.assertTrue(os.path.exists(filename))

    @patch('FinalFinance.utils.db')
    @patch('FinalFinance.utils.open', new_callable=unittest.mock.mock_open, read_data="Mock file content")
    def test_extract_holdings_from_file(self, mock_open, mock_db):
        mock_session = MagicMock()
        mock_db.session = mock_session

        extract_holdings_from_file("path/to/mock/file")

        mock_open.assert_called_once_with("path/to/mock/file", 'r')
        self.assertTrue(mock_session.commit.called)


if __name__ == '__main__':
    unittest.main()
