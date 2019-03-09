from PySide2.QtCore import QSettings

G_QSETTINGS = QSettings("Qmulosoft", "FreeNote")


class Settings:
    """ A struct holding globally significant settings that are used in more than one place, and are calculated
     at runtime. For instance, workspace_dir can be overridden with an ENV var. """

    # The directory where the workspace is saved and should be loaded from
    workspace_dir = ""
    # If specified, the directory where art assets (usually images/videos) for the workspace should be saved
    asset_dir = ""
    # the directory where the application itself (python scripts, icons, etc) resides
    application_dir = ""
    # the fallback theme name for icons if the system doesn't provide one
    fallback_theme_name = "breeze"
