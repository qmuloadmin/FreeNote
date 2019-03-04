from PySide2.QtWidgets import QTabWidget, QWidget, QMessageBox, QApplication, QFileDialog
from utilities.settings import G_QSETTINGS, Settings
from notebook import Notebook
from os import environ, path, listdir
from utilities.save_mixin import just_loaded


class Binder(QTabWidget):
    """ Binders are the root of the notebook workspace. Where each notebook is a file, binders are the folder those
    files are in. Binders display each notebook as a tab, and allow the user to add a new notebook. """

    def __init__(self, workspace=None):
        """ pass a workspace in order to load from a specific folder. Otherwise, the contents of configuration files
        will be checked (or registry, in ms windows), and environment variables to override those defaults """

        super().__init__()
        self.notebooks = []
        self.ids = set()
        # Set the workspace, if not provided
        if workspace is None:
            if "FREENOTE_WORKSPACE_DIR" in environ:
                workspace = environ["FREENOTE_WORKSPACE_DIR"]
            else:
                workspace = G_QSETTINGS.value("workspace/dir", "")
        Settings.workspace_dir = workspace
        # Validate the workspace
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
        # Walk the workspace and create notebooks for each fnbook file in the workspace directory
        else:
            self._load_workspace()

        self.setTabPosition(self.West)

    def _set_workspace_from_dialog(self, dir: str):
        Settings.workspace_dir = dir
        G_QSETTINGS.setValue("workspace/dir", dir)
        self._load_workspace()

    def _load_workspace(self):
        for each in listdir(Settings.workspace_dir):
            if each.endswith(".fnbook"):
                notebook = Notebook.from_file(path.join(Settings.workspace_dir, each))
                self._add_notebook(notebook)

    def _add_notebook(self, book: Notebook):
        self.addTab(book, book.id)
        self.notebooks.append(book)
        self.ids.add(book.id)

    def save(self):
        global just_loaded
        if just_loaded:
            just_loaded = False
            return
        G_QSETTINGS.sync()
        for each in self.notebooks:
            filename = path.join(Settings.workspace_dir, "notebook-{}.fnbook".format(each.id))
            each.save(filename)
