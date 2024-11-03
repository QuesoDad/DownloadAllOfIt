# image_converter.py

import sys
import os
import traceback
from PIL import Image, UnidentifiedImageError
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFileDialog, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRunnable, QThreadPool

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    error = pyqtSignal(str)

class ImageConverterWorker(QRunnable):
    def __init__(self, file_path, index, signals):
        super().__init__()
        self.file_path = file_path
        self.index = index
        self.signals = signals
        self.is_running = True

    def run(self):
        if not self.is_running:
            return
        try:
            self.convert_to_png(self.file_path)
            self.signals.log.emit(f"Converted: {self.file_path}")
        except Exception as e:
            error_message = f"Error converting {self.file_path}:\n{str(e)}"
            self.signals.error.emit(error_message)
            self.signals.log.emit(error_message)
        finally:
            self.signals.progress.emit(1)  # Emit progress increment

    def stop(self):
        self.is_running = False

    def convert_to_png(self, file_path):
        # Skip files that are already in PNG format
        if file_path.lower().endswith('.png'):
            return

        with Image.open(file_path) as img:
            # Convert to RGBA to ensure lossless quality
            img = img.convert('RGBA')
            # Prepare the output file path
            base, ext = os.path.splitext(file_path)
            output_file = f"{base}.png"
            # Avoid overwriting if the output file already exists
            if os.path.isfile(output_file):
                return
            img.save(output_file, 'PNG', optimize=True)
            # Optionally, remove the original file
            os.remove(file_path)

class ImageConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter to Lossless PNG")
        self.setFixedSize(600, 400)
        self.folder_path = ''
        self.image_files = []
        self.init_ui()
        self.threadpool = QThreadPool()
        self.total_files = 0
        self.processed_files = 0

    def init_ui(self):
        layout = QVBoxLayout()

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.select_folder_button = QPushButton("Select Folder")
        self.select_folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.select_folder_button)
        layout.addLayout(folder_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)

        # Log display
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)

        # Start and Stop buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Conversion")
        self.start_button.clicked.connect(self.start_conversion)
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Stop Conversion")
        self.stop_button.clicked.connect(self.stop_conversion)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", "", QFileDialog.ShowDirsOnly
        )
        if folder:
            self.folder_path = folder
            self.folder_label.setText(f"Selected Folder: {folder}")
            self.image_files = self.find_image_files(folder)
            if self.image_files:
                self.start_button.setEnabled(True)
                self.progress_bar.setValue(0)
                self.progress_bar.setMaximum(len(self.image_files))
                self.log_text_edit.append(f"Found {len(self.image_files)} images to convert.")
            else:
                self.start_button.setEnabled(False)
                QMessageBox.information(
                    self, "No Images Found",
                    "No image files were found in the selected folder."
                )

    def find_image_files(self, folder):
        image_extensions = ('.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
        image_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_files.append(os.path.join(root, file))
        return image_files

    def start_conversion(self):
        if not self.image_files:
            QMessageBox.warning(self, "No Images", "No images to convert.")
            return

        self.processed_files = 0
        self.total_files = len(self.image_files)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.total_files)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.threadpool.setMaxThreadCount(4)  # Adjust the number of threads as needed

        for index, file_path in enumerate(self.image_files):
            signals = WorkerSignals()
            signals.progress.connect(self.update_progress)
            signals.log.connect(self.update_log)
            signals.error.connect(self.show_error_message)

            worker = ImageConverterWorker(file_path, index, signals)
            self.threadpool.start(worker)

    def stop_conversion(self):
        self.threadpool.waitForDone(100)  # Wait for threads to finish
        self.threadpool.clear()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_text_edit.append("Conversion stopped by user.")

    def update_progress(self, value):
        self.processed_files += value
        self.progress_bar.setValue(self.processed_files)
        if self.processed_files >= self.total_files:
            self.conversion_finished()

    def update_log(self, message):
        self.log_text_edit.append(message)
        # Auto-scroll to the bottom
        self.log_text_edit.verticalScrollBar().setValue(self.log_text_edit.verticalScrollBar().maximum())

    def conversion_finished(self):
        QMessageBox.information(self, "Conversion Complete", "All images have been converted.")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_text_edit.append("Conversion completed.")

    def show_error_message(self, message):
        # Display error message in the log and as a popup
        self.log_text_edit.append(f"Error: {message}")
        QMessageBox.critical(self, "Error", message)

def main():
    app = QApplication(sys.argv)
    window = ImageConverterApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
