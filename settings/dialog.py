from PySide2 import QtWidgets, QtGui, QtCore
from . import settings
from .mixins import CustomSettingsWidgetMixin


class SettingsDialog(QtWidgets.QDialog):
    """ A container dialog for viewing and altering application settings """
    def __init__(self, parent):
        super().__init__(parent)
        self._lo = QtWidgets.QHBoxLayout()
        self._listview = QtWidgets.QListWidget(self)
        self._categories = dict()
        # Get the keys (e.g. application/autosave) and split out the category (e.g. application)
        # these are the different screens of settings for each category.
        for key in settings.keys():
            val = settings[key]
            key = val.key.split("/")[0]
            # Skip 'restore' key, as this is just for restoring the previous session and can't be edited
            if key == "restore":
                continue
            if key in self._categories:
                self._categories[key].append(val)
            else:
                self._categories[key] = [val]
        for category in self._categories:
            self._listview.addItem(category)
        self._lo.addWidget(self._listview)
        # Render the first, currently selected settings when the dialog opens
        self._listview.setCurrentRow(0)
        current = self._listview.currentItem()
        self._listview.currentRowChanged.connect(self._change_category)
        self._selected_settings = CategorySettings(self, self._categories[current.text()])
        self._lo.addWidget(self._selected_settings)
        self.setLayout(self._lo)

    def _change_category(self, index: int):
        """ called whenever an item in the menu is selected to change settings categories """
        list_item = self._listview.item(index)
        self._listview.setCurrentItem(list_item)
        self._lo.removeWidget(self._selected_settings)
        self._selected_settings.deleteLater()
        self._selected_settings = CategorySettings(self, self._categories[list_item.text()])
        self._lo.addWidget(self._selected_settings)


class CategorySettings(QtWidgets.QWidget):

    def __init__(self, parent, sets: list):
        super().__init__(parent)
        self._lo = QtWidgets.QVBoxLayout(self)
        for setting in sets:
            row = QtWidgets.QWidget(self)
            row.setLayout(QtWidgets.QHBoxLayout(row))
            row.layout().setAlignment(QtCore.Qt.AlignLeft)
            name = QtWidgets.QLabel(setting.name)
            icon = QtGui.QIcon.fromTheme("help-about")
            info = QtWidgets.QLabel()
            info.setPixmap(icon.pixmap(12, 12))
            info.setToolTip(setting.description)
            if issubclass(setting.type, CustomSettingsWidgetMixin):
                value = setting.type.settings_widget(getattr(settings, setting.name), self)
                value.editingFinished.connect(lambda setting=setting, value=value: self._update_setting(setting.name, value.text()))
            elif setting.type == str or setting.type == int or setting.type == float:
                value = QtWidgets.QLineEdit(str(getattr(settings, setting.name)), self)
                value.editingFinished.connect(lambda setting=setting, value=value: self._update_setting(setting.name, value.text()))
            elif setting.type == bool:
                value = QtWidgets.QCheckBox(self)
                value.setChecked(getattr(settings, setting.name))
                value.stateChanged.connect(lambda state, setting=setting: self._update_setting(setting.name, state))
            row.layout().addWidget(name)
            row.layout().addWidget(info)
            row.layout().addWidget(value)
            self._lo.addWidget(row)
        self.setLayout(self._lo)

    @staticmethod
    def _update_setting(setting, value):
        setattr(settings, setting, value)
