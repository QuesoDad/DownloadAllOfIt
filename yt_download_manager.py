# yt_download_manager.py

import os
import yt_dlp
from utils import clean_filename
import json
import time
import logging
import subprocess
import mutagen
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image  # Added for image conversion

def setup_logger():
    # Create a logger object
    logger = logging.getLogger('download_thread')
    logger.setLevel(logging.DEBUG)  # Capture all levels of logs (DEBUG and above)
    logging.basicConfig(encoding='utf-8')
    
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

class YTDownloadManager:
    """
    Simplified download manager using yt-dlp's features.
    """

    def __init__(self, logger, settings, cookies_file=None):
        """
        Initialize the download manager with logger, settings, and optional cookies file.
        """
        self.logger = logger
        self.settings = settings
        self.cookies_file = cookies_file

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
        
        with open(description_filepath, "r", encoding="utf-8") as file:
            description_content = file.read()

        # Define temporary output file
        output_filepath = video_filepath + "_temp_with_comments.mp4"
        command = [
            "ffmpeg",
            "-i", video_filepath,
            "-y",
            "-metadata", f"title={video_title}",
            "-metadata", f"author={uploader_name}",
            "-metadata", f"comment={description_content}",
            "-metadata", f"description={description_content}",
            "-c", "copy",
            output_filepath
        ]
        
        try:
            subprocess.run(command, check=True)
            if os.path.exists(output_filepath):
                os.replace(output_filepath, video_filepath)
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
            if os.path.exists(temp_thumbnail_filepath):
                # Convert the thumbnail to PNG if it's not already
                if ext != '.png':
                    png_thumbnail_filepath = self.convert_thumbnail_to_png(temp_thumbnail_filepath)
                    if png_thumbnail_filepath:
                        thumbnail_filepath = png_thumbnail_filepath
                        break
                else:
                    thumbnail_filepath = temp_thumbnail_filepath
                    break
        
        if thumbnail_filepath and os.path.exists(thumbnail_filepath):
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
        def progress_hook(d):
            """Hook function to monitor download progress."""
            if is_stopped and is_stopped():
                raise yt_dlp.utils.DownloadCancelled()
            if d['status'] == 'downloading':
                if d['info_dict'].get('requested_downloads'):
                    if 'fragment_index' in d:
                        return
                if progress_callback:
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    if total_bytes:
                        percent_value = downloaded_bytes / total_bytes * 100
                        progress_callback(percent_value)
            elif d['status'] == 'finished':
                if progress_callback:
                    progress_callback(100)

        def postprocessor_hook(d):
            """Hook function called after post-processing."""
            if d['status'] == 'finished':
                info_dict = d['info_dict']
                video_filepath = info_dict['filepath']
                video_basename = os.path.splitext(video_filepath)[0]
                metadata_filepath = video_basename + '.txt'
                metadata_json_filepath = video_basename + '.info.json'
                description_filepath = video_filepath.replace('.mp4', '.description')
                
                if os.path.exists(description_filepath):
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

        # Configure yt_dlp options
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
            'embedmetadata': False,  # Disable yt-dlp's embed metadata since handled manually
            'embedthumbnail': False,  # Disable yt-dlp's embed thumbnail
            'postprocessors': [
                {
                    'key': 'FFmpegEmbedSubtitle',
                    'already_have_subtitle': True,
                },
                {
                    'key': 'FFmpegMetadata',
                },
                {
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'png',
                },
            ],
        }

        # Adjust options based on output format
        output_format = self.settings.get('output_format', 'mp4').lower()
        if output_format == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
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
        elif output_format == 'mkv':
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mkv',
                'postprocessors': [
                    {
                        'key': 'FFmpegEmbedSubtitle',
                        'already_have_subtitle': True,
                    },
                    {
                        'key': 'FFmpegMetadata',
                    },
                    {
                        'key': 'FFmpegThumbnailsConvertor',
                        'format': 'png',
                    },
                ],
            })
        else:
            # Default to mp4 settings if not mp3 or mkv
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'postprocessors': [
                    {
                        'key': 'FFmpegEmbedSubtitle',
                        'already_have_subtitle': True,
                    },
                    {
                        'key': 'FFmpegMetadata',
                    },
                    {
                        'key': 'FFmpegThumbnailsConvertor',
                        'format': 'png',
                    },
                ],
            })

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
            if os.path.exists(filepath):  # Only set times if the file exists
                os.utime(filepath, times)
            else:
                self.logger.debug(f"File not found for time update: {filepath}")
