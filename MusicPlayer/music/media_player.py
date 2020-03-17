from vlc import Instance, MediaPlayer, MediaListPlayer, MediaList, EventType

from config import config
import time


def check_media(func):
    '''
        Decorator to check if attribute _media exists
    '''
    
    def inner(self, *args, **kwargs):
        if hasattr(self, "_media"):
            if self._media:
                config.logger.debug(f"Can't call Media Player without setting a file or a file list first. Called from {func}")
                # TODO: raise exception or print error?
                # raise ValueError
            else:
                # only call function if media player is set
                return func(self, *args, **kwargs)
    return inner



class MyMediaPlayer(object):
    """
        Simple audio/video player based on VLC player.
    """
    
    def __init__(self):
        self._vlc_instance = Instance()
        self._song_changed_func = None
        
    def subscribe_song_finished(self, func, *args, **kwargs):
        '''
            Subscriber for when player finishes a song
        '''
        self._song_changed_func = func
        
        
    #TODO: change function name and add a subscriber for the GUI
    def check_event(self, event):
        '''
            Event for when a player finishes a song.
        '''
        print(f'Event happened {event}')
        if self._song_changed_func:
            self._song_changed_func()
            
    def play(self, media):  
        '''
            Plays the given file. (
            media can be 
             - an absolute path or
             - a list of files given in flist
        '''   
        # stop any current play
        self.stop() 
        if isinstance(media, str):
            media = ([media])       
                  
        _media_list = self._vlc_instance.media_list_new(media)                 
        mlp = MediaListPlayer()
        self._media = MediaPlayer()
        mlp.set_media_player(self._media)  
        mlp.set_media_list(_media_list)
        self._media.event_manager().event_attach(EventType.MediaPlayerEndReached, self.check_event)        
        mlp.play()              

     
    @check_media    
    def stop(self):
        '''
            Stops the player.
        '''
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
        return self._media.is_playing()
   
    @check_media 
    def get_length(self):
        '''
            Gets the length of the current media playing.
        '''
        return self._media.get_duration()
    
    @check_media
    def get_mp3_info(self):
        '''
            Gets the info from the mp3 playing currently
        '''
        # TODO
        pass
            
            
        
        
