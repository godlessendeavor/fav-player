'''
Created on Dec 3, 2019

@author: thrasher
'''
from functools import reduce, lru_cache
import os
import dateutil.parser as date_parser
import logging
import re
from music.album import Album
from config import config
import musicbrainzngs
import musicdb_client
from musicdb_client.rest import ApiException
from musicdb_client.configuration import Configuration as Musicdb_config
from builtins import staticmethod


#set log configuration
log_level = logging.getLevelName(config.LOGGING_LEVEL)

logging.basicConfig(
    format='[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

class AlbumManager:
    _collection_root = config.MUSIC_PATH    
    _musicdb_config = Musicdb_config()
    _musicdb_config.host = config.MUSIC_DB_HOST
    _musicdb_config.debug = True
    _musicdb = musicdb_client.PublicApi(musicdb_client.ApiClient(_musicdb_config))
    
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
    #TODO: call the DB API and compare data
    @staticmethod  
    def get_albums_from_collection():
        '''
        Gets the albums collection from the configured Music Directory 
        and compares with the database collection.
        '''
        
        #albums_list = _musicdb.api_albums_get_albums()
        dir_tree = AlbumManager._get_music_directory_tree()
        res_tree= {}
        for band, albums in list(dir_tree.items()):
            for album in albums:
                x = re.search("[0-9][ ]+-[ ]+.+", album)
                if x:
                    #replace the album key with the object from Album class and fill it
                    album_obj = Album()
                    album_obj.band = band
                    album_split = album.split('-',2)
                    album_obj.year = album_split[0]
                    album_obj.title = album_split[1]
                    album_obj.path = os.path.join(AlbumManager._collection_root,band,album)
                    if band not in res_tree:
                        res_tree[band] = {}
                    res_tree[band][album] = album_obj
                else:
                    logger.info('Album {album} of {band} is not following the format'.format(album=album, band=band))
        return res_tree
    
    @staticmethod
    def get_favorites(quantity, score):
        #TODO: check why this is failing
        fav_songs = None
        result = AlbumManager._musicdb.api_songs_get_songs(quantity = quantity, score = score)
        if result:            
            if isinstance(result.songs, list):
                for song in result.songs:
                    albums = AlbumManager._musicdb.api_albums_get_albums(album_id = song.disc_id)
                    if isinstance(albums, list):
                        if len(albums) == 1:
                            #TODO: check if album is in music directory
                            song.abs_path = None    
                fav_songs = result.song                    
               
        return fav_songs
                    
    
    @staticmethod
    def get_album_list_for_band(band_name, country, style):
        '''
        Gets the album list from a 
        '''
        musicbrainzngs.set_useragent("TODO: add name of app","1.0","TODO: add EMAIL from settings")
        bands_list = musicbrainzngs.search_artists(artist = band_name, type = "group", country = country)
        disambiguation_keywords = style.lower().split() 
        filtered_bands = None
        number_of_bands = 0
        #check how many bands are returned in the search 
        # check with the disambiguation contains at least some of the words in the style provided and filter to one band
        if "artist-list" in bands_list.keys():
            bands_with_same_name = [band_info for band_info in bands_list["artist-list"] if band_info["name"] == band_name]  
            number_of_bands = len(bands_with_same_name)
            if number_of_bands == 1:
                filtered_bands = bands_with_same_name
            elif number_of_bands > 1:
                filtered_bands = [band_info for band_info in bands_with_same_name 
                                  if any(word in band_info["disambiguation"].lower() for word in disambiguation_keywords)]
                number_of_bands = len(filtered_bands)
            
        # there should be only one match
        if number_of_bands == 1:
            band_id = filtered_bands[0]['id']
            result = musicbrainzngs.get_artist_by_id(band_id,
                                                     includes=["release-groups"], 
                                                     release_type=["album", "ep"])
            #let's filter out the compilations
            release_list = filter(lambda item: (item["type"] != "Compilation"), result["artist"]["release-group-list"])
            album_year_list = []
            for release in release_list:
                date = release["first-release-date"]
                year = None
                try:
                    year = date_parser.parse(date).year
                except ValueError:
                    logger.exception(f"Date {date} could not be parsed")
                    #TODO: reraise?
                album_year_list.append((release["title"], year))
            
            return album_year_list
        elif number_of_bands > 1:
            return "Too many bands with this description", [(band["name"],band["disambiguation"]) for band in filtered_bands] 
        else:
            return f"Could not find the band {band_name} and {country} in musicbrainz"


        
        