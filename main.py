#!/usr/bin/python3
import sys
from main_window import CMainWindow 
from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = CMainWindow()
    app.exec()

