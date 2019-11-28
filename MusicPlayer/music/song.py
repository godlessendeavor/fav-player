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
    
    def __init__(self):
        super().__init__()
        self._album   = None
        self._minutes = None
        self._seconds = None
        
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
        return str(self.minutes) + ":" + str(self.seconds)

    
    def create_song_from_file(self, song_path):
        self._abs_path = song_path
        total_length = 0
        #get attributes
        file_data = os.path.splitext(song_path)
    
        if file_data[1] == '.mp3':
            try:
                audio = MP3(song_path)
                total_length = audio.info.length
            except MutagenError:
                logger.exception('Error when trying to get MP3 information.')
                #TODO: raise own exception
        else:
            #TODO
            pass
    
        # div - total_length/60, mod - total_length % 60
        mins, secs = divmod(total_length, 60)
        self._minutes = round(mins)
        self._seconds = round(secs)
        
        try:
            #get tags
            mp3_file = MP3File(song_path)
            tags = mp3_file.get_tags()
            
            tagsv2 = tags['ID3TagV2']
            
            self._band = tagsv2['artist']
            self._album = tagsv2['album']
            self._title = tagsv2['song']
        except Exception:
            logger.exception("Some exception occurred while reading MP3 tags. ")
            
        
        
        
        
        
        
        