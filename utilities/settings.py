from PySide2.QtCore import QSettings
from typing import Callable, Any

G_QSETTINGS = QSettings("Qmulosoft", "FreeNote")


class Setting:
    """ Stores the meta data (and in the case of overridden values, the value itself) of various settings so they can be
    read at runtime from the QSettings file/registry key. The meta data provides necessary information to build a
    settings UI component automatically as settings are added """

    def __init__(self):
        self.type = None
        self.key = ""
        self.description = ""
        self.value = None
        self.name = ""


def setting(key: str, type_: Callable, default=None):
    """ A decorator to turn a class field into a singleton, with getter and setter properties built automatically """
    setting = Setting()
    setting.key = key
    setting.type = type_
    setting.value = None

    def decorator(f):
        setting.description = f.__doc__
        setting.name = f.__name__

        @property
        def prop(self):
            # Store this in the settings class instance so the meta data can be read
            if f.__name__ not in self.settings:
                self.settings[f.__name__] = setting
            if setting.value is not None:
                return setting.value
            val = G_QSETTINGS.value(setting.key, default)
            if val is not None:
                # Little hack to make ints (which are stored as strings) correctly cast to bools
                if setting.type == bool:
                    val = int(val)
                return setting.type(val)
            return None

        @prop.setter
        def prop(_, v):
            G_QSETTINGS.setValue(setting.key, v)
        return prop
    return decorator


class _Settings:
    """ A class holding globally significant settings that affect application behavior. Pulls and updates values in
     QStorage automatically, and allows for overridden values to be set at runtime """

    def __init__(self):
        self.settings = dict()

    def override(self, prop: str, value: Any):
        """ given a particular property by name, override the local value to not read from setting store.
        NOTE: minimize usage as it becomes difficult to maintain string values """
        if prop in self.settings:
            self.settings[prop].value = value
        else:
            raise KeyError("Property {} does not exist in settings".format(prop))

    def __getitem__(self, item):
        return self.settings[item]

    def keys(self):
        return self.settings.keys()

    @setting("workspace/dir", str)
    def workspace_dir(self):
        """ The directory where the notebooks and asset files for the running application should saved and loaded"""

    @setting("workspace/assets/dir", str)
    def asset_dir(self):
        """ If specified, the directory where art assets (usually images/videos) for the workspace should be saved """

    @setting("application/autosave", bool, True)
    def auto_save(self):
        """ Turn on or off the application auto save functionality"""

    @setting("application/icons/path", str)
    def icon_path(self):
        """ The path where icon themes should be loaded from. This should usually be left empty unless you know what you're doing. """

    @setting("application/maximum_tab_display_len", int, 16)
    def tab_text_length(self):
        """ The maximum number of characters shown in a section, page, notebook tab before being truncated """

    @setting("application/interval_image_resize", float, 0.05)
    def img_resize_interval(self):
        """ The number of seconds (may be a fraction of a second) of respite during resizing for images to re-render """

    @setting("code/tabstop", int, 4)
    def tabstop(self):
        """ The number of spaces, visually, to indent code widgets in place of tab character """

    @setting("restore/window/height", int, 800)
    def window_height(self):
        """ keys starting with restore/ should be omitted form settings dialog as they are just restoring last state """

    @setting("restore/window/width", int, 1000)
    def window_width(self):
        """ the last width of the application window on close """

    @setting("code/font", str, "DejaVu Sans Mono")
    def code_font(self):
        """ The font family to use to display code in code items """

    # the directory where the application itself (python scripts, icons, etc) resides. Does not store to file
    application_dir = ""
    # the fallback theme name for icons if the system doesn't provide one. Does not store to file
    fallback_theme_name = "breeze"


settings = _Settings()
