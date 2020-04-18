"""
Created on Dec 3, 2019

@author: thrasher
"""
from functools import reduce, lru_cache
import os
import dateutil.parser as date_parser
import logging
import re
from music.album import Album
from music.song import Song
from config import config
import musicbrainzngs

from tkinter import filedialog

# set other logs config
album_log_handler = logging.FileHandler(config.NON_COMPLIANT_ALBUMS_LOG)
songs_log_handler = logging.FileHandler(config.NON_COMPLIANT_SONGS_LOG)        
album_log_handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT))
songs_log_handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT))
album_logger = logging.getLogger('albums')
songs_logger = logging.getLogger('songs')
album_logger.addHandler(album_log_handler)
songs_logger.addHandler(songs_log_handler)

class AlbumManager:
    _collection_root = config.MUSIC_PATH  
    _music_db = config.music_db_api
    
    @classmethod  
    @lru_cache(maxsize=8)
    def _get_music_directory_tree(cls):
        """
            Function that returns a nested dictionary with all files in the Music folder
        """
        # initialize dictionary to store the directory tree
        dir_tree = {}
        root_dir = cls._collection_root.rstrip(os.sep) # remove leading whitespaces
        config.logger.debug(f'Getting music directory tree from {root_dir}')
        # recipe for getting the directory tree
        start = root_dir.rfind(os.sep) + 1 # get the index for the name of the folder
        for path, dirs, files in os.walk(root_dir):
            folders = path[start:].split(os.sep)
            subdir = dict.fromkeys(files)
            parent = reduce(dict.get, folders[:-1], dir_tree)  # call dict.get on every element of the folders list
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
        """
        Gets the albums collection from the configured Music Directory 
        and compares with the database collection.
        """        
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
                        # split to max one '-'
                        album_split = album.split('-', 1)
                        album_obj.year = album_split[0].strip()
                        album_obj.title = album_split[1].strip()
                        album_obj.path = os.path.join(cls._collection_root,band,album)
                        if band_key not in res_tree:
                            res_tree[band_key] = {}
                        res_tree[band_key][album] = album_obj
                    # TODO: add a configurable list of exceptions, for now we hardcode 'Misc' as exception
                    elif album != 'Misc':
                        album_logger.warning('Album {album} of {band} is not following the format'.format(album=album, band=band))
        # now let's check the database
        albums_list = cls._music_db.api_albums_get_albums()
        if isinstance(albums_list, list):
            for db_album in albums_list:
                band_key = db_album.band.casefold().strip()
                if band_key in res_tree:
                    # TODO: looping too many times on this tree, make something a bit more clever
                    for key, album_obj in res_tree[band_key].items():
                        if album_obj.title.casefold() == db_album.title.casefold():
                            album_obj.merge(db_album)
                            album_obj.in_db = True
                            break
                else:
                    album_logger.warning(f'Band {db_album.band} not found in collection')
        # logging all missing albums from the database
        for band_key, album_dict in res_tree.items():
            for album in album_dict.values():
                if not album.in_db:
                    album_logger.warning(f'Album {album.title} of band {album.band} not found in database')
        return res_tree
    
    @classmethod
    def update_album(cls, album):
        """
            Function to update the albums. 
        """
        try:
            cls._music_db.api_albums_update_album(album)
        except Exception as ex:
            config.logger.exception(f'Could not update album with title {album.title}') 
            raise(ex)
    
    @classmethod
    def get_favorites(cls, quantity, score, _window_root):
        """
            Gets a list with random songs from the favorites list that complies with the required score.
            :param quantity, the number of songs to return
            :param score, the minimum score of the song
        """
        fav_songs = []
        # get a list from the database with the favorite songs
        try:
            if quantity:
                result = cls._music_db.api_songs_get_songs(quantity = quantity, score = score)
            else:
                result = cls._music_db.api_songs_get_songs()
        except Exception as ex:
            config.logger.exception('Exception when getting favorite songs')
            raise(ex)
        else:
            return cls._get_songs_in_fs(result.songs, _window_root)

    @classmethod
    def _get_songs_in_fs(cls, song_list, _window_root):
        """
            Returns the songs (of Song type) from the given list that exist on the File System.
        """
        fav_songs = []
        if not isinstance(song_list, list):
            config.logger.error(f'song_list is not of list type')
        else:
            # get albums from collection to search for this song list
            albums_dict = cls.get_albums_from_collection()
            # for every song in the database result search the album info in the database
            for db_song in song_list:
                # if it's the same band then we continue, otherwise there might be a mistake
                if db_song.album.band.casefold() in albums_dict.keys():
                    found_album = False
                    # now check for all albums for this band in the collection to that one with same database id
                    # show the band name instead of the key
                    for album_key, album in albums_dict[db_song.album.band.casefold()].items():
                        if album.id == db_song.album.id:
                            found_album = True
                            song = Song(db_song) # merge the database info with the info got from the filesystem
                            song.album = album
                            found_song = False
                            if song.file_name:
                                abs_path = os.path.join(album.path, song.file_name)
                                if os.path.isfile(abs_path):
                                    song.abs_path = abs_path
                                    found_song = True
                                else:
                                    songs_logger.info(
                                        f'Could not find song with title {song.title} from album title '
                                        f'{song.album.title} and band {song.album.band}'
                                        f'among the files of the corresponding album')
                            else:
                                songs_logger.info(f'Song with title {song.title} from album title '
                                                  f'{song.album.title} and band {song.album.band}'
                                                  f' does not have a file name in the database'
                                                  f'Trying to find the corresponding file')
                                # search for the song in the album path
                                for folder, dirs, files in os.walk(album.path):
                                    for file_name in files:
                                        if not song.file_name:
                                            if song.title.casefold() in file_name.casefold():
                                                found_song = True
                                                song.abs_path = os.path.join(folder, file_name)
                                                song.file_name = file_name
                                                try:
                                                    cls._music_db.api_songs_update_song(song)
                                                except:
                                                    songs_logger.info(
                                                        f'Could not update Song with title {song.title} '
                                                        f'from album title '
                                                        f'{song.album.title} and band {song.album.band}'
                                                        f' among the files of the corresponding album')
                                                break
                                    if not found_song:
                                        songs_logger.info(f'Song with title {song.title} from album title '
                                                          f'{song.album.title} and band {song.album.band}'
                                                          f' not found among the files of the '
                                                          f'corresponding album')
                                        # TODO: remove this call and the window_root from the arguments
                                        cls._add_path_to_fav_song(song, _window_root)
                            if found_song:
                                fav_songs.append(song)
                            break
                    if not found_album:
                        songs_logger.info(f"Album with database id {db_song.album.id} could not be found in "
                                          f"database for song {db_song.title}")
                else:
                    songs_logger.info(f"Band {db_song.album.band} not found in the list of bands")
        config.logger.debug(f"Returning {fav_songs}")
        return fav_songs

    # TODO: remove this function when issues with songs are fixed
    @classmethod
    def _add_path_to_fav_song(cls, song, _window_root):
        file_name = None
        file_name = filedialog.askopenfilenames(initialdir=config.MUSIC_PATH, parent=_window_root,
                                                title=f"Choose file for song {song.title} "
                                                      f"from album title {song.album.title} "
                                                      f"and band {song.album.band}")
        if file_name:
            diff_path = os.path.relpath(file_name[0], song.album.path)
            config.logger.info(f"Setting file name from {song.file_name} to {diff_path}")
            song.file_name = diff_path
            song.type = 'Strong'
            config.music_db_api.api_songs_update_song(song)

    @staticmethod
    def get_album_list_for_band(band_name: str, country: str, style: str):
        """
            Gets the album list for the specified band name from the internet.
            :param band_name the band name.
            :param country the country of the band. Used for disambiguation.
            :param style the style of the band. Used also for disambiguation.
        """
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

        