# yt_download_manager.py

import os
import json
from pathlib import Path
import yt_dlp
from utils import clean_filename
import time
import logging
import subprocess
import mutagen
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image  # Added for image conversion

# Obtain logger from the root logger configured in utils.py
logger = logging.getLogger(__name__)

class YTDownloadManager:
    """
    Simplified download manager using yt-dlp's features.
    """

    def __init__(self, settings, cookies_file=None):
        """
        Initialize the download manager with logger, settings, and optional cookies file.
        """
        self.logger = logger
        self.settings = settings
        self.cookies_file = cookies_file
        # Define the metadata file path for downloaded files
        self.downloaded_metadata_file = Path(settings.get("metadata_file", "downloaded_files.json"))
        # Load previously downloaded files into a dictionary
        self.downloaded_files = self.load_downloaded_files()

    def load_downloaded_files(self):
        """Load previously downloaded file metadata from JSON."""
        if self.downloaded_metadata_file.exists():
            try:
                with self.downloaded_metadata_file.open("r") as file:
                    return json.load(file)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to load metadata file: {e}")
        return {}

    def save_downloaded_file(self, video_url, output_file_path):
        """Save downloaded file info to metadata JSON after a successful download."""
        self.downloaded_files[video_url] = output_file_path
        with self.downloaded_metadata_file.open("w") as file:
            json.dump(self.downloaded_files, file, indent=4)
        self.logger.debug(f"Updated metadata with downloaded file: {output_file_path}")

    
    def convert_thumbnail_to_png(self, thumbnail_filepath):
        """
        Convert the given thumbnail to PNG format.

        Args:
            thumbnail_filepath (str): Path to the thumbnail file to convert.

        Returns:
            str: Path to the converted PNG file.
        """
        png_thumbnail_filepath = thumbnail_filepath.rsplit('.', 1)[0] + '.png'
        try:
            with Image.open(thumbnail_filepath) as img:
                img.save(png_thumbnail_filepath, 'PNG')
            self.logger.debug(f"Thumbnail converted to PNG: {png_thumbnail_filepath}")
            return png_thumbnail_filepath
        except Exception as e:
            self.logger.error(f"Failed to convert thumbnail to PNG: {e}")
            return None

    def add_description_to_video(self, video_filepath, description_filepath, info_dict):
        """
        Adds the content of a description file as metadata (comments) in the video file.
        """
        # Existing title, uploader, and description processing
        video_title = info_dict.get("title", "Unknown Title")
        uploader_name = info_dict.get("uploader", "Unknown Uploader")
        description_content = ""
        
        if description_filepath.exists():
            try:
                with open(description_filepath, "r", encoding="utf-8") as file:
                    description_content = file.read()
            except Exception as e:
                self.logger.error(f"Failed to read description file: {e}")
        
        # Define temporary output file
        output_filepath = video_filepath + "_temp_with_comments.mp4"
        command = [
            "ffmpeg",
            "-i", video_filepath,
            "-y",
            "-metadata", f"title={video_title}",
            "-metadata", f"author={uploader_name}",
        ]
        if description_content:
            command += [
                "-metadata", f"comment={description_content}",
                "-metadata", f"description={description_content}",
            ]

        command += [
            "-c", "copy",
            output_filepath
        ]
        
        try:
            subprocess.run(command, check=True)
            if output_filepath.exists():
                output_filepath.replace(video_filepath)
                self.logger.debug(f"Description metadata added to: {video_filepath}")
                
                # Embed thumbnail using Mutagen after FFmpeg metadata
                self.embed_thumbnail(video_filepath)
            else:
                self.logger.error(f"Failed to create output file: {output_filepath}")
        
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error embedding description: {e}")
        except mutagen.MutagenError as e:
            self.logger.error(f"Error embedding thumbnail: {e}")
    
    def embed_thumbnail(self, video_filepath):
        """
        Embeds the thumbnail into the video file using Mutagen.

        Args:
            video_filepath (str): Path to the video file (e.g., `.mp4`).
        """
        # Attempt to find the thumbnail file with various extensions
        possible_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        thumbnail_filepath = None
        for ext in possible_extensions:
            temp_thumbnail_filepath = video_filepath.replace('.mp4', ext)
            if temp_thumbnail_filepath.exists():
                # Convert the thumbnail to PNG if it's not already
                if ext != '.png':
                    png_thumbnail_filepath = self.convert_thumbnail_to_png(temp_thumbnail_filepath)
                    if png_thumbnail_filepath:
                        thumbnail_filepath = png_thumbnail_filepath
                        break
                else:
                    thumbnail_filepath = temp_thumbnail_filepath
                    break
        
        if thumbnail_filepath and thumbnail_filepath.exists():
            try:
                video = MP4(video_filepath)
                with open(thumbnail_filepath, "rb") as img_file:
                    video["covr"] = [MP4Cover(img_file.read(), imageformat=MP4Cover.FORMAT_PNG)]
                video.save()
                self.logger.debug(f"Thumbnail embedded successfully into: {video_filepath}")
            except mutagen.MutagenError as e:
                self.logger.error(f"Error embedding thumbnail with Mutagen: {e}")
        else:
            self.logger.warning(f"No valid thumbnail file found for embedding. Expected formats: {possible_extensions}")

    def download_video(self, video_url, output_template, info_dict, progress_callback=None, is_stopped=None):
        """
        Simplified download method using yt-dlp's built-in features.

        :param video_url: URL of the video to download.
        :param output_template: Output file template.
        :param info_dict: Dictionary containing video information.
        :param progress_callback: Function to call to update progress.
        :param is_stopped: Function to check if the download should be stopped.
        """
        output_file_path = output_template % {"ext": "mp4"}  # Adjust if necessary for other formats
        download_subtitles = self.settings.get('download_subtitles', False)
        download_quality = self.settings.get('download_quality', 'best')
        # Use video ID or a default name if title is missing
        video_title = info_dict.get('title') or f"video_{info_dict.get('id', 'unknown')}"
        output_template = f"{output_template}/{video_title}.%(ext)s"
        
        # Check if this video was downloaded already, using metadata or file existence
        if video_url in self.downloaded_files or Path(output_file_path).exists():
            self.logger.info(f"File for URL {video_url} already downloaded, skipping.")
            return  # Skip download
        
        
        def progress_hook(d):
            """Hook function to monitor download progress."""
            if is_stopped and is_stopped():
                raise yt_dlp.utils.DownloadCancelled()
            status = d.get('status')
            if status == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                if total_bytes:
                    percent_value = downloaded_bytes / total_bytes * 100
                    progress_callback(int(percent_value))
                else:
                    progress_callback(0)  # Unknown total size
            elif status == 'finished':
                if progress_callback:
                    progress_callback(100)
            elif status == 'error':
                if progress_callback:
                    progress_callback(0)  # Reset progress on error
                self.logger.error(f"Download encountered an error: {d.get('error', 'Unknown error')}")
            elif status == 'started':
                self.logger.info("Download started.")
                if progress_callback:
                    progress_callback(0)
            elif status == 'extracting':
                self.logger.info("Extracting video information.")
                if progress_callback:
                    progress_callback(50)  # Arbitrary progress value

        def postprocessor_hook(d):
            """Hook function called after post-processing."""
            if d['status'] == 'finished':
                info_dict = d['info_dict']
                video_filepath = info_dict['filepath']
                video_basename = video_filepath.stem
                metadata_filepath = video_basename + '.txt'
                metadata_json_filepath = video_basename + '.info.json'
                description_filepath = video_filepath.replace('.mp4', '.description')
                
                if description_filepath.exists():
                    self.add_description_to_video(video_filepath, description_filepath, d['info_dict'])
                
                # Save metadata and URL
                original_url = info_dict.get('original_url', video_url)
                metadata_text = self.prepare_metadata(info_dict, original_url)
                
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    f.write(metadata_text)

                # Set modification times
                upload_timestamp = info_dict.get('timestamp')
                if upload_timestamp:
                    files_to_update = [
                        video_filepath,
                        video_basename + '.png',  # Assuming thumbnail is PNG
                        metadata_filepath,
                        metadata_json_filepath,
                        description_filepath
                    ]
                    # Apply the timestamp
                    self.set_file_times(files_to_update, upload_timestamp)
                else:
                    self.logger.warning("Upload timestamp not available; file modification times not updated.")

        output_format = self.settings.get('output_format', 'mp4').lower()
        ydl_opts = {
            'outtmpl': output_template,
            'logger': self.logger,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],
            'writesubtitles': True,
            'writeautomaticsub': True,
            'writethumbnail': True,
            'writedescription': True,
            'writeinfojson': True,
            'embedmetadata': False,
            'embedthumbnail': False,
            'continuedl': True,  # Enable resume
            'retries': 3,  # Number of retry attempts
            'fragment_retries': 3,  # Retries for fragment downloads
            'concurrent_fragment_downloads': 5,  # Number of concurrent fragment downloads
        }
        
        # Define postprocessors based on output format
        postprocessors = []
        output_format = self.settings.get('output_format', 'mp4').lower()

        if output_format == 'mp3':
            ydl_opts.update({
                'format': download_quality + '/bestaudio/best',
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    {
                        'key': 'FFmpegMetadata',
                    },
                ],
            })
        elif output_format in ['mp4', 'mkv']:
            ydl_opts.update({
                'format': download_quality + '+bestaudio/best',
                'merge_output_format': output_format,
                'postprocessors': postprocessors,
            })
        else:
            ydl_opts.update({
                'format': download_quality + '+bestaudio/best',
                'merge_output_format': 'mp4',
                'postprocessors': postprocessors,
            })

        # Handle subtitles
        if download_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
        else:
            ydl_opts['writesubtitles'] = False
            ydl_opts['writeautomaticsub'] = False
        
        # Handle metadata embedding based on settings
        embed_metadata = {}
        for tag in ['title', 'uploader', 'description', 'tags', 'license']:
            embed = self.settings.get(f'embed_{tag}', True)
            if embed:
                embed_metadata[tag] = info_dict.get(tag, '')
        # Now, use embed_metadata as needed in post-processing
        
        # Include cookies if provided
        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file
            self.logger.debug(f"Using cookies file: {self.cookies_file}")

        # Log the start of the download
        self.logger.debug(f"Starting download for URL: {video_url}")
        self.logger.debug(f"Output template: {output_template}")

        # Log postprocessor hooks
        self.logger.debug(f"Postprocessors: {ydl_opts.get('postprocessors')}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except yt_dlp.utils.DownloadCancelled:
                self.logger.info(f"Download cancelled for URL: {video_url}")
            except Exception as e:
                self.logger.error(f"Unexpected error during download of {video_url}: {e}")
                raise
        
        # After successful download, save the information
        self.save_downloaded_file(video_url, output_file_path)

    def prepare_metadata(self, info_dict, original_url):
        """
        Prepare and format metadata text from video information.

        :param info_dict: Dictionary containing video information.
        :param original_url: Original URL of the video.
        :return: Formatted metadata text.
        """
        metadata_sections = []

        basic_info = {
            'Title': info_dict.get('title', ''),
            'Uploader': info_dict.get('uploader', ''),
            'Upload date': info_dict.get('upload_date', ''),
            'Duration': info_dict.get('duration', ''),
            'View count': info_dict.get('view_count', ''),
            'Like count': info_dict.get('like_count', ''),
            'Description': info_dict.get('description', ''),
            'Tags': ', '.join(info_dict.get('tags', [])),
        }
        metadata_sections.append("Basic Info:\n" + '\n'.join(f"{key}: {value}" for key, value in basic_info.items()))

        technical_info = {
            'Format': info_dict.get('format', ''),
            'Format ID': info_dict.get('format_id', ''),
            'Resolution': info_dict.get('resolution', ''),
            'FPS': info_dict.get('fps', ''),
            'Video Codec': info_dict.get('vcodec', ''),
            'Audio Codec': info_dict.get('acodec', ''),
        }
        metadata_sections.append("Technical Info:\n" + '\n'.join(f"{key}: {value}" for key, value in technical_info.items()))

        other_info = {
            'Categories': ', '.join(info_dict.get('categories', [])),
            'License': info_dict.get('license', ''),
            'Age Limit': info_dict.get('age_limit', ''),
            'Webpage URL': info_dict.get('webpage_url', ''),
            'Original URL': original_url,
        }
        metadata_sections.append("Other Info:\n" + '\n'.join(f"{key}: {value}" for key, value in other_info.items()))

        return '\n\n'.join(metadata_sections)

    def set_file_times(self, filepaths, timestamp):
        """
        Update file modification times to match the upload timestamp.
        
        :param filepaths: List of file paths to update.
        :param timestamp: Unix timestamp to set as the modification time.
        """
        times = (timestamp, timestamp)
        for filepath in filepaths:
            if filepath.exists():  # Only set times if the file exists
                filepath.touch(exist_ok=True)  # Ensure the file exists
                filepath.stat()  # Refresh the file status
                os.utime(filepath, times)
            else:
                self.logger.debug(f"File not found for time update: {filepath}")
                
    def closeEvent(self, event):
        """
        Handle the event when the application window is closed.
        Ensures that all running threads are properly terminated.
        """
        if hasattr(self, 'thread') and self.thread.isRunning():
            # Prompt the user to confirm exit if downloads are in progress
            reply = QMessageBox.question(
                self,
                self.tr("Exit Application"),
                self.tr("Downloads are in progress. Do you really want to exit?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Attempt to stop the thread
                self.thread.stop()
                # Wait for the thread to finish
                self.thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
