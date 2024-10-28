# download_thread.py

import logging
import traceback
import time
import random
import requests
import os
import yt_dlp
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from yt_download_manager import YTDownloadManager
from utils import clean_filename

class DownloadThread(QThread):
    """
    Thread to handle the download process.

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

    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    total_progress_update = pyqtSignal(int)
    current_video_update = pyqtSignal(str)
    update_thumbnail = pyqtSignal(QPixmap)
    update_description = pyqtSignal(str)
    finished = pyqtSignal()
    failed_downloads_signal = pyqtSignal(list)

    def __init__(self, urls: list, output_path: str, settings: dict, cookies_file: str = None):
        """
        Initialize the DownloadThread.

        Args:
            urls (list): A list of video or playlist URLs to download.
            output_path (str): The directory where downloads will be saved.
            settings (dict): Application settings.
            cookies_file (str, optional): Path to the cookies file. Defaults to None.
        """
        super().__init__()
        self.urls = urls
        self.output_path = output_path
        self.settings = settings
        self.cookies_file = cookies_file
        self.logger = logging.getLogger(__name__)
        self.is_stopped = False
        self.failed_urls = []
        self.download_counter = 0
        self.total_items = 0
        self.completed_items = 0

    def stop(self):
        """
        Stop the download process.
        """
        self.is_stopped = True

    def run(self):
        """
        The main method that runs in the separate thread.

        It processes each URL, handles playlists, and manages download progress.
        """
        download_manager = YTDownloadManager(
            logger=self.logger,
            settings=self.settings,
            cookies_file=self.cookies_file
        )

        all_video_urls = []

        # Step 1: Extract all video URLs from the input URLs (handling playlists)
        for index, url in enumerate(self.urls, start=1):
            if self.is_stopped:
                self.status_update.emit("Download stopped by user.")
                break

            self.status_update.emit(
                f"Extracting videos from URL {index}/{len(self.urls)}: {url}"
            )

            try:
                # Use extract_flat=True to get a list of video URLs without full metadata
                ydl_opts_flat = {
                    'quiet': True,
                    'skip_download': True,
                    'extract_flat': True,  # Extract only video URLs
                    'ignoreerrors': True,
                    'logger': self.logger,
                }

                with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl_flat:
                    info_dict = ydl_flat.extract_info(url, download=False)

                    if info_dict is None:
                        self.logger.error(f"No metadata found for URL: {url}")
                        self.failed_urls.append({"url": url, "reason": "No metadata found."})
                        continue

                    info_type = info_dict.get('_type', 'video')

                    if info_type == 'playlist':
                        entries = info_dict.get('entries', [])
                        for entry in entries:
                            if entry is None:
                                # Entry is None, likely due to a private video
                                # However, with extract_flat=True, entry should have 'url' even if inaccessible
                                video_url = entry.get('url') if entry and 'url' in entry else 'Unknown URL'
                                if video_url != 'Unknown URL':
                                    self.failed_urls.append({"url": video_url, "reason": "Private"})
                                    self.logger.warning(f"Private video detected. URL: {video_url}")
                                else:
                                    self.failed_urls.append({"url": url, "reason": "Private"})
                                    self.logger.warning(f"Private video detected. URL: {url}")
                            else:
                                video_url = entry.get('url', 'Unknown URL')
                                # Convert relative URLs to full URLs if necessary
                                if not video_url.startswith('http'):
                                    video_url = f"https://www.youtube.com/watch?v={video_url}"
                                all_video_urls.append(video_url)
                    elif info_type == 'video':
                        video_url = info_dict.get('url', 'Unknown URL')
                        all_video_urls.append(video_url)
                    else:
                        self.logger.warning(f"Unhandled type: {info_type} for URL: {url}")
                        self.failed_urls.append({"url": url, "reason": f"Unhandled type: {info_type}"})
            except Exception as e:
                self.logger.error(f"Error extracting URL '{url}': {e}")
                self.logger.error(traceback.format_exc())
                self.failed_urls.append({"url": url, "reason": str(e)})

        self.total_items = len(all_video_urls)

        # Step 2: Process each video URL individually
        for i, video_url in enumerate(all_video_urls, start=1):
            if self.is_stopped:
                self.status_update.emit("Download stopped by user.")
                break

            self.status_update.emit(f"Downloading video {i}/{self.total_items}: {video_url}")

            try:
                # Extract full metadata for the video
                ydl_opts_full = {
                    'quiet': True,
                    'skip_download': True,
                    'ignoreerrors': True,
                    'logger': self.logger,
                }

                with yt_dlp.YoutubeDL(ydl_opts_full) as ydl_full:
                    video_info = ydl_full.extract_info(video_url, download=False)

                    if video_info is None:
                        # Video is private or inaccessible
                        self.logger.error(f"Private video or inaccessible: {video_url}")
                        self.failed_urls.append({"url": video_url, "reason": "Private"})
                        self.completed_items += 1
                        self.update_total_progress()
                        continue

                # Process the video
                self.process_single_video(video_info, download_manager, self.output_path)
                self.completed_items += 1
                self.update_total_progress()
            except Exception as e:
                self.logger.error(f"Failed to download video '{video_url}': {e}")
                self.failed_urls.append({"url": video_url, "reason": str(e)})
                self.completed_items += 1
                self.update_total_progress()

            # Cool-off every 10 video downloads
            self.download_counter += 1
            if self.download_counter % 10 == 0:
                delay = random.uniform(0, 2)
                self.logger.info(f"Cooling off for {delay:.2f} seconds after {self.download_counter} video downloads.")
                time.sleep(delay)

        # Emit the failed URLs signal
        if self.failed_urls:
            self.failed_downloads_signal.emit(self.failed_urls)

        if self.is_stopped:
            self.status_update.emit("Download stopped by user.")

        self.status_update.emit("Download complete")
        self.finished.emit()  # Signal that the thread has finished

    def update_total_progress(self):
        """Update the overall progress bar based on completed items."""
        if self.total_items > 0:
            total_progress = int((self.completed_items / self.total_items) * 100)
            self.total_progress_update.emit(total_progress)
        else:
            self.total_progress_update.emit(0)

    def process_single_video(self, info_dict: dict, download_manager: YTDownloadManager, base_folder: str):
        """Process an individual video."""
        if self.is_stopped:
            raise yt_dlp.utils.DownloadCancelled()
        if info_dict is None:
                self.logger.warning("Received None info_dict, skipping this video.")
                return
                
        title = info_dict.get('title', 'Unknown Title')
        description = info_dict.get('description', '')
        thumbnail_url = info_dict.get('thumbnail')
        self.current_video_update.emit(title)
        self.update_description.emit(description)

        # Download and emit the thumbnail
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                image_data = response.content
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                self.update_thumbnail.emit(pixmap)
            except Exception as e:
                self.logger.error(f"Failed to download thumbnail: {e}")

        # Determine the folder structure
        final_folder = base_folder

        # If 'use_year_subfolders' is enabled
        if self.settings.get('use_year_subfolders', False):
            upload_date = info_dict.get('upload_date')  # in YYYYMMDD format
            if upload_date and len(upload_date) >= 4:
                year = upload_date[:4]
                final_folder = os.path.join(final_folder, year)

        os.makedirs(final_folder, exist_ok=True)

        # Set file name and path, ensuring it's clean
        video_title = clean_filename(info_dict.get('title', 'Unknown_Title'))
        output_template = os.path.join(final_folder, f"{video_title}.%(ext)s")

        try:
            download_manager.download_video(
                video_url=info_dict.get('webpage_url'),
                output_template=output_template,
                info_dict=info_dict,
                progress_callback=self.progress_update.emit,
                is_stopped=self.is_stopped
            )
        except yt_dlp.utils.DownloadCancelled:
            self.logger.info(f"Download cancelled for video: {title}")
            self.status_update.emit("Download stopped by user.")
            raise  # Re-raise to allow higher-level handling
        except Exception as e:
            error_message = str(e)
            if "Private video" in error_message:
                reason = "Private video - access denied."
            else:
                reason = error_message
            self.logger.error(f"Failed to download video '{title}': {reason}")
            video_url = info_dict.get('webpage_url', 'Unknown URL')
            self.failed_urls.append({"url": video_url, "reason": reason})
