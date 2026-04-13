#!/usr/bin/env python3
import os
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from kiteconnect import KiteConnect

# Make sure we can import from src if needed, and to find settings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings

class OAuthHandler(BaseHTTPRequestHandler):
    """Handles the redirect from Kite login to capture the request_token."""
    request_token = None

    def do_GET(self):
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)

        if 'request_token' in query:
            OAuthHandler.request_token = query['request_token'][0]

            # Send a simple success response to the browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login successful!</h1><p>You can close this window now.</p></body></html>")
        else:
            # Handle favicon or other requests
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error: No request_token found</h1></body></html>")

    def log_message(self, format, *args):
        # Suppress logging to stdout
        pass

def update_env_file(access_token: str):
    """Updates the .env file with the new KITE_ACCESS_TOKEN."""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        sys.exit(1)

    with open(env_path, 'r') as f:
        env_content = f.read()

    # Regex to replace or add KITE_ACCESS_TOKEN
    pattern = r"^(KITE_ACCESS_TOKEN[ \t]*=[ \t]*).*$"

    if re.search(pattern, env_content, flags=re.MULTILINE):
        # Replace existing
        env_content = re.sub(pattern, f"KITE_ACCESS_TOKEN={access_token}", env_content, flags=re.MULTILINE)
    else:
        # Append if not exists
        if not env_content.endswith('\n'):
            env_content += '\n'
        env_content += f"KITE_ACCESS_TOKEN={access_token}\n"

    with open(env_path, 'w') as f:
        f.write(env_content)

def main():
    api_key = settings.KITE_API_KEY
    api_secret = settings.KITE_API_SECRET

    if not api_key or not api_secret:
        print("Error: KITE_API_KEY and KITE_API_SECRET must be set in .env")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    print(f"Opening browser to login: {login_url}")
    webbrowser.open(login_url)

    # Start a local HTTP server on port 8000
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, OAuthHandler)

    print("Waiting for redirect on port 8000...")

    # Wait for exactly one request
    while OAuthHandler.request_token is None:
        httpd.handle_request()

    httpd.server_close()

    request_token = OAuthHandler.request_token
    print(f"Captured request_token: {request_token}")

    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data['access_token']
    except Exception as e:
        print(f"Error generating session: {e}")
        sys.exit(1)

    update_env_file(access_token)

    print("Token refreshed. Valid until midnight IST.")

if __name__ == "__main__":
    main()
