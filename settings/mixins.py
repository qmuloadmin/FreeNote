class CustomSettingsWidgetMixin:
    """ A mixin that provides an interface for setting a custom settings-page widget for a particular setting """

    @classmethod
    def settings_widget(cls, value, parent):
        return cls._settings_widget_factory(value, parent)
