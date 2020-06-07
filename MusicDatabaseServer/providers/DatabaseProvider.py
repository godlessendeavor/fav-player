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
                         **{'charset': 'utf8',
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
    copy = CharField(constraints=[SQL("DEFAULT ' '")])
    band = CharField(column_name='groupName', constraints=[SQL("DEFAULT ' '")])
    country = CharField(column_name='loc', constraints=[SQL("DEFAULT ' '")])
    score = CharField(column_name='mark', constraints=[SQL("DEFAULT ' '")])
    review = TextField(null=True)
    style = CharField(constraints=[SQL("DEFAULT ' '")])
    title = CharField(constraints=[SQL("DEFAULT ' '")])
    type = CharField(constraints=[SQL("DEFAULT ' '")])
    year = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)

    class Meta:
        table_name = 'music'


class Favorites(BaseModel):
    id = AutoField(column_name='Id')
    album_id = ForeignKeyField(Album, column_name='disc_id', backref='favorites')
    score = FloatField(constraints=[SQL("DEFAULT 0")])
    track_number = IntegerField(column_name='track_no', constraints=[SQL("DEFAULT 0")])
    title = CharField(column_name='track_title')
    file_name = CharField()
    type = TextField(null=True)

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

    def _get_album_for_song(self, song):
        """
            Fills in the album info for a given song
        """
        if song and song['album_id']:
            album_list, result = self.get_albums(None, song['album_id'])
            if result == 200:
                song['album'] = album_list[0]
            else:
                logger.error(f"Could not find album for song with album id {song['album_id']} and song id {song['id']}")
                return None
            return song
        else:
            logger.error(f"Could not get a song or album id for {song}")
            return None

    @database_mgmt
    def get_songs(self, quantity, score):
        """
            Get songs from the favorites table by quantity and score
        """
        # get result from database as Peewee model
        if quantity:
            result = Favorites.select() \
                .where(Favorites.score > score) \
                .order_by(fn.Rand()).limit(int(quantity))
        else:
            result = Favorites.select()
        # No, I will not do a JOIN. Some column names are the same in both tables (title for example)
        # The simple Join query on Peewee will override those names
        # That means that every column with shared name has to be given an alias and then map back to the
        # corresponding model. A bit too much and I'm not worried about efficiency here
        list_result = [song for song in result.dicts() if self._get_album_for_song(song)]
        logger.debug('Getting result for get_songs: %s', list_result)
        return {'songs': list_result}

    @database_mgmt
    def create_song(self, song):
        """Creates a song on the favorites table."""
        if song:
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
                logger.warning('Type of song was not provided for song: ', song)

            try:
                # id was provided so it was already on the database. This will update the existing song
                fav.id = song['id']
            except KeyError:
                # Id was not provided search song by title and album_id, perhaps it already exists
                result = self._search_song_by_title_and_album_id(fav.title, fav.album_id)
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
        else:
            return None, 400

    @database_mgmt
    def update_song(self, song) -> str:
        """
            Updates an existing song in the favorites table. Creates it if not existing.
        """
        return self.create_song(song)

    @database_mgmt
    def delete_song(self, song_id) -> str:
        """
            Deletes a song from the favorites table.
        """
        fav = Favorites.get(Favorites.id == song_id)
        try:
            fav.delete_instance()
        except Exception as ex:
            logger.error('Exception when deleting favorite song: ' + str(ex))
            return song_id, 400
        return song_id, 200

    @database_mgmt
    def get_albums(self, quantity, album_id) -> str:
        # TODO: get album list if album_id is a list
        if album_id:
            result = Album.select().where(Album.id == album_id)
        elif quantity:
            result = Album.select().order_by(fn.Rand()).limit(int(quantity))
        else:
            result = Album.select()
        if result:
            list_result = [row for row in result.dicts()]
            logger.debug('Getting result for get_album: %s', list_result)
            return list_result, 200
        else:
            logger.error(f"Could not find album with id {album_id}")
            return album_id, 400

    @database_mgmt
    def create_album(self, album) -> str:
        # load the object and convert to album
        # TODO: could we use the next line to convert to object with attributes from json dict?
        # album_entry = json.loads(album, object_hook=lambda d: Namespace(**d))

        album_entry = Album()
        # first copy compulsory fields and validate types
        try:
            album_entry.band = album['band']
            album_entry.title = album['title']
            album_entry.year = int(album['year'])
        except KeyError:
            logger.exception('Exception on key when creating album.')
            return album, 400
        except ValueError:
            logger.exception('Exception on value when creating album.')
            return album, 400
        # now copy optional fields
        if 'score' in album:
            try:
                album_entry.score = float(album['score'])
            except ValueError as ex:
                logger.warning('Exception on score when creating album %s. %s', album, ex)
        if 'review' in album:
            album_entry.review = album['review']
        if 'type' in album:
            album_entry.type = album['type']
        if 'country' in album:
            album_entry.country = album['country']
        if 'copy' in album:
            album_entry.copy = album['copy']
        if 'style' in album:
            album_entry.style = album['style']
        # if an update is done we will need the id as well
        if 'id' in album:
            album_entry.id = album['id']
        # save object in database
        logger.debug(f'Saving album {album_entry} in database')
        if album_entry.save():
            album['id'] = album_entry.id
            return album, 200
        else:
            # TODO: how to identify a failure from a case where there are no changes
            logger.error(f'Could not save album {album_entry} in database. Maybe there are no changes')
            return album, 400

    @database_mgmt
    def update_album(self, album) -> str:
        return self.create_album(album)

    @database_mgmt
    def delete_album(self, album_id) -> str:
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
