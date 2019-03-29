from style_consants import *
from PySide2 import QtWidgets, QtGui, QtCore
from utilities.save_mixin import SaveMixin
from utilities.debounce import Debouncer
from text_format_palette import G_FORMAT_SIGNALLER
from threading import Timer
from image_page_item import PageImageItem
from utilities.rename_dialog import RenameableMixin
from utilities.settings import settings


class PageItem(SaveMixin, QtWidgets.QWidget, RenameableMixin):
    """ Surrounds every EditText or Image widget so it can be dragged and dropped and resized.
     Can be either text (default) or an image (if `img` is provided, which should be a URL).
     Set height_from_width when providing an image to scale the height of the entire widget from
     the width of the image. (Mostly useful when instantiating from a new image, as opposed to from a file) """

    # raised and lowered indicate that the item has been brought to front or sent to back
    raised = QtCore.Signal(int)
    lowered = QtCore.Signal(int)
    geometry_changed = QtCore.Signal(QtWidgets.QWidget)

    _unique_resource_name = "Item"

    def __init__(self, id: str, pos: QtCore.QRect, *content_args, img="", height_from_width=False):
        super().__init__()
        # satisfy RenameableMixin abstract property
        self.id = id
        self._lo = QtWidgets.QVBoxLayout()
        self._lo.setMargin(0)
        self.z_index = 0
        self._header = PageItemHeader(id)
        self._header.setAlignment(QtCore.Qt.AlignCenter)
        # if img was provided, don't set the content as text, but as a label
        if img != "":
            self._contents = PageImageItem(self, img, pos.width(), *content_args)
            if height_from_width:
                # Make the widget big enough to contain the image
                pos.setHeight(self._contents.height + self._non_content_height())
            try:
                # Let the user customize how often a resize of the image is done when resizing the item container
                timeout = settings.img_resize_interval
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

    def convert_contents(self, new_type: str):
        if new_type == "code":
            text = self._contents.toHtml()
            self._lo.removeWidget(self._contents)
            self._contents.deleteLater()
            self._contents = PageCodeEditItem(text)
            self._lo.insertWidget(1, self._contents)
            self._type = new_type
            self._contents.textChanged.connect(self._set_html_contents)

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

    def _try_rename(self, name: str, *args) -> bool:
        """ check with the parent if we can use the new name. This implementation is kinda hacky. TODO fix """
        success = self.parent().rename_item(self, name)
        if success:
            self._header.setText(self.id)
        return success

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
            item = cls(id, pos, data['contents']['asset_name'], img=data['contents']['url'])
            item._contents.asset_name = data['contents']['asset_name']
        else:
            item = cls(id, pos)
            item._contents.setHtml(data['contents']['value'])
            if data['contents']['type'] != 'text':
                item.convert_contents(data['contents']['type'])

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
        elif self._type == "code":
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


class PageTextContent(QtWidgets.QTextEdit, SaveMixin):
    """ Super class of all text-based item types."""
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

    @staticmethod
    def active_item():
        PageTextContent._active_item.setFocus()
        return PageTextContent._active_item

    @staticmethod
    def set_active_item(v):
        PageTextContent._active_item = v

    def focusInEvent(self, e: QtGui.QFocusEvent):
        super().focusInEvent(e)
        # If this widget is pending deletion and we click it again, cancel deletion
        if self.delete_timer.is_alive():
            self.delete_timer.cancel()
        self.set_active_item(self)
        self._connect_format_signals()
        # Update the global text formatter with our current font size
        G_FORMAT_SIGNALLER.active_font_changed.emit(self.get_format().font())

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        super().mousePressEvent(e)
        G_FORMAT_SIGNALLER.active_font_changed.emit(self.get_format().font())  # in case we selected different text
        e.accept()  # Don't propagate the click even to parent (don't want to show two context menus)

    def focusOutEvent(self, e: QtGui.QFocusEvent):
        """ If the text widget loses focus and has no text, delete it"""
        super().focusOutEvent(e)
        if self.toPlainText() == "":
            self.delete_timer = Timer(5, self.parent().deleteLater)
            self.delete_timer.start()

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

    @classmethod
    def bold_text(cls):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        f = cls.active_item().get_format()
        if f.fontWeight() == 75:
            f.setFontWeight(50)
        else:
            f.setFontWeight(75)
        cls.active_item().set_format(f)

    @classmethod
    def italicize_text(cls):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        f = cls.active_item().get_format()
        if f.fontItalic():
            f.setFontItalic(False)
        else:
            f.setFontItalic(True)
        cls.active_item().set_format(f)

    @classmethod
    def underline_text(cls):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        f = cls.active_item().get_format()
        if f.underlineStyle() == QtGui.QTextCharFormat.NoUnderline:
            f.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)
        else:
            f.setUnderlineStyle(QtGui.QTextCharFormat.NoUnderline)
        cls.active_item().set_format(f)

    @classmethod
    def strikethrough_text(cls):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        f = cls.active_item().get_format()
        if f.fontStrikeOut():
            f.setFontStrikeOut(False)
        else:
            f.setFontStrikeOut(True)
        cls.active_item().set_format(f)

    @classmethod
    def resize_text(cls, size: float):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        f = cls.active_item().get_format()
        font = f.font()
        font.setPointSize(size)
        f.setFont(font)
        cls.active_item().set_format(f)

    @classmethod
    def justify_text(cls, alignment):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        item = cls.active_item()
        item.setAlignment(alignment)

    @classmethod
    def color_text(cls, color: QtGui.QColor):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        brush = QtGui.QBrush(color)
        f = cls.active_item().get_format()
        f.setForeground(brush)
        cls.active_item().set_format(f)

    @classmethod
    def color_text_bg(cls, color: QtGui.QColor):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        brush = QtGui.QBrush(color)
        f = cls.active_item().get_format()
        f.setBackground(brush)
        cls.active_item().set_format(f)

    @classmethod
    def format_text_family(cls, family: str):
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        fmt = cls.active_item().get_format()
        font = fmt.font()
        font.setFamily(family)
        fmt.setFont(font)
        cls.active_item().set_format(fmt)

    @classmethod
    def bullet_text(cls):
        """ convert selected text into a bulletted list. Or, if no text selected, start a new bulleted list """
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        l_format = QtGui.QTextListFormat()
        l_format.setStyle(l_format.ListDisc)
        cls.active_item().convert_to_list(l_format)

    @classmethod
    def number_text(cls):
        """ start a numbered list. Numbered technically just means ordered, so sub-lists could be alpha or roman """
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        l_format = QtGui.QTextListFormat()
        l_format.setStyle(l_format.ListDecimal)
        cls.active_item().convert_to_list(l_format)

    @classmethod
    def format_text_code(cls):
        """ Change the parent's contents to this item's contents as a code item """
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return
        cls.active_item().parent().convert_contents("code")

    @classmethod
    def insert_checkbox(cls):
        """ convert this text content into a check box item """
        if cls.active_item().__class__ != cls:  # Don't process signals to items that aren't us
            return


class PageTextEdit(PageTextContent):
    """ Rich text content, for displaying a wide variety of text styles """

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
        G_FORMAT_SIGNALLER.code_formatted.connect(cls.format_text_code)
        G_FORMAT_SIGNALLER.family_formatted.connect(cls.format_text_family)
        G_FORMAT_SIGNALLER.bulleted.connect(cls.bullet_text)
        G_FORMAT_SIGNALLER.numbered.connect(cls.number_text)
        G_FORMAT_SIGNALLER.checkbox_inserted.connect(cls.insert_checkbox)

    def convert_to_list(self, format: QtGui.QTextListFormat):
        # TODO support automatic nested lists converting formats as needed (numerals to alpha to roman, etc)
        cursor = self.textCursor()
        if cursor.selectedText() != "":
            cursor.createList(format)
        else:
            cursor.insertList(format)


class PageCodeEditItem(PageTextContent):
    """ For displaying text as source code, strict monospacing, standard color schemes and indentation """

    def __init__(self, initial_text: str):
        super().__init__(initial_text)
        self.setStyleSheet("""
                    PageCodeEditItem {{
                        background-color: {};
                        border: 1px solid {};
                    }}
                    PageCodeEditItem::focus {{
                        background-color: {};
                    }}
                    """.format(EDIT_CODE_BG, ITEM_BORDER_COLOR, EDIT_CODE_FOCUS_BG)
        )

        cursor = self.textCursor()
        self.selectAll()
        self.setFontFamily(settings.code_font)
        self.setTextCursor(cursor)
        font = self.font()
        # set tab stop to be no stupidly huge like the default. Unfortunately, this is global for the TextEdit
        # so there might be merit (including in some special bg/color formatting) to making code a discrete TextEdit
        tab_stop = settings.tabstop
        self.setTabStopWidth(tab_stop * QtGui.QFontMetrics(font).width(" "))

    def set_format(self, fmt: QtGui.QTextCharFormat):
        cur = self.textCursor()
        self.selectAll()
        self.setCurrentCharFormat(fmt)
        self.setTextCursor(cur)
        tab_stop = settings.tabstop
        self.setTabStopWidth(tab_stop * QtGui.QFontMetrics(fmt.font()).width(" "))

    @classmethod
    def _connect_format_signals(cls):
        if cls._connected:
            return
        cls._connected = True
        G_FORMAT_SIGNALLER.sized.connect(cls.resize_text)


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
