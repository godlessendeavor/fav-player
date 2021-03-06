from os import listdir
from os.path import isfile, join

from PIL import ImageTk, Image as PILImage

from config import config


class Dimensions:
    """Class to specify dimensions (width and height) for a picture"""

    def __init__(self, width, height):
        self._width = width
        self._height = height

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height


class CoverArtManager:
    """Class to handle cover arts of albums"""

    @classmethod
    def get_cover_art_for_album(cls, album, window, dimensions):
        """Gets the cover art for the given album.
        Args:
            album(Album): the album object for the cover art to return
            window(TkinterWindow): the window in which this image will be shown
            dimensions(Dimension): the dimensions of the picture to be resized to
        Returns:
            ImageTk.PhotoImage object with the image
        """
        if album and album.path:
            try:
                file_names = [f for f in listdir(album.path) if isfile(join(album.path, f))]
            except ValueError:
                config.logger.exception(f"Album {album} provided does not have a path.")
            else:
                image = None
                for file_name in file_names:
                    if "front" in file_name.casefold():
                        image = join(album.path, file_name)
                        break
                if image:
                    pil_image = PILImage.open(image)
                    pil_image = pil_image.resize((dimensions.width, dimensions.height), PILImage.ANTIALIAS)
                    return ImageTk.PhotoImage(pil_image, master=window)
        else:
            config.logger.error("No album given for cover art search")
