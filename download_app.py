# download_app.py

"""
YTDownloadApp class for the main GUI application.

This module defines the main window of the application, handling user interactions,
displaying progress, and managing downloads.
"""

import os
import logging
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QLabel, QTextEdit, QProgressBar,
    QDialogButtonBox, QCheckBox, QComboBox, QVBoxLayout,
    QHBoxLayout, QWidget, QTextBrowser, QSplitter, QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from download_thread import DownloadThread
from log_handler import QTextEditLogger
from dialogs import SupportedSitesDialog, SettingsDialog, FailedDownloadsDialog
from utils import load_last_directory, save_last_directory, load_settings, save_settings, get_supported_sites


class YTDownloadApp(QtWidgets.QWidget):
    """
    Main application class for the video downloader GUI.

    This class sets up the GUI components, handles user interactions,
    and manages the download process through DownloadThread.
    """

    def __init__(self, test_mode=False, test_urls=None):
        """
        Initialize the YTDownloadApp.

        Args:
            test_mode (bool, optional): If True, starts downloading test URLs. Defaults to False.
            test_urls (list, optional): A list of test URLs to download. Defaults to None.
        """
        super().__init__()
        self.output_folder = load_last_directory()  # Load the last directory on startup
        self.settings = load_settings()  # Load settings
        self.cookies_file = self.settings.get('cookies_file', '')  # Load cookies file path
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
            # Set the output folder to a default location if not set
            if not self.output_folder:
                self.output_folder = os.path.join(os.getcwd(), 'test_downloads')
                os.makedirs(self.output_folder, exist_ok=True)
                self.output_label.setText(f"{self.tr('Selected folder')}: {self.output_folder}")
            self.on_start_download_clicked()

    def apply_logging_level(self):
        """
        Apply the logging level from settings.
        """
        level_name = self.settings.get('logging_level', 'DEBUG').upper()
        level = getattr(logging, level_name, logging.DEBUG)
        logging.getLogger().setLevel(level)
        self.logger.debug(f"Logging level set to {level_name}")

    def initUI(self):
        """
        Initialize the user interface.
        """
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

        # Button for selecting output folder
        self.output_button = QPushButton(self.tr('Select Output Folder'), self)
        self.output_button.clicked.connect(self.select_output_folder)
        left_layout.addWidget(self.output_button)

        # Label to show the selected output folder
        self.output_label = QLabel(self.output_folder or self.tr("No folder selected"))
        left_layout.addWidget(self.output_label)

        # Button for selecting cookies file
        self.cookies_button = QPushButton(self.tr('Select Cookies File'), self)
        self.cookies_button.clicked.connect(self.select_cookies_file)
        left_layout.addWidget(self.cookies_button)

        # Label to show the selected cookies file
        self.cookies_label = QLabel(self.cookies_file or self.tr("No cookies file selected"))
        left_layout.addWidget(self.cookies_label)

        # Start and Stop buttons
        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton(self.tr('Start Download'), self)
        self.start_button.clicked.connect(self.on_start_download_clicked)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton(self.tr('Stop Download'), self)
        self.stop_button.clicked.connect(self.on_stop_download_clicked)
        self.stop_button.setEnabled(False)  # Disabled until download starts
        buttons_layout.addWidget(self.stop_button)

        left_layout.addLayout(buttons_layout)

        # Preferences button
        self.preferences_button = QPushButton(self.tr('Preferences'), self)
        self.preferences_button.clicked.connect(self.open_settings_dialog)
        left_layout.addWidget(self.preferences_button)

        # Current video label
        self.current_video_label = QLabel(self.tr("Current Video:"))
        left_layout.addWidget(self.current_video_label)

        # Progress bars and labels
        self.status_label = QLabel(self.tr("Status: Idle"))
        left_layout.addWidget(self.status_label)

        # Overall progress
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

        # Button to show supported sites
        self.supported_sites_button = QPushButton(self.tr('Show Supported Sites'), self)
        self.supported_sites_button.clicked.connect(self.show_supported_sites)
        left_layout.addWidget(self.supported_sites_button)

        # Add the left widget to the main layout
        main_layout.addWidget(left_widget)

        # Right side panel (thumbnail and description)
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout()
        self.side_panel.setLayout(self.side_layout)

        # Create a splitter to split the side panel into two halves
        self.side_splitter = QSplitter(Qt.Vertical)
        self.side_layout.addWidget(self.side_splitter)

        # Thumbnail
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setMinimumHeight(300)  # Set a minimum height
        self.thumbnail_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.side_splitter.addWidget(self.thumbnail_label)

        # Description
        self.video_description_browser = QTextBrowser()
        self.video_description_browser.setReadOnly(True)
        self.video_description_browser.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.side_splitter.addWidget(self.video_description_browser)

        # Set the splitter sizes to split evenly
        self.side_splitter.setSizes([1, 1])

        # Add the side panel to the main layout
        main_layout.addWidget(self.side_panel)

    def resizeEvent(self, event):
        """
        Handle resize event to scale thumbnail.

        Args:
            event (QResizeEvent): The resize event.
        """
        super().resizeEvent(event)
        self.scale_thumbnail()

    def scale_thumbnail(self):
        """
        Scale the thumbnail to fit the available space.
        """
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            label_size = self.thumbnail_label.size()
            scaled_pixmap = self.original_pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)

    def select_output_folder(self):
        """
        Open file dialog to select the output folder and save it.
        """
        try:
            initial_dir = self.output_folder or os.path.expanduser("~")
            folder = QFileDialog.getExistingDirectory(self, self.tr("Select Output Folder"), initial_dir)
            if folder:
                self.output_folder = folder
                self.output_label.setText(f"{self.tr('Selected folder')}: {folder}")
                save_last_directory(folder)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to select folder')}: {e}")

    def select_cookies_file(self):
        """
        Open file dialog to select the cookies.txt file.
        """
        try:
            options = QFileDialog.Options()
            options |= QFileDialog.ReadOnly
            file_name, _ = QFileDialog.getOpenFileName(
                self, self.tr("Select Cookies File"), "", "Text Files (*.txt);;All Files (*)", options=options
            )
            if file_name:
                self.cookies_file = file_name
                self.cookies_label.setText(f"{self.tr('Cookies file')}: {file_name}")
                self.settings['cookies_file'] = file_name
                save_settings(self.settings)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to select cookies file')}: {e}")

    def on_start_download_clicked(self):
        """
        Handle the Start Download button click event.
        """
        try:
            urls = self.url_input.toPlainText().splitlines()
            urls = [url.strip() for url in urls if url.strip()]
            output_path = getattr(self, 'output_folder', None)

            if not urls:
                QMessageBox.warning(self, self.tr('Error'), self.tr('Please enter at least one valid URL.'))
                return
            if not output_path:
                QMessageBox.warning(self, self.tr('Error'), self.tr('Please select an output folder.'))
                return

            # Disable the start button to prevent multiple clicks
            self.start_button.setEnabled(False)

            # Enable the stop button
            self.stop_button.setEnabled(True)

            # Clear the URL input to prevent reprocessing
            self.url_input.clear()

            # Start the download in a separate thread
            self.thread = DownloadThread(urls, output_path, self.settings, self.cookies_file)
            self.thread.progress_update.connect(self.update_progress)
            self.thread.total_progress_update.connect(self.update_total_progress)
            self.thread.status_update.connect(self.update_status)
            self.thread.current_video_update.connect(self.update_current_video)
            self.thread.update_thumbnail.connect(self.update_thumbnail)
            self.thread.update_title.connect(self.update_title)
            self.thread.update_description.connect(self.update_description)
            self.thread.failed_downloads_signal.connect(self.handle_failed_downloads)
            self.thread.finished.connect(self.on_download_finished)
            self.thread.start()

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to start download')}: {e}")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def on_stop_download_clicked(self):
        """
        Handle the Stop Download button click event.
        """
        try:
            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.stop()
                self.stop_button.setEnabled(False)
                self.status_label.setText("Stopping download...")
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to stop download')}: {e}")

    def update_progress(self, value: int):
        """
        Update the individual video progress bar.

        Args:
            value (int): The current download progress percentage.
        """
        self.progress_bar.setValue(value)

    def update_total_progress(self, value: int):
        """
        Update the overall progress bar.

        Args:
            value (int): The overall download progress percentage.
        """
        self.total_progress_bar.setValue(value)

    def update_status(self, message: str):
        """
        Update the status label.

        Args:
            message (str): The status message to display.
        """
        self.status_label.setText(message)

    def update_current_video(self, title: str):
        """
        Update the current video label.

        Args:
            title (str): The title of the current video being downloaded.
        """
        self.current_video_label.setText(f"Downloading: {title}")

    def update_thumbnail(self, pixmap: QPixmap):
        """
        Update the thumbnail image.

        Args:
            pixmap (QPixmap): The thumbnail image to display.
        """
        # Store the original pixmap
        self.original_pixmap = pixmap
        # Scale the pixmap to fit the label
        self.scale_thumbnail()

    def update_title(self, title: str):
        """
        Update the title label.

        Args:
            title (str): The title of the current video.
        """
        # This method can be expanded if a separate title label is added
        pass

    def update_description(self, description: str):
        """
        Update the description display.

        Args:
            description (str): The description of the current video.
        """
        self.video_description_browser.setText(f"{description}")

    def on_download_finished(self):
        """
        Re-enable the start button and reset UI elements after download.
        """
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
        """
        Show the list of supported sites in a dialog box.
        """
        try:
            supported_sites = get_supported_sites()
            supported_sites_str = '\n'.join(supported_sites)

            dialog = SupportedSitesDialog(supported_sites_str, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to retrieve supported sites')}: {e}")

    def open_settings_dialog(self):
        """
        Open the settings dialog.
        """
        try:
            dialog = SettingsDialog(self.settings)
            if dialog.exec_():
                # Reload settings
                self.settings = dialog.get_settings()
                save_settings(self.settings)
                self.apply_logging_level()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to open settings')}: {e}")

    def handle_failed_downloads(self, failed_urls: list):
        """
        Handle the failed downloads by showing a dialog.

        Args:
            failed_urls (list): A list of dictionaries containing failed URLs and reasons.
        """
        if not failed_urls:
            return  # No failed downloads

        # Prepare list of failed URLs with reasons
        failed_urls_formatted = [f"{item['url']} - {item['reason']}" for item in failed_urls]

        try:
            dialog = FailedDownloadsDialog(failed_urls_formatted, self)
            result = dialog.exec_()

            if result == QDialog.Accepted:
                # User chose to add failed URLs back to the download queue
                new_urls = dialog.get_failed_urls()
                if new_urls:
                    # Clear the existing URL input to prevent reprocessing
                    self.url_input.clear()
                    # Set the URL input to only the failed URLs
                    self.url_input.setText('\n'.join(new_urls))
                    # Start downloading the failed URLs
                    self.on_start_download_clicked()
            elif result == QDialog.Rejected:
                # User chose to cancel, do nothing
                pass
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to handle failed downloads')}: {e}")
