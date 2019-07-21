from PySide2.QtCore import QSettings
from typing import Callable, Any
from .password import Password
import subprocess
from os import getcwd, chdir


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
        self._validator = None

    def validate(self, value) -> bool:
        if self._validator is None:
            try:
                self.type(value)
            except ValueError as e:
                raise ValidationError(e)
            return True
        return self._validator(value)


def setting(key: str, type_: Callable, default=None, validate=None):
    """ A decorator to turn a class field into a singleton, with getter and setter properties built automatically
    Notes on usage, as this can be a bit confusing (but is hopefully worth it for how easy it is to add new settings):

    Using the global settings (_Settings) object, getting attributes will fetch the Setting.value,
        e.g. getattr(settings, 'foo') would return a string value if foo was defined like so:
        @setting('/settings/foo', str)
        def foo(self):
            ...
        as the type of foo is defined as str.
    Getting indexes (dict-style) will return the Setting object itself, so you can access attributes.
        e.g. settings['foo'].validate("some string")

    While this is confusing, attributes are rarely needed (only validation) externally, and being able to just get
    the value of a setting based on attribute lookup is extremely convenient.
    """
    setting = Setting()
    setting.key = key
    setting.type = type_
    setting.value = None
    if validate is not None:
        setting._validator = validate

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


def validate_enable_git(value: bool):
    """ Ensure that git is installed and initialize if set to True """
    if value:
        cwd = getcwd()
        chdir(settings.workspace_dir)
        try:
            with subprocess.Popen(["git", "init"], stderr=subprocess.PIPE) as git:
                _, stderr = git.communicate()
            if len(stderr) > 0:
                raise ValidationError("git failed to initialize. Error: {}".format(stderr))
        except FileNotFoundError:
            raise ValidationError("git wasn't found on your system; to enable git integration, please install git")
        chdir(cwd)
    return True


class _Settings:
    """ A class holding globally significant settings that affect application behavior. Pulls and updates values in
     QStorage automatically, and allows for overridden values to be set at runtime """

    def __init__(self):
        self.settings = dict()
        # initialize the settings dict by reading from each setting at initialization
        # TODO this is really hacky and we need a better solution
        for each in self.__dir__():
            getattr(self, each)

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

    @setting("application/autosave_interval", float, 3)
    def auto_save_interval(self):
        """  """

    @setting("application/icons/path", str)
    def icon_path(self):
        """ The path where icon themes should be loaded from.
        This should usually be left empty unless you know what you're doing. """

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

    @setting("git/enabled", bool, False, validate=validate_enable_git)
    def git_enabled(self):
        """ If git version control is installed, use git to allow reverting to arbitrary versions """

    @setting("git/commit_frequency", int, 5)
    def git_commit_frq(self):
        """ If git is enabled, commit changes every N saves """

    @setting("git/remote_repository", str, "")
    def git_remote(self):
        """ If specified, push commits to this repository """

    @setting("git/push_frequency", int, 1)
    def git_push_frq(self):
        """ If configured to push commits to remote repo, push every N commits """

    @setting("git/username", str, "")
    def git_username(self):
        """ The username (if any) required to push to the remote git repository """

    @setting("git/password", Password, "")
    def git_password(self):
        """ The password (if any) required to push to the remote git repository """

    # the directory where the application itself (python scripts, icons, etc) resides. Does not store to file
    application_dir = ""
    # the fallback theme name for icons if the system doesn't provide one. Does not store to file
    fallback_theme_name = "breeze"


settings = _Settings()


class ValidationError(ValueError):
    """ Raised by a setting with a custom validator. If validation fails and the user should see an error prompt,
    this error is raised """

    def __init__(self, value):
        super().__init__(value)
        self._value = str(value)

    @property
    def value(self):
        return self._value
