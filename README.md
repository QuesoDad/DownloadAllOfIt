
# Download All Of It (DAOI)

**Download All Of It (DAOI)** is a feature-rich video downloader with a user-friendly graphical interface. Built with PyQt5 and powered by `yt-dlp`, DAOI allows you to download videos and playlists from a wide range of supported websites effortlessly.

---

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
  - [Downloading Videos](#downloading-videos)
  - [Stopping Downloads](#stopping-downloads)
  - [Viewing Logs](#viewing-logs)
- [Settings](#settings)
  - [Preferences Dialog](#preferences-dialog)
  - [Settings Options](#settings-options)
- [Supported Sites](#supported-sites)
- [Folder Structure](#folder-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)
- [Acknowledgements](#acknowledgements)
- [Contact](#contact)
- [Disclaimer](#disclaimer)

---

## Features

- **Easy to Use Interface:** Intuitive GUI built with PyQt5, suitable for users of all levels.
- **Multiple URL Support:** Download multiple videos or playlists by entering multiple URLs.
- **Format Options:** Choose between downloading videos (`mp4`) or extracting audio (`mp3`).
- **Organize Downloads:** Option to organize downloads into year-based subfolders.
- **Metadata and Thumbnails:**
  - Downloads and embeds metadata into media files.
  - Saves thumbnails as high-quality PNG files matching the video filenames.
  - Creates text files with original URLs and readable metadata.
- **Progress Monitoring:**
  - Individual progress bars for current video download.
  - Overall progress bar for all downloads.
- **Logging:**
  - Real-time log display within the application.
  - Adjustable logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
- **Stop Functionality:** Ability to stop ongoing downloads gracefully.
- **Settings Persistence:** Remembers last used output directory and settings.
- **Supported Sites List:** View the list of all supported websites.

---

## Getting Started

### Installation

To get started with DAOI, please follow these steps:

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/QuesoDad/DownloadAllOfIt.git
   cd DownloadAllOfIt

Install the necessary dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

Run the main Python file to launch the GUI:

```bash
python main.py
```

### Downloading Videos

1. Enter one or multiple URLs (one per line) in the provided text area.
2. Select the output folder where downloaded files will be saved.
3. Click **Start Download** to begin.

### Stopping Downloads

Click **Stop Download** to stop the ongoing downloads. The download thread will attempt to stop gracefully.

### Viewing Logs

Logs are displayed in real-time in the log area at the bottom of the interface. You can adjust the logging level in **Settings**.

## Settings

### Preferences Dialog

Open the **Preferences** dialog from the **Settings** menu to customize the application settings.

### Settings Options

- **Organize into Year Subfolders:** When enabled, downloaded files are organized by their year of publication.
- **Output Format:** Choose `mp4` for videos or `mp3` for audio extraction.
- **Logging Level:** Adjust the logging detail level to suit your needs.

## Supported Sites

Click on **Show Supported Sites** to view a list of all websites supported by `yt-dlp`. A dialog box displays the list for easy reference.

## Troubleshooting

- **Downloads not stopping:** Ensure the stop button is clicked once; if it does not respond, check for error messages in the log.
- **Thumbnails not saving as PNG:** Check if the URLs are correct and if `yt-dlp` has access to the thumbnail.
- **Progress bars not updating:** This may occur if the `yt-dlp` process encounters network issues. Check the logs for details.
- **Error: No Metadata Found:** This typically indicates an unsupported site or a private video.

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request for review. Feel free to open issues for any bugs or feature requests.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Credits

Download All Of It (DAOI) was developed by Kristian Boruff (GitHub: [QuesoDad](https://github.com/QuesoDad)). Special thanks to the `yt-dlp` community for the robust downloading tool that powers this application.

## Acknowledgements

This project uses:
- `yt-dlp` for its powerful video/audio downloading capabilities.
- `PyQt5` for the graphical user interface.

## Contact

For support, questions, or to report issues, feel free to reach out via GitHub issues.

## Disclaimer

This software is for educational and personal use only. Respect the terms of service of any sites you download from and avoid unauthorized use.

## Detailed Explanation of Features

### Download Management

- **Multiple URLs**: Enter multiple video or playlist URLs to download multiple files in one session.
- **Format Options**: Supports video (`mp4`) and audio (`mp3`) downloads.
- **Organize by Year**: Automatically organize files into year-based subfolders, if desired.
- **Progress Indicators**: Track download progress with individual and overall progress bars.

### Metadata and Thumbnail Management

- **Metadata Embedding**: Automatically embeds metadata (title, description, etc.) into the downloaded files.
- **Thumbnails as PNG**: Saves thumbnails as PNG files, named to match the video files.
- **Metadata Text Files**: Creates text files with the original URL and metadata for each download.

---

## Example Commands

```bash
# Running the main application
python main.py

# Updating `yt-dlp` if you encounter issues with unsupported sites
pip install -U yt-dlp
```
