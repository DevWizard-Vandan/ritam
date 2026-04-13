import os
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Adjust path so scripts can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.refresh_token import OAuthHandler, update_env_file, main

class TestRefreshToken(unittest.TestCase):
    def setUp(self):
        OAuthHandler.request_token = None

    def test_oauth_handler_success(self):
        mock_request = MagicMock()
        mock_client_address = ('127.0.0.1', 12345)
        mock_server = MagicMock()

        handler = OAuthHandler.__new__(OAuthHandler)
        handler.path = '/?request_token=my_secret_token&action=login'
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        self.assertEqual(OAuthHandler.request_token, 'my_secret_token')
        handler.send_response.assert_called_with(200)

    def test_oauth_handler_missing_token(self):
        handler = OAuthHandler.__new__(OAuthHandler)
        handler.path = '/favicon.ico'
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        self.assertIsNone(OAuthHandler.request_token)
        handler.send_response.assert_called_with(400)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="KITE_API_KEY=test\nKITE_ACCESS_TOKEN=old_token\n")
    def test_update_env_file_existing_token(self, mock_file, mock_exists):
        mock_exists.return_value = True

        update_env_file('new_token_123')

        mock_file().write.assert_called_once()
        written_content = mock_file().write.call_args[0][0]
        self.assertIn('KITE_ACCESS_TOKEN=new_token_123', written_content)
        self.assertNotIn('old_token', written_content)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="KITE_API_KEY=test\n")
    def test_update_env_file_new_token(self, mock_file, mock_exists):
        mock_exists.return_value = True

        update_env_file('new_token_456')

        mock_file().write.assert_called_once()
        written_content = mock_file().write.call_args[0][0]
        self.assertIn('KITE_ACCESS_TOKEN=new_token_456', written_content)

    @patch('os.path.exists')
    def test_update_env_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            update_env_file('new_token')

    @patch('scripts.refresh_token.settings')
    @patch('scripts.refresh_token.KiteConnect')
    @patch('scripts.refresh_token.webbrowser.open')
    @patch('scripts.refresh_token.HTTPServer')
    @patch('scripts.refresh_token.update_env_file')
    def test_main_success(self, mock_update_env, mock_server, mock_browser, mock_kite, mock_settings):
        mock_settings.KITE_API_KEY = 'test_key'
        mock_settings.KITE_API_SECRET = 'test_secret'

        mock_kite_instance = MagicMock()
        mock_kite.return_value = mock_kite_instance
        mock_kite_instance.login_url.return_value = "http://login.url"
        mock_kite_instance.generate_session.return_value = {'access_token': 'test_access_token'}

        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Simulate the handler getting the token to break the while loop
        def mock_handle_request():
            OAuthHandler.request_token = 'simulated_token'

        mock_server_instance.handle_request.side_effect = mock_handle_request

        main()

        mock_kite_instance.login_url.assert_called_once()
        mock_browser.assert_called_once_with("http://login.url")
        mock_server_instance.handle_request.assert_called_once()
        mock_server_instance.server_close.assert_called_once()
        mock_kite_instance.generate_session.assert_called_once_with('simulated_token', api_secret='test_secret')
        mock_update_env.assert_called_once_with('test_access_token')

    @patch('scripts.refresh_token.settings')
    def test_main_missing_keys(self, mock_settings):
        mock_settings.KITE_API_KEY = ''
        mock_settings.KITE_API_SECRET = ''

        with self.assertRaises(SystemExit):
            main()

if __name__ == '__main__':
    unittest.main()
