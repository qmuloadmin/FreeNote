""" Widgets for displaying interfaces into formatting text: Bold, size and color """

from PySide2.QtWidgets import QHBoxLayout, QPushButton, QWidget, QLabel, QLineEdit, QColorDialog
from PySide2.QtGui import QIcon, QKeySequence, QColor
from PySide2.QtCore import Signal, QObject, Qt
from style_consants import *


class FormatSignaller(QObject):
    bolded = Signal()
    italicized = Signal()
    underlined = Signal()
    struckthrough = Signal()
    justified = Signal(Qt.Alignment)
    sized = Signal(float)
    feedback_sized = Signal(float)
    foreground_colored = Signal(QColor)
    background_colored = Signal(QColor)


G_FORMAT_SIGNALLER = FormatSignaller()


class TextFormatButton(QPushButton):

    def __init__(self, text: str, icon=None):
        if icon is not None:
            super().__init__(icon, "")
        else:
            super().__init__(text)
        self.setMaximumWidth(30)
        self.setContentsMargins(1, 1, 1, 1)

    @classmethod
    def fromTheme(cls, theme: str):
        icon = QIcon.fromTheme(theme)
        btn = cls("", icon)
        return btn


class TextFormatPalette(QWidget):
    """ The main container for text formatting options """

    def __init__(self, parent):
        super().__init__(parent)
        self.lo = QHBoxLayout(self)
        # Check here for icon names
        # https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html#names
        self.bold_button = TextFormatButton.fromTheme("format-text-bold")
        self.ital_button = TextFormatButton.fromTheme("format-text-italic")
        self.undl_button = TextFormatButton.fromTheme("format-text-underline")
        self.strk_button = TextFormatButton.fromTheme("format-text-strikethrough")
        self.just_left_button = TextFormatButton.fromTheme("format-justify-left")
        self.just_right_button = TextFormatButton.fromTheme("format-justify-right")
        self.just_center_button = TextFormatButton.fromTheme("format-justify-center")
        self.foregnd_button = TextFormatButton.fromTheme("format-text-color")
        self.current_fg_color = QColor.fromRgb(0x000)
        self.current_bg_color = QColor.fromRgb(0xfff)
        # TODO find or create a suitable paintbrush or highlight icon, cause this is ugly
        self.backgnd_button = TextFormatButton.fromTheme("format-text-color")
        self.backgnd_button.setStyleSheet("""
            background-color: {};        
        """.format(EDIT_TEXT_FOCUS_BG))
        self.foregnd_select_button = TextFormatButton("")
        self.foregnd_select_button.setStyleSheet("""
            background-color: {};
        """.format(DEFAULT_ITEM_TEXT_COLOR))
        self.foregnd_select_button.setMaximumWidth(10)
        self.backgnd_select_button = QPushButton("▼")
        self.backgnd_select_button.setMaximumWidth(12)

        # Configure font size input
        self.size_label = QLabel("Font Size:")
        self.size_label.setMaximumWidth(80)
        self.size_input = QLineEdit("12")
        # Only accept sizes up to 3 digits, plus one after the decimal
        # TODO update this to a validator so its less clunky to use
        self.size_input.setInputMask("09.0")
        self.size_input.setMaximumWidth(40)

        # Setup short cuts for common text format operations
        self.bold_button.setShortcut(QKeySequence.Bold)
        self.ital_button.setShortcut(QKeySequence.Italic)
        self.undl_button.setShortcut(QKeySequence.Underline)

        # Setup slots for each format operation
        self.bold_button.pressed.connect(G_FORMAT_SIGNALLER.bolded.emit)
        self.ital_button.pressed.connect(G_FORMAT_SIGNALLER.italicized.emit)
        self.undl_button.pressed.connect(G_FORMAT_SIGNALLER.underlined.emit)
        self.strk_button.pressed.connect(G_FORMAT_SIGNALLER.struckthrough.emit)
        self.just_right_button.pressed.connect(self._justify_right)
        self.just_center_button.pressed.connect(self._justify_center)
        self.just_left_button.pressed.connect(self._justify_left)
        self.size_input.editingFinished.connect(self._update_font_size)
        G_FORMAT_SIGNALLER.feedback_sized.connect(self._feedback_font_size)
        self.foregnd_select_button.pressed.connect(self._select_fg_color)
        self.backgnd_select_button.pressed.connect(self._select_bg_color)
        self.foregnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.foreground_colored.emit(self.current_fg_color))
        self.backgnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.background_colored.emit(self.current_bg_color))

        # Add all the widgets to the layout
        self.lo.addWidget(self.bold_button)
        self.lo.addWidget(self.ital_button)
        self.lo.addWidget(self.undl_button)
        self.lo.addWidget(self.strk_button)
        self.lo.addSpacing(30)
        self.lo.addWidget(self.foregnd_button)
        self.lo.addWidget(self.foregnd_select_button)
        self.lo.addWidget(self.backgnd_button)
        self.lo.addWidget(self.backgnd_select_button)
        self.lo.addSpacing(30)
        self.lo.addWidget(self.just_left_button)
        self.lo.addWidget(self.just_center_button)
        self.lo.addWidget(self.just_right_button)
        self.lo.addSpacing(30)
        self.lo.addWidget(self.size_label)
        self.lo.addWidget(self.size_input)
        self.lo.setAlignment(Qt.AlignLeft)
        self.setLayout(self.lo)

    @staticmethod
    def _justify_center():
        G_FORMAT_SIGNALLER.justified.emit(Qt.AlignCenter)

    @staticmethod
    def _justify_right():
        G_FORMAT_SIGNALLER.justified.emit(Qt.AlignRight)

    @staticmethod
    def _justify_left():
        G_FORMAT_SIGNALLER.justified.emit(Qt.AlignLeft)

    def _update_font_size(self):
        value = float(self.size_input.text())
        G_FORMAT_SIGNALLER.sized.emit(value)

    def _feedback_font_size(self, size: int):
        self.size_input.setText(str(size))

    def _select_fg_color(self):
        color = QColorDialog.getColor()
        self.current_fg_color = color
        self.foregnd_select_button.setStyleSheet("background-color: {}".format(color.name()))

    def _select_bg_color(self):
        color = QColorDialog.getColor()
        self.current_bg_color = color
        self.backgnd_button.setStyleSheet("background-color: {}".format(color.name()))
    
