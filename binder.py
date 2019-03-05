from PySide2.QtWidgets import QTabWidget
from utilities.settings import G_QSETTINGS, Settings
from notebook import Notebook
from os import path, listdir


class Binder(QTabWidget):
    """ Binders are the root of the notebook workspace. Where each notebook is a file, binders are the folder those
    files are in. Binders display each notebook as a tab, and allow the user to add a new notebook. """

    def __init__(self):
        """ pass a workspace in order to load from a specific folder. Otherwise, the contents of configuration files
        will be checked (or registry, in ms windows), and environment variables to override those defaults """

        super().__init__()
        self.notebooks = []
        self.ids = set()
        self._just_loaded = False
        self.setTabPosition(self.West)
        self.setStyleSheet("""
        QTabWidget::tab-bar {
            top: 0;
        }
        """)

    def load_workspace(self):
        self._just_loaded = True
        for each in listdir(Settings.workspace_dir):
            if each.endswith(".fnbook"):
                notebook = Notebook.from_file(path.join(Settings.workspace_dir, each))
                self._add_notebook(notebook)
        if len(self.notebooks) == 0:
            # Append a starting notebook, for now, since there's no way to add notebooks yet
            notebook = Notebook("My Notebook")
            self._add_notebook(notebook)

    def _add_notebook(self, book: Notebook):
        self.addTab(book, book.id)
        self.notebooks.append(book)
        self.ids.add(book.id)

    def save(self):
        if self._just_loaded:
            self._just_loaded = False
            return
        G_QSETTINGS.sync()
        for each in self.notebooks:
            filename = path.join(Settings.workspace_dir, "notebook-{}.fnbook".format(each.id))
            each.save(filename)
