from vlc import Instance, MediaPlayer, MediaListPlayer, MediaList, EventType, State

from config import config
from music.song import Song


def check_media(func):
    '''
        Decorator to check if attribute _media exists
    '''
    
    def inner(self, *args, **kwargs):
        if hasattr(self, "_media"):
            if not self._media:
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
        self._volume = 100
        self._song_list = []
        self._song_changed_func = None
        
    def subscribe_song_finished(self, func, *args, **kwargs):
        '''
            Subscriber for when player finishes a song
        '''
        self._song_changed_func = func
        
    def finished_song_event(self, event):
        '''
            Event for when a player finishes a song.
        '''
        config.logging.debug(f'Event from VLC player: {event}')
        self._play_next()
        if self._song_changed_func:
            self._song_changed_func()
            
    def play(self, song_list = None):  
        '''
            Plays the given song list (a list of Song objects).
        '''  
        if not self._song_list and not song_list:
            config.logger.error(f'A playlist needs to be provided before playing.')
            return
        if song_list:
            if not isinstance(song_list, list):
                config.logger.error(f'Wrong type passed to play {type(song_list)}.')
                return   
            if len(song_list) < 1:
                config.logger.error(f'Not enough items to play.')
                return          
            self._song_list = song_list
        
        # stop any current play
        self.stop()    
        self._current_index = -1             
        # start playing the first song
        self._play_next()
        
    def append_to_playlist(self, song_list):
        '''
            Appends a list to the existing playlist
        '''
        if not isinstance(song_list, list):
            config.logger.error(f'Wrong type passed to play {type(song_list)}')
            return   
        self._song_list.extend(song_list)
        
    def _play_next(self): 
        '''
            Plays the next song in the list
        '''   
        self._current_index += 1
        if len(self._song_list) > self._current_index: 
            self._media = self._vlc_instance.media_new(self._song_list[self._current_index].abs_path)  
            self._player = self._vlc_instance.media_player_new()  
            self._player.set_media(self._media)  
            self._player.event_manager().event_attach(EventType.MediaPlayerEndReached, self.finished_song_event) 
            self._player.audio_set_volume(self._volume) 
            self._player.play()
        else:
            config.logger.debug('Finished playing the list of songs')
            
     
    @check_media    
    def stop(self):
        '''
            Stops the player.
        '''
        self._player.stop()
    
    @check_media 
    def pause(self):
        '''
            Pauses and resumes the music.
        '''
        self._player.pause()
    
    @check_media    
    def get_time(self):
        '''
            Gets the elapsed time of the current song.
        '''
        return self._player.get_time()
    
    @check_media 
    def set_volume(self, volume):
        '''
            Sets the volume of the player.
        '''
        if isinstance(volume, str):
            volume = float(volume)
        if isinstance(volume, (float, int)):
            volume = int(round(volume))
        self._volume = volume
        self._player.audio_set_volume(volume)
    
    @check_media     
    def is_playing(self):
        '''
            Checks if any media is playing.
        '''
        return self._player.get_state() == State.Playing 
   
    @check_media 
    def get_length(self):
        '''
            Gets the length of the current media playing.
        '''
        return self._player.get_duration()
    
    @check_media
    def get_current_song(self):
        '''
            Gets the info from the mp3 playing currently
        '''
        song = None
        if self._current_index < len(self._song_list):
            song = self._song_list[self._current_index]
        return song
            
            
        
        
