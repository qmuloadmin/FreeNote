#! /usr/bin/env python3

import sys
from PySide2.QtWidgets import QWidget, QMessageBox, QApplication, QFileDialog, QVBoxLayout
from binder import Binder
from text_format_palette import TextFormatPalette
from utilities.settings import Settings, G_QSETTINGS
from utilities.debounce import g_save_debouncer
from os import environ, path


class MainWindow(QWidget):

    def __init__(self, workspace=None):
        super().__init__()
        # Initialize settings first
        # Set the workspace, if not provided
        if workspace is None:
            if "FREENOTE_WORKSPACE_DIR" in environ:
                workspace = environ["FREENOTE_WORKSPACE_DIR"]
            else:
                workspace = G_QSETTINGS.value("workspace/dir", "")
        Settings.workspace_dir = workspace
        # Validate the workspace

        self.lo = QVBoxLayout()
        self.format_bar = TextFormatPalette(self)
        self.binder = Binder()
        self.lo.setMargin(0)
        self.lo.setSpacing(2)
        g_save_debouncer.action = self.binder.save

    def _set_workspace_from_dialog(self, dir: str):
        Settings.workspace_dir = dir
        G_QSETTINGS.setValue("workspace/dir", dir)
        self._show_layout()

    def _show_layout(self):
        self.binder.load_workspace()
        self.lo.addWidget(self.format_bar)
        self.lo.addWidget(self.binder)
        self.setLayout(self.lo)

    def show(self):
        super().show()
        if not path.isdir(Settings.workspace_dir):
            input = QMessageBox(self).question(self, "FreeNote Workspace",
                                               "No FreeNote Workspace was found. Would you like to create one now?",
                                               QMessageBox.Yes, QMessageBox.No)
            if input == QMessageBox.No:
                raise ValueError("no valid FreeNote workspace found")
            else:
                form = QFileDialog(self, "Select a FreeNote Workspace directory")
                form.setFileMode(form.DirectoryOnly)
                form.setDirectory(".")
                form.fileSelected.connect(self._set_workspace_from_dialog)
                form.open()
        else:
            self._show_layout()


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Free Note")
    window = MainWindow()
    window.resize(1000, 800)
    window.show()

    sys.exit(app.exec_())
