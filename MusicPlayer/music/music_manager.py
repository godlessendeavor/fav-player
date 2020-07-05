"""
Created on Dec 3, 2019

@author: thrasher
"""
import difflib
from functools import reduce, lru_cache
import os
from os.path import relpath, exists
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

# TODO: extend the music types
SUPPORTED_MUSIC_TYPES = ['mp3']


class MusicManager:
    _collection_root = config.MUSIC_PATH
    _music_db = config.music_db_api
    _music_dir_tree = None
    # this tree will contain the validated albums
    _valid_albums = {}
    # this tree will contain the non-validated albums
    _wrong_albums = {}
    # this tree will contain the new albums
    _new_albums = {}

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

    @classmethod
    def update_song(cls, song):
        """Function to update a song in the server."""
        if song.validate():
            try:
                cls._music_db.api_songs_update_song(song)
            except ApiException as ex:
                config.logger.exception(f'Could not update song with title {song.title}')
                raise ex
            except Exception as ex:
                config.logger.exception(f'Could not update song with title {song.title}')
                raise ex
            else:
                config.logger.debug(f"Song {song.title} saved to the database")
                return song
        else:
            config.logger.error(f"Some problem with validation of song {song.title}")
            raise Exception(f"Some problem with validation of song {song.title}")

    @classmethod
    def delete_song(cls, song):
        """Function to delete a song from the server."""
        try:
            cls._music_db.api_songs_delete_song(song.id)
        except Exception as ex:
            config.logger.exception(f'Could not delete song with title {song.title} of album with title {song.album.title}')
            raise ex
        else:
            config.logger.debug(f"Song {song.title} deleted from the database")

    @classmethod
    def get_random_favorites(cls, quantity=None, score=None):
        """Gets a list with random songs from the favorites list that complies with the required score.
        Arguments:
            quantity(int): the number of songs to return. If not specified it will return all songs.
            score(float): the minimum score of the song
        Returns:
            [Song]: list of favorite songs that matches the arguments specified
        """
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
    def create_favorites_playlist(cls, score=None, file_path=None):
        """Creates a m3u playlist of all favorite songs above a score
        Args:
            score(float): the minimum score of the songs to create the playlist for
            file_path(str): the target location of the playlist
        """
        if not file_path:
            config.logger.warning("File path for m3u list was not provided")
        else:
            song_list, _ = cls.get_favorites(check_collection=True, score=score)
            if song_list:
                _m3u = open(os.path.join(file_path,"playlist_" + str(score) + ".m3u"), "w")
                for song in song_list:
                    song_path = relpath(song.abs_path, cls._collection_root)
                    _m3u.write(song_path + "\n")
                _m3u.close()

    @classmethod
    def get_favorites(cls, ids=None, check_collection=False, score=None):
        """Gets a list of favorite songs from the database and collection from the given ids.
        If no ids are given it will return all favorites.
        Args:
           ids([int]): The database ids of requested favorite songs.
           check_collection(bool): indicates if the file system should be checked(True) or not(False).
           score(float): minimum score of songs to search
        Returns:
            ([Song], [Song]): tuple of :
                list of favorite songs that matches the arguments specified
                list of invalid songs that fail to run the Song validation
        """
        # TODO: create the interface to retrieve by ids on the server and complete it here
        try:
            result = cls._music_db.api_songs_get_songs(score=score)
        except Exception as ex:
            config.logger.exception('Exception when getting favorite songs')
            raise ex
        if check_collection:
            return cls._get_songs_in_fs(result.songs)
        else:
            return [Song(song) for song in result.songs], []

    @classmethod
    def add_songs_from_reviews(cls):
        """Checks the reviews of all albums to analyze the favorite songs written on them. These are written with double
         quotes in the review. With this it will check if the song exists in the album and try to identify the filename.
         With this it will:
        1) Check if the song is already added as favorite.
        2) If not, add the song to the database with the corresponding info if the file is found
        3) If not found, add to a list to return to the user to find later on.
        Returns:
            [song]: list of songs from the reviews that were not found in the collection.
        """

        songs_not_found = []

        # if the search for the collection was not performed before it will do it now
        if not cls._valid_albums:
            cls._update_albums_from_collection()
        result = cls._music_db.api_songs_get_songs()
        song_db_list = result.songs
        # create a dictionary with album ids as keys and list of favorite songs belonging to that album as values
        song_db_dict = {}
        for song_db in song_db_list:
            if song_db.album.id in song_db_dict:
                song_db_dict[song_db.album.id].append(song_db)
            else:
                song_db_dict[song_db.album.id] = [song_db]
        for band in cls._valid_albums:
            for album in cls._valid_albums[band].values():
                if not album.review:
                    album_logger.error(f'No review for album "{album.title}. Please add a review."')
                else:
                    song_title_list = re.findall(r'"([^"]*)"', album.review)
                    if not song_title_list:
                        album_logger.warning(
                            f'Album {album.title} from band {album.band} has no favorites in the review')
                    else:
                        songs_of_album = song_db_dict.get(album.id)
                        for song in song_title_list:
                            config.logger.info(f'Checking song with title "{song}"')
                            song_found = False
                            if songs_of_album:
                                for song_in_album in songs_of_album:
                                    if song_in_album.title.casefold().strip() == song.casefold().strip():
                                        song_found = True
                                        songs_of_album.remove(song_in_album)
                                        break
                            if song_found:
                                config.logger.info(f'Song {song} was found for album {album.title}')
                            else:
                                new_song = Song()
                                new_song.album = album
                                new_song.title = song
                                # TODO: debatable if it should be initialized this way but it's compulsory so we need
                                #  something
                                new_song.score = album.score
                                if not cls._search_and_update_song_file_name(new_song):
                                    songs_not_found.append(new_song)
        return songs_not_found

    @classmethod
    def add_song_to_favorites(cls, song):
        """Adds a song to the favorites database.
        Arguments:
            song(Song): the song to add
        """
        if isinstance(song, Song):
            if song.validate():
                if not song.file_name:
                    found_song = cls._search_and_update_song_file_name(song)
                    if not found_song:
                        config.logger.error(f'Song needs a file name. Not being able to get one provided from user.')
                        raise Exception
                else:
                    if not song.album.id:
                        config.logger.error(f'Song needs an album with an id.')
                        raise Exception
                song = cls.update_song(song)
            else:
                config.logger.error(f'Error adding a new favorite song to server.')
                raise Exception
        else:
            config.logger.error(f'Song is not of Song type')
            raise Exception
        return song

    @classmethod
    def add_reviews_batch(cls, reviews_path):
        """Gets reviews from text files and sets them in the corresponding albums.
        Arguments:
            reviews_path(str): the reviews path where to get the text files with the reviews to add
        Returns:
            dict with the updated collection of albums
        """
        # if the search for the collection was not performed before it will do it now
        if not cls._valid_albums:
            cls._update_albums_from_collection()
        files_list = [f for f in os.listdir(reviews_path) if os.path.isfile(os.path.join(reviews_path, f))]
        if not files_list:
            raise FileNotFoundError
        for file_name in files_list:
            full_name = os.path.join(reviews_path, file_name)
            file_name_wo_ext = os.path.splitext(file_name)[0]  # remove file extension
            # get the info from the file name
            # the pattern is BAND - ALBUM - SCORE
            # Album name can contain dashes
            first_split = file_name_wo_ext.split('-', 1)
            band_key = first_split[0].casefold().strip()
            second_split = first_split[1].rsplit('-', 1)
            album_key = second_split[0].casefold().strip()
            score = second_split[1].strip()
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
                    cls._add_album_to_tree(cls._wrong_albums, band_key, album_key)
            else:
                config.logger.error(f'Could not find the band {band_key} in the music directory.')
                cls._add_album_to_tree(cls._wrong_albums, band_key, album_key)
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
            if not exists(root_dir):
                raise Exception(f'Collection directory {root_dir} does not exist')
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

    @staticmethod
    def _check_path_in_music_tree(tree_dict, keys):
        """Recursively check a file path in the given dictionary.
        The main purpose for this is to verify existence of files in the music directory tree.
        Args:
            keys(list): the file path split in a list of keys to access the dictionary
        """
        if len(keys) == 1:
            return tree_dict[keys[0]]
        return MusicManager._check_path_in_music_tree(tree_dict[keys[0]], keys[1:])

    @classmethod
    def _add_album_to_tree(cls, tree, band_key, album_key, album=None):
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
        Args:
              add_to_db(boolean): indicates if the albums that are not in the database should be added.
        Returns:
            (dict,dict,dict):
            1) tree with the albums that are both in the collection and the database
            2) tree with the albums that are in the collection but not in the database. This will be empty if add_to_db
            is True
            3) tree with the albums that are not validated correctly
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
                        # add it to the list of valid albums so it can be fixed from the UI
                        cls._valid_albums[band_key][album_key] = Album()
                        cls._valid_albums[band_key][album_key].merge(db_album)
                        cls._valid_albums[band_key][album_key].in_db = True
                        # log missing album from collection
                        album_logger.error(f"{db_album.title} from {db_album.year} "
                                           f"from {db_album.band} not found")
                        album_logger.error(f"Albums from that band are {cls._valid_albums[band_key].keys()}")
                        # add it to the list of wrong albums as well to inform the user
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
                            config.logger.exception(
                                f"Could not add album {album.title} of band {album.band} to the db.")
                            cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, album)
                    else:
                        album_logger.warning(f'Album {album.title} of band {album.band} not found in database')
                        cls._add_album_to_tree(cls._wrong_albums, band_key, album_key, album)
        return cls._valid_albums, cls._new_albums, cls._wrong_albums

    @classmethod
    def _get_songs_in_fs(cls, song_list):
        """Gets songs from the given list that exist on the File System.
        Returns:
            list with the songs that exist on the file system
        """

        existing_songs = []
        wrong_songs = []
        if not isinstance(song_list, list):
            config.logger.error(f'song_list is not of list type')
        else:
            # get albums from collection to search for this song list
            albums_dict, _, _ = cls._update_albums_from_collection()
            # get the music directory tree all at once.
            # When checking for existence of a song file it's more efficient
            music_file_tree = cls._get_music_directory_tree()

            # for every song in the database result search the album info in the database
            for db_song in song_list:
                # if it's the same band then we continue, otherwise there might be a mistake
                song = Song(db_song)  # merge the database info with the info got from the filesystem
                band_key = db_song.album.band.casefold()
                if band_key in albums_dict.keys():
                    found_album = False
                    # now check for all albums for this band in the collection to that one with same database id
                    # show the band name instead of the key
                    for album in albums_dict[band_key].values():
                        if album.id == db_song.album.id:
                            found_album = True
                            song.album = Album()
                            song.album.merge(album)
                            found_song = False
                            if song.file_name:
                                abs_path = os.path.join(album.path, song.file_name)
                                file_path, song_file_name = os.path.split(abs_path)
                                relative_path = relpath(file_path, cls._collection_root)
                                relative_path = relative_path.split('/')
                                files = cls._check_path_in_music_tree(music_file_tree, relative_path)
                                if song_file_name in files:
                                    song.set_abs_path(abs_path)
                                    found_song = True
                                else:
                                    songs_logger.info(
                                        f'Could not find song with title {song.title} and file {song.file_name} '
                                        f'from album title {song.album.title} and band {song.album.band} '
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
                                existing_songs.append(song)
                                break
                            else:
                                wrong_songs.append(song)

                    if not found_album:
                        songs_logger.info(f"Album with database id {db_song.album.id} not found in "
                                          f"database for song title {db_song.title} and {db_song.id}. "
                                          f"Albums of band {db_song.album.band} are:"
                                          f"{albums_dict[band_key].values()}")
                        wrong_songs.append(song)
                else:
                    songs_logger.info(f"Band {db_song.album.band} not found in the list of bands")
                    wrong_songs.append(song)
        return existing_songs, wrong_songs

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
        song_files = {}
        # get all songs in the album path and check if the name is equal to the song title
        for folder, dirs, files in os.walk(song.album.path):
            for file_name in files:
                abs_path = os.path.join(folder, file_name)
                # check if file is any of the music supported types
                if any(ext in song.title.casefold() for ext in SUPPORTED_MUSIC_TYPES):
                    if song.title.casefold() in file_name.casefold():
                        found_song = True
                        song.abs_path = abs_path
                        diff_path = relpath(abs_path, song.album.path)
                        song.file_name = diff_path
                        break
                    # if not found keep extending the dict with the files to search for close matches later
                    else:
                        song_files[file_name] = abs_path
            # if not found we extend the list in order to search for close matches later
            if found_song:
                break

        # if not found then we check for close matches
        if not found_song:
            match_song = difflib.get_close_matches(song.title, song_files.keys(), n=1, cutoff=0.7)
            if match_song:
                found_song = True
                song.abs_path = song_files[match_song[0]]
                diff_path = relpath(song.abs_path, song.album.path)
                song.file_name = diff_path

        if not found_song:
            songs_logger.info(f'Song with title {song.title} from album title {song.album.title} '
                              f'and band {song.album.band} not found among the files of the corresponding album')
        else:
            # if found try to update this value in the server
            try:
                cls._music_db.api_songs_update_song(song)
                config.logger.info(f"Added song with title {song.title}")
            except:
                songs_logger.exception(
                    f'Could not update automatically Song with title {song.title} '
                    f'from album title {song.album.title} and band {song.album.band}'
                    f' among the files of the corresponding album')
        return found_song

    @classmethod
    def get_missing_albums_for_bands(cls, band_list):
        """Gets a list of the albums from the given bands which are not present on the collection.
        Args:
            [band(str)]
        Returns:
            dict(band:dict(album_title(str):album(Album))
        """
        result = {}
        for band in band_list:
            if band.casefold() in cls._valid_albums:
                band_collection = list(cls._valid_albums[band.casefold()].values())
                country = band_collection[0].country
                style = band_collection[0].style
                try:
                    releases = cls.get_album_list_for_band(band, country, style)
                except KeyError:
                    config.logger.exception(f"Could not find list for band {band}")
                else:
                    if releases:
                        # do casefold for releases, get a set to compare with the releases set later
                        releases_set = set(map(lambda x: x.casefold(), releases[band].keys()))
                        # do it for the dict as well to retrieve the album later
                        releases_lower = {k.casefold():v for k,v in releases[band].items()}
                        # do casefold for albums in collection
                        band_collection_low = list(map(lambda album: album.title.casefold(), band_collection))
                        diff_list = list(releases_set.difference(band_collection_low))
                        for title in diff_list:
                            cls._add_album_to_tree(result, band, title, releases_lower[title])
            else:
                config.logger.error(f'Band {band} is not in the collection')
        return result

    @classmethod
    def get_album_list_for_band(cls, band_name: str, country: str, style: str):
        """Gets the album list for the specified band name from the internet.
        Args:
            band_name(str): the band name.
            country(str): the country of the band. Used for disambiguation.
            style(str): the style of the band. Used also for disambiguation.
        Raises:
            KeyError: if no match for the given arguments has been found in the databases
        Returns:
            [(album(str), year(str)]
        """
        album_dict = {}
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
            # TODO: filter out EPs or add them in type
            release_list = filter(lambda item: (item["type"] != "Compilation"), result["artist"]["release-group-list"])
            for release in release_list:
                date = release["first-release-date"]
                year = 1900
                try:
                    year = date_parser.parse(date).year
                except ValueError:
                    config.logger.exception(f'Date {date} for release {release["title"]} could not be parsed')
                album = Album()
                album.title = release["title"]
                album.band = band_name
                album.year = year
                album.type = release["type"]
                cls._add_album_to_tree(album_dict, band_name, album.title, album)

            return album_dict
        elif number_of_bands > 1:
            band_list = [(band["name"], band["disambiguation"]) for band in filtered_bands]
            raise KeyError(f'Too many bands with description "{band_name}:{country}:{style}" : {band_list}')
        else:
            raise KeyError(f"Could not find the band {band_name} and {country} in musicbrainz")
