""" MixIn for emitting toast messages """

from PySide6.QtCore import Signal
from utilities.debounce import Debouncer
from PySide6 import QtWidgets
from style_consants import *


class ToasterMixin:

    toasted = Signal(str)

    def toast(self, message: str):
        """ Used to display a short message for the user in an unobtrusive way (like status updates or warnings) """
        label = QtWidgets.QLabel(message)
        pos = label.geometry()
        label.setParent(self)
        label.setStyleSheet("background-color: {}".format(PAGE_BG))
        label.show()
        pos.setTop(self.geometry().height() - 20)
        pos.setLeft(self.geometry().width() - 100)
        pos.setWidth(100)
        pos.setHeight(20)
        # TODO make width and positioning based on number of characters
        label.setGeometry(pos)
        self.debouncer = Debouncer()
        self.debouncer.bounced.connect(label.deleteLater)
        self.debouncer.start()
