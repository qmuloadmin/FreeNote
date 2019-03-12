""" Widgets for displaying interfaces into formatting text: Bold, size and color """

from PySide2.QtWidgets import QPushButton, QToolBar, QLabel, QLineEdit, QColorDialog, QAction
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


class TextFormatPalette(QToolBar):
    """ The main container for text formatting options """

    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("""
        QToolBar {
            spacing: 5px;
        }
        QToolBar::separator {
        }
        """)
        # Check here for icon names
        # https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html#names
        self._bold_action = QIcon.fromTheme("format-text-bold")
        self.addAction(self._bold_action, "bold").setShortcut(QKeySequence.Bold)
        self._ital_action = QIcon.fromTheme("format-text-italic")
        self.addAction(self._ital_action, "italic").setShortcut(QKeySequence.Italic)
        self._under_action = QIcon.fromTheme("format-text-underline")
        self.addAction(self._under_action, "underline").setShortcut(QKeySequence.Underline)
        self._strk_action = QIcon.fromTheme("format-text-strikethrough")
        self.addAction(self._strk_action, "strikethrough")
        self.addSeparator()
        self._justl_action = QIcon.fromTheme("format-justify-left")
        self.addAction(self._justl_action, "left")
        self._justr_action = QIcon.fromTheme("format-justify-right")
        self.addAction(self._justr_action, "right")
        self._justc_action = QIcon.fromTheme("format-justify-center")
        self.addAction(self._justc_action, "center")
        self.addSeparator()

        self.current_fg_color = QColor.fromRgb(0x000)
        self.current_bg_color = QColor.fromRgb(0xfff)
        self.foregnd_button = QPushButton(QIcon.fromTheme("format-text-color"), "")
        self.addWidget(self.foregnd_button)
        # TODO find or create a suitable paintbrush or highlight icon, cause this is ugly
        self.backgnd_button = QPushButton(QIcon.fromTheme("format-text-color"), "")
        self.backgnd_button.setStyleSheet("""
            background-color: {};        
        """.format(EDIT_TEXT_FOCUS_BG))
        self.foregnd_select_button = QPushButton("")
        self.foregnd_select_button.setStyleSheet("""
            background-color: {};
        """.format(DEFAULT_ITEM_TEXT_COLOR))
        self.addWidget(self.foregnd_select_button)
        self.foregnd_select_button.setMaximumWidth(10)
        self.backgnd_select_button = QPushButton("▼")
        self.addWidget(self.backgnd_button)
        self.backgnd_select_button.setMaximumWidth(15)
        self.addWidget(self.backgnd_select_button)
        self.addSeparator()

        # Configure font size input
        self.size_label = QLabel("Font Size:")
        self.size_label.setMaximumWidth(80)
        self.addWidget(self.size_label)
        self.size_input = QLineEdit("12")
        # Only accept sizes up to 3 digits, plus one after the decimal
        # TODO update this to a validator so its less clunky to use
        self.size_input.setInputMask("09.0")
        self.size_input.setMaximumWidth(40)
        self.addWidget(self.size_input)

        # connect signals
        self.actionTriggered.connect(self._dispatch_event)
        self.foregnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.foreground_colored.emit(self.current_fg_color))
        self.backgnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.background_colored.emit(self.current_bg_color))
        self.foregnd_select_button.pressed.connect(self._select_fg_color)
        self.backgnd_select_button.pressed.connect(self._select_bg_color)
        G_FORMAT_SIGNALLER.feedback_sized.connect(self._feedback_font_size)
        self.size_input.returnPressed.connect(self._update_font_size)

    def _dispatch_event(self, action: QAction):
        action = action.text()
        if action == "bold":
            G_FORMAT_SIGNALLER.bolded.emit()
        elif action == "italic":
            G_FORMAT_SIGNALLER.italicized.emit()
        elif action == "underline":
            G_FORMAT_SIGNALLER.underlined.emit()
        elif action == "strikethrough":
            G_FORMAT_SIGNALLER.struckthrough.emit()
        elif action == "right":
            self._justify_right()
        elif action == "left":
            self._justify_left()
        elif action == "center":
            self._justify_center()

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
    
