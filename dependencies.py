# dependencies.py

import sys
import subprocess
import pkg_resources

def install(package):
    """Install a package using pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    """Install all necessary libraries."""
    required = {
        'PyQt5',
        'yt-dlp',
        'requests',
    }

    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = required - installed

    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        for package in missing:
            install(package)
    else:
        print("All required packages are already installed.")

if __name__ == "__main__":
    main()
