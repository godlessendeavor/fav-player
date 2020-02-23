from peewee import *
from config import config
import logging

#set log configuration
log_level = logging.getLevelName(config.LOGGING_LEVEL)

logging.basicConfig(
    format='[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

#set database configuration
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
    loc = CharField(constraints=[SQL("DEFAULT ' '")])
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
    disc_id = ForeignKeyField(Album, backref='favorites')
    score = FloatField(constraints=[SQL("DEFAULT 0")])
    track_no = IntegerField(constraints=[SQL("DEFAULT 0")])
    track_title = CharField()
    file_name = CharField()
    type = TextField(null=True)

    class Meta:
        table_name = 'favorites'


def database_mgmt(func):
    '''
        Function decorator for opening/closing the database. Useful for each method that requires access to the database
    '''
    def wrapper_do_open_close(*args, **kwargs):
        database.connect(reuse_if_open=True) 
        ex = None
        try:
            ret = func(*args, **kwargs)
        except Exception as ex:
            logger.warning('Holding exception to close Database')
        if not database.is_closed():
            database.close()
        if ex: 
            raise(ex)
        return ret
    return wrapper_do_open_close


class DatabaseProvider(object):
    
    fav_name_map = {'id': 'id', 'disc_id': 'disc_id', 'track_title': 'title', 'file_name': 'file_name', 'score': 'score', 'track_no': 'track_number', 'type': 'type'}
    
    @database_mgmt       
    def _search_song_by_title_and_album_id(self, song_title, album_id):
        result = Favorites.select().where((Favorites.disc_id == album_id) & (Favorites.track_title == song_title))
        return [row for row  in result.dicts()]
    
    @database_mgmt
    def get_songs(self, quantity, score):
        #get result from database as Peewee model
        result = Favorites.select().where(Favorites.score > score).order_by(fn.Rand()).limit(int(quantity))
        #get results from the query and map the key names to the app_definition response object names
        list_result = [{DatabaseProvider.fav_name_map[name]: val for name, val in row.items()} for row  in result.dicts()]
        logger.debug('Getting result for get_songs: %s', list_result)
        return {'songs' : list_result}
    
    @database_mgmt
    def create_song(self, song) ->str:
        fav = Favorites()
        #first copy compulsory fields and validate types
        try:            
            fav.track_no = int(song['track_number'])
            fav.track_title = song['title']
            fav.score = float(song['score'])
            fav.disc_id = int(song['disc_id'])
            fav.file_name = song['file_name']
        except KeyError:
            logger.exception('Exception on key when creating favorite song')
            return song, 400
        except ValueError:
            logger.exception('Exception on value when creating favorite song')
            return song, 400
        #now copy optional fields
        try:
            fav.type = song['type']            
        except KeyError:
            logger.warning('Type of song was not provided for song: ', song)   
        
        try:
            fav.type = song['_id']
        except KeyError:
            #Id was not provided search song by title and disc_id, perhaps it already exists            
            result = self._search_song_by_title_and_album_id(fav.track_title, fav.disc_id)
            if result[0]:
                try:
                    fav.id = result[0]['id']
                except KeyError:
                    logger.exception('Exception on value when creating favorite song')
        #save object in database
        fav.save()
        return song,200
    
    @database_mgmt
    def update_song(self, song) ->str:
        return self.create_song(song)
    
    @database_mgmt
    def delete_song(self, song_id) ->str:
        fav = Favorites.get(Favorites.id == song_id)
        try:
            fav.delete_instance()
        except Exception as ex:
            logger.error('Exception when deleting favorite song: '+str(ex))
            return song_id, 400
        return song_id, 200
    
    @database_mgmt
    def get_albums(self, quantity, album_id) -> str:
        if album_id:
            result = Album.select().where(Album.id == album_id)          
        elif quantity:
            result = Album.select().order_by(fn.Rand()).limit(int(quantity))
        else:
            result = Album.select()
        if result:
            list_result = [row for row  in result.dicts()]   
            logger.debug('Getting result for get_songs: %s', list_result) 
            return list_result,200
        else:
            return album_id, 400
    
    @database_mgmt
    def create_album(self, album) ->str:
        #load the object and convert to album
        #TODO: could we use the next line to convert to object with attributes from json dict?
        #album_entry = json.loads(album, object_hook=lambda d: Namespace(**d))       
        
        album_entry = Album()
        #first copy compulsory fields and validate types
        try:            
            album_entry.group_name = album['band']
            album_entry.title      = album['title']
            album_entry.path       = album['path']
            album_entry.year       = int(album['year'])
        except KeyError:
            logger.exception('Exception on key when creating album')
            return album, 400
        except ValueError:
            logger.exception('Exception on value when creating album')
            return album, 400
        #now copy optional fields
        try:
            album_entry.mark     = float(album['score'])   
            album_entry.review   = album['review']
            album_entry.type     = album['type']
            album_entry.loc      = album['country']   
            album_entry.copy     = album['copy']
            album_entry.style    = album['style']  
        except KeyError:
            logger.warning('Type was not provided for album: ', album)  
        except ValueError:
            logger.warning('Exception on value when creating album', album) 
        return album, 200
    
    @database_mgmt
    def update_album(self, album) ->str:
        return self.create_album(album)
    
    @database_mgmt
    def delete_album(self, album_id) ->str:
        album_entry = Album.get(Album.id == album_id)
        try:
            album_entry.delete_instance()
        except Exception:
            logger.exception('Exception when deleting album')
            return album_id, 400
        return album_id, 200

    #TODO: implement this in a different way or add behavior (like checking connection to database)
    def get(self):
        return "OK",200
    
    