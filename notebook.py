from PySide2.QtWidgets import QTabWidget, QWidget
from section import Section
from yaml import load, dump
from utilities.toaster import ToasterMixin
from string import ascii_uppercase


class Notebook(QTabWidget, ToasterMixin):
    """ Notebooks hold sections, which hold pages. They are part of a binder, the root of the workspace. Each notebook
     is its own file """

    def __init__(self, id="My Notebook", sections=[]):
        super().__init__()
        self.sections = []
        self.ids = set()
        self.toasted.connect(self.toast)
        self.setTabPosition(self.West)
        self.setTabsClosable(True)
        self.id = id
        self.tabBar().addTab("New Section")
        self.tabBar().tabBarClicked.connect(self._check_handle_new_section)
        self.tabCloseRequested.connect(self._remove_section)
        for each in sections:
            self._add_section(each)

    def _check_handle_new_section(self, index: int):
        """ Called whenever a tab is clicked, to check if the New Section tab was clicked and handle that, if so """
        if index == len(self.sections):
            id = self._next_id()
            section = Section(id)
            self._add_section(section)
            self.setCurrentIndex(len(self.sections) - 1)

    def _remove_section(self, index: int):
        if index == len(self.sections):
            # Don't do anything on requests that aren't actual sections (like the New Section tab)
            return
        self.removeTab(index)
        section = self.sections.pop(index)
        self.ids.remove(section.id)

    def _add_section(self, section: Section):
        self.tabBar().removeTab(len(self.sections))
        self.sections.append(section)
        self.ids.add(section.id)
        self.addTab(section, section.id)
        self.tabBar().addTab("New Section")

    def addTab(self, widget: QWidget, id: str):
        id = id[8:]
        super().addTab(widget, id)

    def _next_id(self, prefix="section", start="A"):
        if "{}-{}".format(prefix, start) not in self.ids:
            return "{}-{}".format(prefix, start)
        i = 1
        while "{}-{}".format(prefix, ascii_uppercase[i]) in self.ids:
            i += 1
        return "{}-{}".format(prefix, ascii_uppercase[i])

    @classmethod
    def from_file(cls, filename: str):
        with open(filename) as f:
            data = load(f)
        sections = []
        new_id = data["id"]
        for id, each in data["sections"].items():
            section = Section.unmarshal(id, each)
            sections.append(section)
        notebook = cls(new_id, sections)
        return notebook

    def save(self, filename: str):
        self.toasted.emit("Saving...")
        data = {
            "id": self.id,
            "sections": {}
        }
        for each in self.sections:
            data["sections"][each.id] = each.marshal()
        with open(filename, "w") as f:
            dump(data, f)
