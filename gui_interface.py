# gui_interface.py

import os
import time
import json
import logging
import random
import traceback
import requests
import yt_dlp
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QTextEdit,
    QProgressBar, QDialogButtonBox, QCheckBox, QComboBox,
    QGridLayout, QHBoxLayout, QWidget, QTextBrowser, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap
from yt_download_manager import YTDownloadManager
from utils import MyLogger, get_supported_sites, clean_filename

# File to store the last used directory
LAST_DIR_FILE = 'last_directory.json'
SETTINGS_FILE = 'settings.json'

class LogEmitter(QObject):
    """Emits log messages to be displayed in the GUI."""
    log_signal = pyqtSignal(str)

class QTextEditLogger(logging.Handler):
    """Custom logging handler that outputs logs to a QTextEdit widget."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.emitter = LogEmitter()
        self.emitter.log_signal.connect(self.append_log)

    def emit(self, record):
        """Emit a log record."""
        msg = self.format(record)
        self.emitter.log_signal.emit(msg)

    def append_log(self, msg):
        """Append a log message to the QTextEdit widget."""
        self.text_edit.append(msg)
        # Auto-scroll to the bottom
        self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())

class YTDownloadApp(QtWidgets.QWidget):
    """Main application class for the video downloader GUI."""
    def __init__(self, test_mode=False, test_urls=None):
        super().__init__()
        self.output_folder = self.load_last_directory()  # Load the last directory on startup
        self.settings = self.load_settings()  # Load settings
        self.cookies_file = self.settings.get('cookies_file', '')  # Load cookies file path
        self.initUI()
        self.logger = MyLogger()

        # Set up logging to use QTextEditLogger
        self.text_edit_logger = QTextEditLogger(self.log_text_edit)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.text_edit_logger.setFormatter(formatter)
        logging.getLogger().addHandler(self.text_edit_logger)
        self.apply_logging_level()

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

        # Left side layout (existing content)
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        # Label and input for URLs
        self.url_label = QLabel(self.tr("Enter Video/Playlist URLs (one per line):"))
        left_layout.addWidget(self.url_label)
        self.url_input = QTextEdit(self)
        left_layout.addWidget(self.url_input)

        # Button for selecting output folder
        self.output_button = QtWidgets.QPushButton(self.tr('Select Output Folder'), self)
        self.output_button.clicked.connect(self.select_output_folder)
        left_layout.addWidget(self.output_button)

        # Label to show the selected output folder
        self.output_label = QLabel(self.output_folder or self.tr("No folder selected"))
        left_layout.addWidget(self.output_label)

        # Button for selecting cookies file
        self.cookies_button = QtWidgets.QPushButton(self.tr('Select Cookies File'), self)
        self.cookies_button.clicked.connect(self.select_cookies_file)
        left_layout.addWidget(self.cookies_button)

        # Label to show the selected cookies file
        self.cookies_label = QLabel(self.cookies_file or self.tr("No cookies file selected"))
        left_layout.addWidget(self.cookies_label)

        # Start and Stop buttons
        buttons_layout = QHBoxLayout()
        self.start_button = QtWidgets.QPushButton(self.tr('Start Download'), self)
        self.start_button.clicked.connect(self.on_start_download_clicked)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton(self.tr('Stop Download'), self)
        self.stop_button.clicked.connect(self.on_stop_download_clicked)
        self.stop_button.setEnabled(False)  # Disabled until download starts
        buttons_layout.addWidget(self.stop_button)

        left_layout.addLayout(buttons_layout)

        # Preferences button
        self.preferences_button = QtWidgets.QPushButton(self.tr('Preferences'), self)
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
        self.supported_sites_button = QtWidgets.QPushButton(self.tr('Show Supported Sites'), self)
        self.supported_sites_button.clicked.connect(self.show_supported_sites)
        left_layout.addWidget(self.supported_sites_button)

        # Add the left widget to the main layout
        main_layout.addWidget(left_widget)

        # Right side panel (side panel)
        self.side_panel = QWidget()
        self.side_layout = QVBoxLayout()
        self.side_panel.setLayout(self.side_layout)

        # Create a splitter to split the side panel into two halves
        self.side_splitter = QSplitter(Qt.Vertical)
        self.side_layout.addWidget(self.side_splitter)

        # Thumbnail
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setMinimumHeight(200)  # Set a minimum height
        self.thumbnail_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.side_splitter.addWidget(self.thumbnail_label)

        # Description
        self.video_description_browser = QTextBrowser()
        self.video_description_browser.setReadOnly(True)
        self.video_description_browser.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.side_splitter.addWidget(self.video_description_browser)

        # Set the splitter sizes to split evenly
        self.side_splitter.setSizes([1,1])

        # Add the side panel to the main layout
        main_layout.addWidget(self.side_panel)

    def resizeEvent(self, event):
        """Handle resize event to scale thumbnail."""
        super().resizeEvent(event)
        self.scale_thumbnail()

    def scale_thumbnail(self):
        """Scale the thumbnail to fit the available space."""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            label_size = self.thumbnail_label.size()
            scaled_pixmap = self.original_pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)

    def load_last_directory(self):
        """Load the last used directory from a JSON file."""
        if os.path.exists(LAST_DIR_FILE):
            with open(LAST_DIR_FILE, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    return data.get('last_directory', '')
                except json.JSONDecodeError:
                    return ''
        return ''

    def save_last_directory(self, folder):
        """Save the last used directory to a JSON file."""
        with open(LAST_DIR_FILE, 'w') as file:
            json.dump({'last_directory': folder}, file)

    def load_settings(self):
        """Load settings from a JSON file."""
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_settings(self, settings):
        """Save settings to a JSON file."""
        with open(SETTINGS_FILE, 'w') as file:
            json.dump(settings, file)

    def select_output_folder(self):
        """Open file dialog to select the output folder and save it."""
        initial_dir = self.output_folder or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select Output Folder"), initial_dir)
        if folder:
            self.output_folder = folder
            self.output_label.setText(f"{self.tr('Selected folder')}: {folder}")
            self.save_last_directory(folder)

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
            self.save_settings(self.settings)

    def on_start_download_clicked(self):
        """Handle the Start Download button click event."""
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

        # Start the download in a separate thread
        self.thread = DownloadThread(urls, output_path, self.settings, self.cookies_file)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.total_progress_update.connect(self.update_total_progress)
        self.thread.status_update.connect(self.update_status)
        self.thread.current_video_update.connect(self.update_current_video)
        self.thread.update_thumbnail.connect(self.update_thumbnail)
        self.thread.update_title.connect(self.update_title)
        self.thread.update_description.connect(self.update_description)
        self.thread.finished.connect(self.on_download_finished)
        self.thread.start()

    def on_stop_download_clicked(self):
        """Handle the Stop Download button click event."""
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.stop()
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping download...")

    def update_progress(self, value):
        """Update the individual video progress bar."""
        self.progress_bar.setValue(value)

    def update_total_progress(self, value):
        """Update the total progress bar."""
        self.total_progress_bar.setValue(value)

    def update_status(self, message):
        """Update the status label."""
        self.status_label.setText(message)

    def update_current_video(self, title):
        """Update the current video label."""
        self.current_video_label.setText(f"Downloading: {title}")

    def update_thumbnail(self, pixmap):
        """Update the thumbnail image."""
        # Store the original pixmap
        self.original_pixmap = pixmap
        # Scale the pixmap to fit the label
        self.scale_thumbnail()

    def update_title(self, title):
        """Update the title label."""
        # This method can be used if you have a separate label for the title
        pass

    def update_description(self, description):
        """Update the description display."""
        self.video_description_browser.setText(f"{description}")

    def on_download_finished(self):
        """Re-enable the start button after download."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.total_progress_bar.setValue(0)
        QMessageBox.information(
            self, self.tr('Download Complete'),
            self.tr('All videos have been downloaded successfully.')
        )

    def show_supported_sites(self):
        """Show the list of supported sites in a dialog box."""
        supported_sites = get_supported_sites()
        supported_sites_str = '\n'.join(supported_sites)

        dialog = SupportedSitesDialog(supported_sites_str)
        dialog.exec_()

    def open_settings_dialog(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings)
        if dialog.exec_():
            # Reload settings
            self.settings = dialog.get_settings()
            self.save_settings(self.settings)
            self.apply_logging_level()

class SupportedSitesDialog(QDialog):
    """Dialog to display the list of supported sites."""
    def __init__(self, supported_sites_str):
        super().__init__()
        self.setWindowTitle(self.tr("Supported Sites"))

        # Set dialog size
        self.resize(400, 600)  # Width x Height

        # Layout
        layout = QVBoxLayout()

        # Label
        label = QLabel(self.tr("List of Supported Sites:"))
        layout.addWidget(label)

        # TextEdit (read-only) with scroll bar
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(supported_sites_str)
        layout.addWidget(text_edit)

        self.setLayout(layout)

class SettingsDialog(QDialog):
    """Dialog for application settings."""
    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle(self.tr("Settings"))
        self.settings = settings

        # Layout
        layout = QGridLayout()

        # Use year subfolders
        self.year_subfolders_checkbox = QCheckBox(
            self.tr("Organize downloads into year subfolders")
        )
        self.year_subfolders_checkbox.setChecked(
            self.settings.get('use_year_subfolders', False)
        )
        layout.addWidget(self.year_subfolders_checkbox, 0, 0, 1, 2)

        # Output format
        layout.addWidget(QLabel(self.tr("Output Format:")), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['mp4', 'mp3'])
        current_format = self.settings.get('output_format', 'mp4')
        index = self.format_combo.findText(current_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        layout.addWidget(self.format_combo, 1, 1)

        # Logging level
        layout.addWidget(QLabel(self.tr("Logging Level:")), 2, 0)
        self.logging_combo = QComboBox()
        self.logging_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        current_level = self.settings.get('logging_level', 'DEBUG')
        index = self.logging_combo.findText(current_level)
        if index >= 0:
            self.logging_combo.setCurrentIndex(index)
        layout.addWidget(self.logging_combo, 2, 1)

        # Save and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, 3, 0, 1, 2)

        self.setLayout(layout)

    def save_settings(self):
        """Save settings to the instance variable."""
        self.settings['use_year_subfolders'] = self.year_subfolders_checkbox.isChecked()
        self.settings['output_format'] = self.format_combo.currentText()
        self.settings['logging_level'] = self.logging_combo.currentText()
        self.accept()

    def get_settings(self):
        """Return the updated settings."""
        return self.settings

class DownloadThread(QThread):
    """Thread to handle the download process."""
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    total_progress_update = pyqtSignal(int)
    current_video_update = pyqtSignal(str)
    update_thumbnail = pyqtSignal(QPixmap)
    update_title = pyqtSignal(str)
    update_description = pyqtSignal(str)
    finished = pyqtSignal()
    stop_signal = pyqtSignal()  # Signal to stop the download

    def __init__(self, urls, output_path, settings, cookies_file):
        super().__init__()
        self.urls = urls
        self.output_path = output_path
        self.settings = settings
        self.cookies_file = cookies_file
        self.logger = logging.getLogger()
        self.is_stopped = False
        self.stop_signal.connect(self.stop)
        self.metadata_counter = 0
        self.download_counter = 0

    def stop(self):
        """Stop the download process."""
        self.is_stopped = True

    def run(self):
        """Main method that runs in the separate thread."""
        self.total_items = 0  # Will be updated dynamically
        self.completed_items = 0

        download_manager = YTDownloadManager(
            logger=MyLogger(), settings=self.settings, cookies_file=self.cookies_file
        )

        for index, url in enumerate(self.urls, start=1):
            if self.is_stopped:
                self.status_update.emit("Download stopped by user.")
                break

            self.status_update.emit(
                f"Processing URL {index}/{len(self.urls)}: {url}"
            )

            try:
                # Extract metadata
                ydl_opts = {
                    'quiet': True,
                    'skip_download': True,
                    'logger': self.logger,
                    'ignoreerrors': True,
                    'noplaylist': False,
                    'extract_flat': False,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    if info_dict is None:
                        self.logger.error(f"No metadata found for URL: {url}")
                        continue

                    # Get channel_name and base_folder
                    channel_name = clean_filename(info_dict.get("channel", info_dict.get("uploader", "Unknown_Channel")))
                    base_folder = os.path.join(self.output_path, channel_name)
                    os.makedirs(base_folder, exist_ok=True)

                    # Now, check the type of info_dict to handle different cases
                    info_type = info_dict.get('_type', 'video')  # Default to 'video' if '_type' is None

                    if info_type == 'playlist':
                        # Could be a playlist or a list of playlists
                        entries = info_dict.get('entries', [])
                        if entries and entries[0].get('_type') == 'playlist':
                            # This is a list of playlists
                            for playlist_entry in entries:
                                if self.is_stopped:
                                    break
                                self.process_playlist(playlist_entry, download_manager, base_folder)
                        else:
                            # This is a single playlist
                            self.process_playlist(info_dict, download_manager, base_folder)
                    elif info_type == 'video' or info_type is None:
                        # Single video
                        try:
                            self.total_items += 1
                            self.process_single_video(info_dict, download_manager, base_folder)
                        except yt_dlp.utils.DownloadCancelled:
                            self.logger.info("Download cancelled by user.")
                            self.status_update.emit("Download stopped by user.")
                            break
                        self.completed_items += 1
                        self.update_total_progress()
                    else:
                        self.logger.warning(f"Unhandled type: {info_type} for URL: {url}")

                if self.is_stopped:
                    self.status_update.emit("Download stopped by user.")
                    break

                # Cool-off every 10 video downloads
                self.download_counter += 1
                if self.download_counter % 10 == 0:
                    delay = random.uniform(0, 2)
                    self.logger.info(f"Cooling off for {delay:.2f} seconds after {self.download_counter} video downloads.")
                    time.sleep(delay)

            except Exception as e:
                self.logger.error(f"Error processing URL '{url}': {e}")
                self.logger.error(traceback.format_exc())
                self.completed_items += 1
                self.update_total_progress()
            finally:
                self.progress_update.emit(0)  # Reset individual progress bar

        self.status_update.emit("Download complete")
        self.finished.emit()  # Signal that the thread has finished

    def update_total_progress(self):
        """Update the overall progress."""
        if self.total_items > 0:
            total_progress = int((self.completed_items / self.total_items) * 100)
            self.total_progress_update.emit(total_progress)
        else:
            self.total_progress_update.emit(0)

    def process_playlist(self, playlist_info_dict, download_manager, base_folder):
        """Process a playlist and download its entries."""
        playlist_title = clean_filename(playlist_info_dict.get('title', 'Unknown_Playlist'))
        playlist_folder = os.path.join(base_folder, playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)
        entries = playlist_info_dict.get('entries', [])
        self.total_items += len(entries)
        for entry in entries:
            if self.is_stopped:
                break
            if entry is None:
                self.logger.warning("Skipping an entry in the playlist because it's None.")
                self.completed_items += 1
                self.update_total_progress()
                continue  # Skip this entry
            try:
                self.process_single_video(entry, download_manager, playlist_folder)
            except yt_dlp.utils.DownloadCancelled:
                self.logger.info("Download cancelled by user.")
                self.status_update.emit("Download stopped by user.")
                break
            self.completed_items += 1
            self.update_total_progress()

    def process_single_video(self, info_dict, download_manager, base_folder):
        """Process individual video or playlist entry."""
        if self.is_stopped:
            raise yt_dlp.utils.DownloadCancelled()
        if info_dict is None:
            self.logger.warning("Received None info_dict, skipping this video.")
            return
        
        title = info_dict.get('title', 'Unknown Title')
        description = info_dict.get('description', '')
        thumbnail_url = info_dict.get('thumbnail')
        self.current_video_update.emit(title)
        self.update_title.emit(title)
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

        # Now set file name and path, ensuring it's clean
        video_title = clean_filename(info_dict.get('title', 'Unknown_Title'))
        output_template = os.path.join(final_folder, f"{video_title}.%(ext)s")

        def progress_callback(percent):
            """Callback function to update progress."""
            if percent is not None:
                self.progress_update.emit(int(percent))

        def is_stopped():
            """Function to check if download should be stopped."""
            return self.is_stopped  # Check if the stop button was clicked

        try:
            download_manager.download_video(
                video_url=info_dict.get('webpage_url'),
                output_template=output_template,
                info_dict=info_dict,
                progress_callback=progress_callback,
                is_stopped=is_stopped  # Pass the is_stopped function
            )
        except yt_dlp.utils.DownloadCancelled:
            self.logger.info(f"Download cancelled for video: {title}")
            self.status_update.emit("Download stopped by user.")
            raise  # Re-raise the exception to be caught in the calling method

# If this script is run directly, create and display the application window
if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # Test section
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    window = YTDownloadApp(test_mode=True, test_urls=[test_url])
    window.show()
    sys.exit(app.exec_())
