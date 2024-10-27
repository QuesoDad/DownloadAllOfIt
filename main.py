# main_v4.py

import sys
from PyQt5 import QtWidgets
from gui_interface import YTDownloadApp

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    gui = YTDownloadApp()
    gui.show()
    sys.exit(app.exec_())
