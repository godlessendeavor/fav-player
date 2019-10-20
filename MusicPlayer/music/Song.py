'''
Created on Aug 22, 2019

@author: thrasher
'''

import os
from mutagen.mp3 import MP3
from mp3_tagger import MP3File

class Song(object):
    '''
    This is the object for songs
    '''


    def __init__(self):
        '''
        
        '''
        self._album = ""
        self._title = ""
        self._band = ""
        self._minutes = 0
        self._seconds = 0
        self._abs_path = ""
        
    @property
    def album(self):
        return self._album
    
    @property
    def title(self):
        return self._title
    
    @property
    def band(self):
        return self._band
    
    @property
    def minutes(self):
        return self._minutes
    
    @property
    def seconds(self):
        return self._seconds
    
    @property
    def total_length(self):
        return str(self.minutes) + ":" + str(self.seconds)
    
    @property
    def abs_path(self):
        return self._abs_path
    
    def create_song(self, song_path):
        self._abs_path = song_path
        total_length = 0
        #get attributes
        file_data = os.path.splitext(song_path)
    
        if file_data[1] == '.mp3':
            audio = MP3(song_path)
            total_length = audio.info.length
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
        except Exception as ex:
            print(ex)
            print("Some exception occurred while reading MP3 tags")
            
        
        
        
        
        
        
        