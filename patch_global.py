import sys

with open('src/config/settings.py', 'r') as f:
    content = f.read()

search_block = """    # Intraday data config"""
replace_block = """    GLOBAL_MARKET_CACHE_TTL_MINUTES: int = 30

    # Intraday data config"""

if search_block in content:
    content = content.replace(search_block, replace_block)
    with open('src/config/settings.py', 'w') as f:
        f.write(content)
    print("Replaced settings successfully")
else:
    print("Search block not found")
