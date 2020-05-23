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

from musicdb_client.rest import ApiException

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


class MusicManager:
    _collection_root = config.MUSIC_PATH
    _music_db = config.music_db_api
    _set_album_data_cb = None
    _set_song_data_cb = None
    _music_dir_tree = None
    # this tree will contain the validated albums
    _valid_albums = {}
    # this tree will contain the non-validated albums
    _wrong_albums = {}
    # this tree will contain the new albums
    _new_albums = {}

    @classmethod
    def set_update_song_data_cb(cls, cb):
        """Sets a callback to set the file name from the GUI."""
        cls._set_song_data_cb = cb

    @classmethod
    def set_update_album_data_cb(cls, cb):
        """Sets a callback to set the album data from the GUI."""
        cls._set_album_data_cb = cb

    @classmethod
    def get_albums_from_collection(cls):
        """Gets the albums collection from the configured Music Directory
            and compares with the database collection.
            @return tuple containing:
            1) the dict of validated albums from collection
            2) the new albums added to the collection (Always empty)
            3) the albums not in the database
        """
        return cls._update_albums_from_collection()

    @classmethod
    def add_new_albums_from_collection_to_db(cls):
        """
            Adds all the albums from the collection that are not in the database yet.
            @return tuple containing:
            1) the dict of validated albums from collection
            2) the new albums added to the collection (duplicated from the 1st param in this tuple)
            3) the albums not in the database.
        """
        return cls._update_albums_from_collection(True)

    @classmethod
    def update_album(cls, album):
        """Function to update an album in the server."""
        if album.validate():
            try:
                album = cls._music_db.api_albums_update_album(album)
            except Exception as ex:
                config.logger.exception(f'Could not update album with title {album.title}')
                raise ex
            else:
                config.logger.debug(f"Album {album.title} saved to the database")
                return album
        else:
            config.logger.error(f"Some problem with validation of album {album.title}")

    @classmethod
    def delete_album(cls, album):
        """Function to delete an album from the server."""
        try:
            cls._music_db.api_albums_delete_album(album.id)
        except Exception as ex:
            config.logger.exception(f'Could not delete album with title {album.title}')
            raise ex
        else:
            config.logger.debug(f"Album {album.title} deleted from the database")
            return album

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
            if quantity:
                result = cls._music_db.api_songs_get_songs(quantity=quantity, score=score)
            else:
                result = cls._music_db.api_songs_get_songs()
        except Exception as ex:
            config.logger.exception('Exception when getting favorite songs')
            raise ex
        else:
            return cls._get_songs_in_fs(result.songs)

    @classmethod
    def add_song_to_favorites(cls, song):
        # TODO: check for existing album_id and other compulsory data. Add validate function to song class
        if isinstance(song, Song):
            if not song.file_name:
                found_song = cls._search_and_update_song_file_name(song)
                if not found_song:
                    config.logger.error(f'Song needs a file name. Not being able to get one provided from user.')
                    raise Exception
            if not song.album:
                config.logger.error(f'Song needs an album.')
                raise Exception
            else:
                if not song.album.id:
                    config.logger.error(f'Song needs an album with an id.')
                    raise Exception
            try:
                song = cls._musicdb.api_songs_update_song(song)
            except ApiException as ex:
                config.logger.exception(f'Error adding a new favorite song to server.')
                raise ex
        else:
            config.logger.error(f'Song is not of Song type')

    @classmethod
    def add_reviews_batch(cls, reviews_path):
        """Gets reviews from text files and sets them in the corresponding albums.
        Arguments:
            reviews_path(str): the reviews path where to get the text files with the reviews to add
        Returns:
            dict with the updated collection of albums
        """
        if not cls._valid_albums:
            cls._update_albums_from_collection()
        files_list = [f for f in os.listdir(reviews_path) if os.path.isfile(os.path.join(reviews_path, f))]
        if not files_list:
            raise FileNotFoundError
        for file_name in files_list:
            full_name = os.path.join(reviews_path, file_name)
            file_name_wo_ext = os.path.splitext(file_name)[0] # remove file extension
            # get the info from the file name
            # the pattern is BAND - ALBUM - SCORE
            keys = file_name_wo_ext.split('-')
            if len(keys) != 3:
                config.logger.error(f'The file {file_name} does not follow the pattern BAND - ALBUM - SCORE')
            else:
                band_key = keys[0].casefold().strip()
                album_key = keys[1].casefold().strip()
                score = keys[2].strip()
                found_album = False
                if band_key in cls._valid_albums:
                    for key, album_obj in cls._valid_albums[band_key].items():
                        if album_obj.title.casefold() == album_key:
                            found_album = True
                            # set the score
                            album_obj.score = score
                            try:
                                with open(full_name) as f:
                                    review = f.read()
                            except:
                                config.logger.exception(f'Could not open file {full_name}')
                            else:
                                album_obj.review = review
                                try:
                                    cls._valid_albums[band_key][key].merge(cls.update_album(album_obj))
                                    cls._valid_albums[band_key][key].in_db = True
                                except:
                                    config.logger.exception(f'Could not update review for album {album_key} '
                                                        f'for band {band_key}')
                                    cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, album_obj)
                                else:
                                    try:
                                        # move the review file out
                                        os.rename(full_name, os.path.join(reviews_path, 'DONE - ' + file_name))
                                    except:
                                        config.logger.exception(f'Could not move file {file_name} to tmp')
                            break
                    if not found_album:
                        config.logger.error(f'Could not find the album {album_key} for band {band_key} '
                                            f'in the music directory.')
                else:
                    config.logger.error(f'Could not find the band {band_key} in the music directory.')
                    cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, None)
        return cls._valid_albums, cls._wrong_albums

    @classmethod
    def _get_music_directory_tree(cls):
        """Function to get all files in the Music folder
        Returns:
            dict, nested with all files in the Music folder
        """
        if cls._music_dir_tree:
            res_tree = cls._music_dir_tree
        else:
            # initialize dictionary to store the directory tree
            dir_tree = {}
            root_dir = cls._collection_root.rstrip(os.sep)  # remove leading whitespaces
            config.logger.debug(f'Getting music directory tree from {root_dir}')
            # recipe for getting the directory tree
            start = root_dir.rfind(os.sep) + 1  # get the index for the name of the folder
            for path, dirs, files in os.walk(root_dir):
                folders = path[start:].split(os.sep)
                subdir = dict.fromkeys(files)
                parent = reduce(dict.get, folders[:-1], dir_tree)  # call dict.get on every element of the folders list
                parent[folders[-1]] = subdir
            # get the first value of the dictionary, we're not interested in the root name
            try:
                key, val = next(iter(dir_tree.items()))
            except StopIteration as ex:
                config.logger.exception("Could not get Music directory tree")
                raise ex
            res_tree = val
        return res_tree

    @classmethod
    def _add_album_to_tree(cls, tree, band_key, album_key, album):
        """Adds an album to a tree.
        Arguments:
            tree(dict): the tree of albums to be added to
            band_key(str): the band key in the tree (if it doesn't exist it will create it)
            album_key(str): the album key in the band
            album(Album): the album object
        """
        if band_key not in tree:
            tree[band_key] = {}
        tree[band_key][album_key] = album

    @classmethod
    def _update_albums_from_collection(cls, add_to_db=False):
        """Returns a tree with the albums that are both in the collection and the database.
            @param: add_to_db, indicates if the albums that are not in the database should be added.
        """
        # First we get a directory tree with all the folders and files in the music directory tree
        dir_tree = cls._get_music_directory_tree()
        # this will be our directory tree with the validated albums
        # initialize albums trees
        cls._valid_albums = {}
        cls._wrong_albums = {}
        cls._new_albums = {}
        # let's check that the folders match our format Year - Title
        for band, albums in list(dir_tree.items()):
            if albums:
                for album in albums:
                    album_obj = Album()
                    album_obj.band = band
                    # check that it complies with the "YEAR - TITLE" rule
                    x = re.search("[0-9][ ]+-[ ]+.+", album)
                    if x:
                        # replace the album key with the object from Album class and fill it
                        band_key = band.casefold()
                        # split to max one '-'
                        album_split = album.split('-', 1)
                        album_obj.year = album_split[0].strip()
                        album_obj.title = album_split[1].strip()
                        album_obj.path = os.path.join(cls._collection_root, band, album)
                        if band_key not in cls._valid_albums:
                            cls._valid_albums[band_key] = {}
                        cls._valid_albums[band_key][album.strip().casefold()] = album_obj
                    # TODO: add a configurable list of exceptions, for now we hardcode 'Misc' as exception
                    elif album != 'Misc':
                        album_logger.warning('Album {album} of {band} is not following the format'
                                             .format(album=album, band=band))
                        album_obj.title = album
                        cls._add_album_to_tree(cls._wrong_albums, band, album, album_obj)
        # now let's check the database
        albums_list = cls._music_db.api_albums_get_albums()
        if isinstance(albums_list, list):
            for db_album in albums_list:
                band_key = db_album.band.casefold().strip()
                if band_key in cls._valid_albums:
                    # TODO: look for an alternative solution for the albums with no year
                    if db_album.year == '0':
                        db_album.year = '0000'
                    album_key = f'{db_album.year} - {db_album.title}'.strip().casefold()
                    if album_key in cls._valid_albums[band_key]:
                        cls._valid_albums[band_key][album_key].merge(db_album)
                        cls._valid_albums[band_key][album_key].in_db = True
                    else:
                        # log missing album from collection
                        album_logger.error(f"{db_album.title} from {db_album.year} "
                                           f"from {db_album.band} not found")
                        album_logger.error(f"Albums from that band are {cls._valid_albums[band_key].keys()}")
                        cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, db_album)
                else:
                    album_logger.warning(f'Band {db_album.band} not found in collection')
        # processing all missing albums in the database
        for band_key, album_dict in cls._valid_albums.items():
            for album_key, album in album_dict.items():
                if not album.in_db:
                    if add_to_db:
                        # if we need to add to the database we call the server with this info
                        try:
                            cls._valid_albums[band_key][album_key].merge(cls.update_album(album))
                            cls._valid_albums[band_key][album_key].in_db = True
                            cls._add_album_to_tree(cls._new_albums, band_key, album_key, album)
                        except:
                            config.logger.exception(f"Could not add album {album.title} of band {album.band} to the db.")
                            cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, album)
                    else:
                        album_logger.warning(f'Album {album.title} of band {album.band} not found in database')
                        cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, album)
        return cls._valid_albums, cls._new_albums, cls._wrong_albums

    @classmethod
    def _get_songs_in_fs(cls, song_list):
        """Gets songs from the given list that exist on the File System.
        Returns:
            [Song]
        """
        fav_songs = []
        if not isinstance(song_list, list):
            config.logger.error(f'song_list is not of list type')
        else:
            # get albums from collection to search for this song list
            albums_dict, _, _ = cls._update_albums_from_collection()
            # for every song in the database result search the album info in the database
            for db_song in song_list:
                # if it's the same band then we continue, otherwise there might be a mistake
                band_key = db_song.album.band.casefold()
                if band_key in albums_dict.keys():
                    found_album = False
                    # now check for all albums for this band in the collection to that one with same database id
                    # show the band name instead of the key
                    for album in albums_dict[band_key].values():
                        if album.id == db_song.album.id:
                            found_album = True
                            song = Song(db_song)  # merge the database info with the info got from the filesystem
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
                                        f'{song.album.title} and band {song.album.band} '
                                        f'among the files of the corresponding album')
                                    # search for the song in the album path
                                    found_song = cls._search_and_update_song_file_name(song)
                            else:
                                songs_logger.info(f'Song with title {song.title} from album title '
                                                  f'{song.album.title} and band {song.album.band} '
                                                  f'does not have a file name in the database'
                                                  f'Trying to find the corresponding file')
                                # search for the song in the album path
                                found_song = cls._search_and_update_song_file_name(song)

                            if found_song:
                                fav_songs.append(song)
                            break
                    if not found_album:
                        songs_logger.info(f"Album with database id {db_song.album.id} not found in "
                                          f"database for song title {db_song.title} and {db_song.id}")
                else:
                    songs_logger.info(f"Band {db_song.album.band} not found in the list of bands")
        config.logger.debug(f"Returning {fav_songs}")
        return fav_songs

    @classmethod
    def _search_and_update_song_file_name(cls, song):
        """Helper to add the file_name attribute to a song when it's empty.
            It will check if there is a music file within the album folder which name contains the title of the song.
            If it's found the file_name attribute will be updated.
        Arguments:
            song(Song)
        Returns:
            boolean indicating if song was found or not.
        """
        found_song = False
        for folder, dirs, files in os.walk(song.album.path):
            for file_name in files:
                if song.title.casefold() in file_name.casefold() and ".mp3" in file_name:
                    found_song = True
                    song.abs_path = os.path.join(folder, file_name)
                    song.file_name = file_name
                    break
        if not found_song:
            songs_logger.info(f'Song with title {song.title} from album title {song.album.title} '
                              f'and band {song.album.band} not found among the files of the corresponding album')

        if not found_song:
            try:
                # call the GUI function to set the file name interactively
                file_name = cls._set_song_data_cb(song)
                if file_name and os.path.isfile(file_name):
                    # getting diff path
                    diff_path = os.path.relpath(file_name, song.album.path)
                    config.logger.info(f"Setting file name from {song.file_name} to {diff_path}")
                    song.file_name = diff_path
                    found_song = True
            except:
                songs_logger.info(
                    f'Could not update Song with title {song.title} from album title {song.album.title} '
                    f'and band {song.album.band} among the files of the corresponding album')

        if found_song:
            # if found try to update this value in the server
            try:
                cls._music_db.api_songs_update_song(song)
            except:
                songs_logger.info(
                    f'Could not update automatically Song with title {song.title} '
                    f'from album title {song.album.title} and band {song.album.band}'
                    f' among the files of the corresponding album')
        return found_song

    @staticmethod
    def get_album_list_for_band(band_name: str, country: str, style: str):
        """
            Gets the album list for the specified band name from the internet.
            :param band_name the band name.
            :param country the country of the band. Used for disambiguation.
            :param style the style of the band. Used also for disambiguation.
        """
        musicbrainzngs.set_useragent("TODO: add name of app", "1.0", "TODO: add EMAIL from settings")
        bands_list = musicbrainzngs.search_artists(artist=band_name, type="group", country=country)
        disambiguation_keywords = style.lower().split()
        filtered_bands = None
        number_of_bands = 0
        # check how many bands are returned in the search 
        # check with the disambiguation contains at least some of the words in the style provided and filter to one band
        if "artist-list" in bands_list.keys():
            bands_with_same_name = [band_info for band_info in bands_list["artist-list"] if
                                    band_info["name"] == band_name]
            number_of_bands = len(bands_with_same_name)
            if number_of_bands == 1:
                filtered_bands = bands_with_same_name
            elif number_of_bands > 1:
                filtered_bands = [band_info for band_info in bands_with_same_name
                                  if
                                  any(word in band_info["disambiguation"].lower() for word in disambiguation_keywords)]
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
                    raise KeyError(f'Date {date} could not be parsed')
                album_year_list.append((release["title"], year))

            return album_year_list
        elif number_of_bands > 1:
            return "Too many bands with this description", [(band["name"], band["disambiguation"]) for band in
                                                            filtered_bands]
        else:
            return f"Could not find the band {band_name} and {country} in musicbrainz"
