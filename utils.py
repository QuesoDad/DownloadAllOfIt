# utils.py

import re
import os
import logging
from yt_dlp.extractor import gen_extractors

MAX_FILENAME_LENGTH = 255

class MyLogger:
    """
    Custom logger class to handle logging within the application.
    """
    def __init__(self):
        self.logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # File handler
        file_handler = logging.FileHandler('app.log', mode='a')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def debug(self, msg):
        """Log debug messages."""
        self.logger.debug(msg)

    def info(self, msg):
        """Log info messages."""
        self.logger.info(msg)

    def warning(self, msg):
        """Log warning messages."""
        self.logger.warning(msg)

    def error(self, msg):
        """Log error messages."""
        self.logger.error(msg)

def clean_filename(filename):
    """
    Clean the filename by removing or replacing illegal characters.

    :param filename: The original filename.
    :return: A cleaned version of the filename.
    """
    filename = filename.replace('...', '…')
    filename = re.sub(r'[<>:"/\\|?*#%&{}$!‘’@^~+]', '', filename)
    filename = filename.strip()
    reserved_names = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3",
        "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6",
        "LPT7", "LPT8", "LPT9"
    ]

    if filename.upper() in reserved_names:
        filename = f"{filename}_file"

    return filename[:MAX_FILENAME_LENGTH]

def get_supported_sites():
    """
    Return a list of unique supported site names.

    :return: A sorted list of supported site names.
    """
    extractors = gen_extractors()
    site_names = set()
    for extractor in extractors:
        ie_name = extractor.IE_NAME
        base_site = ie_name.split(':')[0]
        site_names.add(base_site)
    return sorted(site_names)
