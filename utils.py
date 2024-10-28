# utils.py

"""
Utility functions for JSON and file management.

This module provides functions to load and save JSON configurations,
manage file paths, and sanitize filenames.
"""

import os
import json
from typing import Any, Dict, List


def load_last_directory(file_path: str = 'last_directory.json') -> str:
    """
    Load the last used directory from a JSON file.

    Args:
        file_path (str): Path to the JSON file storing the last directory.

    Returns:
        str: The last used directory path. Returns an empty string if not found or on error.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data.get('last_directory', '')
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading last directory: {e}")
    return ''


def save_last_directory(folder: str, file_path: str = 'last_directory.json') -> None:
    """
    Save the last used directory to a JSON file.

    Args:
        folder (str): The directory path to save.
        file_path (str): Path to the JSON file storing the last directory.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump({'last_directory': folder}, file)
    except IOError as e:
        print(f"Error saving last directory: {e}")


def load_settings(file_path: str = 'settings.json') -> Dict[str, Any]:
    """
    Load application settings from a JSON file.

    Args:
        file_path (str): Path to the JSON settings file.

    Returns:
        Dict[str, Any]: A dictionary of settings. Returns an empty dict on error.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}")
    return {}


def save_settings(settings: Dict[str, Any], file_path: str = 'settings.json') -> None:
    """
    Save application settings to a JSON file.

    Args:
        settings (Dict[str, Any]): A dictionary of settings to save.
        file_path (str): Path to the JSON settings file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(settings, file, indent=4)
    except IOError as e:
        print(f"Error saving settings: {e}")


def clean_filename(filename: str) -> str:
    """
    Sanitize the filename by removing or replacing invalid characters.

    Args:
        filename (str): The original filename.

    Returns:
        str: A sanitized filename safe for use in file systems.
    """
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def get_supported_sites() -> List[str]:
    """
    Retrieve a list of supported sites for downloading.

    Returns:
        List[str]: A list of supported website URLs or names.
    """
    # This is a placeholder. Replace with actual supported sites as needed.
    return [
        "YouTube",
        "Vimeo",
        "Facebook",
        "Twitter",
        "Dailymotion",
        "Twitch",
        "SoundCloud",
        "Instagram"
    ]
