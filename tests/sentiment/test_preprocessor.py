import pytest
from src.sentiment.preprocessor import clean_headline, clean_headlines

def test_clean_headline_strip_whitespace():
    # Test that leading and trailing whitespace are removed
    assert clean_headline("   Headline text   ") == "Headline text"

def test_clean_headline_remove_urls():
    # Test that URLs are stripped out completely
    text = "Check this out https://example.com/news?id=123"
    # Preprocessor does not rstrip after removing URLs, so there is a trailing space
    assert clean_headline(text) == "Check this out "

def test_clean_headline_normalize_spaces():
    # Test that multiple spaces are compressed into a single space
    text = "This   has \t multiple   spaces."
    assert clean_headline(text) == "This has multiple spaces."

def test_clean_headline_truncation():
    # Test that strings exceeding 512 characters are truncated
    long_text = "a" * 600
    cleaned = clean_headline(long_text)
    assert len(cleaned) == 512
    assert cleaned == "a" * 512

def test_clean_headlines_list_processing():
    # Test processing a list and ignoring empty/whitespace-only items
    input_list = [
        "Headline 1",
        "  ",
        "",
        "Headline 2 http://link.com"
    ]
    expected = [
        "Headline 1",
        "Headline 2 "
    ]
    assert clean_headlines(input_list) == expected
