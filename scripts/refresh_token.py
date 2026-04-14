#!/usr/bin/env python3
"""
Automates fetching the Kite Connect request token by starting a local HTTP server
to capture the redirect, and then updating the .env file with the new access token.
Intended to be run daily before market open.
"""

import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from loguru import logger
from kiteconnect import KiteConnect

# Adjust sys.path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config.settings import settings

class OAuthHandler(BaseHTTPRequestHandler):
    request_token = None

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'request_token' in params:
            OAuthHandler.request_token = params['request_token'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentication successful!</h2><p>You can close this window and return to the terminal.</p></body></html>")
            logger.info("Request token successfully captured via redirect.")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentication failed.</h2><p>Missing request_token in URL.</p></body></html>")
            logger.error("Failed to capture request token from URL.")

    def log_message(self, format, *args):
        # Suppress default HTTP server logging to keep terminal clean
        pass

def update_env_file(new_access_token: str):
    """Updates the KITE_ACCESS_TOKEN value in the .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')

    if not os.path.exists(env_path):
        logger.error(f".env file not found at {env_path}. Make sure it exists.")
        sys.exit(1)

    with open(env_path, 'r') as f:
        lines = f.readlines()

    token_updated = False
    with open(env_path, 'w') as f:
        for line in lines:
            if line.startswith('KITE_ACCESS_TOKEN='):
                f.write(f'KITE_ACCESS_TOKEN={new_access_token}\n')
                token_updated = True
            else:
                f.write(line)

        if not token_updated:
            f.write(f'KITE_ACCESS_TOKEN={new_access_token}\n')

    logger.success(".env file successfully updated with new access token.")

def main():
    api_key = settings.KITE_API_KEY
    api_secret = settings.KITE_API_SECRET

    if not api_key or not api_secret:
        logger.error("KITE_API_KEY or KITE_API_SECRET is missing from configuration.")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    logger.info("Starting local server to capture redirect...")
    server = HTTPServer(('127.0.0.1', 8000), OAuthHandler)

    logger.info(f"Opening browser to authenticate: {login_url}")
    webbrowser.open(login_url)

    logger.info("Waiting for authentication callback on http://127.0.0.1:8000 ...")
    while OAuthHandler.request_token is None:
        server.handle_request()

    server.server_close()
    request_token = OAuthHandler.request_token

    logger.info("Generating session with Kite API...")
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        logger.success("Session generated successfully.")
        update_env_file(access_token)
    except Exception as e:
        logger.error(f"Failed to generate session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
