# test_cookies.py

import yt_dlp
import json

def test_cookies(cookies_path, url):
    """
    Test yt_dlp with the provided cookies file and URL.

    Args:
        cookies_path (str): Path to the cookies.txt file.
        url (str): The video or playlist URL to test.

    Returns:
        dict: Metadata dictionary if successful, None otherwise.
    """
    ydl_opts = {
        'cookies': cookies_path,
        'quiet': False,  # Set to True to suppress output
        'dump_single_json': True,  # Dump the metadata as JSON
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            print(json.dumps(info_dict, indent=4))
            return info_dict
    except yt_dlp.utils.DownloadError as e:
        print(f"DownloadError: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None

if __name__ == "__main__":
    # Replace with your actual paths and URLs
    cookies_file = "F:/Google Drive Mirror/Downloads/cookies.txt"
    test_url = "https://youtu.be/otQ-e8SRpRI"  # Replace with a private video or playlist URL

    result = test_cookies(cookies_file, test_url)

    if result:
        print("Cookies are working correctly.")
    else:
        print("Failed to use cookies. Please check the cookies.txt file.")
