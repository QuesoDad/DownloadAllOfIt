# generate_cookies.py
import browser_cookie3
import logging
import os
import sys

# Add the parent directory (main project directory) to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#This script fails. Most browsers don't allow access to these files in this fashion, or at least I couldn't make it work. Please use Get Cookies.txt LOCALLY extension or similar. 1. Log into the website you want to get cookies from. 2. Save the cookies. 3. Use the cookies.txt or whatever file name it gives you in the program to download. A smart move would be to add the domain on the front of your cookie file so you can keep track of different sites.

def save_cookies_txt(domains):
    """
    Extract cookies for specified domains from the default browser and save to cookies.txt.

    Args:
        domains (list): List of domain names to extract cookies for.
    """
    try:
        # Load cookies from the browser
        cj = browser_cookie3.load()

        # Filter cookies for the specified domains
        filtered_cookies = [cookie for cookie in cj if any(domain in cookie.domain for domain in domains)]

        if not filtered_cookies:
            logging.info(f"No cookies found for domains: {', '.join(domains)}")
            return

        # Construct the local path for cookies.txt in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_txt_path = os.path.join(current_dir, 'cookies.txt')

        # Save cookies to cookies.txt in Netscape format
        with open(cookies_txt_path, 'w') as f:
            f.write('# Netscape HTTP Cookie File\n')
            for cookie in filtered_cookies:
                f.write('\t'.join([
                    cookie.domain,
                    'TRUE' if cookie.domain.startswith('.') else 'FALSE',
                    cookie.path,
                    'TRUE' if cookie.secure else 'FALSE',
                    str(cookie.expires or 0),
                    cookie.name,
                    cookie.value
                ]) + '\n')
        logging.info(f"Cookies for domains '{', '.join(domains)}' saved to {cookies_txt_path}")
    except Exception as e:
        logging.error(f"Failed to save cookies: {e}")

