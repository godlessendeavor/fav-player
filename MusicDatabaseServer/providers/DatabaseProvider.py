#import requests
song = {
        "_id":"123",
        "title": "Northern Chaos gods",
        "band": "Immortal",
        "album": "Northern Chaos Gods",
        "total_lenght": "4:34",
        "abs_path": "/home/thrasher/Downloads/2018\ -\ Northern\ Chaos\ Gods/01\ -\ Northern\ Chaos\ Gods\.mp3",
        "score":"7.5"
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
    
    