from vlc import Instance, MediaPlayer, MediaListPlayer, MediaList, EventType, State

from config import config
from music.song import Song
import functools


def check_media(func):
    """
        Decorator to check if attribute _media exists
    """

    def inner(self, *args, **kwargs):
        if hasattr(self, "_media"):
            if not self._media:
                config.logger.debug(
                    f"Can't call Media Player without setting a file or a file list first. Called from {func}")
                # TODO: raise exception or print error?
                # raise ValueError
            else:
                # only call function if media player is set
                return func(self, *args, **kwargs)

    return inner


def check_song_list(func):
    """
        Decorator to check if "songs" argument complies with the following:
        - it is either a list
        - or a song, in this case it will convert it into a list
        It does not check if its value is None
    """

    def inner(self, *args, **kwargs):
        if 'songs' not in kwargs:
            config.logger.error(f'Wrongly used function {func}')
            raise Exception
        else:
            song_list = kwargs['songs']
            if song_list:
                if isinstance(song_list, Song):
                    kwargs['songs'] = [song_list]
                elif isinstance(song_list, list):
                    if len(song_list) < 1:
                        config.logger.error(f'Song list should at least have one item.')
                        raise Exception
                else:
                    config.logger.error(f'Wrong type passed to player {type(song_list)}.')
                    raise Exception
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
        self._song_finished_func = None
        self._song_started_func = None
        self._playlist_finished_func = None
        self._current_index = -1

    def subscribe_song_finished(self, func, *args, **kwargs):
        """
            Subscriber for when player finishes a song
        """
        self._song_finished_func = functools.partial(func, *args, **kwargs)

    def subscribe_playlist_finished(self, func, *args, **kwargs):
        """
            Subscriber for when player finishes all songs in existing playlist
        """
        self._playlist_finished_func = functools.partial(func, *args, **kwargs)

    def subscribe_song_started(self, func, *args, **kwargs):
        """
            Subscriber for when player finishes a song
        """
        self._song_started_func = functools.partial(func, *args, **kwargs)

    def _finished_song_event(self, event):
        """
            Event for when a player finishes a song.
        """
        config.logging.debug(f'Event from VLC player: {event}')
        self._play_next()
        if self._song_finished_func:
            self._song_finished_func()

    def _finished_playlist_event(self):
        """
            Event for when a player finishes a song.
        """
        config.logging.debug(f'Finished playlist event')
        if self._playlist_finished_func:
            self._playlist_finished_func()

    def _started_song_event(self, event):
        """
            Event for when a player starts a song.
        """
        config.logging.debug(f'Event from VLC player: {event}')
        if self._song_started_func:
            self._song_started_func()

    @check_song_list
    def play(self, *, songs):
        """
            Plays the given song list (a list of Song objects).
        """
        if songs:
            self._song_list.extend(songs)

        # stop any current play
        self.stop()
        # start playing the next song (self._current_index points to that)
        self._play_next()

    @check_song_list
    def add_to_playlist(self, *, songs):
        """
            Appends a song or a list of songs to the existing playlist.
        """
        if songs:
            self._song_list.extend(songs)

    @check_song_list
    def delete_from_playlist(self, *, songs):
        """
            Deletes a song or a list of songs from the existing playlist.
        """
        for song in songs:
            for song_player in self._song_list:
                # TODO: implement a proper check (do not use ids because that's only for favorite songs)
                if song == song_player:
                    self._song_list.remove(song_player)
                    break
        # TODO: remove from the list. Check the id of the song to identify it

    @check_media
    def stop(self):
        """
            Stops the player.
        """
        self._player.stop()

    @check_media
    def pause(self):
        """
            Pauses and resumes the music.
        """
        self._player.pause()

    @check_media
    def get_time(self):
        """
            Gets the elapsed time of the current song.
        """
        time = self._player.get_time()
        time_str = str(int(time / 60000)) + ':' + format(int((time % 60000) / 1000), '02d')
        return time_str

    @check_media
    def set_volume(self, volume):
        """
            Sets the volume of the player.
        """
        if isinstance(volume, str):
            volume = float(volume)
        if isinstance(volume, (float, int)):
            volume = int(round(volume))
        self._volume = volume
        self._player.audio_set_volume(volume)

    @check_media
    def is_playing(self):
        """
            Checks if any media is playing.
        """
        return self._player.get_state() == State.Playing

    @check_media
    def get_length(self):
        """
            Gets the length of the current media playing.
        """
        return self._player.get_duration()

    @check_media
    def get_current_song(self):
        """
            Gets the info from the mp3 playing currently
        """
        song = None
        if self._current_index < len(self._song_list):
            song = self._song_list[self._current_index]
        return song

    def _play_next(self):
        """
            Plays the next song in the list
        """
        self._current_index += 1
        if len(self._song_list) > self._current_index:
            self._media = self._vlc_instance.media_new(self._song_list[self._current_index].abs_path)
            self._player = self._vlc_instance.media_player_new()
            self._player.set_media(self._media)
            self._player.event_manager().event_attach(EventType.MediaPlayerEndReached, self._finished_song_event)
            self._player.event_manager().event_attach(EventType.MediaPlayerPlaying, self._started_song_event)
            self._player.audio_set_volume(self._volume)
            self._player.play()
        elif len(self._song_list) == self._current_index:
            self._finished_playlist_event()
            config.logger.debug('Finished playing the list of songs')
        else:
            config.logger.error(
                f'Current playing index is {self._current_index} and the length of the list is {len(self._song_list)}')
