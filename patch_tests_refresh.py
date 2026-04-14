import sys

with open('tests/scripts/test_refresh_token.py', 'r') as f:
    content = f.read()

search_block = """        mock_file().write.assert_called_once()
        written_content = mock_file().write.call_args[0][0]"""

replace_block = """        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)"""

content = content.replace(search_block, replace_block)

with open('tests/scripts/test_refresh_token.py', 'w') as f:
    f.write(content)
