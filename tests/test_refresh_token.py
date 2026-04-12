import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import importlib

# Ensure we can import the script
# It's an executable script so we have to import it as a module
import scripts.refresh_token as rt

class TestRefreshToken(unittest.TestCase):
    @patch("scripts.refresh_token.settings")
    @patch("scripts.refresh_token.KiteConnect")
    @patch("scripts.refresh_token.HTTPServer")
    @patch("scripts.refresh_token.webbrowser.open")
    def test_refresh_token_success(self, mock_webbrowser_open, mock_httpserver_class, mock_kiteconnect_class, mock_settings):
        mock_settings.KITE_API_KEY = "dummy_key"
        mock_settings.KITE_API_SECRET = "dummy_secret"

        mock_kite_instance = MagicMock()
        mock_kite_instance.login_url.return_value = "http://dummy_url"
        mock_kite_instance.generate_session.return_value = {"access_token": "dummy_access_token"}
        mock_kiteconnect_class.return_value = mock_kite_instance

        mock_server_instance = MagicMock()
        # Mock handle_request to set request_token to simulate receiving the request
        def mock_handle_request():
            mock_server_instance.request_token = "dummy_request_token"

        mock_server_instance.handle_request.side_effect = mock_handle_request
        mock_server_instance.request_token = None
        mock_httpserver_class.return_value = mock_server_instance

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        # Use patch to replace ENV_PATH with a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_env:
            temp_env.write("KITE_API_KEY=dummy_key\n")
            temp_env_path = temp_env.name

        try:
            with patch("scripts.refresh_token.ENV_PATH", temp_env_path):
                rt.main()

            # Verify ENV file was updated
            with open(temp_env_path, "r") as f:
                env_content = f.read()
                self.assertIn("KITE_ACCESS_TOKEN=dummy_access_token", env_content)

            # Verify output
            output = captured_output.getvalue()
            self.assertIn("Token refreshed. Valid until midnight IST.", output)

        finally:
            sys.stdout = sys.__stdout__
            os.remove(temp_env_path)

    @patch("scripts.refresh_token.settings")
    def test_refresh_token_missing_credentials(self, mock_settings):
        mock_settings.KITE_API_KEY = ""
        mock_settings.KITE_API_SECRET = ""

        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            with self.assertRaises(SystemExit) as cm:
                rt.main()

            self.assertEqual(cm.exception.code, 1)
            output = captured_output.getvalue()
            self.assertIn("Error: KITE_API_KEY and KITE_API_SECRET must be set in .env", output)
        finally:
            sys.stdout = sys.__stdout__

    @patch("scripts.refresh_token.settings")
    @patch("scripts.refresh_token.KiteConnect")
    @patch("scripts.refresh_token.HTTPServer")
    @patch("scripts.refresh_token.webbrowser.open")
    def test_refresh_token_generate_session_failure(self, mock_webbrowser_open, mock_httpserver_class, mock_kiteconnect_class, mock_settings):
        mock_settings.KITE_API_KEY = "dummy_key"
        mock_settings.KITE_API_SECRET = "dummy_secret"

        mock_kite_instance = MagicMock()
        mock_kite_instance.login_url.return_value = "http://dummy_url"
        mock_kite_instance.generate_session.side_effect = Exception("API Error")
        mock_kiteconnect_class.return_value = mock_kite_instance

        mock_server_instance = MagicMock()
        def mock_handle_request():
            mock_server_instance.request_token = "dummy_request_token"

        mock_server_instance.handle_request.side_effect = mock_handle_request
        mock_server_instance.request_token = None
        mock_httpserver_class.return_value = mock_server_instance

        captured_output = StringIO()
        sys.stdout = captured_output

        try:
            with self.assertRaises(SystemExit) as cm:
                rt.main()

            self.assertEqual(cm.exception.code, 1)
            output = captured_output.getvalue()
            self.assertIn("Failed to generate session: API Error", output)
        finally:
            sys.stdout = sys.__stdout__

    def test_update_env_file_no_existing_file(self):
        import tempfile
        temp_env_path = tempfile.mktemp()

        with patch("scripts.refresh_token.ENV_PATH", temp_env_path):
            rt.update_env_file("new_token")

        with open(temp_env_path, "r") as f:
            env_content = f.read()
            self.assertIn("KITE_ACCESS_TOKEN=new_token", env_content)

        os.remove(temp_env_path)

    def test_redirect_handler_with_token(self):
        # Test the RedirectHandler explicitly
        mock_request = MagicMock()
        mock_client_address = ('127.0.0.1', 12345)
        mock_server = MagicMock()

        # We don't want to actually start the server logic or bind
        # So we can just instantiate the class by bypassing init
        handler = rt.RedirectHandler.__new__(rt.RedirectHandler)
        handler.path = "/?request_token=my_test_token&action=login"

        # Mock wfile and other methods
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.server = mock_server

        handler.do_GET()

        self.assertEqual(mock_server.request_token, "my_test_token")
        handler.send_response.assert_called_with(200)

    def test_redirect_handler_without_token(self):
        mock_request = MagicMock()
        mock_client_address = ('127.0.0.1', 12345)
        mock_server = MagicMock()

        handler = rt.RedirectHandler.__new__(rt.RedirectHandler)
        handler.path = "/?other_param=value"

        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.server = mock_server

        handler.do_GET()

        handler.send_response.assert_called_with(400)
        self.assertTrue(handler.wfile.write.called)
        self.assertIn(b"Missing request_token!", handler.wfile.write.call_args[0][0])
