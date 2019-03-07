from style_consants import *
from PySide2 import QtWidgets, QtGui, QtCore
from utilities.save_mixin import SaveMixin
from utilities.debounce import Debouncer
from utilities.settings import Settings
from text_format_palette import G_FORMAT_SIGNALLER
from threading import Timer
from urllib.request import urlopen
from os.path import join, exists
from os import remove, chdir, getcwd


class PageItem(SaveMixin, QtWidgets.QWidget):
    """ Surrounds every EditText or Image widget so it can be dragged and dropped and resized.
     Can be either text (default) or an image (if `img` is provided, which should be a URL).
     Set height_from_width when providing an image to scale the height of the entire widget from
     the width of the image. (Mostly useful when instantiating from a new image, as opposed to from a file) """

    # raised and lowered indicate that the item has been brought to front or sent to back
    raised = QtCore.Signal(int)
    lowered = QtCore.Signal(int)

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
            self._contents = QtWidgets.QLabel()
            # asset URLs, when they are local files, are relative paths, are relative, not absolute
            # for portability reasons. When we are restoring from a saved state. So, we should
            # set our working directory to the asset directory
            # URLs for files dragged in should be absolute anyway and not affected.
            old_wd = getcwd()
            chdir(Settings.asset_dir)
            data = urlopen(img).read()
            chdir(old_wd)

            orig_pixmap = QtGui.QPixmap()
            orig_pixmap.loadFromData(data)
            pixmap = orig_pixmap.scaledToWidth(pos.width())

            # orig pixmap is an asset that gets saved to disk
            self.orig_pixmap = orig_pixmap

            if height_from_width:
                # Make the widget big enough to contain the image
                pos.setHeight(pixmap.height() + self._non_content_height())
            self._contents.setPixmap(pixmap)
            self._resize_debouncer = Debouncer(timeout=0.25)
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

    def setGeometry(self, pos: QtCore.QRect):
        super().setGeometry(pos)
        if self._type == "image":
            self._resize_debouncer.start()
        if self.parent() is not None:
            self.parent().edge_check(self)

    def _resize_image(self):
        width = self.geometry().width()
        pixmap = self.orig_pixmap
        pixmap = pixmap.scaledToWidth(width)
        self._contents.setPixmap(pixmap)

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
        else:
            item = cls(id, pos)
            item._contents.setHtml(data['contents']['value'])
        return item

    def _save_asset(self):
        """ If there is an asset, save it if it hasn't been saved, yet """
        if self._type == "image" and not exists(self.asset_file_fq):
            self.orig_pixmap.save(self.asset_file_fq, "PNG")  # TODO support GIFs

    def _delete_asset(self):
        """ If there is an asset, delete it """
        if self._type == "image":
            try:
                remove(self.asset_file_fq)
            except FileNotFoundError:
                """ Do nothing """

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
            self._save_asset()
            url = QtCore.QUrl.fromLocalFile(self.asset_file)
            contents["url"] = url.url()
        return {
            "geometry": geometry,
            "contents": contents,
        }

    @property
    def asset_file(self):
        return "{}-{}-{}.fna".format(
            self.parent().section.id,
            self.parent().id,
            self.id
        )

    @property
    def asset_file_fq(self):
        return join(Settings.asset_dir, self.asset_file)

    def deleteLater(self):
        self._delete_asset()
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


class PageItemHeader(PageItemSurround):
    """ A target for drag start events, as well as right click dialog menu """

    def __init__(self, s: str):
        super().__init__(s, "border: 1px solid {}; border-radius: 3px;".format(ITEM_BORDER_COLOR))

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        # TODO make this offset part more accurate and less hacky
        if ev.button() == QtCore.Qt.LeftButton:
            self.parent().drag_offset = ev.globalPos() - self.parent().mapToGlobal(self.pos())
            self.parent().setMouseTracking(True)
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
            close_option.triggered.connect(self._remove)
            raise_option = QtWidgets.QAction("Bring To Front", dialog)
            raise_option.triggered.connect(lambda: self.parent().raised.emit(self.parent().z_index))
            lower_option = QtWidgets.QAction("Send To Back", dialog)
            lower_option.triggered.connect(lambda: self.parent().lowered.emit(self.parent().z_index))
            cancel_option = QtWidgets.QAction("Cancel", dialog)
            dialog.addAction(close_option)
            dialog.addAction(raise_option)
            dialog.addAction(lower_option)
            dialog.addAction(cancel_option)
            dialog.triggered.connect(lambda _: dialog.deleteLater())
            dialog.popup(ev.pos())

        ev.accept()

    def _remove(self):
        self.parent().deleteLater()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        self.parent().setMouseTracking(False)
        ev.accept()


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
