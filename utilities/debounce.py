""" classes and functions for debouncing user actions. """

from threading import Timer
from PySide2.QtCore import Signal, QObject


class Debouncer(QObject):
    """ Debouncer provides a two-way interface for taking actions after some input event, but not duplicating
    the action for every event inside a certain window. You can set the action attribute on a Debouncer instance
    and it will call that action, or you can provide your own factory function (probably unnecessary) to create the
    timer instance each time.

    In addition to being able to execute functions asynchronously, you can also utilize the bounced signal, which
    is useful for needing to add or remove widgets from the GUI, which normally couldn't be done in a normal function
    due to threading constraints. """

    bounced = Signal()

    def __init__(self, timer_factory=None, timeout=3):
        super().__init__()
        self.action = self._noop
        self.timeout = timeout
        self.timer_factory = timer_factory
        if timer_factory is None:
            self.timer_factory =  self._default_timer
        self.timer = None

    def _noop(self):
        """ Does nothing """

    def _default_timer(self):
        return Timer(self.timeout, self._log_action)

    def _log_action(self):
        # TODO make this actually a log
        print("debouncer: calling action")
        self.bounced.emit()
        self.action()

    def start(self, *args):
        """ Start the debouncing timer. If timer is reached and no action is taken, action will trigger.
         Accepts an arbitrary number of arguments to make it easier to connect to arbitrary signals """
        if self.timer is None:
            self.timer = self.timer_factory()
            self.timer.start()
        else:
            self.timer.cancel()
            self.timer = self.timer_factory()
            self.timer.start()

    def stop(self):
        if self.timer is not None:
            self.timer.cancel()


g_save_debouncer = Debouncer()
