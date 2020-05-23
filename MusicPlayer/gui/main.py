import copy
import threading
import time
import hashlib
from concurrent.futures.thread import ThreadPoolExecutor
from os import listdir
from os.path import basename, dirname, isfile, join
from functools import partial

import tkinter.messagebox as messagebox
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from ttkthemes import themed_tk as tk

from musicdb_client.rest import ApiException

from config import config
from music.song import Song
from music.album import Album
from music.music_manager import MusicManager
from music.media_player import MyMediaPlayer
from music.cover_art_manager import CoverArtManager, Dimensions


def get_signature(contents):
    """
        Function to get the MD5 hash of the given string. Useful for checking if changes have been made to a string.
    """
    return hashlib.md5(str(contents).encode()).digest()


class GUI:

    def __init__(self):
        self._player = MyMediaPlayer()
        self._player.subscribe_song_started(self._player_song_started_event)
        self._player.subscribe_playlist_finished(self._player_playlist_finished_event)
        self._paused = FALSE
        self._muted = FALSE
        self._parallel_thread = None  # the thread for executing parallel tasks alongside the GUI main loop
        self._playlist = {}  # dictionary containing the song objects of the playlist
        self._albums_list = {}  # dictionary containing the album objects for the album list
        self._albums_from_server = {}  # preliminary dictionary containing the data from the server, to be processed to _albums_list
        self._details_thread = threading.Thread(target=self._start_count)
        self._stop_details_thread = False
        # workers pool for parallel threads
        self._workers_pool = None
        # get the client to access the music_db server
        self._music_db = config.music_db_api
        MusicManager.set_update_song_data_cb(self.update_song_data)
        MusicManager.set_update_album_data_cb(self.update_album_data)
        self._albums_window = None
        # always initialize layout at the end because it contains the gui main loop
        self._init_main_window_layout()

    def _init_main_window_layout(self):
        """
            Initializes the main window layout
        """
        self._window_root = tk.ThemedTk()
        self._window_root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._window_root.get_themes()  # Returns a list of all themes that can be set
        self._window_root.set_theme("radiance")  # Sets an available theme
        self._window_root.title("MusicPlayer")

        # TODO: create a default list of settings for the themes: which theme and fonts to use.
        # These themes will be used by all windows like the socre question window

        # Fonts - Arial (corresponds to Helvetica), Courier New (Courier), Comic Sans MS, Fixedsys,
        # MS Sans Serif, MS Serif, Symbol, System, Times New Roman (Times), and Verdana
        #
        # Styles - normal, bold, roman, italic, underline, and overstrike.

        self.status_bar = ttk.Label(self._window_root, text="Welcome to MusicPlayer", relief=SUNKEN, anchor=W,
                                    font='Times 12')
        self.status_bar.pack(side=BOTTOM, fill=X)

        # Create the main Menu bar
        self._menu_bar = Menu(self._window_root)
        self._window_root.config(menu=self._menu_bar)
        # Create the File sub menu            
        self._file_sub_menu = Menu(self._menu_bar, tearoff=0)
        self._menu_bar.add_cascade(label="File", menu=self._file_sub_menu)
        self._file_sub_menu.add_command(label="Open", command=self._browse_file)
        self._file_sub_menu.add_command(label="Exit", command=self._window_root.destroy)
        # Create the Albums sub menu            
        self._file_sub_menu = Menu(self._menu_bar, tearoff=0)
        self._menu_bar.add_cascade(label="Albums", menu=self._file_sub_menu)
        album_list_func = partial(self._execute_thread,
                                  self._get_album_list_thread,
                                  post_function=self._show_album_list)
        self._file_sub_menu.add_command(label="Open List", command=album_list_func)
        album_add_to_db_func = partial(self._execute_thread,
                                       self._add_albums_to_db_thread,
                                       post_function=self._show_album_list)
        self._file_sub_menu.add_command(label="Add albums from filesystem to DB", command=album_add_to_db_func)
        review_add_to_db_func = partial(self._execute_thread,
                                        self._add_reviews_to_db_thread,
                                        post_function=self._show_album_list)
        self._file_sub_menu.add_command(label="Add reviews from filesystem to DB", command=review_add_to_db_func)
        # Create the Play sub menu            
        self._play_sub_menu = Menu(self._menu_bar, tearoff=0)
        self._menu_bar.add_cascade(label="Play", menu=self._play_sub_menu)
        self._play_sub_menu.add_command(label="Favorites random", command=self._play_favorites)

        # FRAMES STRUCTURE
        self._left_frame = Frame(self._window_root)
        self._left_frame.pack(side=LEFT, padx=30, pady=30)

        self._right_frame = Frame(self._window_root)
        self._right_frame.pack(pady=30)

        self._top_right_frame = Frame(self._right_frame)
        self._top_right_frame.pack()

        self._top_left_frame = Frame(self._left_frame)
        self._top_left_frame.pack()

        self._bottom_left_frame = Frame(self._left_frame)
        self._bottom_left_frame.pack()

        # Bottom Frame for volume, rewind, mute etc.
        self._bottom_right_frame = Frame(self._right_frame)
        self._bottom_right_frame.pack()

        # PLAYLIST
        v_scroll_bar = Scrollbar(self._top_left_frame, orient="vertical")
        h_scroll_bar = Scrollbar(self._top_left_frame, orient="horizontal")

        self._playlistbox = ttk.Treeview(self._top_left_frame, yscrollcommand=v_scroll_bar.set,
                                         xscrollcommand=h_scroll_bar.set, height=20)
        self._playlistbox["columns"] = ('FileName', 'Title', 'Band', 'Album', 'Length')
        self._playlistbox.heading("FileName", text="File Name", anchor=W)
        self._playlistbox.heading("Title", text="Title", anchor=W)
        self._playlistbox.heading("Band", text="Band", anchor=W)
        self._playlistbox.heading("Album", text="Album", anchor=W)
        self._playlistbox.heading("Length", text="Length")
        self._playlistbox.column("Length", minwidth=0, width=60, anchor=E)
        self._playlistbox[
            "show"] = "headings"  # This will remove the first column from the viewer (first column of this widget is the identifier of the row)

        v_scroll_bar.config(command=self._playlistbox.yview)
        v_scroll_bar.pack(side="right", fill="y")

        self._playlistbox.pack(side="left", fill="y", expand=True)

        # PLAYLIST POUP
        self._playlist_popup = Menu(self._window_root, tearoff=0)
        self._playlist_popup.add_command(label="Add song to favorites", command=self._playlist_box_add_to_favorites)
        self._playlist_popup.add_separator()

        self._playlist_popup.selection = None

        def do_playlist_popup(event):
            # display the _playlist_popup menu
            try:
                self._playlist_popup.selection = self._playlistbox.identify_row(event.y)
                self._playlist_popup.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self._playlist_popup.grab_release()

        def do_playlist_play_song(event):
            """    
                Play item on double click.
            """
            row = self._playlistbox.identify_row(event.y)
            self._play_music([(self._playlist[str(row)])])

        # add popup to playlist tree view
        self._playlistbox.bind("<Button-3>", do_playlist_popup)
        self._playlistbox.bind('<Double-Button-1>', do_playlist_play_song)

        # ADD DELETE BUTTONS
        self.add_button = ttk.Button(self._bottom_left_frame, text="+ Add", command=self._browse_file)
        self.delete_button = ttk.Button(self._bottom_left_frame, text="- Del", command=self._delete_song)

        self.add_button.pack(side=LEFT)
        self.delete_button.pack(side=RIGHT)

        # PLAY/STOP BUTTONS
        self._current_time_label = ttk.Label(self._top_right_frame, text='Current Time : --:--', relief=GROOVE)
        self._current_time_label.pack()

        self._middle_right_frame = Frame(self._right_frame)
        self._middle_right_frame.pack(pady=30, padx=30)

        # images must be 50x50 pix since I couldn't find the way to resize them by code
        gui_root = dirname(__file__)
        self._play_photo = PhotoImage(file=join(gui_root, 'images/play_small.png'))
        self._stop_photo = PhotoImage(file=join(gui_root, 'images/stop_small.png'))
        self._pause_photo = PhotoImage(file=join(gui_root, 'images/pause_small.png'))
        self._rewind_photo = PhotoImage(file=join(gui_root, 'images/rewind_small.png'))
        self._mute_photo = PhotoImage(file=join(gui_root, 'images/mute_small.png'))
        self._volume_photo = PhotoImage(file=join(gui_root, 'images/volume_small.png'))

        self._play_button = Button(self._middle_right_frame, image=self._play_photo, borderwidth=3,
                                   command=self._play_music)
        self._stop_button = Button(self._middle_right_frame, image=self._stop_photo, borderwidth=3,
                                   command=self._stop_music)
        self._pause_button = Button(self._middle_right_frame, image=self._pause_photo, borderwidth=3,
                                    command=self._pause_music)
        self._volume_button = Button(self._bottom_right_frame, image=self._volume_photo, borderwidth=3,
                                     command=self._mute_music)

        self._play_button.grid(row=0, column=0, padx=10)
        self._stop_button.grid(row=0, column=1, padx=10)
        self._pause_button.grid(row=0, column=2, padx=10)

        self._volume_button.grid(row=0, column=0)
        self._volume_scale = ttk.Scale(self._bottom_right_frame, from_=0, to=100, orient=HORIZONTAL,
                                       command=self._set_volume)
        self._volume_scale.grid(row=0, column=2, pady=15, padx=30)
        # initialize to maximum
        self._volume_scale.set(100)

        self._progressbar = ttk.Progressbar(self._middle_right_frame, mode='indeterminate')
        self._progressbar.grid(row=1, column=1, sticky=W, pady=15)

        # start the gui loop
        self._window_root.mainloop()

    def _init_albums_window_layout(self):
        """
            Initializes the albums window layout
        """
        if not self._albums_window:
            self._albums_window = tk.ThemedTk()
            self._albums_window.protocol("WM_DELETE_WINDOW", self._on_closing_album_window)

            self._albums_window.get_themes()  # Returns a list of all themes that can be set
            self._albums_window.set_theme("radiance")  # Sets an available theme
            self._albums_window.title("Album Search")
            self._albums_window.geometry("1400x600")

            self._album_status_bar = ttk.Label(self._albums_window, text="Album library", relief=SUNKEN, anchor=W,
                                               font='Times 12')
            self._album_status_bar.pack(side=BOTTOM, fill=X)

            # variable that stores the selected album
            self._selected_album = None
            self._selected_album_review_signature = None

            # ALBUM WINDOW FRAMES STRUCTURE

            self._top_album_frame = Frame(self._albums_window)
            self._top_album_frame.pack(side=TOP, expand=True)

            self._left_album_frame = Frame(self._top_album_frame)
            self._left_album_frame.pack(side=LEFT, padx=30, pady=30, expand=True)

            self._right_album_frame = Frame(self._top_album_frame)
            self._right_album_frame.pack(side=RIGHT, padx=30, pady=30, expand=True)

            self._bottom_album_frame = Frame(self._albums_window)
            self._bottom_album_frame.pack(side=BOTTOM, expand=True)

            # ALBUM LIST
            v_scroll_bar = Scrollbar(self._left_album_frame, orient="vertical")

            self._album_listbox = ttk.Treeview(self._left_album_frame, yscrollcommand=v_scroll_bar.set, height=20)
            self._album_listbox["columns"] = ('Band', 'Title', 'Style', 'Year', 'Location', 'Type', 'Score', 'InDB')
            self._album_listbox.heading("Band", text="Band", anchor=W)
            self._album_listbox.heading("Title", text="Title", anchor=W)
            self._album_listbox.heading("Style", text="Style", anchor=W)
            self._album_listbox.heading("Year", text="Year", anchor=W)
            self._album_listbox.heading("Location", text="Location", anchor=W)
            self._album_listbox.heading("Type", text="Type", anchor=W)
            self._album_listbox.heading("Score", text="Score", anchor=W)
            self._album_listbox.heading("InDB", text="In DB", anchor=W)
            self._album_listbox["show"] = "headings"  # This will remove the first column from the viewer
            # (first column of this widget is the identifier of the row)
            # add functionality for sorting
            for col in self._album_listbox["columns"]:
                self._album_listbox.heading(col, text=col, command=lambda _col=col: \
                    GUI._tree_view_sort_column(self._album_listbox, _col, False))

            self._album_listbox.column("Band", minwidth=0, width=220)
            self._album_listbox.column("Title", minwidth=0, width=280)
            self._album_listbox.column("Style", minwidth=0, width=160)
            self._album_listbox.column("Year", minwidth=0, width=50)
            self._album_listbox.column("Location", minwidth=0, width=120)
            self._album_listbox.column("Type", minwidth=0, width=120)
            self._album_listbox.column("Score", minwidth=0, width=40)
            self._album_listbox.column("InDB", minwidth=0, width=20)

            v_scroll_bar.config(command=self._album_listbox.yview)
            v_scroll_bar.pack(side=RIGHT, fill=Y, expand=True)

            self._album_listbox.pack(side=LEFT, fill=BOTH, expand=True)

            # review text
            self._review_text_box = Text(self._bottom_album_frame,
                                         font='Times 12', relief=GROOVE, height=100, width=100)
            self._review_text_box.pack(side=BOTTOM, fill=BOTH, expand=True)

            def do_album_list_popup(event):
                # display the _album_list_popup menu
                try:
                    self._album_list_popup.selection = self._album_listbox.identify_row(event.y)
                    self._album_list_popup.post(event.x_root, event.y_root)
                finally:
                    # make sure to release the grab (Tk 8.0a1 only)
                    self._album_list_popup.grab_release()

            def album_list_popup_focus_out(event=None):
                self._album_list_popup.unpost()

            def do_album_list_play_album():
                """Plays selected album on popup"""
                row = self._album_list_popup.selection
                try:
                    album = self._albums_list[row]
                except KeyError:
                    # not an album but a band key, do not play
                    pass
                else:
                    file_names = [f for f in listdir(album.path) if isfile(join(album.path, f))]
                    for file_name in file_names:
                        self._add_file_to_playlist(join(album.path, file_name), album)
                    self._play_music()

            def do_album_edit():
                """Edits the selected album"""
                try:
                    self._edit_album(self._albums_list[self._album_list_popup.selection])
                except KeyError:
                    # not an album but a band key, do not edit
                    pass

            def do_album_delete():
                """Deletes the selected album"""
                try:
                    self._delete_album(self._albums_list[self._album_list_popup.selection])
                except KeyError:
                    # not an album but a band key, do nothing.
                    pass

            def do_album_selection(event):
                """Event on album selection, it will:
                    - Show the cover art from the selected album in _current_album_img
                    - Show the review of the album in _review_text_box
                """
                selection = self._album_listbox.identify_row(event.y)
                try:
                    album = self._albums_list[selection]
                except KeyError:
                    # if selected row is from the band root then we do not continue
                    pass
                else:
                    # if there was a previous album let's check if we have to update the review
                    if self._selected_album:
                        review = self._review_text_box.get(1.0, END)
                        # it there was a review selected before we check the signature
                        if self._selected_album_review_signature:
                            if self._selected_album_review_signature != get_signature(review):
                                config.logger.info(
                                    f"Review for album {self._selected_album.title} has changed. Updating the DB.")
                                self._selected_album.review = review
                                try:
                                    MusicManager.update_album(self._selected_album)
                                except Exception as ex:
                                    config.logger.exception('Could not save album review.')
                                    messagebox.showerror('Error',
                                                         message='Could not save album review. See log for errors.')

                    # set the review text
                    self._review_text_box.delete(1.0, END)
                    if album.review:
                        self._review_text_box.insert(END, album.review)
                        self._selected_album_review_signature = get_signature(self._review_text_box.get(1.0, END))
                    # update selected album
                    self._selected_album = album

                    dim = Dimensions(250, 250)
                    # PhotoImage object must reside in memory
                    self._current_album_img = CoverArtManager.get_covert_art_for_album(album, self._albums_window, dim)
                    self._album_work_art_canvas.create_image(20, 20, anchor=NW, image=self._current_album_img)

            self._album_list_popup = Menu(self._albums_window, tearoff=0)
            self._album_list_popup.add_command(label="Play album", command=do_album_list_play_album)
            self._album_list_popup.add_command(label="Edit album", command=do_album_edit)
            self._album_list_popup.add_command(label="Delete album", command=do_album_delete)

            # add popup to album_list tree view
            self._album_listbox.bind("<Button-3>", do_album_list_popup)
            # add Cover art change to tree view selection
            self._album_listbox.bind("<Button-1>", do_album_selection)
            self._album_listbox.bind("<FocusOut>", album_list_popup_focus_out)

            # album image
            self._album_work_art_canvas = Canvas(self._top_album_frame, width=300, height=300)
            self._album_work_art_canvas.pack(expand=True)
            self._album_work_art_canvas_frame = self._album_work_art_canvas.create_window((0, 0),
                                                                                          window=self._right_album_frame,
                                                                                          anchor=NW)

            self._album_list_popup.selection = None

    # ------------------ TASKS EXECUTION -----------------------------------------------------#
    # ------------------ TASKS EXECUTION -----------------------------------------------------#
    # ------------------ TASKS EXECUTION -----------------------------------------------------#
    # ------------------ TASKS EXECUTION -----------------------------------------------------#

    def _execute_thread(self, target_thread, post_function=None, *post_function_args):
        """
            Function execute tasks in parallel with the GUI main loop.
            It will start a new thread passed on target_thread and a progressbar to indicate progress
            Progress update is checked in _check_thread
            @post_function: function to be called after the thread is finished. Generally a GUI update.
            @post_function_args: arguments for the post function.
            NOTE: any result of the function thread will be passed as last argument to the post function
        """
        if self._workers_pool:
            if self._workers_pool.running():
                messagebox.showerror('Error',
                                     "Can't perform more than one task in parallel. "
                                     "Please wait until the current one finishes.")
                return

        self._progressbar.start()
        executor = ThreadPoolExecutor(max_workers=2)
        self._workers_pool = executor.submit(target_thread)

        self._window_root.after(100, self._check_thread, post_function, *post_function_args)

    def _check_thread(self, post_function, *args):
        """
            Function to check progress of a thread. It updates a progress bar while working.
            Once the thread is finished it calls the post_function passed by argument with its arguments.
        """
        self._window_root.update()
        if self._workers_pool:
            if self._workers_pool.running():
                self._window_root.after(100, self._check_thread, post_function, *args)
            else:
                result = self._workers_pool.result()
                if result:
                    args = list(args)
                    args.append(result)
                self._progressbar.stop()
                # call the post function once the thread is finished
                if post_function:
                    post_function(*args)

    # ----------------- MENU ACTIONS ----------------------------------------------------#
    # ----------------- MENU ACTIONS ----------------------------------------------------#
    # ----------------- MENU ACTIONS ----------------------------------------------------#
    # ----------------- MENU ACTIONS ----------------------------------------------------#

    def _browse_file(self):
        file_names = filedialog.askopenfilenames(parent=self._window_root, title="Choose files")
        if file_names:
            self._window_root.tk.splitlist(file_names)
            for file_name in file_names:
                self._add_file_to_playlist(file_name, None)

    # ----------------------- GET FAVORITE SONGS ---------------------------------------------#

    class FavoritesScoreWindow(object):
        """
            Window for asking the score for favorite songs
        """

        def __init__(self, master, message):
            top = self.top = Toplevel(master)
            self.label = Label(top, text=message)
            self.label.pack()
            self.entry = Entry(top)
            self.entry.pack()
            self.button = Button(top, text='Ok', command=self.cleanup)
            self.button.pack()
            self.score = None

        def cleanup(self):
            self.score = self.entry.get()
            self.top.destroy()

    def _get_score_input(self, message):
        question_window = self.FavoritesScoreWindow(self._window_root, message)
        self._window_root.wait_window(question_window.top)
        score = None
        try:
            score = float(question_window.score)
        except ValueError:
            messagebox.showerror("Error", "Score must be a number between 0 and 10")
        except Exception:
            messagebox.showerror("Error", "Some error parsing the score value. Please check logging.")
            config.logger.exception("Error parsing the score value")
        else:
            if score < 0.0 or score > 10.0:
                messagebox.showerror("Error", "Score must be between 0 and 10")
        return score

    def _play_favorites(self):
        """
            Function to play the favorite songs
        """
        self._favorites_score = self._get_score_input("Please give the minimum score of songs to play")
        if self._favorites_score:
            self._execute_thread(self._search_favorites_thread, self._play_music)

    def _search_favorites_thread(self):
        """
            Thread to search favorite songs and add to the playlist
        """
        self.status_bar['text'] = 'Getting favorite songs'
        try:
            quantity = 10
            songs = MusicManager.get_favorites(quantity, self._favorites_score)
            for song in songs:
                self._add_song_to_playlist(song)
            self.status_bar['text'] = 'Favorite songs ready!'
        except ApiException:
            config.logger.exception("Exception when getting favorite songs from the server")
            messagebox.showerror("Error", "Some error while searching for favorites. "
                                          "Please check the connection to the server.")
        except Exception as ex:
            messagebox.showerror("Error",
                                 "Some error while searching for favorites. Please see logging.")
            config.logger.exception("Exception when getting favorite songs from the server")

    # --------------------------- GET THE ALBUM LIST ----------------------------------------------#

    def _show_album_list(self, album_dict):
        """Function to be called after the get album list thread
            @param: album_dict, album dictionary with band as keys and values as a dict of albumes
        """
        if album_dict:
            self._init_albums_window_layout()
            self._add_to_album_list(album_dict)
            self.status_bar['text'] = 'Album list ready'
        else:
            messagebox.showerror("Error", "Error getting album collection. Please check logging.")

    def _get_album_list_thread(self):
        """
            Thread to get the album list.
        """
        self.status_bar['text'] = 'Getting album list'
        try:
            albums_from_server, _, wrong_albums = MusicManager.get_albums_from_collection()
            if wrong_albums:
                albums_list = ''
                for band in wrong_albums:
                    for album in wrong_albums[band]:
                        albums_list += f"\n{album} from {band}"
                message = f"The following albums are not correct {albums_list}"
                self.InfoWindow(self._window_root, message)
        except:
            config.logger.exception("Exception when getting album collection")
        else:
            return albums_from_server

    def _add_albums_to_db_thread(self):
        """
            Thread to add albums from the filesystem to the database.
        """
        self.status_bar['text'] = 'Adding albums to database'
        try:
            albums_from_server, new_albums, wrong_albums = MusicManager.add_new_albums_from_collection_to_db()
            if wrong_albums:
                albums_list = ''
                for band in wrong_albums:
                    for album in wrong_albums[band]:
                        albums_list += f"\n{album} from {band}"
                message = f"The following albums are not correct: {albums_list}"
                self.InfoWindow(self._window_root, message)
            if new_albums:
                albums_list = ''
                for band in new_albums:
                    for album in new_albums[band]:
                        albums_list += f"\n{album} from {band}"
                message = f"The following albums were added to the database {albums_list}"
                self.InfoWindow(self._window_root, message)
        except:
            config.logger.exception("Exception when getting album collection")
        else:
            return albums_from_server

    # --------------------------- UPDATE REVIEWS ----------------------------------------------#

    def _add_reviews_to_db_thread(self):
        """
            Thread to add reviews from the filesystem to the database.
        """
        self.status_bar['text'] = 'Adding reviews to database'
        reviews_dir = filedialog.askdirectory(initialdir=config.MUSIC_PATH, parent=self._window_root,
                                              title=f"Choose reviews path")
        if reviews_dir:
            try:
                album_list, wrong_album_list  = MusicManager.add_reviews_batch(reviews_dir)
                if wrong_album_list:
                    albums_list = ''
                    for band in wrong_album_list:
                        for album in wrong_album_list[band]:
                            albums_list += f"\n{album} from {band}"
                    message = f"The following reviews could not be updated in the database {albums_list}"
                    self.InfoWindow(self._window_root, message)
            except:
                config.logger.exception("Exception when updating reviews to album collection")
                messagebox.showerror("Error", "Error adding reviews to db. Please check logging.")

    # --------------- POP UP ACTIONS -----------------------------------------------------------#

    # --------------- MAIN PLAYER ---------------#

    def _playlist_box_add_to_favorites(self):
        """
            Adds the selected song from the playlist to the favorites in the server.
        """
        song = self._playlist[self._playlist_popup.selection]
        score = self._get_score_input(f"Give the score for the current song {song.title}"
                                      f" with current score {song.score}")
        if score:
            song.score = score
            try:
                MusicManager.add_song_to_favorites(song)
            except Exception:
                config.logger.exception(f'Error adding new favorite song.')
                messagebox.showerror("Error", "Error adding a new favorite song. Please check logging.")

    # ----------------------- BUTTONS ACTIONS -------------------------------------------#

    class AlbumEditWindow(object):
        """ Window for editing album fields."""

        def __init__(self, master, album):
            top = self.top = Toplevel(master)
            desc_label = Label(top, text=f'Editing album with title "{album.title}" of band "{album.band}"')
            desc_label.grid(row=0, column=1)
            style_label = Label(top, text="Style")
            style_label.grid(row=1, column=0)
            self.style_entry = Entry(top)
            self.style_entry.grid(row=1, column=1)
            self.style_entry.insert(END, str(album.style) if album.style  else '')
            year_label = Label(top, text="Year")
            year_label.grid(row=2, column=0)
            self.year_entry = Entry(top)
            self.year_entry.grid(row=2, column=1)
            self.year_entry.insert(END, str(album.year) if album.year else '')
            country_label = Label(top, text="Country/State")
            country_label.grid(row=3, column=0)
            self.country_entry = Entry(top)
            self.country_entry.grid(row=3, column=1)
            self.country_entry.insert(END, str(album.country) if album.country else '')
            type_label = Label(top, text="Type")
            type_label.grid(row=4, column=0)
            self.type_entry = Entry(top)
            self.type_entry.grid(row=4, column=1)
            self.type_entry.insert(END, str(album.type) if album.type else '')
            score_label = Label(top, text="Score")
            score_label.grid(row=5, column=0)
            self.score_entry = Entry(top)
            self.score_entry.grid(row=5, column=1)
            self.score_entry.insert(END, str(album.score) if album.score else '')
            review_label = Label(top, text="Review")
            review_label.grid(row=6, column=0)
            self._review_text_box_album = Text(top, font='Times 12', relief=GROOVE, height=15, width=100)
            self._review_text_box_album.grid(row=6, column=1)
            self._review_text_box_album.insert(END, str(album.review) if album.review else '')
            button = Button(top, text='Save', command=self.save)
            button.grid(row=7, column=1)
            self.album = album

        def save(self):
            self.album.style = self.style_entry.get().strip()
            self.album.year = self.year_entry.get().strip()
            self.album.country = self.country_entry.get().strip()
            self.album.type = self.type_entry.get().strip()
            self.album.score = self.score_entry.get().strip()
            # when getting the text from the widget it will ad a newline that
            # will have to be removed manually with [:-1]
            self.album.review = self._review_text_box_album.get(1.0, END)[:-1]
            self.top.destroy()

    def _edit_album(self, album):
        """Edits an album interactively.
            It will open a window to edit the different fields for the given album.
            After the album is saved the albums_window will be refreshed.
            @param: album, the album to edit
        """
        old_album = copy.deepcopy(album)
        album_window = self.AlbumEditWindow(self._window_root, album)
        self._window_root.wait_window(album_window.top)
        try:
            if old_album != album_window.album:
                MusicManager.update_album(album_window.album)
                # remove the selected album so review is not updated again
                self._selected_album = None
                self._refresh_album_list()
        except:
            config.logger.exception(f"Could not save album with title {album.title}")
            messagebox.showerror('Editor error', f"Could not save album with title {album.title}")

    class DeleteQuestionWindow(object):
        """ Window for editing album fields."""

        def __init__(self, master, album):
            top = self.top = Toplevel(master)
            self.delete = False
            desc_label = Label(top, text=f'Are you sure you want to delete album with title "{album.title}" of band "{album.band}"')
            desc_label.grid(row=0, column=1)
            button = Button(top, text='Yes', command=self.do_delete)
            button.grid(row=1, column=1)
            button = Button(top, text='No', command=self.quit)
            button.grid(row=1, column=2)

        def do_delete(self):
            self.delete = True
            self.top.destroy()

        def quit(self):
            self.top.destroy()

    def _delete_album(self, album):
        """Deletes an album.
            @param: album, the album to edit
        """
        delete_question_window = self.DeleteQuestionWindow(self._window_root, album)
        self._window_root.wait_window(delete_question_window.top)
        if delete_question_window.delete:
            try:
                MusicManager.delete_album(album)
                # remove the selected album so review is not updated again
                self._selected_album = None
                self._refresh_album_list()
            except:
                config.logger.exception(f"Could not delete album with title {album.title}")
                messagebox.showerror('Editor error', f"Could not delete album with title {album.title}")

    def _delete_song(self):
        """
            Deletes the selected song from the playlist.
            It does not remove it from the server even if it's a favorite song.
        """
        selected_songs = self._playlistbox.selection()
        if selected_songs:
            for selected_song in selected_songs:
                self._playlistbox.delete(selected_song)
                self._playlist.pop(selected_song)
            self._player.delete_from_playlist(selected_songs)

    def _play_music(self, song_list=None):
        """
            Plays the list of songs from the playlistbox. 
            It will start on the selected song from the playlist.
        """
        if self._paused and not song_list:
            self._player.pause()
            self.status_bar['text'] = "Music Resumed"
            self._paused = FALSE
        else:
            try:
                if not song_list:
                    selected_songs_list = self._playlistbox.selection()
                    if selected_songs_list:
                        song_list = [self._playlist[str(index_song)] for index_song in selected_songs_list]
                    else:
                        pass  # playlist has already been provided just play
                if len(self._playlist) != 0:
                    self._player.play(songs=song_list)
                else:
                    config.logger.error("Playlist for music hasn't been provided")
            except Exception:
                config.logger.exception('Exception while playing music')
                messagebox.showerror('Player error', 'Player could not play the file. Please check logging.')
            else:
                self._show_details()
                self._paused = FALSE
                self.status_bar['text'] = "Music playing"

    def _stop_music(self):
        """
            Stops playing music.
        """
        self._player.stop()
        self._stop_details_thread = True
        self.status_bar['text'] = "Music stopped"

    def _pause_music(self):
        """
            Pauses the music in the current playing song.
        """
        self._player.pause()
        if self._paused:
            self._paused = FALSE
            self.status_bar['text'] = "Music Resumed"
        else:
            self._paused = TRUE
            self.status_bar['text'] = "Music paused"

    def _set_volume(self, volume):
        """
            Sets the volume of the player.
        """
        self._player.set_volume(volume)

    def _mute_music(self):
        """
            Toggles the player sound.
        """
        if self._muted:  # Unmute the music
            self._player.set_volume(1)
            self._volume_button.configure(image=self._volume_photo)
            self._volume_scale.set(100)
            self._muted = FALSE
        else:  # mute the music
            self._player.set_volume(0)
            self._volume_button.configure(image=self._mute_photo)
            self._volume_scale.set(0)
            self._muted = TRUE

    # ------------------------- Other Window helpers ------------------------------------------#

    class InfoWindow(object):
        """Window for showing some info.
        Args:
            master, the master window
            message, the message to show in the window label
        """

        def __init__(self, master, message):
            top = self.top = Toplevel(master)
            self.label = Label(top, text=message)
            self.label.pack()

    # ------------------------- GUI EVENTS ------------------------------------------#

    def _on_closing(self):
        """
            Event called on closing the main window.
            It will stop the music and destroy any existing window.
        """
        self._stop_music()
        self._stop_details_thread = True
        self._on_closing_album_window()
        self._window_root.destroy()

    def _on_closing_album_window(self):
        """
           Event called on albums window closure.
           It will save the latest modified review if any.
        """
        if hasattr(self, '_selected_album') and self._selected_album:
            try:
                review = self._review_text_box.get(1.0, END)
            except Exception as ex:
                config.logger.exception(
                    'Could not get text from review box on closing window. Maybe album window was already closed')
            else:
                if self._selected_album_review_signature != get_signature(review):
                    config.logger.info(f"Review for album {self._selected_album.title} has changed. Updating the DB.")
                    self._selected_album.review = review
                    try:
                        MusicManager.update_album(self._selected_album)
                    except Exception as ex:
                        config.logger.exception('Could not save album review.')
        if hasattr(self, '_albums_window'):
            try:
                self._albums_window.destroy()
                self._albums_window = None
            except Exception:
                # window might have already been destroyed
                pass

    # ------------------------ PLAYER EVENTS  -----------------------------------------#

    def _player_song_started_event(self):
        """
            Event called when a song is started
        """
        song = self._player.get_current_song()
        if song:
            self.status_bar['text'] = f'Playing: {song.title}'

    def _player_playlist_finished_event(self):
        """
            Event called when the playlist is finished. 
            It will call more favorite songs to play.
        """
        if self._favorites_score:
            self._execute_thread(self._search_favorites_thread, post_function=self._play_music)

    # -------------------- FUNCTION HELPERS  ------------------------------------##

    def _add_file_to_playlist(self, path_name, album):
        file_name = basename(path_name)
        song = Song()
        song.album = album
        song.file_name = file_name
        try:
            updated = song.update_song_data_from_file(path_name)
        except:
            config.logger.exception("Failed to add song to the playlist")
        else:
            if updated:
                self._add_song_to_playlist(song)

    def _add_song_to_playlist(self, song):
        """Adds song to GUI playlist and to the player.
            Args:
                song (Song): the song to add
        """
        if song:
            pl_index = self._playlistbox.insert("", 'end', text="Band Name",
                                                values=(
                                                    song.file_name, song.title, song.band, song.album.title,
                                                    song.total_length))
            # add song to playlist dictionary, the index is the index in the playlist
            self._playlist[pl_index] = song
            try:
                self._player.add_to_playlist(songs=song)
            except:
                config.logger.exception(f'Could not add song with title {song.title}')
        else:
            config.logger.error(f'There was no song to add to playlist')

    def _add_to_album_list(self, album_dict):
        """Add input dict to album tree view
        Args:
            album_dict (dict): the dict of albums to add to the album list.
        """

        # remove existing tree if there were any items
        try:
            self._album_listbox.delete(*self._album_listbox.get_children())
        except:
            config.logger.warning("Some error when refreshing album list")

        band_index = 1
        for band_key, albums in sorted(album_dict.items()):
            # add tags for identifying which background color to apply
            if band_index % 2:
                tags = ('odd_row',)
            else:
                tags = ('even_row',)
            band_name = next(iter(albums.values())).band
            band_root = self._album_listbox.insert("", band_index, text=band_name,
                                                   values=(band_name,
                                                           "",
                                                           "",
                                                           "",
                                                           "",
                                                           "",
                                                           "",
                                                           ""), tags=tags)
            # config.logger.debug(f"Adding band {band} from {band_root}")
            band_index += 1
            album_index = 1
            for album_key, album in albums.items():
                # config.logger.debug(f"Adding album {album} to band {band}")
                try:
                    album_id = self._album_listbox.insert(band_root, 'end',
                                                          values=("",
                                                                  album.title,
                                                                  album.style,
                                                                  album.year,
                                                                  album.country,
                                                                  album.type,
                                                                  album.score,
                                                                  album.in_db))
                    self._albums_list[album_id] = album
                    album_index += 1
                except AttributeError:
                    config.logger.error(f"Could not add album {album} to playlist")

        # apply background colors
        self._album_listbox.tag_configure('odd_row', background='#D9FFDB')
        self._album_listbox.tag_configure('even_row', background='#FFE5CD')

    def _refresh_album_list(self):
        """
            Refreshes the album list.
        """
        self._execute_thread(self._get_album_list_thread, post_function=self._add_to_album_list)
        self.status_bar['text'] = 'Album list ready'

    def update_song_data(self, song):
        """
            Callback function to update interactively song data.
            We only ask for file name.
        """
        file_name = filedialog.askopenfilenames(initialdir=config.MUSIC_PATH, parent=self._window_root,
                                                title=f"Choose file for song {song.title} "
                                                      f"from album title {song.album.title} "
                                                      f"and band {song.album.band}")
        if file_name:
            return file_name[0]
        else:
            return None

    def update_album_data(self, album):
        """
            Callback function to update interactively album data.
        """
        # TODO: check this
        self._edit_album(album)

    def _show_details(self):
        """
            Starts the player time details thread 
        """
        if not self._stop_details_thread and not self._details_thread.is_alive():
            self._details_thread.start()

    def _start_count(self):
        """
            Implementation of timer details thread
        """
        while not self._stop_details_thread:
            while self._player.is_playing():
                self._current_time_label['text'] = "Current Time" + ' - ' + self._player.get_time()
                time.sleep(1)
            time.sleep(1)

    @staticmethod
    def _tree_view_sort_column(treeview, col, reverse):
        """
            Function to sort the columns of a treeview when headings are clicked.
            @param: treeview, the treeview to sort
            @param: col, the column to sort
            @param: reverse, parameter to specify if it has to be sorted in reverse.        
        """
        l = [(treeview.set(k, col), k) for k in treeview.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            treeview.move(k, '', index)

        # reverse sort next time
        treeview.heading(col, command=lambda: \
            GUI._tree_view_sort_column(treeview, col, not reverse))


if __name__ == '__main__':
    gui = GUI()
