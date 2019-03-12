from PySide2.QtWidgets import QTabWidget
from utilities.settings import G_QSETTINGS, Settings
from utilities.rename_dialog import RenameableMixin
from notebook import Notebook
from os import path, listdir, rename
from style_consants import TAB_PANE_BORDER_COLOR


class Binder(QTabWidget, RenameableMixin):
    """ Binders are the root of the notebook workspace. Where each notebook is a file, binders are the folder those
    files are in. Binders display each notebook as a tab, and allow the user to add a new notebook. """

    _unique_resource_name = "notebook"

    def __init__(self):
        """ pass a workspace in order to load from a specific folder. Otherwise, the contents of configuration files
        will be checked (or registry, in ms windows), and environment variables to override those defaults """
        super().__init__()
        self.notebooks = []
        self.ids = set()
        self._just_loaded = False
        self.setTabPosition(self.West)
        self.tabBarDoubleClicked.connect(self._rename_dialog)
        self.setStyleSheet("""
        QTabWidget::pane {{
            border: 0px;
            border-top: 1px solid {};
        }}
        QTabWidget::tab-bar {{
            top: 0;
        }}
        """.format(TAB_PANE_BORDER_COLOR))

    def _try_rename(self, new_id: str, *args):
        index = args[0]
        if index > len(self.notebooks):
            return True
        if new_id not in self.ids:
            notebook = self.notebooks[index]
            self.ids.remove(notebook.id)
            rename(
                path.join(Settings.workspace_dir, "notebook-{}.fnbook".format(notebook.id)),
                path.join(Settings.workspace_dir, "notebook-{}.fnbook".format(new_id))
            )
            self.ids.add(new_id)
            notebook.id = new_id
            self.setTabText(index, new_id)
            return True
        return False

    def load_workspace(self):
        self._just_loaded = True
        for each in listdir(Settings.workspace_dir):
            if each.endswith(".fnbook"):
                notebook = Notebook.from_file(path.join(Settings.workspace_dir, each))
                self._add_notebook(notebook)
        if len(self.notebooks) == 0:
            # Append a starting notebook
            notebook = Notebook("My Notebook")
            self._add_notebook(notebook)

    def _add_notebook(self, book: Notebook):
        self.addTab(book, book.id)
        self.notebooks.append(book)
        self.ids.add(book.id)

    def new_notebook(self, name: str) -> bool:
        """ Try to create a new notebook with name. If the name already exists, return False"""
        if name in self.ids:
            return False
        nb = Notebook(name)
        self._add_notebook(nb)
        return True

    def save(self):
        if self._just_loaded:
            self._just_loaded = False
            return
        G_QSETTINGS.sync()
        for each in self.notebooks:
            filename = path.join(Settings.workspace_dir, "notebook-{}.fnbook".format(each.id))
            each.save(filename)
