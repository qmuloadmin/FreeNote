from PySide2.QtCore import QSettings

G_QSETTINGS = QSettings("Qmulosoft", "FreeNote")


class Settings:
    """ A struct holding globally significant settings """

    workspace_dir = ""
    asset_dir = ""
