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
from music.song import Song
from config import config
import musicbrainzngs
from builtins import staticmethod

#set other logs config
album_log_handler = logging.FileHandler(config.NON_COMPLIANT_ALBUMS_LOG)  
songs_log_handler = logging.FileHandler(config.NON_COMPLIANT_SONGS_LOG)        
album_log_handler.setFormatter(config.LOGGING_FORMAT)
songs_log_handler.setFormatter(config.LOGGING_FORMAT)
album_logger = logging.getLogger(__name__)   
songs_logger = logging.getLogger(__name__)

class AlbumManager:
    _collection_root = config.MUSIC_PATH  
    _musicdb = config._musicdb_api
    
    @classmethod  
    @lru_cache(maxsize=8)
    def _get_music_directory_tree(cls):
        '''
            Function that returns a nested dictionary with all files in the Music folder
        '''
        # initialize dictionary to store the directory tree
        dir_tree = {}
        rootdir = cls._collection_root.rstrip(os.sep) #remove leading whitespaces        
        config.logger.debug(f'Getting music directory tree from {rootdir}')
        # recipe for getting the directory tree
        start = rootdir.rfind(os.sep) + 1 #get the index for the name of the folder 
        for path, dirs, files in os.walk(rootdir):
            folders = path[start:].split(os.sep)
            subdir = dict.fromkeys(files)
            parent = reduce(dict.get, folders[:-1], dir_tree)  #call dict.get on every element of the folders list
            parent[folders[-1]] = subdir
        # get the first value of the dictionary, we're not interested in the root name
        try:
            key, val = next(iter(dir_tree.items()))
        except Exception as ex:
            config.logger.exception("Could not get Music directory tree")
            raise(ex)            
        return val
    
    @classmethod  
    def get_albums_from_collection(cls):
        '''
        Gets the albums collection from the configured Music Directory 
        and compares with the database collection.
        '''        
        # First we get a directory tree with all the folders and files in the music directory tree
        dir_tree = cls._get_music_directory_tree()
        # this will be our final directory tree
        res_tree = {}
        # let's check that the folders match our format Year - Title
        for band, albums in list(dir_tree.items()):
            if albums:
                for album in albums:
                    x = re.search("[0-9][ ]+-[ ]+.+", album)
                    if x:
                        # replace the album key with the object from Album class and fill it
                        album_obj = Album()
                        album_obj.band = band
                        band_key = band.casefold()
                        album_split = album.split('-',2)
                        album_obj.year = album_split[0].strip()
                        album_obj.title = album_split[1].strip()
                        album_obj.path = os.path.join(cls._collection_root,band,album)
                        if band_key not in res_tree:
                            res_tree[band_key] = {}
                        res_tree[band_key][album] = album_obj
                    else:
                        config.logger.info('Album {album} of {band} is not following the format'.format(album=album, band=band))
        # now let's check the database
        albums_list = cls._musicdb.api_albums_get_albums()
        if isinstance(albums_list, list):
            for db_album in albums_list:
                band_key = db_album.band.casefold()
                if band_key in res_tree:
                    for key, album_obj in res_tree[band_key].items():
                        if album_obj.title.casefold() == db_album.title.casefold():
                            album_obj.merge(db_album)
                            album_obj.in_db = True   
                            break
                    if not album_obj.in_db:
                        album_logger.warning(f'Album {album_obj.title} of band {album_obj.band} not found in database')
                else:
                    album_logger.warning(f'Band {db_album.band} not found in collection')                     
        return res_tree
    
    @classmethod
    def update_album(cls, album):
        '''
            Function to update the albums. 
        '''
        try:
            cls._musicdb.api_albums_update_album(album)
        except Exception as ex:
            config.logger.exception(f'Could not update album with title {album.title}') 
            raise(ex)
            
    
    @classmethod
    def get_favorites(cls, quantity, score):
        """
        Gets a list with random songs from the favorites list that complies with the required score.
        :param quantity, the number of songs to return
        :param score, the minimum score of the song 
        """
        fav_songs = []
        # get a list from the database with the favorite songs
        try:
            result = cls._musicdb.api_songs_get_songs(quantity = quantity, score = score)
        except Exception as ex:
           config.logger.exception('Exception when getting favorite songs')
           raise(ex) 
        if result:            
            if isinstance(result.songs, list):
                # get albums from collection to search for this song
                albums_dict = cls.get_albums_from_collection()
                # for every song in the database result search the album info in the database
                for db_song in result.songs:
                    try:
                        db_albums = cls._musicdb.api_albums_get_albums(album_id = db_song.disc_id)
                    except Exception as ex:
                        config.logger.exception(f'Could not get album with id {db_song.disc_id}')
                        continue
                    # make sure it's only one
                    if isinstance(db_albums, list):
                        if len(db_albums) == 1:
                            db_album = db_albums[0]
                            # if it's the same band then we continue, otherwise there might be a mistake
                            if db_album.band.casefold() in albums_dict.keys():
                                found_album = False
                                # now check for all albums for this band in the collection to that one with same database id
                                # TODO: some of these casefolds makes the list show with the result of the casefold, 
                                # show the band name instead of the key 
                                for album_key, album in albums_dict[db_album.band.casefold()].items():
                                    if album.id == db_album.id:   
                                        found_album = True
                                        song = Song(db_song)    
                                        song.album = album     
                                        found_song = False             
                                        #search for the song in the album path
                                        for folder, dirs, files in os.walk(album.path):
                                            for file_name in files:
                                                #TODO: change the next check for a check against the file_name
                                                #right now it's not stored in the database but it should
                                                #if file == song.file_name:                                
                                                if song.title in file_name and 'mp3' in file_name:
                                                    found_song = True
                                                    song.abs_path = os.path.join(folder, file_name)
                                                    song.file_name = file_name
                                                    fav_songs.append(song)
                                                    break
                                            if not found_song:
                                                songs_logger.info(f'Song with title {song.title} from album title '
                                                                 f'{song.album.title} and band {song.album.band} not found among the '
                                                                 f'files of the corresponding album')
                                        break   
                                if not found_album:
                                    songs_logger.info(f"Album with database id {db_album.id} could not be found in database for song {db_song.title}")       
                            else:
                                songs_logger.info(f"Band {db_album.band} not found in the list of bands")       
                        else:
                            config.logger.error(f'Found too many albums ({len(db_albums) }) with id {db_song.disc_i}')
        config.logger.debug(f"returning {fav_songs}")
        return fav_songs
                    
    
    @staticmethod
    def get_album_list_for_band(band_name: str, country: str, style: str):
        '''
        Gets the album list for the specified band name from the internet.
        :param band_name the band name.
        :param country the country of the band. Used for disambiguation.
        :param style the style of the band. Used also for disambiguation.        
        '''
        musicbrainzngs.set_useragent("TODO: add name of app","1.0","TODO: add EMAIL from settings")
        bands_list = musicbrainzngs.search_artists(artist=band_name, type="group", country=country)
        disambiguation_keywords = style.lower().split() 
        filtered_bands = None
        number_of_bands = 0
        # check how many bands are returned in the search 
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
            # let's filter out the compilations
            release_list = filter(lambda item: (item["type"] != "Compilation"), result["artist"]["release-group-list"])
            album_year_list = []
            for release in release_list:
                date = release["first-release-date"]
                year = None
                try:
                    year = date_parser.parse(date).year
                except ValueError:
                    config.logger.exception(f"Date {date} could not be parsed")
                    #TODO: reraise?
                album_year_list.append((release["title"], year))
            
            return album_year_list
        elif number_of_bands > 1:
            return "Too many bands with this description", [(band["name"],band["disambiguation"]) for band in filtered_bands] 
        else:
            return f"Could not find the band {band_name} and {country} in musicbrainz"


        
        