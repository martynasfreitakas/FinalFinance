import unittest
import os
from utils import get_user_agent  # Adjust this import based on the location of `utils`


class TestUtils(unittest.TestCase):

    def test_get_user_agent_with_env_var(self):
        os.environ['EMAIL_FOR_AUTHORIZATION'] = 'test_agent'
        self.assertEqual(get_user_agent(), 'test_agent')

    def test_get_user_agent_default(self):
        if 'EMAIL_FOR_AUTHORIZATION' in os.environ:
            del os.environ['EMAIL_FOR_AUTHORIZATION']
        self.assertEqual(get_user_agent(), 'USER_AGENT')


if __name__ == '__main__':
    unittest.main()
