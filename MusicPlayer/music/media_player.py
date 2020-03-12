from vlc import MediaPlayer, MediaListPlayer, MediaList, EventType

from config import config


def check_media(func):
    '''
        Decorator to check if attribute _media exists
    '''
    
    def inner(self, *args, **kwargs):
        if self._media is None:
            config.logger.warning("Can't call Media Player without setting a file or a file list first")
            # TODO: raise exception or print error?
            # raise ValueError
        else:
            # only call function if media player is set
            return func(self, *args, **kwargs)
    return inner


def check_event(event):
    print('Event happened')


class MyMediaPlayer(object):
    """
        Simple audio/video player based on VLC player.
    """
    def __init__(self):
        self._media = None
     
    def play(self, fname):
        '''
            Plays the given file. (fname must be an absolute path)
        '''
        self._media = MediaPlayer(fname)
        self._event_manager = self._media.event_manager()
        self._event_manager.event_attach(EventType.MediaListPlayerNextItemSet, check_event)
        self._media.play()
    
    def play_list(self, flist):
        '''
            Plays the list of files given in flist
        '''
        # stop any current play
        self.stop()            
        mlp = MediaListPlayer()
        self._media = MediaPlayer()
        mlp.set_media_player(self._media)  
        self._event_manager = self._media.event_manager()
        self._event_manager.event_attach(EventType.MediaListPlayerNextItemSet, check_event)     
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
        '''
            Pauses and resumes the music.
        '''
        self._media.pause()
    
    @check_media    
    def get_time(self):
        '''
            Gets the elapsed time of the current song.
        '''
        return self._media.get_time()
    
    @check_media 
    def set_volume(self, volume):
        '''
            Sets the volume of the player.
        '''
        if isinstance(volume, str):
            volume = float(volume)
        if isinstance(volume, (float, int)):
            volume = int(round(volume))
        self._media.audio_set_volume(volume)
    
    @check_media     
    def is_playing(self):
        '''
            Checks if any media is playing.
        '''
        self._media.is_playing()
   
    @check_media 
    def get_length(self):
        '''
            Gets the length of the current media playing.
        '''
        self._media.get_duration()
        
