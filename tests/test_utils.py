# tests/test_utils.py

import pytest
from pathlib import Path
import sys
#import os
import tempfile
# Get the current file's directory
current_file = Path(__file__).resolve()
parent_dir = current_file.parent
grandparent_dir = current_file.parent.parent

# Add the current script dir
#sys.path.append(str(parent_dir))

# Add the main project dir
sys.path.append(str(grandparent_dir))
from utils import clean_filename, validate_cookies_file

def test_clean_filename_basic():
    filename = "Sample:Video*Title?.mp4"
    sanitized = clean_filename(filename)
    assert sanitized == "Sample_Video_Title_.mp4"

def test_clean_filename_reserved_name():
    filename = "CON.mp4"
    sanitized = clean_filename(filename)
    assert sanitized == "_CON.mp4"

def test_clean_filename_truncate():
    filename = "a" * 300 + ".mp4"  # 300 characters + extension
    sanitized = clean_filename(filename)
    assert len(sanitized) <= 255

def test_clean_filename_no_invalid_chars():
    filename = "ValidVideoTitle.mp4"
    sanitized = clean_filename(filename)
    assert sanitized == "ValidVideoTitle.mp4"

def test_validate_cookies_file_valid(tmp_path):
    cookies_file = tmp_path / "cookies.txt"
    with cookies_file.open("w") as f:
        f.write("# Netscape HTTP Cookie File\n")
    assert validate_cookies_file(str(cookies_file)) == True

def test_validate_cookies_file_invalid(tmp_path):
    cookies_file = tmp_path / "cookies.txt"
    with cookies_file.open("w") as f:
        f.write("Invalid content\n")
    assert validate_cookies_file(str(cookies_file)) == False
