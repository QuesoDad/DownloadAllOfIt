# tests/test_yt_download_manager.py
import sys
import pytest
from unittest.mock import patch, MagicMock

import yt_dlp
from pathlib import Path
# Get the current file's directory
current_file = Path(__file__).resolve()
parent_dir = current_file.parent
grandparent_dir = current_file.parent.parent

# Add the current script dir
#sys.path.append(str(parent_dir))

# Add the main project dir
sys.path.append(str(grandparent_dir))
from yt_download_manager import YTDownloadManager

def test_download_video_already_downloaded(tmp_path):
    manager = YTDownloadManager(settings={})
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    output_template = str(tmp_path / "TestVideo.%(ext)s")
    info_dict = {'title': 'Test Video'}

    # Compute the output_file using yt_dlp's prepare_filename
    with yt_dlp.YoutubeDL({'outtmpl': output_template}) as ydl:
        output_file = ydl.prepare_filename(info_dict)

    # Simulate that the file already exists
    Path(output_file).touch()

    with patch.object(manager, 'save_downloaded_file') as mock_save:
        manager.download_video(video_url, output_template, info_dict)
        mock_save.assert_called_once_with(video_url, output_file)

def test_download_video_success(tmp_path):
    manager = YTDownloadManager(settings={})

    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    output_template = str(tmp_path / "TestVideo.%(ext)s")
    info_dict = {'title': 'Test Video'}

    # Compute the output_file using yt_dlp's prepare_filename
    with yt_dlp.YoutubeDL({'outtmpl': output_template}) as ydl:
        output_file = ydl.prepare_filename(info_dict)

    # Ensure the output_file does not exist
    assert not Path(output_file).exists()

    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.download.return_value = None

        manager.download_video(video_url, output_template, info_dict)
        mock_ydl.assert_called_once_with({
            'outtmpl': output_template,
            # Include other options if your code uses them
        })
        mock_instance.download.assert_called_once_with([video_url])
