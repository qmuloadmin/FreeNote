""" this mixin keeps track of when anything at all is changed and triggers the global save debouncer """

from utilities.debounce import g_save_debouncer
from PySide2 import QtCore


class SaveMixin:

    def setGeometry(self, pos: QtCore.QRect):
        super().setGeometry(pos)
        g_save_debouncer.start()

    def deleteLater(self):
        g_save_debouncer.start()
        super().deleteLater()

    def setText(self, text):
        g_save_debouncer.start()
        super().setText(text)

    def _connect_signals(self):
        try:
            self.textChanged.connect(g_save_debouncer.start)
        except AttributeError:
            """ Do nothing as this simply means this signal doesn't exist on the mixed in type """
        try:
            self.tabCloseRequested.connect(g_save_debouncer.start)
        except AttributeError:
            """ Do nothing """
        try:
            self.raised.connect(g_save_debouncer.start)
            self.lowered.connect(g_save_debouncer.start)
        except AttributeError:
            """ Do nothing """
