from PySide6 import QtWidgets, QtGui, QtCore
from utilities.save_mixin import SaveMixin
from os import chdir, getcwd, remove
from urllib.request import urlopen
from settings.__init__ import settings
from os.path import exists, join
from style_consants import *
import uuid


class PageImageItem(QtWidgets.QLabel, SaveMixin):
    """ Supports common image formats, as well as GIF images, which technically load as QMovies, instead of Pixmaps """

    def __init__(self, parent, img_url, width: int, asset_name=None, **extra):
        super().__init__(parent)

        self._play_btn = None
        self._toolbar = None
        # The name of the asset file once saved to disk
        self.asset_name = str(uuid.uuid4())
        if asset_name is not None:
            self.asset_name = asset_name
        # asset URLs, when they are local files, are relative paths, not absolute
        # for portability reasons. When we are restoring from a saved state. So, we should
        # set our working directory to the asset directory
        # URLs for files dragged in should be absolute anyway and not affected.
        old_wd = getcwd()
        chdir(settings.asset_dir)
        data = urlopen(img_url).read()
        chdir(old_wd)
        self.setStyleSheet("background: transparent;")

        orig_pixmap = QtGui.QPixmap()
        orig_pixmap.loadFromData(data)
        pixmap = orig_pixmap.scaledToWidth(width)
        # orig pixmap is an asset that gets saved to disk
        self._orig_pixmap = orig_pixmap
        if "transform" in extra:
            self._rotation = extra['transform']['rotation']
        else:
            self._rotation = 0

        self._mimedb = QtCore.QMimeDatabase()
        if self._mimedb.mimeTypeForData(data).name() == "image/gif":
            self._mimetype = "GIF"
            # If this is a qmovie, we need to write the bytes to disk ourselves, the QMovie object doesn't save()
            self._data = data
            self.save_asset()
            movie = QtGui.QMovie(self.asset_file_fq)
            self._movie = movie
            self.setMovie(self._movie)
            self._movie.start()
            self._playing = True
        else:
            self.setPixmap(pixmap)
            self._mimetype = "PNG"

    @property
    def height(self):
        return self.pixmap().height()

    @property
    def width(self):
        return self.pixmap().width()

    @property
    def extra(self) -> dict:
        """ Returns extra information to save along with the standard information, which may differ based on
        mimetype, configuration, etc. This is to provide more control over what attributes get saved for images and
         remove responsibility for those attributes from parent widgets"""
        return {
            "transform": {
                "rotation": self._rotation
            }
        }

    def save_asset(self):
        """ If there is an asset, save it if it hasn't been saved, yet """
        if not exists(self.asset_file_fq):
            if self._mimetype != "GIF":
                self._orig_pixmap.save(self.asset_file_fq, self._mimetype)  # TODO support GIFs
            else:
                with open(self.asset_file_fq, "wb") as f:
                    f.write(self._data)

    def delete_asset(self):
        """ If there is an asset, delete it """
        try:
            remove(self.asset_file_fq)
        except FileNotFoundError:
            """ Do nothing """

    def resize(self, width: int):
        pixmap = self._orig_pixmap
        pixmap = pixmap.scaledToWidth(width)
        if self._mimetype != "GIF":
            self.setPixmap(pixmap)
        else:
            self._movie.setScaledSize(pixmap.size())

    def setPixmap(self, pixmap):
        pixmap = self._rotate(pixmap)
        super().setPixmap(pixmap)

    @property
    def asset_file(self):
        """ return the calculated, unique name of this item for the workspace. """
        return "{}.fna".format(self.asset_name)

    @property
    def asset_file_fq(self):
        return join(settings.asset_dir, self.asset_file)

    def _toggle_movie_play(self):
        if self._movie.state() == self._movie.Running:
            self._movie.setPaused(True)
        else:
            self._movie.setPaused(False)
        if self._play_btn is not None:
            self._play_btn.deleteLater()
            self._play_btn = None

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if self._mimetype == "GIF" and ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            self._toggle_movie_play()
        else:
            # If it's a right click or otherwise, pass it on
            ev.ignore()

    def enterEvent(self, ev: QtGui.QMouseEvent):
        """ on images, if the mimetype is GIF, we want to allow the user to play the GIF and present a play button
        on mouseover """
        if self._mimetype == "GIF" and self._play_btn is None:
            self._play_btn = QtWidgets.QLabel(self)
            if self._movie.state() == self._movie.Running:
                icon = QtGui.QIcon.fromTheme("media-playback-pause")
            else:
                icon = QtGui.QIcon.fromTheme("media-playback-start")
            self._play_btn.setPixmap(icon.pixmap(self.geometry().width(), self.geometry().height()))
            self._play_btn.setStyleSheet("background: transparent;")
            self._play_btn.show()
            # the icon should be square. So, set the offset of X equal to the different between width and height
            # then halved (so it's centered)
            pos = self._play_btn.geometry()
            diffX = self.geometry().width() - self.geometry().height()
            if diffX > 1:
                pos.setX(int(diffX/2))
            else:
                # But if we're taller than we are wide, we need to offset on the other axis
                pos.setY(int((self.geometry().height() - self.geometry().width()) / 2))
            self._play_btn.setGeometry(pos)
        elif self._mimetype == "PNG" and self._toolbar is None:
            self._toolbar = ImageEditToolbar(self)
            self._toolbar.show()

    def leaveEvent(self, event: QtCore.QEvent):
        """ on images, if the mimetype is GIF, we need to get rid of the play/pause button if their mouse leaves the
        screen """
        if self._mimetype == "GIF" and self._play_btn is not None:
            self._play_btn.deleteLater()
            self._play_btn = None
        elif self._mimetype == "PNG" and self._toolbar is not None:
            self._toolbar.deleteLater()
            self._toolbar = None

    def rotate_counter_clockwise(self):
        self._rotation = (self._rotation - 90) % 360
        transform = QtGui.QTransform()
        pixmap = self.pixmap().transformed(transform.rotate(-90))
        super().setPixmap(pixmap)

    def rotate_clockwise(self):
        self._rotation = (self._rotation + 90) % 360
        transform = QtGui.QTransform()
        pixmap = self.pixmap().transformed(transform.rotate(90))
        super().setPixmap(pixmap)

    def _rotate(self, pixmap):
        transform = QtGui.QTransform()
        return pixmap.transformed(transform.rotate(self._rotation))


class ImageEditToolbar(QtWidgets.QToolBar):
    """ Stores icons for editing images when hovering over an image """
    def __init__(self, parent: PageImageItem):
        super().__init__(parent)
        crop_icon = QtGui.QIcon.fromTheme("transform-crop")
        rotate_cw = QtGui.QIcon.fromTheme("transform-rotate")
        rotate_ccw = QtGui.QIcon.fromTheme("transform-rotate")
        pixmap = rotate_ccw.pixmap(QtCore.QSize(32, 32)).transformed(QtGui.QTransform().rotate(180, QtCore.Qt.Axis.YAxis))
        rotate_ccw = QtGui.QIcon(pixmap)
        self.addAction(crop_icon, "crop")
        self.addAction(rotate_cw, "rotate", parent.rotate_clockwise)
        self.addAction(rotate_ccw, "rotate back", parent.rotate_counter_clockwise)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setStyleSheet("""
        QToolBar {{
            background-color: {};
        }}
        QToolTip {{
            opacity: 128;
            color {}: 
        }}""".format(IMAGE_ITEM_TOOLBAR_BG, EDIT_TEXT_FOCUS_BG))
