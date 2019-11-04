#import requests
song = {
        "_id":"123",
        "title": "Northern Chaos gods",
        "score":"7.5",
        "disc_id":"13456"
        }

album = {
         "_id":"234589",
         "band":"Slayer",
                 }


class DatabaseProvider(object):
    
    def get_songs(self, quantity, score) -> str:
        return song,200
    
    def create_song(self, song) ->str:
        print(song)
        return 200
    
    def update_song(self, song) ->str:
        print(song)
        return 200
    
    def delete_song(self, song_id) ->str:
        print(song_id)
        return 200
    
    def get_albums(self, quantity) -> str:
        return album,200
    
    def create_album(self, album) ->str:
        print(album)
        return 200
    
    def update_album(self, album) ->str:
        print(album)
        return 200
    
    def delete_album(self, album_id) ->str:
        print(album_id)
        return 200
    
    