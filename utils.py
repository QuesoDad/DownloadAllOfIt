# utils.py

"""
Utility functions for JSON and file management.

This module provides functions to load and save JSON configurations,
manage file paths, sanitize filenames, and retrieve supported video sites
using yt-dlp. It ensures that the application remains configurable and
compatible with a wide range of video platforms.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import logging.handlers
import shutil

# Initialize the logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels of log messages

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)  # Adjust as needed (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Create formatter and add it to the handler
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
ch.setFormatter(formatter)

# Add the handler to the logger
if not logger.handlers:
    logger.addHandler(ch)

# Define default configuration directory and files using pathlib for cross-platform compatibility
DEFAULT_CONFIG_DIR = Path.home() / '.my_downloader'
DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the config directory exists

DEFAULT_LAST_DIR_FILE = DEFAULT_CONFIG_DIR / 'last_directory.json'
DEFAULT_SETTINGS_FILE = DEFAULT_CONFIG_DIR / 'settings.json'
DEFAULT_SUPPORTED_SITES_FILE = DEFAULT_CONFIG_DIR / 'supported_sites.json'
DEFAULT_LOG_FILE = DEFAULT_CONFIG_DIR / 'app.log'

DEFAULT_SETTINGS = {
    'use_year_subfolders': False,
    'output_format': 'mp4',
    'download_quality': 'best',
    'download_subtitles': False,
    'embed_title': True,
    'embed_uploader': True,
    'embed_description': True,
    'embed_tags': True,
    'embed_license': True,
    'logging_level': 'DEBUG',
    # Add more default settings as needed
}

def setup_logging(log_level=logging.DEBUG):
    """
    Configures the root logger to log to both console and a file.
    
    Args:
        log_level (int): Logging level from the logging module (e.g., logging.DEBUG).
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove all existing handlers to reset
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    # File handler with rotation
    fh = logging.handlers.RotatingFileHandler(
        DEFAULT_LOG_FILE, maxBytes=5*1024*1024, backupCount=5
    )
    fh.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)

    logger.debug("Logging is set up.")

# Call setup_logging with default level
setup_logging()


def load_last_directory(file_path: Path = DEFAULT_LAST_DIR_FILE) -> str:
    """
    Load the last used directory from a JSON file.

    This function reads a JSON configuration file to retrieve the path of the
    last directory used by the application for downloading files. If the file
    does not exist or an error occurs during loading, it returns an empty string.

    Args:
        file_path (Path): Path to the JSON file storing the last directory.

    Returns:
        str: The last used directory path. Returns an empty string if not found or on error.
    """
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as file:
                data = json.load(file)
                last_dir = data.get('last_directory', '')
                logger.debug(f"Loaded last directory: {last_dir}")
                return last_dir
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading last directory from {file_path}: {e}")
    else:
        logger.debug(f"Last directory file {file_path} does not exist.")
    return ''


def save_last_directory(folder: str, file_path: Path = DEFAULT_LAST_DIR_FILE) -> None:
    """
    Save the last used directory to a JSON file.

    This function writes the provided directory path to a JSON configuration
    file, allowing the application to remember the last location used for downloads.

    Args:
        folder (str): The directory path to save.
        file_path (Path): Path to the JSON file storing the last directory.
    """
    try:
        with file_path.open('w', encoding='utf-8') as file:
            json.dump({'last_directory': folder}, file, indent=4)
            logger.debug(f"Saved last directory: {folder} to {file_path}")
    except IOError as e:
        logger.error(f"Error saving last directory to {file_path}: {e}")


def load_settings(file_path: Path = DEFAULT_SETTINGS_FILE) -> Dict[str, Any]:
    """
    Load application settings from a JSON file.
    Applies default settings for missing keys.
    """
    settings = DEFAULT_SETTINGS.copy()
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as file:
                loaded_settings = json.load(file)
                settings.update(loaded_settings)
                logging.getLogger(__name__).debug(f"Loaded settings from {file_path}: {loaded_settings}")
        except (json.JSONDecodeError, IOError) as e:
            logging.getLogger(__name__).error(f"Error loading settings from {file_path}: {e}")
    else:
        logging.getLogger(__name__).debug(f"Settings file {file_path} does not exist. Using default settings.")
    return settings


def save_settings(settings: Dict[str, Any], file_path: Path = DEFAULT_SETTINGS_FILE) -> None:
    """
    Save application settings to a JSON file atomically.
    
    Args:
        settings (Dict[str, Any]): A dictionary of settings to save.
        file_path (Path): Path to the JSON settings file.
    """
    try:
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile('w', delete=False, dir=file_path.parent, encoding='utf-8') as tf:
            json.dump(settings, tf, indent=4)
            temp_name = tf.name
        # Atomically replace the old settings file with the new one
        shutil.move(temp_name, file_path)
        logging.getLogger(__name__).debug(f"Saved settings to {file_path}: {settings}")
    except IOError as e:
        logging.getLogger(__name__).error(f"Error saving settings to {file_path}: {e}")


def clean_filename(filename: str) -> str:
    """
    Sanitize the filename by removing or replacing invalid characters.
    
    Args:
        filename (str): The original filename.
    
    Returns:
        str: A sanitized filename safe for use in file systems.
    """
    if not filename:
        return 'unknown_file'
    # Define a regex pattern for invalid characters across major operating systems
    invalid_pattern = r'[<>:"/\\|?*\x00-\x1F]'
    sanitized = re.sub(invalid_pattern, '_', filename)
    logging.getLogger(__name__).debug(f"Sanitized filename: '{filename}' to '{sanitized}'")

    # Additionally, strip leading/trailing whitespace and dots to prevent issues
    sanitized = sanitized.strip().strip('.')
    logging.getLogger(__name__).debug(f"Trimmed filename: '{sanitized}'")

    # Truncate the filename if it's too long (e.g., over 255 characters)
    max_length = 255
    if len(sanitized) > max_length:
        path = Path(sanitized)
        sanitized = f"{path.stem[:max_length - len(path.suffix)]}{path.suffix}"
        logging.getLogger(__name__).debug(f"Truncated filename to {max_length} characters: '{sanitized}'")

    # Handle reserved filenames on Windows
    reserved_names = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    path = Path(sanitized)
    if path.stem.upper() in reserved_names:
        sanitized = f"_{sanitized}"
        logger.debug(f"Adjusted reserved filename: '{sanitized}'")

    # Append unique identifier if filename already exists to prevent collisions
    if output_dir:
        output_path = output_dir / sanitized
        if output_path.exists():
            unique_id = time.strftime("%Y%m%d-%H%M%S")
            sanitized = f"{path.stem}_{unique_id}{path.suffix}"
            logger.debug(f"Appended unique identifier to filename: '{sanitized}'")

    return sanitized

def validate_cookies_file(file_path: str) -> bool:
    """
    Validate the format of the selected cookies file.
    
    Args:
        file_path (str): Path to the cookies file.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            # Basic check: Netscape format starts with # Netscape HTTP Cookie File
            if first_line.strip() == '# Netscape HTTP Cookie File':
                return True
        return False
    except Exception as e:
        logging.getLogger(__name__).error(f"Error validating cookies file: {e}")
        return False
    
def check_ffmpeg_installed() -> bool:
    """
    Check if FFmpeg is installed and accessible in the system PATH.
    
    Returns:
        bool: True if FFmpeg is installed, False otherwise.
    """
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    
def get_supported_sites() -> List[str]:
    """
    Retrieve a list of supported sites for downloading.

    This function dynamically retrieves all video sites supported by yt-dlp
    by accessing its internal extractors. This ensures that the list remains
    up-to-date with any additions or changes made to yt-dlp's supported platforms.

    **Note**: This function requires yt-dlp to be installed in the environment.
    If yt-dlp is not installed, it will log an error and return an empty list.

    Returns:
        List[str]: A sorted list of supported website names.
    """
    try:
        from yt_dlp.extractor import gen_extractors

        # Retrieve all extractor instances
        extractors = gen_extractors()
        supported_sites = set()

        for extractor in extractors:
            # Each extractor has an 'IE_NAME' attribute representing the site name
            if hasattr(extractor, 'IE_NAME'):
                name = extractor.IE_NAME
                if name:
                    supported_sites.add(name)

        sorted_sites = sorted(supported_sites)
        logger.debug(f"Retrieved supported sites from yt-dlp: {sorted_sites}")
        return sorted_sites

    except ImportError:
        logger.error("yt-dlp is not installed. Unable to retrieve supported sites.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving supported sites: {e}")

    return []  # Return an empty list if yt-dlp is not available or an error occurs
