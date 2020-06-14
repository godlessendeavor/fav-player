"""
Created on Nov 28, 2019

@author: thrasher
"""

from musicdb_client.models.album import Album as DB_album
from config import config
import datetime


class Album(DB_album):
    """This is the model for songs in the Music Player"""

    def __init__(self):
        super().__init__()
        self._in_db = None
        self._path = None

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, Album):
            return False
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def in_db(self):
        return self._in_db

    @in_db.setter
    def in_db(self, in_db: bool):
        self._in_db = in_db

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path: bool):
        self._path = path

    def merge(self, album):
        """
            Function to merge the Album server object type to this object type.
            @param: the album server type
        """
        in_dict = album.to_dict()
        self_dict = self.to_dict()
        self_dict.update(in_dict)
        self.from_dict(self_dict)

    def validate(self):
        try:
            year = int(self._year)
        except (ValueError, TypeError):
            config.logger.error(f"Year of album is not an Integer")
            return False
        else:
            now = datetime.datetime.now()
            if year < 1900 or year > now.year:
                config.logger.error(f"Year of album is not correct {year}")
                return False
        if self._score and not self._score.isspace():
            try:
                score = float(self._score)
            except (ValueError, TypeError):
                config.logger.error(f"Score of album is not a Float")
                return False
            else:
                if score < 0.0 or score > 10.0:
                    config.logger.error(f"Score of album is not correct {self._score}")
                    return False
        return True

    def from_dict(self, album_dict):
        if 'id' in album_dict:
            self._id = album_dict['id']
        if 'title' in album_dict:
            self._title = album_dict['title']
        if 'band' in album_dict:
            self._band = album_dict['band']
        if 'copy' in album_dict:
            self._copy = album_dict['copy']
        if 'country' in album_dict:
            self._country = album_dict['country']
        if 'review' in album_dict:
            self._review = album_dict['review']
        if 'score' in album_dict:
            self._score = album_dict['score']
        if 'style' in album_dict:
            self._style = album_dict['style']
        if 'type' in album_dict:
            self._type = album_dict['type']
        if 'year' in album_dict:
            self._year = album_dict['year']
        if 'path' in album_dict:
            self._path = album_dict['path']
        if 'in_db' in album_dict:
            self._in_db = album_dict['in_db']
