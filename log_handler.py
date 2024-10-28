# log_handler.py

"""
Logging handlers for the GUI application.

This module provides custom logging handlers that emit log messages
to be displayed within the application's GUI.
"""

import logging
from PyQt5.QtCore import QObject, pyqtSignal


class LogEmitter(QObject):
    """
    Emits log messages to be displayed in the GUI.

    Attributes:
        log_signal (pyqtSignal): Signal emitted with log messages.
    """
    log_signal = pyqtSignal(str)


class QTextEditLogger(logging.Handler):
    """
    Custom logging handler that outputs logs to a QTextEdit widget.

    Args:
        text_edit (QTextEdit): The QTextEdit widget to display logs.
    """

    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.emitter = LogEmitter()
        self.emitter.log_signal.connect(self.append_log)

    def emit(self, record):
        """
        Emit a log record.

        Args:
            record (LogRecord): The log record to emit.
        """
        msg = self.format(record)
        self.emitter.log_signal.emit(msg)

    def append_log(self, msg):
        """
        Append a log message to the QTextEdit widget.

        Args:
            msg (str): The log message to append.
        """
        self.text_edit.append(msg)
        # Auto-scroll to the bottom
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )
