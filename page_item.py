from style_consants import *
from PySide2 import QtWidgets, QtGui, QtCore
from utilities.save_mixin import SaveMixin
from utilities.debounce import Debouncer
from text_format_palette import G_FORMAT_SIGNALLER
from threading import Timer
from image_page_item import PageImageItem
from utilities.settings import G_QSETTINGS


class PageItem(SaveMixin, QtWidgets.QWidget):
    """ Surrounds every EditText or Image widget so it can be dragged and dropped and resized.
     Can be either text (default) or an image (if `img` is provided, which should be a URL).
     Set height_from_width when providing an image to scale the height of the entire widget from
     the width of the image. (Mostly useful when instantiating from a new image, as opposed to from a file) """

    # raised and lowered indicate that the item has been brought to front or sent to back
    raised = QtCore.Signal(int)
    lowered = QtCore.Signal(int)
    geometry_changed = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self, id: str, pos: QtCore.QRect, img="", height_from_width=False):
        super().__init__()
        self.id = id
        self._lo = QtWidgets.QVBoxLayout()
        self._lo.setMargin(0)
        self.z_index = 0
        self._header = PageItemHeader(id)
        self._header.setAlignment(QtCore.Qt.AlignCenter)
        # if img was provided, don't set the content as text, but as a label
        if img != "":
            self._contents = PageImageItem(self, img, pos.width())
            if height_from_width:
                # Make the widget big enough to contain the image
                pos.setHeight(self._contents.height + self._non_content_height())
            try:
                # Let the user customize how often a resize of the image is done when resizing the item container
                timeout = int(G_QSETTINGS.value("application/interval_image_resize", "0.05"))
            except ValueError:
                timeout = 0.05
            self._resize_debouncer = Debouncer(timeout=timeout)
            self._resize_debouncer.action = self._resize_image
            self._type = "image"
        else:
            self._contents = PageTextEdit()
            self._html_contents = ""  # stores item contents in a thread-safe way for saving
            self._contents.textChanged.connect(self._set_html_contents)
            self._type = "text"

        self._resizeArrow = PageItemResizeLabel()
        self._resizeArrow.setAlignment(QtCore.Qt.AlignRight)
        self._lo.addWidget(self._header)
        self._lo.addWidget(self._contents)
        self._lo.addWidget(self._resizeArrow)
        self._lo.setSpacing(0)
        self.setLayout(self._lo)
        self.setGeometry(pos)
        self._connect_signals()

    @property
    def page(self):
        return self.parent()

    def _set_html_contents(self):
        """ stores the contents of the inner text edit widget in the main thread """
        # this means all text is duplicated in memory. Should find a safer way to save that can access
        # the toHTML() method safely without causing whatever races condition causes it to crash
        self._html_contents = self._contents.toHtml()

    def _non_content_height(self) -> int:
        """ The vertical space occupied by things other than the content (header, footer) """
        return 30  # TODO make it calculated, not hardcoded

    def setFocus(self):
        self._contents.setFocus()

    def _try_rename(self, name: str) -> bool:
        """ check with the parent if we can use the new name. This implementation is kinda hacky. TODO fix """
        return self.parent().rename_item(self, name)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent):
        if not self.hasMouseTracking():
            # don't accept propagated events
            return
        pos = self.geometry()
        width = pos.width()
        height = pos.height()
        map = self.parent().mapFromGlobal(ev.globalPos() - self.drag_offset)
        pos.setX(map.x())
        pos.setY(map.y())
        pos.setWidth(width)
        pos.setHeight(height)
        self.setGeometry(pos)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._rename_dialog()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self.setMouseTracking(False)
        event.accept()

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == QtCore.Qt.LeftButton:
            self.drag_offset = ev.globalPos() - self.parent().mapToGlobal(self.pos())
            self.setMouseTracking(True)
            ev.accept()
        elif ev.button() == QtCore.Qt.RightButton:
            """Open context dialog"""
            dialog = QtWidgets.QMenu("Actions")
            dialog.setParent(self.parent())
            dialog.setStyleSheet("""
            QMenu {{
                background-color: {};
            }}
            QMenu::item {{
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {};
                color: {};
            }}
            """.format(PAGE_ITEM_MENU_BG, PAGE_ITEM_MENU_SELECTED, DEFAULT_ITEM_TEXT_COLOR))
            close_option = QtWidgets.QAction("Remove", dialog)
            close_option.setStatusTip("Delete this text box and all its contents")
            close_option.triggered.connect(self.deleteLater)
            raise_option = QtWidgets.QAction("Bring To Front", dialog)
            # Using parent() (and especially parent().parent()) is extremely fragile.
            # TODO make more clear cut ways of retrieving the element we want
            raise_option.triggered.connect(lambda: self.raised.emit(self.z_index))
            lower_option = QtWidgets.QAction("Send To Back", dialog)
            lower_option.triggered.connect(lambda: self.lowered.emit(self.z_index))
            rename_option = QtWidgets.QAction("Rename", dialog)
            rename_option.triggered.connect(self._rename_dialog)
            cancel_option = QtWidgets.QAction("Cancel", dialog)
            dialog.addAction(close_option)
            dialog.addAction(raise_option)
            dialog.addAction(lower_option)
            dialog.addAction(rename_option)
            dialog.addSeparator()
            dialog.addAction(cancel_option)
            dialog.triggered.connect(lambda _: dialog.deleteLater())
            pos = self.mapToGlobal(ev.pos())
            dialog.popup(self.parent().parent().mapFromGlobal(pos))
            ev.accept()

    def _rename_dialog(self):
        new_id, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Item",
            "New name for this item",
            QtWidgets.QLineEdit.Normal,
            self.id
        )
        if ok:
            result = self._try_rename(new_id)
            if not result:
                msg = QtWidgets.QMessageBox(self)
                msg.setWindowTitle("Name Taken")
                msg.setText("Another item on this page already has that name.")
                msg.show()
            else:
                self._header.setText(self.id)

    def setGeometry(self, pos: QtCore.QRect):
        super().setGeometry(pos)
        if self._type == "image":
            self._resize_debouncer.start()
        if self.parent() is not None:
            self.geometry_changed.emit(self)

    def _resize_image(self):
        width = self.geometry().width()
        self._contents.resize(width)

    @classmethod
    def unmarshall(cls, id: str, data: dict):
        pos = QtCore.QRect()
        geo = data["geometry"]
        pos.setX(geo[0])
        pos.setY(geo[1])
        pos.setWidth(geo[2])
        pos.setHeight(geo[3])
        if data['contents']['type'] == "image":
            item = cls(id, pos, img=data['contents']['url'])
            item._contents.asset_name = str(data['contents']['asset_name'])
        else:
            item = cls(id, pos)
            item._contents.setHtml(data['contents']['value'])
        return item

    def marshal(self) -> dict:
        """ marshal should return the content necessary to later restore this widget from a file """
        # TODO should probably make this a formal type
        geometry = (
            self.geometry().x(),
            self.geometry().y(),
            self.geometry().width(),
            self.geometry().height()
        )
        contents = {
            "type": self._type,
        }
        if self._type == "text":
            contents["value"] = self._html_contents
        elif self._type == "image":
            # Write assets to a file, then generate a url from it
            self._contents.save_asset()
            url = QtCore.QUrl.fromLocalFile(self._contents.asset_file)
            contents["url"] = url.url()
            contents["asset_name"] = self._contents.asset_name
        return {
            "geometry": geometry,
            "contents": contents,
        }

    def deleteLater(self):
        if self._type == "image":
            self._contents.delete_asset()
        self.parent().delete_item(self.z_index)
        super().deleteLater()


class PageTextEdit(QtWidgets.QTextEdit, SaveMixin):

    # _active_item tracks, statically, which Item currently has focus. This is for receiving text format signals
    # from the global text formatter.
    _active_item = None
    _connected = False

    def __init__(self, initial_text=""):
        super().__init__(initial_text)
        self.delete_timer = Timer(5, self.deleteLater)
        self.setStyleSheet("""
        QTextEdit {{
            background-color: transparent;
            border: 1px dotted {};
        }}
        QTextEdit::focus {{
            background-color: {};
        }}
        """.format(ITEM_BORDER_COLOR, EDIT_TEXT_FOCUS_BG))
        self._connect_signals()

    @classmethod
    def active_item(cls):
        cls._active_item.setFocus()
        return cls._active_item

    @classmethod
    def set_active_item(cls, v):
        cls._active_item = v

    @classmethod
    def _connect_format_signals(cls):
        if cls._connected:
            return
        cls._connected = True
        G_FORMAT_SIGNALLER.underlined.connect(cls.underline_text)
        G_FORMAT_SIGNALLER.bolded.connect(cls.bold_text)
        G_FORMAT_SIGNALLER.italicized.connect(cls.italicize_text)
        G_FORMAT_SIGNALLER.struckthrough.connect(cls.strikethrough_text)
        G_FORMAT_SIGNALLER.sized.connect(cls.resize_text)
        G_FORMAT_SIGNALLER.justified.connect(cls.justify_text)
        G_FORMAT_SIGNALLER.background_colored.connect(cls.color_text_bg)
        G_FORMAT_SIGNALLER.foreground_colored.connect(cls.color_text)

    def focusInEvent(self, e: QtGui.QFocusEvent):
        super().focusInEvent(e)
        # If this widget is pending deletion and we click it again, cancel deletion
        if self.delete_timer.is_alive():
            self.delete_timer.cancel()
        self.set_active_item(self)
        self._connect_format_signals()
        # Update the global text formatter with our current font size
        G_FORMAT_SIGNALLER.feedback_sized.emit(self.get_format().font().pointSize())

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        super().mousePressEvent(e)
        e.accept()  # Don't propagate the click even to parent (don't want to show two context menus)

    def focusOutEvent(self, e: QtGui.QFocusEvent):
        """ If the text widget loses focus and has no text, delete it"""
        super().focusOutEvent(e)
        if self.toPlainText() == "":
            self.delete_timer = Timer(5, self.parent().deleteLater)
            self.delete_timer.start()

    @classmethod
    def bold_text(cls):
        f = cls.active_item().get_format()
        if f.fontWeight() == 75:
            f.setFontWeight(50)
        else:
            f.setFontWeight(75)
        cls.active_item().set_format(f)

    @classmethod
    def italicize_text(cls):
        f = cls.active_item().get_format()
        if f.fontItalic():
            f.setFontItalic(False)
        else:
            f.setFontItalic(True)
        cls.active_item().set_format(f)

    @classmethod
    def underline_text(cls):
        f = cls.active_item().get_format()
        if f.underlineStyle() == QtGui.QTextCharFormat.NoUnderline:
            f.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)
        else:
            f.setUnderlineStyle(QtGui.QTextCharFormat.NoUnderline)
        cls.active_item().set_format(f)

    @classmethod
    def strikethrough_text(cls):
        f = cls.active_item().get_format()
        if f.fontStrikeOut():
            f.setFontStrikeOut(False)
        else:
            f.setFontStrikeOut(True)
        cls.active_item().set_format(f)

    @classmethod
    def resize_text(cls, size: float):
        f = cls.active_item().get_format()
        font = f.font()
        font.setPointSize(size)
        f.setFont(font)
        cls.active_item().set_format(f)

    @classmethod
    def justify_text(cls, alignment):
        item = cls.active_item()
        item.setAlignment(alignment)

    @classmethod
    def color_text(cls, color: QtGui.QColor):
        brush = QtGui.QBrush(color)
        f = cls.active_item().get_format()
        f.setForeground(brush)
        cls.active_item().set_format(f)

    @classmethod
    def color_text_bg(cls, color: QtGui.QColor):
        brush = QtGui.QBrush(color)
        f = cls.active_item().get_format()
        f.setBackground(brush)
        cls.active_item().set_format(f)

    def get_format(self) -> QtGui.QTextCharFormat:
        cursor = self.textCursor()
        if cursor.selectedText() != "":
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start, QtGui.QTextCursor.MoveAnchor)
            cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
            return cursor.charFormat()
        return self.currentCharFormat()

    def set_format(self, fmt: QtGui.QTextCharFormat):
        cursor = self.textCursor()
        if cursor.selectedText() != "":
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start, QtGui.QTextCursor.MoveAnchor)
            cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt)
        else:
            self.setCurrentCharFormat(fmt)


class PageItemSurround(QtWidgets.QLabel):
    def __init__(self, s: str, additional_style=""):
        super().__init__(s)
        self.opacityEffect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setMaximumHeight(15)
        self.opacityEffect.setProperty("opacity", 0)
        self.setStyleSheet("background-color: transparent;" + additional_style)
        self.setGraphicsEffect(self.opacityEffect)

    def enterEvent(self, event: QtCore.QEvent):
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.SizeAllCursor)
        self.opacityEffect.setProperty("opacity", 0.7)

    def leaveEvent(self, event: QtCore.QEvent):
        QtGui.QGuiApplication.setOverrideCursor(QtCore.Qt.ArrowCursor)
        self.opacityEffect.setProperty("opacity", 0)


class PageItemHeader(SaveMixin, PageItemSurround):
    """ A target for drag start events, as well as right click dialog menu """

    def __init__(self, s: str):
        super().__init__(s, "border: 1px solid {}; border-radius: 3px;".format(ITEM_BORDER_COLOR))

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        ev.ignore()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        event.ignore()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        ev.ignore()


class PageItemResizeLabel(PageItemSurround):

    def __init__(self):
        super().__init__("⇲")
        self.last_pos = None

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.last_pos = ev.globalPos()
        self.setMouseTracking(True)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        self.setMouseTracking(False)
        self.last_pos = None

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent):
        if self.last_pos is None:
            return
        travel_x = ev.globalPos().x() - self.last_pos.x()
        travel_y = ev.globalPos().y() - self.last_pos.y()
        self.last_pos = ev.globalPos()
        pos = self.parent().geometry()
        pos.setWidth(pos.width() + travel_x)
        pos.setHeight(pos.height() + travel_y)
        self.parent().setGeometry(pos)
