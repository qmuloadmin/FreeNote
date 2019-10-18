""" Widgets for displaying interfaces into formatting text: Bold, size and color """

from PySide2.QtWidgets import QPushButton, QToolBar, QLabel, QLineEdit, QColorDialog, QAction, QComboBox, QWidget, QHBoxLayout
from PySide2.QtGui import QIcon, QKeySequence, QColor, QFontDatabase, QFont, QValidator
from PySide2.QtCore import Signal, QObject, Qt, QSize


class FormatSignaller(QObject):
    bolded = Signal()
    italicized = Signal()
    underlined = Signal()
    struckthrough = Signal()
    justified = Signal(Qt.Alignment)
    sized = Signal(float)
    # below emitted when a text box is selected with a different active font
    active_font_changed = Signal(QFont)
    foreground_colored = Signal(QColor)
    background_colored = Signal(QColor)
    code_formatted = Signal()
    family_formatted = Signal(str)
    bulleted = Signal()
    numbered = Signal()
    checkbox_inserted = Signal()


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
        self._justc_action = QIcon.fromTheme("format-justify-center")
        self.addAction(self._justc_action, "center")
        self._justr_action = QIcon.fromTheme("format-justify-right")
        self.addAction(self._justr_action, "right")
        self.addSeparator()

        self._bullet_action = QIcon.fromTheme("format-list-unordered")
        self.addAction(self._bullet_action, "bullet")
        self._number_action = QIcon.fromTheme("format-list-ordered")
        self.addAction(self._number_action, "numbered")
        self.addSeparator()
        # the following convert regular text items into special text items
        self._code_action = QIcon.fromTheme("format-text-code")
        self.addAction(self._code_action, "source code")
        self._check_action = QIcon.fromTheme("checkbox")
        self.addAction(self._check_action, "check")
        self.addSeparator()

        self.current_fg_color = QColor.fromRgb(0x000000)
        self.current_bg_color = QColor.fromRgb(0xffffff)
        self.foregnd_button = FontColorButton(QIcon.fromTheme("format-text-color"), "set text color")
        self.foregnd_button.set_color_display(self.current_fg_color)
        self.addWidget(self.foregnd_button)
        self.backgnd_button = FontColorButton(QIcon.fromTheme("color-fill"), "set text highlight color")
        self.backgnd_button.set_color_display(self.current_bg_color)
        self.foregnd_select_button = QPushButton(QIcon.fromTheme("color-management"), "")
        self.foregnd_select_button.setToolTip("Select a new text foreground color")
        self.addWidget(self.foregnd_select_button)
        self.foregnd_select_button.setMaximumWidth(30)
        self.backgnd_select_button = QPushButton(QIcon.fromTheme("color-management"), "")
        self.backgnd_select_button.setToolTip("Select a new text highlight color")
        self.addWidget(self.backgnd_button)
        self.backgnd_select_button.setMaximumWidth(30)
        self.addWidget(self.backgnd_select_button)
        self.addSeparator()

        # Configure font family and size input
        self.family_label = QLabel("Font")
        self.family_label.setMaximumWidth(40)
        self.addWidget(self.family_label)
        self.family_menu = QComboBox()
        self.family_menu.setMaximumWidth(180)
        self._fonts = {}  # dict for fast lookups
        for i, each in enumerate(QFontDatabase().families()):
            font = self.family_menu.font()
            font.setFamily(each)
            font.setPointSize(12)
            self.family_menu.addItem(each)
            self._fonts[each] = i
            self.family_menu.setItemData(i, font, Qt.FontRole)
        self.addWidget(self.family_menu)
        self.size_label = QLabel("Size")
        self.size_label.setMaximumWidth(40)
        self.addWidget(self.size_label)
        self.size_input = QLineEdit("12")
        self.size_input.setValidator(FontSizeValidator())
        self.size_input.setMaximumWidth(40)
        self.addWidget(self.size_input)

        # connect signals
        self.actionTriggered.connect(self._dispatch_event)
        self.foregnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.foreground_colored.emit(self.current_fg_color))
        self.backgnd_button.pressed.connect(lambda: G_FORMAT_SIGNALLER.background_colored.emit(self.current_bg_color))
        self.foregnd_select_button.pressed.connect(self._select_fg_color)
        self.backgnd_select_button.pressed.connect(self._select_bg_color)
        G_FORMAT_SIGNALLER.active_font_changed.connect(self._feedback_font_size)
        self.size_input.returnPressed.connect(self._update_font_size)
        self.family_menu.activated[str].connect(lambda x: G_FORMAT_SIGNALLER.family_formatted.emit(x))

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
        elif action == "source code":
            G_FORMAT_SIGNALLER.code_formatted.emit()
        elif action == "bullet":
            G_FORMAT_SIGNALLER.bulleted.emit()
        elif action == "numbered":
            G_FORMAT_SIGNALLER.numbered.emit()
        elif action == "check":
            G_FORMAT_SIGNALLER.checkbox_inserted.emit()

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

    def _feedback_font_size(self, font: QFont):
        size = font.pointSize()
        self.size_input.setText(str(size))
        family = font.family()
        if family in self._fonts:
            self.family_menu.setCurrentIndex(self._fonts[family])

    def _select_fg_color(self):
        color = QColorDialog.getColor()
        self.current_fg_color = color
        self.foregnd_button.set_color_display(color)

    def _select_bg_color(self):
        color = QColorDialog.getColor()
        self.current_bg_color = color
        self.backgnd_button.set_color_display(color)


class FontSizeValidator(QValidator):

    def validate(self, contents: str, index: int):
        if contents.isnumeric():
            return self.Acceptable
        parts = contents.split(".")
        if len(parts) == 2:
            if parts[0].isnumeric() and parts[1].isnumeric():
                return self.Acceptable
            if parts[0] == "":
                return self.Invalid
            if parts[0].isnumeric() and parts[1] == "":
                return self.Acceptable
        return self.Invalid


class FontColorButton(QPushButton):
    """ Displays the currently selected color and provides an icon for indicating what is being colored """

    def __init__(self, icon: QIcon, s: str):
        super().__init__()
        self._lo = QHBoxLayout()
        self._filler = QToolBar()
        self._filler.addAction(icon, s)
        self._filler.setMaximumHeight(25)
        self._filler.setMaximumWidth(25)
        self._filler.setStyleSheet("""
            QWidget {
                border: 0px
            }
        """)
        self._filler.actionTriggered.connect(lambda _: self.pressed.emit())
        self._lo.addWidget(self._filler)
        self._lo.setSpacing(0)
        self.setMaximumWidth(40)
        self._color_display = QLabel("")
        self._color_display.setMinimumWidth(8)
        self._lo.addWidget(self._color_display)
        self.setLayout(self._lo)
        self._lo.setMargin(3)

    def set_color_display(self, color: QColor):
        self._color_display.setStyleSheet("border-radius: 2px; background-color: {};".format(color.name()))
