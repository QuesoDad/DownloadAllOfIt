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
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

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

    This function reads a JSON configuration file containing various settings
    for the application. If the file does not exist or an error occurs during
    loading, it returns an empty dictionary.

    Args:
        file_path (Path): Path to the JSON settings file.

    Returns:
        Dict[str, Any]: A dictionary of settings. Returns an empty dict on error.
    """
    if file_path.exists():
        try:
            with file_path.open('r', encoding='utf-8') as file:
                settings = json.load(file)
                logger.debug(f"Loaded settings from {file_path}: {settings}")
                return settings
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading settings from {file_path}: {e}")
    else:
        logger.debug(f"Settings file {file_path} does not exist.")
    return {}


def save_settings(settings: Dict[str, Any], file_path: Path = DEFAULT_SETTINGS_FILE) -> None:
    """
    Save application settings to a JSON file.

    This function writes the provided settings dictionary to a JSON configuration
    file, allowing the application to persist user preferences and configurations.

    Args:
        settings (Dict[str, Any]): A dictionary of settings to save.
        file_path (Path): Path to the JSON settings file.
    """
    try:
        with file_path.open('w', encoding='utf-8') as file:
            json.dump(settings, file, indent=4)
            logger.debug(f"Saved settings to {file_path}: {settings}")
    except IOError as e:
        logger.error(f"Error saving settings to {file_path}: {e}")


def clean_filename(filename: str) -> str:
    """
    Sanitize the filename by removing or replacing invalid characters.

    This function ensures that the provided filename is safe for use across
    different file systems by replacing characters that are typically invalid
    or reserved. It uses regular expressions for efficient pattern matching
    and substitution.

    Args:
        filename (str): The original filename.

    Returns:
        str: A sanitized filename safe for use in file systems.
    """
    # Define a regex pattern for invalid characters across major operating systems
    invalid_pattern = r'[<>:"/\\|?*\x00-\x1F]'
    sanitized = re.sub(invalid_pattern, '_', filename)
    logger.debug(f"Sanitized filename: '{filename}' to '{sanitized}'")

    # Additionally, strip leading/trailing whitespace and dots to prevent issues
    sanitized = sanitized.strip().strip('.')
    logger.debug(f"Trimmed filename: '{sanitized}'")

    return sanitized


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
