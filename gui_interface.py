# gui_interface.py

import os
import logging
import subprocess
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QLabel, QTextEdit, QProgressBar,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QDialog
)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QPixmap
from download_thread import DownloadThread
from dialogs import SupportedSitesDialog, SettingsDialog, FailedDownloadsDialog
from utils import load_last_directory, save_last_directory, load_settings, save_settings, get_supported_sites
from log_handler import QTextEditLogger  # Import QTextEditLogger for logging

def check_ffmpeg_installed():
    """Check if ffmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

class YTDownloadApp(QtWidgets.QWidget):
    """Main application class for the video downloader GUI."""
    def __init__(self, test_mode=False, test_urls=None):
        super().__init__()
        # Check if ffmpeg is installed
        if not check_ffmpeg_installed():
            QMessageBox.critical(
                self,
                "FFmpeg Not Found",
                "FFmpeg is not installed or not found in system PATH.\nPlease install FFmpeg to enable full functionality."
            )
            sys.exit(1)  # Exit the application
        
        self.output_folder = load_last_directory()
        self.settings = load_settings()
        self.cookies_file = self.settings.get('cookies_file', '')
        self.initUI()
        self.logger = logging.getLogger(__name__)

        # Set up logging to use QTextEditLogger
        self.text_edit_logger = QTextEditLogger(self.log_text_edit)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.text_edit_logger.setFormatter(formatter)
        logging.getLogger().addHandler(self.text_edit_logger)
        self.apply_logging_level()

        # Initialize a list to keep track of URLs to retry
        self.retry_urls = []

        # If test_mode is True, start the download automatically
        if test_mode and test_urls:
            self.url_input.setText('\n'.join(test_urls))
            if not self.output_folder:
                self.output_folder = os.path.join(os.getcwd(), 'test_downloads')
                os.makedirs(self.output_folder, exist_ok=True)
                self.output_label.setText(f"{self.tr('Selected folder')}: {self.output_folder}")
            self.on_start_download_clicked()

    def apply_logging_level(self):
        """Apply the logging level from settings."""
        level_name = self.settings.get('logging_level', 'DEBUG').upper()
        level = getattr(logging, level_name, logging.DEBUG)
        logging.getLogger().setLevel(level)
        self.logger.debug(f"Logging level set to {level_name}")

    def initUI(self):
        """Initialize the user interface."""
        self.setWindowTitle(self.tr('Video Downloader'))

        # Main layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Left side layout (URL input and controls)
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        # Label and input for URLs
        self.url_label = QLabel(self.tr("Enter Video/Playlist URLs (one per line):"))
        left_layout.addWidget(self.url_label)
        self.url_input = QTextEdit(self)
        left_layout.addWidget(self.url_input)

        # Output folder selection
        self.output_button = QPushButton(self.tr('Select Output Folder'), self)
        self.output_button.clicked.connect(self.select_output_folder)
        left_layout.addWidget(self.output_button)
        self.output_label = QLabel(self.output_folder or self.tr("No folder selected"))
        left_layout.addWidget(self.output_label)

        # Cookies file selection
        self.cookies_button = QPushButton(self.tr('Select Cookies File'), self)
        self.cookies_button.clicked.connect(self.select_cookies_file)
        left_layout.addWidget(self.cookies_button)
        self.cookies_label = QLabel(self.cookies_file or self.tr("No cookies file selected"))
        left_layout.addWidget(self.cookies_label)

        # Start and Stop buttons
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton(self.tr('Start Download'), self)
        self.start_button.clicked.connect(self.on_start_download_clicked)
        buttons_layout.addWidget(self.start_button)
        self.stop_button = QPushButton(self.tr('Stop Download'), self)
        self.stop_button.clicked.connect(self.on_stop_download_clicked)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)
        left_layout.addLayout(buttons_layout)

        # Preferences button
        self.preferences_button = QPushButton(self.tr('Preferences'), self)
        self.preferences_button.clicked.connect(self.open_settings_dialog)
        left_layout.addWidget(self.preferences_button)

        # Current video label
        self.current_video_label = QLabel(self.tr("Current Video:"))
        left_layout.addWidget(self.current_video_label)

        # Progress bars
        self.status_label = QLabel(self.tr("Status: Idle"))
        left_layout.addWidget(self.status_label)
        self.total_progress_label = QLabel(self.tr("Overall Progress:"))
        left_layout.addWidget(self.total_progress_label)
        self.total_progress_bar = QProgressBar(self)
        self.total_progress_bar.setValue(0)
        self.total_progress_bar.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.total_progress_bar)
        self.progress_label = QLabel(self.tr("Current Video Progress:"))
        left_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.progress_bar)

        # Log display
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        left_layout.addWidget(self.log_text_edit)

        # Supported sites button
        self.supported_sites_button = QPushButton(self.tr('Show Supported Sites'), self)
        self.supported_sites_button.clicked.connect(self.show_supported_sites)
        left_layout.addWidget(self.supported_sites_button)

        main_layout.addWidget(left_widget)

        # Right side panel (thumbnail and description)
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout()
        self.side_panel.setLayout(self.side_layout)
        main_layout.addWidget(self.side_panel)

        # Initialize Thumbnail Label
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.side_layout.addWidget(self.thumbnail_label)

        # Initialize Video Description Browser
        self.video_description_browser = QTextEdit(self)
        self.video_description_browser.setReadOnly(True)
        self.side_layout.addWidget(self.video_description_browser)

    def select_output_folder(self):
        """Open file dialog to select the output folder and save it."""
        initial_dir = self.output_folder or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select Output Folder"), initial_dir)
        if folder:
            self.output_folder = folder
            self.output_label.setText(f"{self.tr('Selected folder')}: {folder}")
            save_last_directory(folder)

    def select_cookies_file(self):
        """Open file dialog to select the cookies.txt file."""
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Cookies File"), "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            self.cookies_file = file_name
            self.cookies_label.setText(f"{self.tr('Cookies file')}: {file_name}")
            self.settings['cookies_file'] = file_name
            save_settings(self.settings)

    def on_start_download_clicked(self):
        """Handle the Start Download button click event."""
        urls = self.url_input.toPlainText().splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        output_path = self.output_folder

        if not urls:
            QMessageBox.warning(self, self.tr('Error'), self.tr('Please enter at least one valid URL.'))
            return
        if not output_path:
            QMessageBox.warning(self, self.tr('Error'), self.tr('Please select an output folder.'))
            return

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.url_input.clear()

        # Start the download in a separate thread
        self.thread = DownloadThread(urls, output_path, self.settings, self.cookies_file)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.total_progress_update.connect(self.update_total_progress)
        self.thread.status_update.connect(self.update_status)
        self.thread.current_video_update.connect(self.update_current_video)
        self.thread.update_thumbnail.connect(self.update_thumbnail)
        self.thread.update_description.connect(self.update_description)
        self.thread.failed_downloads_signal.connect(self.handle_failed_downloads)
        self.thread.finished.connect(self.on_download_finished)
        self.thread.start()

    def on_stop_download_clicked(self):
        """Handle the Stop Download button click event."""
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.stop()
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping download...")

    def update_progress(self, value: int):
        """Update the individual video progress bar."""
        self.progress_bar.setValue(value)

    def update_total_progress(self, value: int):
        """Update the total progress bar."""
        self.total_progress_bar.setValue(value)

    def update_status(self, message: str):
        """Update the status label."""
        self.status_label.setText(message)

    def update_current_video(self, title: str):
        """Update the current video label."""
        self.current_video_label.setText(f"Downloading: {title}")

    def update_thumbnail(self, pixmap: QPixmap):
        """Update the thumbnail image."""
        self.thumbnail_label.setPixmap(pixmap)

    def update_description(self, description: str):
        """Update the description display."""
        self.video_description_browser.setText(f"{description}")

    def on_download_finished(self):
        """Re-enable the start button after download."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.total_progress_bar.setValue(0)
        self.status_label.setText("Download complete")
        QMessageBox.information(
            self, self.tr('Download Complete'),
            self.tr('All videos have been downloaded successfully.')
        )

    def show_supported_sites(self):
        """Show the list of supported sites in a dialog box."""
        supported_sites = get_supported_sites()
        supported_sites_str = '\n'.join(supported_sites)

        dialog = SupportedSitesDialog(supported_sites_str, self)
        dialog.exec_()

    def open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.settings = dialog.get_settings()
            save_settings(self.settings)
            self.apply_logging_level()

    def handle_failed_downloads(self, failed_urls: list):
        """Handle the failed downloads by showing a dialog."""
        if not failed_urls:
            return

        # Format each failed URL with its original value, marking private videos as such
        failed_urls_formatted = [
            f"{item.get('url', 'Unknown URL')} - {item.get('reason', 'No reason provided')}"
            for item in failed_urls
        ]

        # Log the formatted list for debugging
        self.logger.debug(f"Formatted Failed URLs: {failed_urls_formatted}")

        dialog = FailedDownloadsDialog(failed_urls_formatted, self)
        if dialog.exec_() == QDialog.Accepted:
            new_urls = dialog.get_failed_urls()
            if new_urls:
                self.url_input.setText('\n'.join(new_urls))
                self.on_start_download_clicked()




# If this script is run directly, create and display the application window
if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Test section
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    window = YTDownloadApp(test_mode=True, test_urls=[test_url])
    window.show()
    sys.exit(app.exec_())