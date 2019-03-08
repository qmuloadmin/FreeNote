from PySide2.QtCore import QSettings

G_QSETTINGS = QSettings("Qmulosoft", "FreeNote")


class Settings:
    """ A struct holding globally significant settings """

    # The directory where the workspace is saved and should be loaded from
    workspace_dir = ""
    # If specified, the directory where art assets (usually images/videos) for the workspace should be saved
    asset_dir = ""
    # the directory where the application itself (python scripts, icons, etc) resides
    application_dir = ""
    # the subdirectory of application dir where icon assets can be found
    icon_dir = "icons"
    # the fallback theme name for icons if the system doesn't provide one
    fallback_theme_name = "breeze"
