from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model
from config import config
import json


import logging

logging.basicConfig(
    format='[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s',
    level=logging.DEBUG
)


database = MySQLDatabase('music', 
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
    group_name = CharField(column_name='groupName', constraints=[SQL("DEFAULT ' '")])
    loc = CharField(constraints=[SQL("DEFAULT ' '")])
    mark = CharField(constraints=[SQL("DEFAULT ' '")])
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
    type = TextField(null=True)

    class Meta:
        table_name = 'favorites'


class DatabaseProvider(object):
    
    def __init__(self):
        database.connect() 
    
    def get_songs(self, quantity, score) -> str:
        #get result from database as Peewee model
        result = Favorites.select().where(Favorites.score > score).order_by(fn.Rand()).limit(int(quantity))
        list_result = [row for row  in result.dicts()]
        return json.dumps(list_result),200
    
    def create_song(self, song) ->str:
        print(song)
        return 200
    
    def update_song(self, song) ->str:
        print(song)
        return 200
    
    def delete_song(self, song_id) ->str:
        print(song_id)
        return 200
    
    def get_albums(self, quantity, album_id) -> str:
        if album_id:
            result = Album.select().where(Album.id == album_id)          
        elif quantity:
            result = Album.select().order_by(fn.Rand()).limit(int(quantity))
        else:
            result = Album.select()
        if result:
            list_result = [row for row  in result.dicts()]    
            return json.dumps(list_result),200
        else:
            return 400
    
    def create_album(self, album) ->str:
        print(album)
        return 200
    
    def update_album(self, album) ->str:
        print(album)
        return 200
    
    def delete_album(self, album_id) ->str:
        print(album_id)
        return 200
    
    