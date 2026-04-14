import sys

with open('tests/agents/test_base_retry.py', 'r') as f:
    content = f.read()

# Replace src.agents.base.time.sleep with builtins.time if time is an issue,
# Wait, base.py imports time inside the function `_gemini_call`...
# Ah, I should import time at the top of base.py or just mock `time.sleep` directly
# We can just mock `time.sleep`.
search_block = """@patch("src.agents.base.time.sleep")"""
replace_block = """@patch("time.sleep")"""

content = content.replace(search_block, replace_block)

with open('tests/agents/test_base_retry.py', 'w') as f:
    f.write(content)
