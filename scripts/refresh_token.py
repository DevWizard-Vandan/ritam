from kiteconnect import KiteConnect
kite = KiteConnect(api_key="kw2hxvxslrdnvts0")
data = kite.generate_session("Request_Token_Here", api_secret="5aum9tyv22ik7jlfvchumw4uwdjj781g")
print(data["access_token"])