from PySide2 import QtWidgets
from .mixins import CustomSettingsWidgetMixin


class Password(str, CustomSettingsWidgetMixin):
    """ A wrapper around str to provide a different settings widget """

    @staticmethod
    def _settings_widget_factory(value, parent):
        le = QtWidgets.QLineEdit(str(value), parent)
        le.setEchoMode(QtWidgets.QLineEdit.Password)
        return le
