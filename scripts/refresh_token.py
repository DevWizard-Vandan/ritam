import os
import re
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from kiteconnect import KiteConnect
from src.config.settings import settings

ENV_PATH = ".env"

class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        qs = parse_qs(parsed_url.query)

        if "request_token" in qs:
            self.server.request_token = qs["request_token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login successful! You can close this window.</h1></body></html>")
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Missing request_token!</h1></body></html>")

    def log_message(self, format, *args):
        # Suppress logging
        pass

def update_env_file(access_token):
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    updated = False
    for i, line in enumerate(lines):
        if line.startswith("KITE_ACCESS_TOKEN="):
            lines[i] = f"KITE_ACCESS_TOKEN={access_token}\n"
            updated = True
            break

    if not updated:
        lines.append(f"\nKITE_ACCESS_TOKEN={access_token}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)

def main():
    api_key = settings.KITE_API_KEY
    api_secret = settings.KITE_API_SECRET

    if not api_key or not api_secret:
        print("Error: KITE_API_KEY and KITE_API_SECRET must be set in .env")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    # Start HTTP server
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, RedirectHandler)
    httpd.request_token = None

    print("Opening browser for Kite login...")
    webbrowser.open(login_url)

    print("Waiting for redirect on port 8000...")
    # Wait for one request
    while httpd.request_token is None:
        httpd.handle_request()

    request_token = httpd.request_token

    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        update_env_file(access_token)
        print("Token refreshed. Valid until midnight IST.")
    except Exception as e:
        print(f"Failed to generate session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
