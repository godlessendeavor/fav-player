'''
Created on Aug 22, 2019

@author: thrasher
'''

import os
from mutagen.mp3 import MP3, MutagenError
from mp3_tagger import MP3File
from music.album import Album
from musicdb_client.models.song import Song as DB_song
from config import config
import logging
#set log configuration
log_level = logging.getLevelName(config.LOGGING_LEVEL)

logging.basicConfig(
    format='[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

class Song(DB_song):
    '''
    This is the model for songs in the Music Player
    '''
    
    def __init__(self, song : DB_song = None):
        super().__init__()
        self._album    = None
        self._minutes  = None
        self._seconds  = None
        self._band     = None
        self._abs_path = None
        #Copy all attributes from base class object if provided
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
        return str(self.minutes) + ":" + format(self.seconds, '02d')
    
    @property
    def abs_path(self):
        return self._abs_path
    
    @abs_path.setter
    def abs_path(self, path):
        self.update_song_data_from_file(path)
        self._abs_path = path

    
    def update_song_data_from_file(self, song_path):
        self._abs_path = song_path
        total_length = 0
        #get attributes
        file_data = os.path.splitext(song_path)
    
        if file_data[1] == '.mp3':
            try:
                audio = MP3(song_path)
                total_length = audio.info.length
            except MutagenError as ex:
                logger.exception('Error when trying to get MP3 information.')
                raise ex
            else:                
                # div - total_length/60, mod - total_length % 60
                mins, secs = divmod(total_length, 60)
                self._minutes = round(mins)
                self._seconds = round(secs)
                
                try:
                    #get tags
                    mp3_file = MP3File(song_path)
                    tags = mp3_file.get_tags()
                    
                    tagsv2 = tags['ID3TagV2']
                    
                    if not self._band:
                        self._band = tagsv2['artist']
                    if not self._album:
                        self._album = tagsv2['album']
                    if not self._title:
                        self._title = tagsv2['song']
                except Exception:
                    logger.exception("Some exception occurred while reading MP3 tags.")
        else:
            raise Exception(f"File {song_path} is not MP3.")
        
    def __str__(self):
        return str(self.__repr__())    
        
    def __repr__(self):
        obj = self.__dict__
        return str(obj)
        
      
    
            
        
        
        
        
        
        
        