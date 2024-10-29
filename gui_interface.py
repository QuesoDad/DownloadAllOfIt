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

# Import custom modules for download functionality, dialogs, utilities, and logging
from download_thread import DownloadThread
from dialogs import SupportedSitesDialog, SettingsDialog, FailedDownloadsDialog
from utils import (
    load_last_directory, save_last_directory,
    load_settings, save_settings, get_supported_sites
)
from log_handler import QTextEditLogger  # Custom logger to display logs in QTextEdit

def check_ffmpeg_installed():
    """
    Check if FFmpeg is installed and accessible in the system PATH.
    
    Returns:
        bool: True if FFmpeg is installed, False otherwise.
    """
    try:
        # Attempt to run 'ffmpeg -version' to check if FFmpeg is available
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If the command fails or FFmpeg is not found, return False
        return False

class YTDownloadApp(QtWidgets.QWidget):
    """
    Main application class for the YouTube (YT) downloader GUI.
    
    Inherits from QtWidgets.QWidget to create the main window of the application.
    """
    def __init__(self, test_mode=False, test_urls=None):
        """
        Initialize the application.
        
        Args:
            test_mode (bool): If True, the application runs in test mode with predefined URLs.
            test_urls (list): List of URLs to download in test mode.
        """
        super().__init__()  # Initialize the parent class (QWidget)
        
        # Check if FFmpeg is installed; FFmpeg is required for full functionality
        if not check_ffmpeg_installed():
            QMessageBox.critical(
                self,
                "FFmpeg Not Found",
                "FFmpeg is not installed or not found in system PATH.\n"
                "Please install FFmpeg to enable full functionality."
            )
            sys.exit(1)  # Exit the application if FFmpeg is not found
        
        # Load the last used output directory from settings
        self.output_folder = load_last_directory()
        # Load application settings (e.g., preferences)
        self.settings = load_settings()
        # Get the path to the cookies file from settings (if any)
        self.cookies_file = self.settings.get('cookies_file', '')
        # Initialize the user interface components
        self.initUI()
        # Set up logging for the application
        self.logger = logging.getLogger(__name__)

        # Set up logging to use QTextEditLogger for displaying logs in the GUI
        self.text_edit_logger = QTextEditLogger(self.log_text_edit)
        # Define the log message format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.text_edit_logger.setFormatter(formatter)
        # Add the QTextEditLogger handler to the root logger
        logging.getLogger().addHandler(self.text_edit_logger)
        # Apply the logging level based on user settings
        self.apply_logging_level()

        # Initialize a list to keep track of URLs that failed to download and may need to be retried
        self.retry_urls = []

        # If the application is started in test mode with predefined URLs
        if test_mode and test_urls:
            # Populate the URL input field with the test URLs, separated by newlines
            self.url_input.setText('\n'.join(test_urls))
            if not self.output_folder:
                # If no output folder is set, create a 'test_downloads' folder in the current working directory
                self.output_folder = os.path.join(os.getcwd(), 'test_downloads')
                os.makedirs(self.output_folder, exist_ok=True)
                # Update the output folder label to show the selected folder
                self.output_label.setText(f"{self.tr('Selected folder')}: {self.output_folder}")
            # Automatically start the download process
            self.on_start_download_clicked()

    def apply_logging_level(self):
        """
        Apply the logging level based on user settings.
        
        Retrieves the logging level from the settings and sets it for the root logger.
        """
        # Get the logging level name from settings; default to 'DEBUG' if not set
        level_name = self.settings.get('logging_level', 'DEBUG').upper()
        # Get the corresponding logging level from the logging module
        level = getattr(logging, level_name, logging.DEBUG)
        # Set the logging level for the root logger
        logging.getLogger().setLevel(level)
        # Log a debug message indicating the current logging level
        self.logger.debug(f"Logging level set to {level_name}")

    def initUI(self):
        """
        Initialize the user interface components of the application.
        
        Sets up the layout, widgets, and their properties.
        """
        # Set the window title, with support for translations
        self.setWindowTitle(self.tr('Video Downloader'))

        # Create the main horizontal layout to divide the window into left and right sections
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # ------------------------
        # Left Side Layout
        # ------------------------
        # Create a QWidget to hold the left side components
        left_widget = QWidget()
        # Create a vertical layout for the left side
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        # Label for URL input
        self.url_label = QLabel(self.tr("Enter Video/Playlist URLs (one per line):"))
        left_layout.addWidget(self.url_label)

        # TextEdit widget for users to input multiple URLs
        self.url_input = QTextEdit(self)
        left_layout.addWidget(self.url_input)

        # Button to select the output folder where downloaded videos will be saved
        self.output_button = QPushButton(self.tr('Select Output Folder'), self)
        self.output_button.clicked.connect(self.select_output_folder)  # Connect the button to its handler
        left_layout.addWidget(self.output_button)

        # Label to display the currently selected output folder
        self.output_label = QLabel(self.output_folder or self.tr("No folder selected"))
        left_layout.addWidget(self.output_label)

        # Button to select a cookies file (useful for downloading private or age-restricted videos)
        self.cookies_button = QPushButton(self.tr('Select Cookies File'), self)
        self.cookies_button.clicked.connect(self.select_cookies_file)  # Connect the button to its handler
        left_layout.addWidget(self.cookies_button)

        # Label to display the currently selected cookies file
        self.cookies_label = QLabel(self.cookies_file or self.tr("No cookies file selected"))
        left_layout.addWidget(self.cookies_label)

        # Horizontal layout to hold Start and Stop buttons side by side
        buttons_layout = QHBoxLayout()

        # Button to start the download process
        self.start_button = QPushButton(self.tr('Start Download'), self)
        self.start_button.clicked.connect(self.on_start_download_clicked)  # Connect to handler
        buttons_layout.addWidget(self.start_button)

        # Button to stop the ongoing download process
        self.stop_button = QPushButton(self.tr('Stop Download'), self)
        self.stop_button.clicked.connect(self.on_stop_download_clicked)  # Connect to handler
        self.stop_button.setEnabled(False)  # Initially disabled; enabled when download starts
        buttons_layout.addWidget(self.stop_button)

        # Add the Start and Stop buttons layout to the main left layout
        left_layout.addLayout(buttons_layout)

        # Button to open the Preferences/Settings dialog
        self.preferences_button = QPushButton(self.tr('Preferences'), self)
        self.preferences_button.clicked.connect(self.open_settings_dialog)  # Connect to handler
        left_layout.addWidget(self.preferences_button)

        # Label to display the title of the currently downloading video
        self.current_video_label = QLabel(self.tr("Current Video:"))
        left_layout.addWidget(self.current_video_label)

        # Label and progress bar for overall download progress
        self.status_label = QLabel(self.tr("Status: Idle"))
        left_layout.addWidget(self.status_label)

        self.total_progress_label = QLabel(self.tr("Overall Progress:"))
        left_layout.addWidget(self.total_progress_label)

        self.total_progress_bar = QProgressBar(self)
        self.total_progress_bar.setValue(0)  # Initialize to 0%
        self.total_progress_bar.setAlignment(Qt.AlignCenter)  # Center the text
        left_layout.addWidget(self.total_progress_bar)

        # Label and progress bar for current video download progress
        self.progress_label = QLabel(self.tr("Current Video Progress:"))
        left_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)  # Initialize to 0%
        self.progress_bar.setAlignment(Qt.AlignCenter)  # Center the text
        left_layout.addWidget(self.progress_bar)

        # TextEdit widget to display log messages; set to read-only
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        left_layout.addWidget(self.log_text_edit)

        # Button to show a dialog with the list of supported websites
        self.supported_sites_button = QPushButton(self.tr('Show Supported Sites'), self)
        self.supported_sites_button.clicked.connect(self.show_supported_sites)  # Connect to handler
        left_layout.addWidget(self.supported_sites_button)

        # Add the left widget (with all its components) to the main layout
        main_layout.addWidget(left_widget)

        # ------------------------
        # Right Side Panel
        # ------------------------
        # Create a QWidget for the right side panel
        self.side_panel = QWidget()
        # Create a vertical layout for the side panel
        self.side_layout = QVBoxLayout()
        self.side_panel.setLayout(self.side_layout)
        # Add the side panel to the main layout
        main_layout.addWidget(self.side_panel)

        # Label to display the thumbnail image of the current video
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)  # Center the thumbnail
        self.side_layout.addWidget(self.thumbnail_label)

        # TextEdit widget to display the description of the current video; set to read-only
        self.video_description_browser = QTextEdit(self)
        self.video_description_browser.setReadOnly(True)
        self.side_layout.addWidget(self.video_description_browser)

    def select_output_folder(self):
        """
        Open a dialog for the user to select the output folder where videos will be saved.
        Save the selected folder path to settings and update the label in the GUI.
        """
        # Determine the initial directory for the dialog; use the last selected folder or the user's home directory
        initial_dir = self.output_folder or os.path.expanduser("~")
        # Open a directory selection dialog
        folder = QFileDialog.getExistingDirectory(
            self, 
            self.tr("Select Output Folder"), 
            initial_dir
        )
        if folder:
            # If a folder is selected, update the output_folder attribute
            self.output_folder = folder
            # Update the label to display the selected folder
            self.output_label.setText(f"{self.tr('Selected folder')}: {folder}")
            # Save the selected folder path to settings for future use
            save_last_directory(folder)

    def select_cookies_file(self):
        """
        Open a dialog for the user to select a cookies.txt file.
        Save the selected file path to settings and update the label in the GUI.
        """
        # Define options for the file dialog
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly  # Make the dialog read-only
        # Open a file selection dialog for text files
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            self.tr("Select Cookies File"), 
            "", 
            "Text Files (*.txt);;All Files (*)", 
            options=options
        )
        if file_name:
            # If a file is selected, update the cookies_file attribute
            self.cookies_file = file_name
            # Update the label to display the selected cookies file
            self.cookies_label.setText(f"{self.tr('Cookies file')}: {file_name}")
            # Save the selected cookies file path to settings
            self.settings['cookies_file'] = file_name
            save_settings(self.settings)

    def on_start_download_clicked(self):
        """
        Handle the event when the Start Download button is clicked.
        Collect URLs, validate inputs, and start the download process in a separate thread.
        """
        # Get the list of URLs entered by the user, splitting by newlines and stripping whitespace
        urls = self.url_input.toPlainText().splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        # Get the output path where videos will be saved
        output_path = self.output_folder

        # Validate that at least one URL has been entered
        if not urls:
            QMessageBox.warning(self, self.tr('Error'), self.tr('Please enter at least one valid URL.'))
            return
        # Validate that an output folder has been selected
        if not output_path:
            QMessageBox.warning(self, self.tr('Error'), self.tr('Please select an output folder.'))
            return

        # Disable the Start button to prevent multiple clicks
        self.start_button.setEnabled(False)
        # Enable the Stop button to allow the user to stop the download
        self.stop_button.setEnabled(True)
        # Clear the URL input field as downloads are starting
        self.url_input.clear()

        # Initialize a DownloadThread to handle the downloading process without freezing the GUI
        self.thread = DownloadThread(urls, output_path, self.settings, self.cookies_file)
        # Connect signals from the thread to corresponding slots (methods) in the GUI
        self.thread.progress_update.connect(self.update_progress)
        self.thread.total_progress_update.connect(self.update_total_progress)
        self.thread.status_update.connect(self.update_status)
        self.thread.current_video_update.connect(self.update_current_video)
        self.thread.update_thumbnail.connect(self.update_thumbnail)
        self.thread.update_description.connect(self.update_description)
        self.thread.failed_downloads_signal.connect(self.handle_failed_downloads)
        self.thread.finished.connect(self.on_download_finished)
        # Start the download thread
        self.thread.start()

    def on_stop_download_clicked(self):
        """
        Handle the event when the Stop Download button is clicked.
        Attempts to stop the ongoing download process gracefully.
        """
        # Check if the download thread exists and is currently running
        if hasattr(self, 'thread') and self.thread.isRunning():
            # Request the thread to stop
            self.thread.stop()
            # Disable the Stop button as the stop request has been made
            self.stop_button.setEnabled(False)
            # Update the status label to inform the user that the download is stopping
            self.status_label.setText("Stopping download...")

    def update_progress(self, value: int):
        """
        Update the progress bar for the current video's download progress.
        
        Args:
            value (int): The current progress value (0-100).
        """
        self.progress_bar.setValue(value)

    def update_total_progress(self, value: int):
        """
        Update the overall progress bar for all downloads.
        
        Args:
            value (int): The total progress value (0-100).
        """
        self.total_progress_bar.setValue(value)

    def update_status(self, message: str):
        """
        Update the status label to reflect the current state of the download process.
        
        Args:
            message (str): The status message to display.
        """
        self.status_label.setText(message)

    def update_current_video(self, title: str):
        """
        Update the label that shows the title of the currently downloading video.
        
        Args:
            title (str): The title of the current video.
        """
        self.current_video_label.setText(f"Downloading: {title}")

    def update_thumbnail(self, pixmap: QPixmap):
        """
        Update the thumbnail image displayed in the GUI.
        
        Args:
            pixmap (QPixmap): The pixmap image of the video's thumbnail.
        """
        self.thumbnail_label.setPixmap(pixmap)

    def update_description(self, description: str):
        """
        Update the text area that displays the description of the current video.
        
        Args:
            description (str): The description text of the video.
        """
        self.video_description_browser.setText(f"{description}")

    def on_download_finished(self):
        """
        Handle the event when the download thread has finished processing all URLs.
        Re-enable buttons and reset progress indicators.
        """
        # Re-enable the Start button to allow new downloads
        self.start_button.setEnabled(True)
        # Disable the Stop button as downloads are complete
        self.stop_button.setEnabled(False)
        # Reset the progress bars to 0%
        self.progress_bar.setValue(0)
        self.total_progress_bar.setValue(0)
        # Update the status label to indicate completion
        self.status_label.setText("Download complete")
        # Show an information message box to inform the user that downloads are complete
        QMessageBox.information(
            self, 
            self.tr('Download Complete'),
            self.tr('All videos have been downloaded successfully.')
        )

    def show_supported_sites(self):
        """
        Display a dialog listing all supported video sites for downloading.
        """
        # Retrieve the list of supported sites from utility functions
        supported_sites = get_supported_sites()
        # Join the list into a single string separated by newlines for display
        supported_sites_str = '\n'.join(supported_sites)

        # Create and display a dialog showing the supported sites
        dialog = SupportedSitesDialog(supported_sites_str, self)
        dialog.exec_()  # Execute the dialog modally

    def open_settings_dialog(self):
        """
        Open the settings/preferences dialog where users can adjust application settings.
        """
        # Create the SettingsDialog, passing current settings and the parent widget
        dialog = SettingsDialog(self.settings, self)
        # Execute the dialog and check if the user accepted the changes
        if dialog.exec_():
            # If accepted, retrieve the updated settings from the dialog
            self.settings = dialog.get_settings()
            # Save the updated settings
            save_settings(self.settings)
            # Apply the new logging level based on updated settings
            self.apply_logging_level()

    def handle_failed_downloads(self, failed_urls: list):
        """
        Handle URLs that failed to download by displaying a dialog with options to retry.
        
        Args:
            failed_urls (list): A list of dictionaries containing failed URLs and reasons.
        """
        if not failed_urls:
            # If there are no failed downloads, do nothing
            return

        # Format each failed URL with its reason for failure
        failed_urls_formatted = [
            f"{item.get('url', 'Unknown URL')} - {item.get('reason', 'No reason provided')}"
            for item in failed_urls
        ]

        # Log the formatted list of failed URLs for debugging purposes
        self.logger.debug(f"Formatted Failed URLs: {failed_urls_formatted}")

        # Create and display a dialog showing the failed downloads
        dialog = FailedDownloadsDialog(failed_urls_formatted, self)
        # If the user chooses to retry the failed downloads
        if dialog.exec_() == QDialog.Accepted:
            # Retrieve the list of URLs the user wants to retry
            new_urls = dialog.get_failed_urls()
            if new_urls:
                # Populate the URL input field with the new URLs, separated by newlines
                self.url_input.setText('\n'.join(new_urls))
                # Start the download process again with the new URLs
                self.on_start_download_clicked()

# ------------------------
# Entry Point of the Application
# ------------------------

# If this script is run directly (not imported as a module), execute the following
if __name__ == '__main__':
    import sys  # Import sys to handle command-line arguments and exit

    # Create the QApplication instance, which manages application-wide resources
    app = QtWidgets.QApplication(sys.argv)

    # ------------------------
    # Test Section
    # ------------------------
    # Define a test URL (commonly known as a "Rickroll" link)
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    # Create an instance of the YTDownloadApp in test mode with the test URL
    window = YTDownloadApp(test_mode=True, test_urls=[test_url])
    # Show the main application window
    window.show()
    # Start the application's event loop and exit when done
    sys.exit(app.exec_())
