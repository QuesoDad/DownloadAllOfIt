# yt_download_manager.py

import os
import yt_dlp
from utils import MyLogger
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
                # Check if this is the main video or audio file
                if d['info_dict'].get('requested_downloads'):
                    # Multiple files are being downloaded (video+audio)
                    # Only proceed if 'fragment_index' is in 'd' to avoid counting the same file multiple times
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
                # Get the path to the video file
                video_filepath = info_dict['filepath']
                video_basename = os.path.splitext(video_filepath)[0]
                # Thumbnail filename after conversion
                thumbnail_filepath = video_basename + '.png'
                # Text file with metadata
                metadata_filepath = video_basename + '.txt'

                # Write the metadata and original URL to the text file
                original_url = info_dict.get('original_url', video_url)

                # Prepare readable metadata with section headers
                metadata_sections = []
                # Basic Info
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
                basic_info_str = '\n'.join(f"{key}: {value}" for key, value in basic_info.items())
                metadata_sections.append(f"Basic Info:\n{basic_info_str}")

                # Technical Info
                technical_info = {
                    'Format': info_dict.get('format', ''),
                    'Format ID': info_dict.get('format_id', ''),
                    'Resolution': info_dict.get('resolution', ''),
                    'FPS': info_dict.get('fps', ''),
                    'Codec': info_dict.get('acodec', ''),
                    'Video Codec': info_dict.get('vcodec', ''),
                    'Audio Codec': info_dict.get('acodec', ''),
                }
                technical_info_str = '\n'.join(f"{key}: {value}" for key, value in technical_info.items())
                metadata_sections.append(f"Technical Info:\n{technical_info_str}")

                # Other Info
                other_info = {
                    'Categories': ', '.join(info_dict.get('categories', [])),
                    'License': info_dict.get('license', ''),
                    'Age Limit': info_dict.get('age_limit', ''),
                    'Webpage URL': info_dict.get('webpage_url', ''),
                    'Original URL': original_url,
                }
                other_info_str = '\n'.join(f"{key}: {value}" for key, value in other_info.items())
                metadata_sections.append(f"Other Info:\n{other_info_str}")

                # Combine all sections
                metadata_text = '\n\n'.join(metadata_sections)

                with open(metadata_filepath, 'w', encoding='utf-8') as f:
                    f.write(metadata_text)

                # Get the video's upload timestamp
                upload_timestamp = info_dict.get('timestamp')

                # If upload_timestamp is available, set the modification times
                if upload_timestamp:
                    # Convert timestamp to a tuple (atime, mtime)
                    times = (upload_timestamp, upload_timestamp)

                    # Update modification time of the video file
                    if os.path.exists(video_filepath):
                        os.utime(video_filepath, times)

                    # Update modification time of the thumbnail file
                    if os.path.exists(thumbnail_filepath):
                        os.utime(thumbnail_filepath, times)

                    # Update modification time of the metadata text file
                    if os.path.exists(metadata_filepath):
                        os.utime(metadata_filepath, times)
                else:
                    self.logger.warning("Upload timestamp not available; file modification times not updated.")

        ydl_opts = {
            'outtmpl': output_template,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'writesubtitles': True,
            'writethumbnail': True,
            'write_all_thumbnails': False,
            'convert_thumbnails': 'png',  # Convert thumbnails to PNG
            'embedthumbnail': True,
            'writedescription': True,
            'writeinfojson': True,
            'embedmetadata': True,
            'updatetime': False,  # We handle the file times manually
            'retries': 3,
            'continuedl': True,
            'ignoreerrors': True,
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],  # Hook to set modification date
            'logger': self.logger,
            'noplaylist': True,  # Do not download playlists
        }

        postprocessors = [
            {
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'png',
            },
            {
                'key': 'EmbedThumbnail',
            },
        ]

        if self.settings.get('output_format') == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                    *postprocessors,  # Append thumbnail processors
                ],
            })

        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except yt_dlp.utils.DownloadCancelled:
                self.logger.info(f"Download cancelled for URL: {video_url}")
