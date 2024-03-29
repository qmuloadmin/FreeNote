from PySide6 import QtWidgets, QtGui, QtCore
from utilities.debounce import Debouncer
from page_item import PageItem
from threading import Timer


class Page(QtWidgets.QWidget):
    """ Page is a single, infinitely scrolling, drag and drop target-able page in the notebook """

    def __init__(self, id="1"):
        super().__init__()
        self.id = id
        self.ids = set()
        self._section = None
        self._scroll_area = None
        # NOTE: order of items is SIGNIFICANT. Do not arbitrarily adjust it, without updating child item's z_index
        self.items = []
        # debouncing for resizing (shrinking) purposes
        self.size_debouncer = Debouncer(self._size_timer, timeout=0.5)
        self.size_debouncer.start()
        # these max variables store the farthest items for resizing based on item geometry
        self.bottom_max = None
        self.right_max = None
        self.setAcceptDrops(True)

    @property
    def scroll_area(self):
        return self._scroll_area

    @scroll_area.setter
    def scroll_area(self, v):
        self._scroll_area = v

    @property
    def section(self):
        return self._section

    @section.setter
    def section(self, value):
        self._section = value

    def _size_timer(self):
        return Timer(0.5, self._eval_resize)

    def _raise_item(self, index):
        """ Slot for listening to child item's raised signals. Handles reordering of the list of items """
        item = self.items.pop(index)
        self.items.append(item)
        for i, each in enumerate(self.items):
            each.z_index = i
        item.raise_()

    def _lower_item(self, index):
        """ Slot for listening to child item's lowered signals. Handles reordering of the list of items """
        item = self.items.pop(index)
        self.items.insert(0, item)
        for i, each in enumerate(self.items):
            each.z_index = i
        item.lower()

    def _eval_resize(self):
        """ Called to re-evaluate what the right-most and bottom-most items are based on their geometries, and
        shrink to fit them """
        pos = self.geometry()
        # If there are no items, resize to the size of the parent
        if len(self.items) == 0:
            pos.setHeight(self.section.height())
            pos.setWidth(self.section.width())
            self.setGeometry(pos)
            return

        self.bottom_max = self.items[0]
        self.right_max = self.items[0]

        for item in self.items:
            if item.geometry().right() > self.right_max.geometry().right():
                self.right_max = item
            if item.geometry().bottom() > self.bottom_max.geometry().bottom():
                self.bottom_max = item

        if self.bottom_max.geometry().bottom() < self.scroll_area.viewport().height():
            pos.setHeight(self.scroll_area.viewport().height())
        else:
            pos.setHeight(self.bottom_max.geometry().bottom())

        if self.right_max.geometry().right() < self.scroll_area.viewport().width():
            pos.setWidth(self.scroll_area.viewport().width())
        else:
            pos.setWidth(self.right_max.geometry().right())
        self.setGeometry(pos)

    def rename_item(self, item, name: str) -> bool:
        """ check to see if the suggested new id is available or not """
        if name in self.ids:
            return False
        else:
            self.ids.add(name)
            self.ids.remove(item.id)
            item.id = name
        return True

    def marshal(self):
        data = {
            "items": {},
            "geometry": (self.geometry().width(), self.geometry().height()),
        }
        for each in self.items:
            data["items"][each.id] = each.marshal()
        return data

    @classmethod
    def unmarshal(cls, id: str, data: {}):
        page = cls(id)
        pos = page.geometry()
        pos.setWidth(data["geometry"][0])
        pos.setHeight(data["geometry"][1])
        page.setGeometry(pos)
        for id, each in data['items'].items():
            item = PageItem.unmarshall(id, each)
            page._add_item(item)
        return page

    def _edge_check(self, item: PageItem):
        """ Called when a PageItem is moved, sending it's new right-most point and bottom-most point """
        # TODO make this support top left corner detection for infinite scrolling in both directions (more complicated)
        pos = self.geometry()
        right = item.geometry().right()
        bottom = item.geometry().bottom()
        if right > pos.width():
            pos.setWidth(right)
            self.right_max = item
        elif self.right_max == item:
            # The element being moved right now was the previous right-most element. Check if it still is
            self.size_debouncer.start()

        if bottom > pos.height():
            pos.setHeight(bottom)
            self.bottom_max = item
        elif self.bottom_max == item:
            self.size_debouncer.start()
        # TODO don't bother setting if there's no change (or is this already checked downstream?)
        self.setGeometry(pos)

    def _add_item(self, item: PageItem):
        self.ids.add(item.id)
        self.items.append(item)
        item.setParent(self)
        item.show()
        item.setFocus()
        item.z_index = len(self.items) - 1  # MUST start at zero for proper behavior of self._raise_item
        item.raised.connect(self._raise_item)
        item.lowered.connect(self._lower_item)
        item.geometry_changed.connect(self._edge_check)

    def dropEvent(self, event: QtGui.QDropEvent):
        super().dropEvent(event)
        if event.mimeData().hasFormat("text/uri-list"):
            pos = QtCore.QRect()
            pos.setX(int(event.pos().x()))
            pos.setY(int(event.pos().y()))
            pos.setWidth(200)  # TODO find a better way to set default width
            db = QtCore.QMimeDatabase()
            if "image" in db.mimeTypeForUrl(event.mimeData().urls()[0]).name():
                image = event.mimeData().urls()[0].url()
                id = self._next_id("Image")
                item = PageItem(id, pos, img=image, height_from_width=True)
                self._add_item(item)
            elif "application/octet-stream" in db.mimeTypeForUrl(event.mimeData().urls()[0]).name():
                # If it's a stream, we need to download it. However, that could be arbitrarily huge
                # For now, we're going to base the decision on the file extension.
                url = event.mimeData().urls()[0].url()
                if url.endswith(".png") or url.endswith(".jpg") or url.endswith(".jpeg") or url.endswith(".gif"):
                    id = self._next_id("Image")
                    item = PageItem(id, pos, img=url, height_from_width=True)
                    self._add_item(item)

        event.accept()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        pos = QtCore.QRect()
        pos.setX(int(event.localPos().x()))
        pos.setY(int(event.localPos().y()))
        pos.setHeight(100)
        pos.setWidth(400)
        id = self._next_id("Text Box")
        item = PageItem(id, pos)
        self._add_item(item)
        event.accept()

    def _next_id(self, prefix: str) -> str:
        if prefix not in self.ids:
            return prefix
        i = 1
        while "{} {}".format(prefix, i) in self.ids:
            i += 1
        return "{} {}".format(prefix, i)

    def delete_item(self, i: int):
        item = self.items.pop(i)
        self.ids.remove(item.id)
        for i, each in enumerate(self.items):
            each.z_index = i
