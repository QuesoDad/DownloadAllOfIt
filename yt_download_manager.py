# yt_download_manager.py

import os
import yt_dlp
from utils import clean_filename
import json
import time

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
                thumbnail_filepath = video_basename + '.png'
                metadata_filepath = video_basename + '.txt'

                # Save metadata and URL
                original_url = info_dict.get('original_url', video_url)
                metadata_text = self.prepare_metadata(info_dict, original_url)
                
                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    f.write(metadata_text)

                # Set modification times
                upload_timestamp = info_dict.get('timestamp')
                if upload_timestamp:
                    self.set_file_times([video_filepath, thumbnail_filepath, metadata_filepath], upload_timestamp)
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
            'embedmetadata': True,
            'embedthumbnail': True,  # Embed thumbnail
            'postprocessors': [
                {
                    'key': 'FFmpegEmbedSubtitle',
                    'already_have_subtitle': False,
                },
                {
                    'key': 'FFmpegMetadata',
                },
                {
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'png',
                },
                {
                    'key': 'EmbedThumbnail',
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
                        'already_have_subtitle': False,
                    },
                    {
                        'key': 'FFmpegMetadata',
                    },
                    {
                        'key': 'FFmpegThumbnailsConvertor',
                        'format': 'png',
                    },
                    {
                        'key': 'EmbedThumbnail',
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
                        'already_have_subtitle': False,
                    },
                    {
                        'key': 'FFmpegMetadata',
                    },
                    {
                        'key': 'FFmpegThumbnailsConvertor',
                        'format': 'png',
                    },
                    {
                        'key': 'EmbedThumbnail',
                    },
                ],
            })

        # Include cookies if provided
        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

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
        Update file modification times based on video upload timestamp.

        :param filepaths: List of file paths to update.
        :param timestamp: Unix timestamp to set as the file modification time.
        """
        times = (timestamp, timestamp)
        for filepath in filepaths:
            if os.path.exists(filepath):
                os.utime(filepath, times)
