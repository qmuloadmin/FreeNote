from PySide2 import QtWidgets
from abc import abstractmethod
from utilities.save_mixin import g_save_debouncer


class RenameableMixin:
    """ Not actually an ABC to prevent Metaclass issues as a Mixin. A little hacky. """

    @abstractmethod
    def _try_rename(self, new_id: str, *args) -> bool:
        """ this method should check to see if the new name is valid, and if so, return true and update the id """

    @property
    @abstractmethod
    def _unique_resource_name(self) -> str:
        """ this method should return the name of the child resource that can be renamed (like Page or Section) """

    def _rename_dialog(self, *args):
        """ open a rename dialog and test the new name against _try_rename.
        in order to be used as a slot, args may be passed, and they will be forwarded to _try_rename call """
        titled_name = self._unique_resource_name
        lc_name = titled_name.lower()
        new_id, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename {}".format(titled_name),
            "New name for this {}".format(lc_name),
            QtWidgets.QLineEdit.Normal,
            ""
        )
        if ok:
            result = self._try_rename(new_id, *args)
            if not result:
                QtWidgets.QMessageBox(self).warning(
                    self,
                    "Name Taken",
                    "Another {} already has that name.".format(lc_name)
                )
            else:
                # Not sure if we should explicitly call the save debouncer here, or emit a signal that is connected
                # by something using SaveMixin. TODO evaluate
                g_save_debouncer.start()
