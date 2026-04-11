# Run this once: scripts/generate_token.py
from kiteconnect import KiteConnect

API_KEY = "kw2hxvxslrdnvts0"
API_SECRET = "5aum9tyv22ik7jlfvchumw4uwdjj781g"

kite = KiteConnect(api_key=API_KEY)

# Step 4a — Open this URL in browser, login, copy the request_token from redirect URL
print(kite.login_url())

# Step 4b — Paste request_token here after login
request_token = input("Paste request_token: ")
data = kite.generate_session(request_token, api_secret=API_SECRET)

print(f"\nACCESS_TOKEN={data['access_token']}")
print("\nCopy this into your .env file")