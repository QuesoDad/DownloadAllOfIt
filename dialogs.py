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

    Args:
        supported_sites_str (str): A string listing all supported sites.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, supported_sites_str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Supported Sites"))

        # Set dialog size
        self.resize(400, 600)  # Width x Height

        # Layout
        layout = QVBoxLayout()

        # Instruction label
        label = QLabel(self.tr("List of Supported Sites:"))
        layout.addWidget(label)

        # TextEdit (read-only) with scroll bar
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(supported_sites_str)
        layout.addWidget(text_edit)

        self.setLayout(layout)


class SettingsDialog(QDialog):
    """
    Dialog for application settings.

    Args:
        settings (dict): A dictionary containing current settings.
    """

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.settings = settings

        # Layout
        layout = QVBoxLayout()

        # Use year subfolders (Checkbox)
        self.year_subfolders_checkbox = QCheckBox(
            self.tr("Organize downloads into year subfolders")
        )
        self.year_subfolders_checkbox.setChecked(
            self.settings.get('use_year_subfolders', False)
        )
        layout.addWidget(self.year_subfolders_checkbox)

        # Output format (ComboBox)
        output_format_label = QLabel(self.tr("Output Format:"))
        layout.addWidget(output_format_label)

        self.format_combo = QComboBox()
        self.format_combo.addItems(['mp4', 'mp3', 'mkv'])
        current_format = self.settings.get('output_format', 'mp4')
        index = self.format_combo.findText(current_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        layout.addWidget(self.format_combo)

        # Logging level (ComboBox)
        logging_level_label = QLabel(self.tr("Logging Level:"))
        layout.addWidget(logging_level_label)

        self.logging_combo = QComboBox()
        self.logging_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        current_level = self.settings.get('logging_level', 'DEBUG')
        index = self.logging_combo.findText(current_level)
        if index >= 0:
            self.logging_combo.setCurrentIndex(index)
        layout.addWidget(self.logging_combo)

        # Save and Cancel buttons
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
        """
        self.settings['use_year_subfolders'] = self.year_subfolders_checkbox.isChecked()
        self.settings['output_format'] = self.format_combo.currentText()
        self.settings['logging_level'] = self.logging_combo.currentText()
        self.accept()

    def get_settings(self) -> dict:
        """
        Return the updated settings.

        Returns:
            dict: The updated settings dictionary.
        """
        return self.settings


class FailedDownloadsDialog(QDialog):
    """
    Dialog to display failed download URLs with options to retry or cancel.

    Args:
        failed_urls_formatted (list): A list of formatted strings listing failed URLs and reasons.
        parent (QWidget, optional): The parent widget. Defaults to None.
    """

    def __init__(self, failed_urls_formatted, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Failed Downloads"))
        self.failed_urls_formatted = failed_urls_formatted

        if not all(isinstance(item, str) for item in self.failed_urls_formatted):
            raise ValueError("All items in failed_urls_formatted must be strings.")
        
        # Set dialog size
        self.resize(500, 400)  # Width x Height

        # Layout
        layout = QVBoxLayout()

        # Instruction label
        instruction_label = QLabel(self.tr("The following videos failed to download:"))
        layout.addWidget(instruction_label)

        # TextEdit to display failed URLs
        self.failed_urls_text = QTextEdit()
        self.failed_urls_text.setReadOnly(True)
        self.failed_urls_text.setText('\n'.join(self.failed_urls_formatted))
        layout.addWidget(self.failed_urls_text)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        self.retry_button = QPushButton(self.tr("Add to Download Queue"))
        self.retry_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.retry_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def get_failed_urls(self) -> list:
        """
        Return the list of failed URLs extracted from the text.

        Returns:
            list: A list of failed URLs as strings.
        """
        text = self.failed_urls_text.toPlainText()
        # Extract URLs before the ' - ' separator
        return [line.split(' - ')[0].strip() for line in text.splitlines() if ' - ' in line]