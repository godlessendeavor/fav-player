from vlc import MediaPlayer, MediaListPlayer, MediaList

from config import config

#Function to check if attribute _media exists
def check_media(func):
    def inner(self, *args, **kwargs):
        if self._media is None:
            config.logger.warning("Can't call Media Player without setting a file or a file list first")
            #TODO: raise exception or print error?
            #raise ValueError
        else:
            return func(self, *args, **kwargs)
    return inner

class MyMediaPlayer(object):
    """Simple audio/video player.
    """
    def __init__(self):
        self._media = None
    
    @check_media     
    def play(self, fname):
        self._media = MediaPlayer(fname)
        self._media.play()
    
    @check_media 
    def play_list(self, flist):
        mlp = MediaListPlayer()
        self._media = MediaPlayer()
        mlp.set_media_player(self._media)        
        ml = MediaList()
        for song_path in flist:
            ml.add_media(song_path)

        mlp.set_media_list(ml)
        mlp.play()
     
    @check_media    
    def stop(self):
        self._media.stop()
    
    @check_media 
    def pause(self):
        self._media.pause()
    
    @check_media    
    def get_time(self):
        return self._media.get_time()
    
    @check_media 
    def set_volume(self, volume):
        if isinstance(volume, str):
            volume = float(volume)
        if isinstance(volume, (float, int)):
            volume = int(round(volume))
        self._media.audio_set_volume(volume)
    
    @check_media     
    def is_playing(self):
        self._media.is_playing()
   
    @check_media 
    def get_length(self):
        self._media.get_duration()
        
