'''
Created on Dec 3, 2019

@author: thrasher
'''
from functools import reduce, lru_cache
import os
from config import config
import re
from music.album import Album
from pymysql.constants.CR import CR_SHARED_MEMORY_CONNECT_ABANDONED_ERROR

class AlbumManager:
    _collection_root = config.MUSIC_PATH
    
    #TODO: consider caching for this: lru_cache vs CacheTools?
    @staticmethod  
    #@lru_cache(maxsize=8)
    def _get_music_directory_tree():
        '''
            Function that returns a nested dictionary with all files in the Music folder
        '''
        #result dictionary
        dir_tree = {}
        rootdir = AlbumManager._collection_root.rstrip(os.sep)
        start = rootdir.rfind(os.sep) + 1
        for path, dirs, files in os.walk(rootdir):
            folders = path[start:].split(os.sep)
            subdir = dict.fromkeys(files)
            parent = reduce(dict.get, folders[:-1], dir_tree)
            parent[folders[-1]] = subdir
        #return the first value of the dictionary, we're not interested in the root name
        key, val = next(iter( dir_tree.items()))
        return val
    
    #TODO: make async function using asyncio. Follow https://realpython.com/async-io-python/
    @staticmethod  
    def get_albums_from_collection():
        dir_tree = AlbumManager._get_music_directory_tree()
        res_tree= {}
        for band, albums in list(dir_tree.items()):
            for album in albums:
                x = re.search("[0-9][ ]+-[ ]+.+", album)
                if x:
                    #replace the album key with the object from Album class and fill it
                    #TODO: add year stripped from the name
                    album_obj = Album()
                    album_obj.band = band
                    album_obj.title = album.split('-',2)[1]
                    if band not in res_tree:
                        res_tree[band] = {}
                    res_tree[band][album] = album_obj
                    #print(res_tree)
                else:
                    print('Album {album} of {band} is not following the format'.format(album=album, band=band))
        print(res_tree)
        return res_tree
        
        
        