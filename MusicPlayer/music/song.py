"""
Created on Aug 22, 2019

@author: thrasher
"""

import os
from mutagen.mp3 import MP3, MutagenError
from mp3_tagger import MP3File
from music.album import Album
from musicdb_client.models.song import Song as DB_song
from config import config


class Song(DB_song):
    """
        This is the model for songs in the Music Player
    """

    def __init__(self, song: DB_song = None):
        super().__init__()
        self._album = None
        self._minutes = None
        self._seconds = None
        self._band = None
        self._abs_path = None
        # Copy all attributes from base class object if provided
        if song is not None:
            self.__dict__.update(song.__dict__)

    @property
    def album(self):
        return self._album

    @album.setter
    def album(self, album):
        self._album = album

    @property
    def band(self):
        if self._album:
            return self._album.band
        else:
            return None

    @property
    def minutes(self):
        return self._minutes

    @property
    def seconds(self):
        return self._seconds

    @property
    def total_length(self):
        if not self._seconds:
            self._seconds = 0
        return str(self.minutes) + ":" + format(self.seconds, '02d')

    @property
    def abs_path(self):
        return self._abs_path

    @abs_path.setter
    def abs_path(self, path):
        try:
            self.update_song_data_from_file(path)
            self._abs_path = path
        except:
            config.logger.exception(f'Could not set absolute path for song in {path}')

    def validate(self):
        """Validates the attributes of this instance.
        Returns:
            bool: True if it's a valid song. False if not.
        """
        if not self._album:
            config.logger.error(f"Album of song is empty")
            return False
        else:
            if not self._album.validate():
                return False
        if not self._title:
            config.logger.error(f"Title of song is empty")
            return False
        if not self._album:
            config.logger.error(f"Album of song is empty")
            return False
        elif not isinstance(self._album, Album):
            config.logger.error(f"Album of song {self._title}is not the right type. Expecting type {type(Album)} got {type(self._album)}")
            return False
        if not self._file_name:
            config.logger.error(f'Song {self._title} does not have a file name')
            return False
        if self._track_number and not self._score.isspace():
            try:
                int(self._track_number)
            except ValueError:
                config.logger.error(f"Track number of song is not an integer")
                return False
        if self._score and not self._score.isspace():
            try:
                score = float(self._score)
            except ValueError:
                config.logger.error(f"Score of song is not a Float")
                return False
            else:
                if score < 0.0 or score > 10.0:
                    config.logger.error(f"Score of song is not correct {self._score}")
                    return False
        return True

    def update_song_data_from_file(self, song_path):
        """
            Updates the abs path of a song from a given path and it reads the MP3 data.
            #TODO: support other types of audio
        """
        updated = False
        if os.path.isfile(song_path):
            self._abs_path = song_path
            total_length = 0
            # get attributes
            file_data = os.path.splitext(song_path)

            if file_data[1] == '.mp3':
                try:
                    audio = MP3(song_path)
                    total_length = audio.info.length
                except MutagenError as ex:
                    config.logger.exception(f'Error when trying to get MP3 information for song in {song_path}')
                else:
                    # div - total_length/60, mod - total_length % 60
                    mins, secs = divmod(total_length, 60)
                    self._minutes = round(mins)
                    self._seconds = round(secs)

                    try:
                        # get tags
                        mp3_file = MP3File(song_path)
                        tags = mp3_file.get_tags()

                        tagsv2 = tags['ID3TagV2']
                    except Exception:
                        config.logger.exception(f"Some exception occurred while reading MP3 tags for {song_path}.")
                    else:
                        if not self._band and 'artist' in tagsv2:
                            self._band = tagsv2['artist']
                        if not self._album and 'album' in tagsv2:
                            self._album = tagsv2['album']
                        if not self._title and 'song' in tagsv2:
                            self._title = tagsv2['song']
                updated = True

            else:
                config.logger.info(f"File {song_path} is not MP3.")
        else:
            raise Exception(f"File {song_path} does not exist. Could not set abs path for song.")
        return updated

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        obj = self.__dict__
        return str(obj)
