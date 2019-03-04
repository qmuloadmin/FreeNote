#! /usr/bin/env python3

import sys
from PySide2 import QtWidgets
from binder import Binder
from text_format_palette import TextFormatPalette
from utilities.debounce import g_save_debouncer


class MainWindow(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.lo = QtWidgets.QVBoxLayout()
        self.format_bar = TextFormatPalette(self)
        self.binder = Binder()
        self.lo.addWidget(self.format_bar)
        self.lo.addWidget(self.binder)
        self.lo.setMargin(0)
        self.lo.setSpacing(2)
        g_save_debouncer.action = self.binder.save

        self.setLayout(self.lo)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationName("Free Note")
    window = MainWindow()
    window.resize(1000, 800)
    window.show()

    sys.exit(app.exec_())
