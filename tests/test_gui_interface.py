# tests/test_gui_interface.py
import sys
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from unittest.mock import patch, MagicMock
from pathlib import Path


# Get the current file's directory
current_file = Path(__file__).resolve()
parent_dir = current_file.parent
grandparent_dir = current_file.parent.parent

# Add the current script dir
#sys.path.append(str(parent_dir))

# Add the main project dir
sys.path.append(str(grandparent_dir))

from gui_interface import YTDownloadApp


@pytest.fixture
def app(qtbot):
    test_app = YTDownloadApp()
    qtbot.addWidget(test_app)
    return test_app

def test_gui_initialization(app):
    assert app is not None
    assert app.windowTitle() == "Video Downloader"

@patch('gui_interface.DownloadThread')
def test_start_download_clicked(mock_thread_class, app, qtbot):
    mock_thread = mock_thread_class.return_value
    mock_thread.start = MagicMock()
    mock_thread.isRunning = MagicMock(return_value=False)  # Add this line
    # Set up input data and simulate a button click
    app.url_input.setPlainText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    app.output_folder = Path("/tmp")

    # Use qtbot to simulate a button click, ensuring it occurs within event loop
    qtbot.mouseClick(app.start_button, Qt.LeftButton)

    # Assertions to confirm that the thread is started correctly
    mock_thread_class.assert_called_once()
    mock_thread.start.assert_called_once()