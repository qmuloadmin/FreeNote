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


class TextFormatPalette(QWidget):
    """ The main container for text formatting options """

    def __init__(self, parent):
        super().__init__(parent)
        self.lo = QHBoxLayout(self)
        # Check here for icon names
        # https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html#names
        # TODO all these have some shared properties... break them out into a sub class
        self.bold_button = QPushButton(QIcon.fromTheme("format-text-bold"), "")
        self.bold_button.setMaximumWidth(30)
        self.ital_button = QPushButton(QIcon.fromTheme("format-text-italic"), "")
        self.ital_button.setMaximumWidth(30)
        self.undl_button = QPushButton(QIcon.fromTheme("format-text-underline"), "")
        self.undl_button.setMaximumWidth(30)
        self.strk_button = QPushButton(QIcon.fromTheme("format-text-strikethrough"), "")
        self.strk_button.setMaximumWidth(30)
        self.just_left_button = QPushButton(QIcon.fromTheme("format-justify-left"), "")
        self.just_left_button.setMaximumWidth(30)
        self.just_right_button = QPushButton(QIcon.fromTheme("format-justify-right"), "")
        self.just_right_button.setMaximumWidth(30)
        self.just_center_button = QPushButton(QIcon.fromTheme("format-justify-center"), "")
        self.just_center_button.setMaximumWidth(30)
        self.foregnd_button = QPushButton("A")
        self.foregnd_button.setMaximumWidth(30)
        self.current_fg_color = QColor.fromRgb(0x000)
        self.current_bg_color = QColor.fromRgb(0xfff)
        self.backgnd_button = QPushButton("A")
        self.backgnd_button.setMaximumWidth(30)
        self.backgnd_button.setStyleSheet("""
            background-color: {};        
        """.format(EDIT_TEXT_FOCUS_BG))
        # TODO Figure out how to make these select buttons be long-press variants of the fg/bg buttons
        self.foregnd_select_button = QPushButton("...")
        self.foregnd_select_button.setMaximumWidth(30)
        self.backgnd_select_button = QPushButton("...")
        self.backgnd_select_button.setMaximumWidth(30)

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

    def _spawn_color_dialog(self, color: QColor) -> QColorDialog:
        cd = QColorDialog(self.current_bg_color)
        cd.setParent(self.parent())
        cd.show()
        return cd

    def _select_bg_color(self):
        cd = self._spawn_color_dialog(self.current_bg_color)
        cd.colorSelected.connect(self._selected_bg_color)

    def _selected_bg_color(self, color: QColor):
        self.current_bg_color = color
        self.backgnd_button.setStyleSheet("background-color: {}".format(color.name()))

    def _select_fg_color(self):
        cd = self._spawn_color_dialog(self.current_fg_color)
        cd.colorSelected.connect(self._selected_fg_color)

    def _selected_fg_color(self, color: QColor):
        self.current_fg_color = color
        self.foregnd_button.setStyleSheet("color: {}".format(color.name()))
