import sys

with open('src/agents/base.py', 'r') as f:
    content = f.read()

import re

search_block = """    def _gemini_call(self, prompt: str, model_name: str) -> str:
        \"\"\"Makes Gemini call with assigned key, falls back to key 7.\"\"\"
        from src.config import settings
        keys_to_try = [self.assigned_api_key, settings.GEMINI_API_KEY_7]
        for slot, key in enumerate(keys_to_try, start=1):
            if not key:
                continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.warning(f"{self.name} Gemini call failed "
                               f"(key slot {slot}): {e}")
        logger.error(f"{self.name}: all API keys exhausted")
        return "" """

replace_block = """    def _gemini_call(self, prompt: str, model_name: str) -> str:
        \"\"\"Makes Gemini call with assigned key, falls back to key 7.\"\"\"
        import re, time
        from src.config import settings
        keys_to_try = [self.assigned_api_key, settings.GEMINI_API_KEY_7]

        for key in keys_to_try:
            if not key:
                continue
            for attempt in range(2):  # max 2 attempts per key
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    return response.text.strip()
                except Exception as e:
                    err_str = str(e)
                    # Extract retry_delay seconds from 429 error
                    retry_match = re.search(
                        r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str
                    )
                    if retry_match and attempt == 0:
                        wait = int(retry_match.group(1)) + 1
                        logger.warning(
                            f"{self.name}: 429 on key slot "
                            f"{keys_to_try.index(key)+1} — "
                            f"retrying in {wait}s"
                        )
                        time.sleep(wait)
                        continue  # retry same key after wait
                    else:
                        logger.warning(
                            f"{self.name}: failed on key slot "
                            f"{keys_to_try.index(key)+1}: "
                            f"{type(e).__name__}"
                        )
                        break  # try next key

        logger.error(f"{self.name}: all API keys exhausted")
        return "" """

if search_block.strip() in content:
    content = content.replace(search_block.strip(), replace_block.strip())
    with open('src/agents/base.py', 'w') as f:
        f.write(content)
    print("Replaced base successfully")
else:
    print("Search block not found")
