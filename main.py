#! /usr/bin/env python3

import sys
from PySide2.QtWidgets import QWidget, QMessageBox, QApplication, QFileDialog, QVBoxLayout, QMainWindow
from PySide2.QtGui import QIcon
from binder import Binder
from text_format_palette import TextFormatPalette
from utilities.settings import Settings, G_QSETTINGS
from utilities.debounce import g_save_debouncer
from os import environ, path


class ContentWidget(QWidget):
    """ The main, central widget for the QMainWindow. Most widgets are a child of this one. """

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
        Settings.asset_dir = G_QSETTINGS.value("workspace/asset_path", Settings.workspace_dir)

        # Set the currently running application's directory, for convenience
        Settings.application_dir = __file__.replace("main.py", "")
        icon_dir = G_QSETTINGS.value("application/icon_path", path.join(Settings.application_dir, "icons"))

        # Initialize QIcon search paths and themes
        search_paths = QIcon.themeSearchPaths()
        search_paths.append(icon_dir)
        QIcon.setThemeSearchPaths(search_paths)
        if QIcon.themeName() == "":
            QIcon.setThemeName(Settings.fallback_theme_name)

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
    window = ContentWidget()
    window.resize(1000, 800)
    window.show()

    sys.exit(app.exec_())
