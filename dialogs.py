# dialogs.py

"""
Dialog classes for the GUI application.

This module contains various QDialog subclasses used for different
user interactions within the application.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit,
    QDialogButtonBox, QPushButton, QHBoxLayout, QCheckBox, QComboBox
)
from PyQt5.QtCore import Qt


class SupportedSitesDialog(QDialog):
    """
    Dialog to display the list of supported sites.

    This dialog presents the user with a list of all websites from which
    videos can be downloaded using the application.

    Args:
        supported_sites_str (str): A string listing all supported sites.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, supported_sites_str, parent=None):
        """
        Initialize the SupportedSitesDialog.

        Sets up the dialog's layout, window title, and populates the
        text area with the list of supported sites.

        Args:
            supported_sites_str (str): A string listing all supported sites.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)  # Initialize the parent QDialog class
        self.setWindowTitle(self.tr("Supported Sites"))  # Set the window title with translation support

        # Set the fixed size of the dialog window (Width x Height in pixels)
        self.resize(400, 600)

        # Create the main vertical layout for the dialog
        layout = QVBoxLayout()

        # Instruction label to inform the user about the content of the dialog
        label = QLabel(self.tr("List of Supported Sites:"))
        layout.addWidget(label)  # Add the label to the layout

        # Create a read-only QTextEdit widget to display the list of supported sites
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)  # Make the text edit read-only to prevent user modifications
        text_edit.setText(supported_sites_str)  # Populate the text edit with the supported sites
        layout.addWidget(text_edit)  # Add the text edit to the layout

        self.setLayout(layout)  # Apply the layout to the dialog


class SettingsDialog(QDialog):
    """
    Dialog for application settings.

    This dialog allows users to configure various settings of the application,
    such as organizing downloads into year-based subfolders, selecting the
    output format for downloaded files, and setting the logging level.

    Args:
        settings (dict): A dictionary containing current settings.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, settings, parent=None):
        """
        Initialize the SettingsDialog.

        Sets up the dialog's layout, window title, and initializes widgets
        based on the current settings.

        Args:
            settings (dict): A dictionary containing current settings.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)  # Initialize the parent QDialog class
        self.setWindowTitle(self.tr("Settings"))  # Set the window title with translation support
        self.settings = settings  # Store the current settings

        # Create the main vertical layout for the dialog
        layout = QVBoxLayout()

        # ------------------------
        # Option 1: Use Year Subfolders
        # ------------------------
        # Create a checkbox for organizing downloads into year-based subfolders
        self.year_subfolders_checkbox = QCheckBox(
            self.tr("Organize downloads into year subfolders")
        )
        # Set the checkbox state based on current settings; default to unchecked if not set
        self.year_subfolders_checkbox.setChecked(
            self.settings.get('use_year_subfolders', False)
        )
        layout.addWidget(self.year_subfolders_checkbox)  # Add the checkbox to the layout

        # ------------------------
        # Option 2: Output Format Selection
        # ------------------------
        # Label for the output format selection
        output_format_label = QLabel(self.tr("Output Format:"))
        layout.addWidget(output_format_label)  # Add the label to the layout

        # ComboBox for selecting the desired output format
        self.format_combo = QComboBox()
        # Populate the ComboBox with supported formats
        self.format_combo.addItems(['mp4', 'mp3', 'mkv'])
        # Retrieve the current output format from settings; default to 'mp4' if not set
        current_format = self.settings.get('output_format', 'mp4')
        # Find the index of the current format in the ComboBox
        index = self.format_combo.findText(current_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)  # Set the ComboBox to the current format
        layout.addWidget(self.format_combo)  # Add the ComboBox to the layout

        # ------------------------
        # Option 3: Download Quality
        # ------------------------
        download_quality_label = QLabel(self.tr("Download Quality:"))
        layout.addWidget(download_quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['best', 'worst', 'highest', 'lowest', 'highestvideo', 'highestaudio'])
        current_quality = self.settings.get('download_quality', 'best')
        index = self.quality_combo.findText(current_quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
        layout.addWidget(self.quality_combo)

        # ------------------------
        # Option 4: Download Subtitles
        # ------------------------
        self.download_subtitles_checkbox = QCheckBox(
            self.tr("Download Subtitles")
        )
        self.download_subtitles_checkbox.setChecked(
            self.settings.get('download_subtitles', False)
        )
        layout.addWidget(self.download_subtitles_checkbox)

        # ------------------------
        # Option 5: Metadata Embedding
        # ------------------------
        metadata_label = QLabel(self.tr("Metadata to Embed:"))
        layout.addWidget(metadata_label)

        self.metadata_tags = {
            'Title': QCheckBox(self.tr("Title")),
            'Uploader': QCheckBox(self.tr("Uploader")),
            'Description': QCheckBox(self.tr("Description")),
            'Tags': QCheckBox(self.tr("Tags")),
            'License': QCheckBox(self.tr("License")),
            # Add more metadata fields as needed
        }

        for tag, checkbox in self.metadata_tags.items():
            checkbox.setChecked(
                self.settings.get(f'embed_{tag.lower()}', True)
            )
            layout.addWidget(checkbox)

        # ------------------------
        # Option 6: Logging Level Selection
        # ------------------------
        logging_level_label = QLabel(self.tr("Logging Level:"))
        layout.addWidget(logging_level_label)

        self.logging_combo = QComboBox()
        self.logging_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        current_level = self.settings.get('logging_level', 'DEBUG')
        index = self.logging_combo.findText(current_level)
        if index >= 0:
            self.logging_combo.setCurrentIndex(index)
        layout.addWidget(self.logging_combo)

        # ------------------------
        # Save and Cancel Buttons
        # ------------------------
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def save_settings(self):
        """
        Save settings to the instance variable and accept the dialog.

        This method updates the settings dictionary based on the user's selections
        in the dialog and closes the dialog with an accepted status.
        """
        self.settings['use_year_subfolders'] = self.year_subfolders_checkbox.isChecked()
        self.settings['output_format'] = self.format_combo.currentText()
        self.settings['download_quality'] = self.quality_combo.currentText()
        self.settings['download_subtitles'] = self.download_subtitles_checkbox.isChecked()
        for tag, checkbox in self.metadata_tags.items():
            self.settings[f'embed_{tag.lower()}'] = checkbox.isChecked()
        self.settings['logging_level'] = self.logging_combo.currentText()
        self.accept()

    def get_settings(self) -> dict:
        """
        Return the updated settings.

        This method allows other parts of the application to retrieve the updated
        settings after the dialog has been accepted.

        Returns:
            dict: The updated settings dictionary.
        """
        return self.settings  # Return the updated settings


class FailedDownloadsDialog(QDialog):
    """
    Dialog to display failed download URLs with options to retry or cancel.

    This dialog informs the user about videos that failed to download and
    provides options to retry downloading those specific URLs or cancel the
    operation.

    Args:
        failed_urls_formatted (list): A list of formatted strings listing failed URLs and reasons.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, failed_urls_formatted, parent=None):
        """
        Initialize the FailedDownloadsDialog.

        Sets up the dialog's layout, window title, and populates the
        text area with the list of failed downloads.

        Args:
            failed_urls_formatted (list): A list of formatted strings listing failed URLs and reasons.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)  # Initialize the parent QDialog class
        self.setWindowTitle(self.tr("Failed Downloads"))  # Set the window title with translation support
        self.failed_urls_formatted = failed_urls_formatted  # Store the list of failed URLs

        # Validate that all items in failed_urls_formatted are strings
        if not all(isinstance(item, str) for item in self.failed_urls_formatted):
            raise ValueError("All items in failed_urls_formatted must be strings.")

        # Set the fixed size of the dialog window (Width x Height in pixels)
        self.resize(500, 400)

        # Create the main vertical layout for the dialog
        layout = QVBoxLayout()

        # ------------------------
        # Instruction Label
        # ------------------------
        # Label to inform the user about the content of the dialog
        instruction_label = QLabel(self.tr("The following videos failed to download:"))
        layout.addWidget(instruction_label)  # Add the label to the layout

        # ------------------------
        # Failed URLs Display
        # ------------------------
        # Create a read-only QTextEdit widget to display the list of failed URLs and reasons
        self.failed_urls_text = QTextEdit()
        self.failed_urls_text.setReadOnly(True)  # Make the text edit read-only
        # Populate the text edit with the failed URLs, each on a new line
        self.failed_urls_text.setText('\n'.join(self.failed_urls_formatted))
        layout.addWidget(self.failed_urls_text)  # Add the text edit to the layout

        # ------------------------
        # Dialog Buttons: Retry and Cancel
        # ------------------------
        # Create a horizontal layout to hold the Cancel and Retry buttons side by side
        buttons_layout = QHBoxLayout()

        # Cancel button to reject the dialog without retrying
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)  # Connect to reject (close without action)
        buttons_layout.addWidget(self.cancel_button)  # Add the Cancel button to the buttons layout

        # Retry button to accept the dialog and retry the failed downloads
        self.retry_button = QPushButton(self.tr("Add to Download Queue"))
        self.retry_button.clicked.connect(self.accept)  # Connect to accept (close with action)
        buttons_layout.addWidget(self.retry_button)  # Add the Retry button to the buttons layout

        layout.addLayout(buttons_layout)  # Add the buttons layout to the main layout

        self.setLayout(layout)  # Apply the layout to the dialog

    def get_failed_urls(self) -> list:
        """
        Return the list of failed URLs extracted from the text.

        This method parses the text area to extract the URLs that failed to download,
        stripping out any accompanying reasons.

        Returns:
            list: A list of failed URLs as strings.
        """
        # Get the plain text from the text edit widget
        text = self.failed_urls_text.toPlainText()
        # Split the text into lines and extract URLs before the ' - ' separator
        return [line.split(' - ')[0].strip() for line in text.splitlines() if ' - ' in line]
