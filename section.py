from PySide6 import QtWidgets, QtGui
from utilities.save_mixin import SaveMixin
from utilities.rename_dialog import RenameableMixin
from page import Page
from style_consants import *


class Section(QtWidgets.QTabWidget, SaveMixin, RenameableMixin):

    _unique_resource_name = "Page"

    def __init__(self, id: str, pages=[]):
        super().__init__()
        self.ids = set()
        self.id = id
        self.setTabPosition(self.East)
        self.pages = []
        self.tabCloseRequested.connect(self._remove_page)
        self.setTabsClosable(True)
        # TODO figure out why the ::tab styles below are being ignored
        self.setStyleSheet("""
        background-color: {};
        margin: 0px;
        QTabWidget::pane {{
            border-top: 0px;
            border-bottom: 0px;
            border-left: 0px;
            border-right: 1px solid black
        }}
        QTabBar::tab {{
            background-color: {};
            min-height: 12ex;
            padding: 2px;
            margin-top:-3px;
        }}
        """.format(PAGE_BG, PAGE_ITEM_MENU_BG))
        self._append_placeholder()
        for page in pages:
            self._add_page(page)

        self.tabBar().tabBarClicked.connect(self._check_handle_new_section)
        self.tabBarDoubleClicked.connect(self._rename_dialog)
        self._connect_signals()

    def _append_placeholder(self):
        self.tabBar().addTab("New Page")

    def _try_rename(self, new_id: str, *args) -> bool:
        index = args[0]
        if index == len(self.pages):
            return False  # TODO should really indicate that "new page" can't be renamed. Return true and do nothing?
        new_id = "page-" + new_id
        if new_id not in self.ids:
            page = self.pages[index]
            self.ids.remove(page.id)
            self.ids.add(new_id)
            page.id = new_id
            self.setTabText(index, new_id)
            return True
        return False

    def _check_handle_new_section(self, index: str):
        if index == len(self.pages):
            id = self._next_id()
            page = Page(id)
            i = self._add_page(page)
            self.setCurrentIndex(i)

    def _remove_page(self, index: int):
        self.removeTab(index)
        page = self.pages.pop(index)
        self.ids.remove(page.id)

    def _next_id(self, prefix="page", start="1"):
        if "{}-{}".format(prefix, start) not in self.ids:
            return "{}-{}".format(prefix, start)
        i = 1
        while "{}-{}".format(prefix, i) in self.ids:
            i += 1
        return "{}-{}".format(prefix, i)

    def _add_page(self, page: Page) -> int:
        self.tabBar().removeTab(len(self.pages))
        page.section = self
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidget(page)
        scroll.setStyleSheet("border: 0px;")
        page.scroll_area = scroll
        self.ids.add(page.id)
        self.pages.append(page)
        pos = page.geometry()
        pos.setWidth(self.width())
        pos.setHeight(self.height())
        page.setGeometry(pos)
        self._append_placeholder()
        return self.addTab(scroll, page.id)

    def transform_page(self, event: QtGui.QMouseEvent):
        """ Turns the current dummy page into a real page and adds a new dummy page tab """
        id = self._next_id()
        page = Page(id)
        self.removeTab(len(self.pages))
        index = self._add_page(page)
        self.setCurrentIndex(index)
        page.mousePressEvent(event)
        self._append_placeholder()

    # overridden methods to deal with using the id (which starts with page-) without displaying the prefix
    def addTab(self, w: QtWidgets.QWidget, id: str) -> int:
        return super().addTab(w, id[5:])

    def setTabText(self, index: int, text: str):
        super().setTabText(index, text[5:])

    @classmethod
    def unmarshal(cls, new_id: str, data: dict):
        pages = []
        for id, each in data["pages"].items():
            page = Page.unmarshal(id, each)
            pages.append(page)
        section = cls(new_id, pages)
        section.setCurrentIndex(len(section.pages) - 1)
        return section

    def marshal(self) -> dict:
        data = {
            "pages": {}
        }
        for page in self.pages:
            data["pages"][page.id] = page.marshal()
        return data
