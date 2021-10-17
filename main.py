#! /usr/bin/env python3

import sys
from PySide6.QtWidgets import QWidget, QMessageBox, QApplication, QFileDialog, QVBoxLayout, QMainWindow, QMenu
from PySide6.QtWidgets import QInputDialog, QLineEdit
from PySide6.QtGui import QIcon, QCloseEvent, QAction
from binder import Binder
from text_format_palette import TextFormatPalette
from settings.dialog import SettingsDialog
from settings.__init__ import settings
from utilities.debounce import g_save_debouncer
from os import environ, path


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._content = ContentWidget(self)
        self.addToolBar(TextFormatPalette(self))
        self.setCentralWidget(self._content)
        self.menuBar().addMenu(self._file_menu)
        self.menuBar().addMenu(QMenu("Edit", self))
        self.menuBar().addMenu(QMenu("Tools", self))
        self.menuBar().addMenu(self._help_menu)
        self.menuBar().triggered.connect(self._menu_dispatch)

    @property
    def _file_menu(self):
        # TODO turn these into constants or dictionary of names mapped to functions to call on click
        menu = QMenu("&File", self)
        menu.addAction("New Notebook")
        menu.addAction("New...")  # TODO add support for creating new pages, sections, etc here.
        menu.addSeparator()
        menu.addAction("&Save")
        menu.addSeparator()
        menu.addAction("S&ettings")
        menu.addSeparator()
        menu.addAction("Exit")
        return menu

    @property
    def _help_menu(self):
        menu = QMenu("&Help")
        menu.addAction("About")
        return menu

    def _menu_dispatch(self, action: QAction):
        if action.text() == "Exit":
            self.close()
        elif action.text() == "&Save":
            self._content.binder.save()
        elif action.text() == "New Notebook":
            name, ok = QInputDialog.getText(
                self,
                "New Notebook",
                "New Notebook Name:",
                QLineEdit.Normal,
                ""
            )
            if ok:
                success = self._content.binder.new_notebook(name)
                if not success:
                    QMessageBox(self).warning(
                        self,
                        "Notebook Name Already Exists",
                        "Another notebook with the name {} already exists in your workspace.".format(name)
                    )
        elif action.text() == "About":
            QMessageBox.about(self, "FreeNote",
                              "Free Note is note taking software, developed by Zach Bullough. "
                              "For more information, please visit github.com/qmuloadmin/freenote")
        elif action.text() == "S&ettings":
            SettingsDialog(self).show()

    def show(self):
        super().show()
        if settings.workspace_dir is None:
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
            if "FREENOTE_WORKSPACE_DIR" in environ:
                self._content.show(environ["FREENOTE_WORKSPACE_DIR"])
            else:
                self._content.show()

    def _set_workspace_from_dialog(self, dir: str):
        settings.workspace_dir = dir
        self._content.show()

    def closeEvent(self, event: QCloseEvent):
        # catch before the window closes and store some settings to be restored on next run
        size = self.size()
        settings.window_height = size.height()
        settings.window_width = size.width()
        super().closeEvent(event)


class ContentWidget(QWidget):
    """ The main, central widget for the QMainWindow. Most widgets are a child of this one. """

    def __init__(self, parent):
        super().__init__(parent)
        self.lo = QVBoxLayout()
        self.binder = Binder()
        # Allow the user to disable auto save
        if settings.auto_save:
            g_save_debouncer.action = self.binder.save

    def _show_layout(self):
        self.binder.load_workspace()
        self.lo.addWidget(self.binder)
        self.setLayout(self.lo)

    def show(self, workspace=None):
        super().show()
        # Initialize settings first
        # Set the workspace, if not provided
        if workspace is not None:
            settings.override("workspace_dir", workspace)

        if settings.asset_dir is None:
            settings.override("asset_dir", settings.workspace_dir)

        # Set the currently running application's directory, for convenience
        settings.application_dir = __file__.replace("main.py", "")
        icon_dir = settings.icon_path
        if icon_dir is None:
            icon_dir = path.join(settings.application_dir, "icons")

        # Initialize QIcon search paths and themes
        search_paths = QIcon.themeSearchPaths()
        search_paths.append(icon_dir)
        QIcon.setThemeSearchPaths(search_paths)
        QIcon.setFallbackThemeName(settings.fallback_theme_name)
        self._show_layout()


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Free Note")
    window = MainWindow()
    window.resize(settings.window_width, settings.window_height)
    window.show()

    sys.exit(app.exec_())
