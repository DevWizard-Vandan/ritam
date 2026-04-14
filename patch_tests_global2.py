import sys

with open('tests/agents/test_global_market.py', 'r') as f:
    content = f.read()

# I need to add an autouse fixture to reset the cache before each test
insert_block = """
@pytest.fixture(autouse=True)
def reset_global_cache():
    import src.agents.global_market as gm
    gm._cache = {}
    gm._cache_ts = None
"""

# add it after imports
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.startswith('TICKERS ='):
        lines.insert(i, insert_block)
        break

content = '\n'.join(lines)

with open('tests/agents/test_global_market.py', 'w') as f:
    f.write(content)

print("Updated tests/agents/test_global_market.py to add fixture")
