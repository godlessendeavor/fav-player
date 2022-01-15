from peewee import *
from config import config
import logging

# set log configuration
log_level = logging.getLevelName(config.LOGGING_LEVEL)

logging.basicConfig(
    format='[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

# set database configuration
database = MySQLDatabase(config.DATABASE_NAME,
                         **{'charset': 'utf8mb4',
                            'sql_mode': 'PIPES_AS_CONCAT',
                            'use_unicode': True,
                            'host': config.DATABASE_HOST,
                            'port': config.DATABASE_PORT,
                            'user': config.DATABASE_USER,
                            'password': config.DATABASE_PASSWORD})


class BaseModel(Model):
    class Meta:
        database = database


class Album(BaseModel):
    id = AutoField(column_name='Id')
    copy = CharField(constraints=[SQL("DEFAULT ''")], default='')
    band = CharField(constraints=[SQL("DEFAULT ''")], default='')
    country = CharField(constraints=[SQL("DEFAULT ''")], default='')
    score = CharField(constraints=[SQL("DEFAULT ''")], default='')
    review = TextField(null=True, default='')
    style = CharField(constraints=[SQL("DEFAULT ''")], default='')
    title = CharField(constraints=[SQL("DEFAULT ''")], default='')
    type = CharField(constraints=[SQL("DEFAULT ''")], default='')
    year = IntegerField(constraints=[SQL("DEFAULT 0")], null=True, default=0)

    class Meta:
        table_name = 'music'


class Favorites(BaseModel):
    id = AutoField(column_name='Id')
    album_id = ForeignKeyField(Album, column_name='album_id', backref='favorites')
    score = FloatField(constraints=[SQL("DEFAULT 0")], default=0)
    track_number = IntegerField(constraints=[SQL("DEFAULT 0")], default='')
    title = CharField(column_name='track_title', default='')
    file_name = CharField()
    type = TextField(null=True, default='')

    class Meta:
        table_name = 'favorites'


def database_mgmt(func):
    """
        Function decorator for opening/closing the database. Useful for each method that requires access to the database
    """

    def wrapper_do_open_close(*args, **kwargs):
        database.connect(reuse_if_open=True)
        ex = None
        try:
            ret = func(*args, **kwargs)
        except Exception as ex:
            logger.warning('Holding exception to close Database')
            logger.exception(ex)
            if not database.is_closed():
                database.close()
            raise (ex)
        if not database.is_closed():
            database.close()
        return ret

    return wrapper_do_open_close


class DatabaseProvider(object):

    @database_mgmt
    def _search_song_by_title_and_album_id(self, song_title, album_id):
        """
            Gets a song from the favorites table by song title and album id.
        """
        result = Favorites.select().where((Favorites.album_id == album_id) & (Favorites.title == song_title))
        return [row for row in result.dicts()]

    @database_mgmt
    def _search_song_by_file_name_and_album_id(self, file_name, album_id):
        """
            Gets a song from the favorites table by file name and album id.
        """
        result = Favorites.select().where((Favorites.album_id == album_id) & (Favorites.file_name == file_name))
        return [row for row in result.dicts()]

    def _get_album_for_song(self, song):
        """Fills in the album info for a given song
        Args:
            song(dict): the song to fill the info for
        """
        if not song and not song['album_id']:
            logger.error(f"Could not get a song or album id for {song}")
            return None

        album_list, result = self.get_album_by_id(song['album_id'])
        if result == 200:
            song['album'] = album_list[0]
        else:
            logger.error(f"Could not find album for song with album id {song['album_id']} and song id {song['id']}")
            return None
        return song


    @database_mgmt
    def get_random_songs(self, quantity=None, score=None):
        """Get songs from the favorites table by quantity and score
        Args:
            quantity(int): limit of songs to retrieve
            score(float): minimum score of songs to retrieve (Values are from 0 to 10, but no validation is done here)
        Returns:
            dict: with 'songs' as key and the song list as value
        """
        # get result from database as Peewee model
        if quantity and score:
            result = Favorites.select() \
                .where(Favorites.score > score) \
                .order_by(fn.Rand()).limit(int(quantity))
        elif quantity:
            result = Favorites.select() \
                .order_by(fn.Rand()).limit(int(quantity))
        elif score:
            result = Favorites.select() \
                .where(Favorites.score > score)
        else:
            result = Favorites.select()
        # No, I will not do a JOIN. Some column names are the same in both tables (title for example)
        # The simple Join query on Peewee will override those names
        # That means that every column with shared name has to be given an alias and then map back to the
        # corresponding model. A bit too much effort and not clean. I'm not worried about efficiency here
        list_result = [song for song in result.dicts() if self._get_album_for_song(song)]
        logger.debug('Getting result for get_songs: %s', list_result)
        return {'songs': list_result}

    @database_mgmt
    def create_song(self, song):
        """Creates a song on the favorites table.
        Args:
            song(dict): the song to add to the table.
        """
        if not song:
            logger.error("No song was provided")
            return None, 400

        fav = Favorites()
        # first copy compulsory fields and validate types
        try:
            fav.title = song['title']
            fav.score = float(song['score'])
            fav.album_id = int(song['album']['id'])
            fav.file_name = song['file_name']
        except KeyError:
            logger.exception('Exception on key when creating favorite song')
            return song, 400
        except ValueError:
            logger.exception('Exception on value when creating favorite song')
            return song, 400
        # now copy optional fields
        try:
            fav.track_number = int(song['track_number'])
            fav.type = song['type']
        except KeyError:
            logger.warning('Type of song or track number was not provided for song: ', song)

        try:
            # id was provided so it was already on the database. This will update the existing song
            fav.id = song['id']
        except KeyError:
            # Id was not provided search song by title and album_id, in case it already exists
            result = self._search_song_by_file_name_and_album_id(fav.file_name, fav.album_id)
            if result and result[0]:
                try:
                    # id exists add it to the object to save to update the existing one
                    fav.id = result[0]['id']
                except KeyError:
                    logger.exception('Exception on value when creating favorite song')
                    return None, 400
        # save object in database
        fav.save()
        return song, 200

    @database_mgmt
    def update_song(self, song):
        """Updates an existing song in the favorites table. Creates it if not existing.
        Args:
            song(dict): the song to update
        """
        return self.create_song(song)

    @database_mgmt
    def delete_song(self, file_name=None, album_title=None, band=None):
        """Deletes a song from the favorites table.
        Args:
            file_name(str): The file name of the song to delete
            album_title(str): the album of the song to delete
            band(str): the band of the song to delete
        """
        albums, res = self.get_album(album_title, band)
        if res != 200:
            logger.error(f"Could not find the album {album_title} for band {band} to delete song {file_name}")
            return None, 404
        fav = Favorites.get((Favorites.file_name == file_name) & (Favorites.album_id == albums[0]['id']))
        try:
            fav.delete_instance()
        except Exception as ex:
            logger.exception(f'Exception when deleting favorite song with file_name {file_name}')
            return file_name, 400
        return file_name, 200

    @database_mgmt
    def get_album(self, album_title, band):
        """Gets an album by its title and band name
        Args:
            album_title(str): the id of the album to get
            band(str): the name of the band
        """
        result = Album.select().where((Album.band == band) & (Album.title == album_title))
        if result:
            list_result = [row for row in result.dicts()]
            logger.debug('Getting result for get_album: %s', list_result)
            return list_result, 200
        else:
            logger.error(f"Could not find album with title {album_title} for band {band}")
            return album_title, 400

    @database_mgmt
    def get_album_by_id(self, album_id):
        """Gets an album by its id
        Args:
            album_id(int): the id of the album to get
        """
        result = Album.select().where(Album.id == album_id)
        if result:
            list_result = [row for row in result.dicts()]
            logger.debug('Getting result for get_album_by_id: %s', list_result)
            return list_result, 200
        else:
            logger.error(f"Could not find album with id {album_id}")
            return album_id, 400

    @database_mgmt
    def get_random_albums(self, quantity):
        """Gets random albums
        Args:
            quantity(int): the number of albums to retrieve
        """
        result = Album.select().order_by(fn.Rand()).limit(int(quantity))
        if result:
            list_result = [row for row in result.dicts()]
            logger.debug('Getting result for get_random_album: %s', list_result)
            return list_result, 200
        else:
            logger.error(f"Could not find random albums")
            return quantity, 400

    @database_mgmt
    def create_album(self, album) -> str:
        """
        Creates/Updates an album into the database.
        Args:
            album(dict): the album dict with fields named as the Album model
        """
        # load the object and convert to album
        db_album = Album()
        # first let's check if the album provided already exists
        album_res, result = self.get_album(album_title=album['title'], band=album['band'])
        if result == 200:
            logger.info(f"Album with title {album['title']} already exists. Trying to update")
            db_album.id = album_res[0]['id']
        elif 'id' in album:
            # if an update is done we will need the id as well
            db_album.id = album['id']

        # first copy compulsory fields and validate types
        try:
            db_album.band = album['band']
            db_album.title = album['title']
            db_album.year = int(album['year'])
        except KeyError:
            logger.exception('Exception on key when creating album.')
            return album, 400
        except ValueError:
            logger.exception('Exception on value when creating album.')
            return album, 400
        # now copy optional fields
        if 'score' in album:
            try:
                db_album.score = float(album['score'])
            except ValueError as ex:
                logger.warning('Exception on score when creating album %s. %s', album, ex)
        if 'review' in album:
            db_album.review = album['review']
        if 'type' in album:
            db_album.type = album['type']
        if 'country' in album:
            db_album.country = album['country']
            logger.debug(f'Country is {db_album.country}')
        if 'copy' in album:
            db_album.copy = album['copy']
        if 'style' in album:
            db_album.style = album['style']
        # save object in database
        logger.debug(f'Saving album with title {db_album.title} for band {db_album.band} in database')
        if db_album.save():
            album['id'] = db_album.id
            return album, 200
        else:
            # TODO: how to identify a failure from a case where there are no changes
            logger.error(f'Could not save album {db_album} in database. Maybe there are no changes')
            return album, 500

    @database_mgmt
    def update_album(self, album) -> str:
        """
        Updates an album.
        Args:
            album(dict): the album dict with fields named as the Album model
        """
        return self.create_album(album)

    @database_mgmt
    def delete_album(self, album_id) -> str:
        """
        Deletes an album.
        Args:
            album_id(int): the album id
        """
        album_entry = Album.get(Album.id == album_id)
        try:
            album_entry.delete_instance()
        except Exception:
            logger.exception('Exception when deleting album')
            return album_id, 400
        return album_id, 200

    # TODO: implement this in a different way or add behavior (like checking connection to database)
    def get(self):
        return "OK", 200
