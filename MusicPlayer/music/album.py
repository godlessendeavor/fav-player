'''
Created on Nov 28, 2019

@author: thrasher
'''

from musicdb_client.models.album import Album as DB_album

class Album(DB_album):
    '''
    This is the model for songs in the Music Player
    '''
    
    def __init__(self):
        super().__init__()
        self._in_db = None
        self._path = None
        
    @property
    def in_db(self):
        return self._in_db
    
    @in_db.setter
    def in_db(self, in_db : bool):
        self._in_db = in_db
        
    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path : bool):
        self._path = path
        
    def merge(self, album):
        #TODO: merge attributes of DB_album to album
        pass
        #if not self.title:
        #    self._title = album.title and so on    
        

        
        
        
        
        