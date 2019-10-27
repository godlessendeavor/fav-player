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
    
    def get_song(self, quantity, score) -> str:
        print("Number of songs requested is "+str(quantity))
        print("Score requested is"+str(score))
        return song,200