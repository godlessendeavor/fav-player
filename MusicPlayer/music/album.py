"""
Created on Nov 28, 2019

@author: thrasher
"""

from musicdb_client.models.album import Album as DB_album


class Album(DB_album):
    """
        This is the model for songs in the Music Player
    """

    def __init__(self):
        super().__init__()
        self._in_db = None
        self._path = None

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
        in_dict = album.to_dict()
        self_dict = self.to_dict()
        self_dict.update(in_dict)
        self.from_dict(self_dict)

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
