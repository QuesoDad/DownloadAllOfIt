# tests/test_download_thread.py
import sys
import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtCore import QThread
from pathlib import Path

# Get the current file's directory
current_file = Path(__file__).resolve()
parent_dir = current_file.parent
grandparent_dir = current_file.parent.parent

# Add the current script dir
#sys.path.append(str(parent_dir))

# Add the main project dir
sys.path.append(str(grandparent_dir))

from download_thread import DownloadThread

def test_download_thread_initialization():
    urls = ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    output_path = Path("/tmp")
    settings = {}
    thread = DownloadThread(urls, output_path, settings)
    assert isinstance(thread, QThread)
    assert thread.urls == urls
    assert thread.output_path == output_path
    assert thread.settings == settings

@patch('download_thread.YTDownloadManager')
def test_run_method(mock_manager_class):
    urls = ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    output_path = Path("/tmp")
    settings = {}
    thread = DownloadThread(urls, output_path, settings)

    mock_manager = mock_manager_class.return_value
    mock_manager.download_video.return_value = None

    with patch('yt_dlp.YoutubeDL') as mock_ydl, \
         patch('sys.stdout', sys.__stdout__), \
         patch('sys.stderr', sys.__stderr__):
        mock_instance = mock_ydl.return_value
        mock_instance.extract_info.return_value = {
            '_type': 'video',
            'title': 'Test Video',
            'webpage_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'thumbnail': 'https://example.com/thumbnail.jpg',
        }
        thread.run()
         # Check if the method was called
        assert mock_manager.download_video.called, "download_video was not called"
        mock_manager.download_video.assert_called_once()