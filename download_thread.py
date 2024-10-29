# download_thread.py

import logging
import traceback
import time
import random
import requests
import os
import yt_dlp
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from yt_download_manager import YTDownloadManager
from utils import clean_filename

def setup_logger():
    # Create a logger object
    logger = logging.getLogger('download_thread')
    logger.setLevel(logging.DEBUG)  # Capture all levels of logs (DEBUG and above)

    # Create console handler and set level to DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # (Optional) Create file handler to save logs to a file
    fh = logging.FileHandler('download_debug.log')
    fh.setLevel(logging.DEBUG)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger

# Initialize the logger
logger = setup_logger()

class DownloadThread(QThread):
    """
    Thread to handle the download process.

    This class manages downloading videos from provided URLs using yt_dlp,
    handles progress updates, manages failed downloads, and communicates
    with the main GUI thread through PyQt signals.

    Signals:
        progress_update (int): Emits the current download progress percentage.
        status_update (str): Emits status messages.
        total_progress_update (int): Emits the overall download progress percentage.
        current_video_update (str): Emits the title of the current video being downloaded.
        update_thumbnail (QPixmap): Emits the thumbnail image of the current video.
        update_description (str): Emits the description of the current video.
        finished (): Emits when the download process is finished.
        failed_downloads_signal (list): Emits a list of failed download URLs with reasons.
    """

    # Define PyQt signals to communicate with the main thread
    progress_update = pyqtSignal(int)          # For individual video progress
    status_update = pyqtSignal(str)            # For status messages
    total_progress_update = pyqtSignal(int)    # For overall progress
    current_video_update = pyqtSignal(str)     # For current video title
    update_thumbnail = pyqtSignal(QPixmap)     # For current video thumbnail
    update_description = pyqtSignal(str)       # For current video description
    finished = pyqtSignal()                    # When all downloads are done
    failed_downloads_signal = pyqtSignal(list) # When there are failed downloads

    def __init__(self, urls: list, output_path: str, settings: dict, cookies_file: str = None):
        """
        Initialize the DownloadThread.

        Args:
            urls (list): A list of video or playlist URLs to download.
            output_path (str): The directory where downloads will be saved.
            settings (dict): Application settings.
            cookies_file (str, optional): Path to the cookies file. Defaults to None.
        """
        super().__init__()  # Initialize the parent QThread class

        # Store the provided arguments as instance variables
        self.urls = urls
        self.output_path = output_path
        self.settings = settings
        self.cookies_file = cookies_file

        # Set up a logger for logging messages, errors, and debug information
        self.logger = logging.getLogger(__name__)

        # Flag to indicate if the download process has been requested to stop
        self.is_stopped = False

        # List to keep track of URLs that failed to download along with reasons
        self.failed_urls = []

        # Counters to manage download statistics and throttling
        self.download_counter = 0  # Counts how many videos have been downloaded
        self.total_items = 0        # Total number of videos to download
        self.completed_items = 0    # Number of videos successfully downloaded

    def stop(self):
        """
        Stop the download process.

        Sets the `is_stopped` flag to True, which signals the thread to halt
        ongoing and future download operations gracefully.
        """
        self.is_stopped = True

    def run(self):
        """
        The main method that runs in the separate thread.

        This method orchestrates the download process by:
            1. Extracting all video URLs from the provided URLs (handling playlists).
            2. Downloading each video individually.
            3. Emitting signals to update the GUI about progress and status.
            4. Handling any failed downloads and notifying the GUI.
        """
        
        # Check if the cookies file exists if provided
        if self.cookies_file:
            if not Path(self.cookies_file).exists():
                self.status_update.emit(f"Cookies file '{self.cookies_file}' not found. Some downloads may fail.")
                self.logger.warning(f"Cookies file '{self.cookies_file}' does not exist.")
                # Optionally, you can choose to stop the download process here
                # self.failed_urls.append({"url": "N/A", "reason": "Missing cookies file."})
                # self.failed_downloads_signal.emit(self.failed_urls)
                # self.finished.emit()
                # return
            else:
                self.logger.debug(f"Cookies file found: {self.cookies_file}")
        
        # Initialize the download manager with the provided settings and cookies file
        download_manager = YTDownloadManager(
            logger=self.logger,
            settings=self.settings,
            cookies_file=self.cookies_file
        )

        # List to hold all individual video URLs extracted from input URLs
        all_video_urls = []

        # Step 1: Extract all video URLs from the input URLs (handling playlists)
        for index, url in enumerate(self.urls, start=1):
            # Check if a stop has been requested before processing each URL
            if self.is_stopped:
                self.status_update.emit("Download stopped by user.")
                break  # Exit the loop if a stop is requested

            # Emit a status update to inform the user about the current extraction process
            self.status_update.emit(
                f"Extracting videos from URL {index}/{len(self.urls)}: {url}"
            )

            try:
                # yt_dlp options for extracting video URLs without downloading them
                ydl_opts_flat = {
                    'quiet': False,              # Suppress yt_dlp's own output
                    'verbose': True,
                    'skip_download': True,      # Do not download videos
                    'extract_flat': True,       # Extract URLs without full metadata
                    'ignoreerrors': True,       # Ignore errors and continue
                    'logger': self.logger,      # Use the custom logger
                }

                # Use yt_dlp to extract information about the provided URL
                with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl_flat:
                    info_dict = ydl_flat.extract_info(url, download=False)

                    # If no metadata is found, log an error and record the failure
                    if info_dict is None:
                        self.logger.error(f"No metadata found for URL: {url}")
                        self.failed_urls.append({"url": url, "reason": "No metadata found."})
                        continue  # Move to the next URL

                    # Determine if the URL is a single video or a playlist
                    info_type = info_dict.get('_type', 'video')

                    if info_type == 'playlist':
                        # If it's a playlist, extract all video entries within it
                        entries = info_dict.get('entries', [])
                        for entry in entries:
                            if entry is None:
                                # Entry is None, likely due to a private or inaccessible video
                                video_url = entry.get('url') if entry and 'url' in entry else 'Unknown URL'
                                if video_url != 'Unknown URL':
                                    self.failed_urls.append({"url": video_url, "reason": "Private"})
                                    self.logger.warning(f"Private video detected. URL: {video_url}")
                                else:
                                    self.failed_urls.append({"url": url, "reason": "Private"})
                                    self.logger.warning(f"Private video detected. URL: {url}")
                            else:
                                # Extract the actual video URL from the entry
                                video_url = entry.get('url', 'Unknown URL')
                                # Convert relative URLs to full URLs if necessary
                                if not video_url.startswith('http'):
                                    video_url = f"https://www.youtube.com/watch?v={video_url}"
                                # Add the fully qualified video URL to the list
                                all_video_urls.append(video_url)
                    elif info_type == 'video':
                        video_url = info_dict.get('webpage_url', 'Unknown URL')
                        all_video_urls.append(video_url)
                    else:
                        # Handle any unexpected types gracefully
                        self.logger.warning(f"Unhandled type: {info_type} for URL: {url}")
                        self.failed_urls.append({"url": url, "reason": f"Unhandled type: {info_type}"})
            except Exception as e:
                # Log any exceptions that occur during the extraction process
                self.logger.error(f"Error extracting URL '{url}': {e}")
                self.logger.error(traceback.format_exc())  # Log the stack trace for debugging
                self.failed_urls.append({"url": url, "reason": str(e)})

        # After extracting, set the total number of videos to download
        self.total_items = len(all_video_urls)

        # Step 2: Process each video URL individually
        for i, video_url in enumerate(all_video_urls, start=1):
            # Check if a stop has been requested before downloading each video
            if self.is_stopped:
                self.status_update.emit("Download stopped by user.")
                break  # Exit the loop if a stop is requested

            # Emit a status update to inform the user about the current download
            self.status_update.emit(f"Downloading video {i}/{self.total_items}: {video_url}")

            try:
                # yt_dlp options for extracting full metadata of the video
                ydl_opts_full = {
                    'quiet': False,          # Suppress yt_dlp's own output
                    'verbose': True,
                    'skip_download': True,  # Do not download yet; metadata only
                    'ignoreerrors': True,   # Ignore errors and continue
                    'logger': self.logger,  # Use the custom logger
                }

                # Include 'cookiefile' if cookies are provided
                if self.cookies_file:
                    ydl_opts_full['cookiefile'] = self.cookies_file
                    self.logger.debug(f"Using cookies file for metadata extraction: {self.cookies_file}")
                else:
                    self.logger.debug("No cookies file provided for metadata extraction.")
                self.logger.debug(f"Metadata extraction options for video {video_url}: {ydl_opts_full}")
                
                # Use yt_dlp to extract detailed information about the video
                with yt_dlp.YoutubeDL(ydl_opts_full) as ydl_full:
                    video_info = ydl_full.extract_info(video_url, download=False)

                    # If video_info is None, the video might be private or inaccessible
                    if video_info is None:
                        self.logger.error(f"Private video or inaccessible: {video_url}")
                        self.failed_urls.append({"url": video_url, "reason": "Private"})
                        self.completed_items += 1
                        self.update_total_progress()
                        continue  # Move to the next video

                # Process and download the video using the download manager
                self.process_single_video(video_info, download_manager, self.output_path)
                self.completed_items += 1  # Increment the count of completed downloads
                self.update_total_progress()  # Update the overall progress bar
            except Exception as e:
                # Log any exceptions that occur during the download process
                self.logger.error(f"Failed to download video '{video_url}': {e}")
                self.failed_urls.append({"url": video_url, "reason": str(e)})
                self.completed_items += 1
                self.update_total_progress()

            # Implement a cool-off period after every 10 video downloads to prevent rate limiting
            self.download_counter += 1
            if self.download_counter % 10 == 0:
                # Choose a random delay between 0 and 2 seconds
                delay = random.uniform(0, 2)
                self.logger.info(f"Cooling off for {delay:.2f} seconds after {self.download_counter} video downloads.")
                time.sleep(delay)  # Pause the thread for the chosen duration

        # After processing all videos, emit the failed downloads signal if there are any failures
        if self.failed_urls:
            self.failed_downloads_signal.emit(self.failed_urls)

        # If the download was stopped by the user, emit a corresponding status update
        if self.is_stopped:
            self.status_update.emit("Download stopped by user.")

        # Emit a final status update indicating that the download process is complete
        self.status_update.emit("Download complete")
        self.finished.emit()  # Signal that the thread has finished its execution

    def update_total_progress(self):
        """
        Update the overall progress bar based on completed items.

        Calculates the percentage of videos downloaded and emits the
        `total_progress_update` signal to update the GUI's progress bar.
        """
        if self.total_items > 0:
            # Calculate progress as a percentage
            total_progress = int((self.completed_items / self.total_items) * 100)
            self.total_progress_update.emit(total_progress)
        else:
            # If there are no items to download, set progress to 0%
            self.total_progress_update.emit(0)

    def process_single_video(self, info_dict: dict, download_manager: YTDownloadManager, base_folder: str):
        """
        Process an individual video by downloading it and handling its metadata.

        This method performs the following tasks:
            - Emits signals to update the GUI with video details.
            - Downloads the thumbnail image.
            - Determines the appropriate folder structure based on settings.
            - Initiates the download using the download manager.

        Args:
            info_dict (dict): A dictionary containing metadata of the video.
            download_manager (YTDownloadManager): An instance of the download manager to handle the download.
            base_folder (str): The base directory where downloads are saved.
        """
        # Check if a stop has been requested before processing the video
        if self.is_stopped:
            raise yt_dlp.utils.DownloadCancelled()

        if info_dict is None:
            # If no metadata is available, log a warning and skip processing
            self.logger.warning("Received None info_dict, skipping this video.")
            return

        # Extract relevant metadata from the info dictionary
        title = info_dict.get('title', 'Unknown Title')            # Video title
        description = info_dict.get('description', '')             # Video description
        thumbnail_url = info_dict.get('thumbnail')                 # URL of the video's thumbnail

        # Emit signals to update the GUI with the current video's title and description
        self.current_video_update.emit(title)
        self.update_description.emit(description)

        # Download and emit the thumbnail image if available
        if thumbnail_url:
            try:
                # Send a GET request to fetch the thumbnail image
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()  # Raise an exception for HTTP errors
                image_data = response.content  # Get the image data as bytes

                # Create a QPixmap from the image data
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)

                # Emit the pixmap to update the thumbnail in the GUI
                self.update_thumbnail.emit(pixmap)
            except Exception as e:
                # Log any errors that occur while downloading the thumbnail
                self.logger.error(f"Failed to download thumbnail: {e}")

        # Determine the final folder path where the video will be saved
        final_folder = base_folder

        # If the user has enabled organizing downloads into year-based subfolders
        if self.settings.get('use_year_subfolders', False):
            upload_date = info_dict.get('upload_date')  # Upload date in YYYYMMDD format
            if upload_date and len(upload_date) >= 4:
                year = upload_date[:4]  # Extract the year from the upload date
                # Append the year to the base folder path
                final_folder = os.path.join(final_folder, year)

        # Create the final folder if it doesn't exist
        os.makedirs(final_folder, exist_ok=True)

        # Clean the video title to create a valid filename
        video_title = clean_filename(info_dict.get('title', 'Unknown_Title'))
        # Define the output template with the desired file extension
        output_template = os.path.join(final_folder, f"{video_title}.%(ext)s")

        # Log video details
        self.logger.debug(f"Processing video: {title}")
        self.logger.debug(f"Video URL: {video_url}")
        self.logger.debug(f"Final folder: {final_folder}")
        self.logger.debug(f"Output template: {output_template}")
        
        try:
            # Initiate the download using the download manager
            download_manager.download_video(
                video_url=info_dict.get('webpage_url'),       # URL of the video page
                output_template=output_template,              # Output file template
                info_dict=info_dict,                          # Video metadata
                progress_callback=self.progress_update.emit,   # Callback for progress updates
                is_stopped=self.is_stopped                     # Pass the stop flag
            )
        except yt_dlp.utils.DownloadCancelled:
            # If the download was cancelled, log the event and emit a status update
            self.logger.info(f"Download cancelled for video: {title}")
            self.status_update.emit("Download stopped by user.")
            raise  # Re-raise the exception to allow higher-level handling
        except Exception as e:
            # Handle any other exceptions that occur during the download
            error_message = str(e)
            if "Private video" in error_message:
                reason = "Private video - access denied."
            else:
                reason = error_message
            # Log the failure reason
            self.logger.error(f"Failed to download video '{title}': {reason}")
            # Extract the video's webpage URL for reference
            video_url = info_dict.get('webpage_url', 'Unknown URL')
            # Record the failed download with its reason
            self.failed_urls.append({"url": video_url, "reason": reason})