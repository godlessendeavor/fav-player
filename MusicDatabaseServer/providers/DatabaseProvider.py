#import requests
song = {
        "_id":"123",
        "title": "Northern Chaos gods",
        "score":"7.5",
        "disc_id":"13456"
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
    
    