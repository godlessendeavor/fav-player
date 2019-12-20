import os
import threading
import time
import traceback
import tkinter.messagebox
from tkinter import *
#from tkinter import filedialog
from tkinter import ttk
from ttkthemes import themed_tk as tk
from PIL import ImageTk, Image as PILImage
import logging
from os import listdir
from os.path import isfile, join

import musicdb_client
from musicdb_client.rest import ApiException
from musicdb_client.configuration import Configuration as Musicdb_config

from config import config
from music.song import Song
from music.album import Album
from music.album_manager import AlbumManager
from music.media_player import MyMediaPlayer

#set log configuration
logging.basicConfig(
    format=config.LOGGING_FORMAT,
    level=config.LOGGING_LEVEL
)
logger = logging.getLogger(__name__)

class GUI():
    
    class Splash(Toplevel):
        def __init__(self, parent):
            Toplevel.__init__(self, parent)
            self.title("Loading...")
    
            ## required to make window show before the program gets to the mainloop
            self.update()
    
    def __init__(self):
        self._player = MyMediaPlayer()
        self._paused = FALSE          
        self._muted  = FALSE
        self._playlist = {}   #dictionary containing the song objects of the playlist  
        self._albums_list = {} #dictionary containing the album objects for the album list
        self._config_reader = config
        self._music_path = config.MUSIC_PATH
        self._details_thread = threading.Thread(target=self._start_count, args =(lambda : self._stop_details_thread, ))
        self._stop_details_thread = False
        self._musicdb_config = Musicdb_config()
        self._musicdb_config.host = config.MUSIC_DB_HOST
        self._musicdb_config.debug = True
        self._musicdb = musicdb_client.PublicApi(musicdb_client.ApiClient(self._musicdb_config))
        #always initialize layout at the end because it contains the gui main loop
        self._init_main_window_layout() 

        
        
    def _init_main_window_layout(self):
        self._window_root = tk.ThemedTk()
        self._window_root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._window_root.get_themes()                 # Returns a list of all themes that can be set
        self._window_root.set_theme("radiance")        # Sets an available theme
        self._window_root.title("MusicPlayer")
        
        # Fonts - Arial (corresponds to Helvetica), Courier New (Courier), Comic Sans MS, Fixedsys,
        # MS Sans Serif, MS Serif, Symbol, System, Times New Roman (Times), and Verdana
        #
        # Styles - normal, bold, roman, italic, underline, and overstrike.
           
        self.statusbar = ttk.Label(self._window_root, text="Welcome to MusicPlayer", relief=SUNKEN, anchor=W, font='Times 12')
        self.statusbar.pack(side=BOTTOM, fill=X)
               
        # Create the self._menubar
        self._menubar = Menu(self._window_root)
        self._window_root.config(menu=self._menubar)
        # Create the File sub menu            
        self._file_sub_menu = Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="File", menu=self._file_sub_menu)
        self._file_sub_menu.add_command(label="Open", command=self._browse_file)
        self._file_sub_menu.add_command(label="Exit", command=self._window_root.destroy)
        # Create the Albums sub menu            
        self._file_sub_menu = Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="Albums", menu=self._file_sub_menu)
        self._file_sub_menu.add_command(label="Open List", command=self._show_album_list)
        # Create the Play sub menu            
        self._play_sub_menu = Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="Play", menu=self._play_sub_menu)
        self._play_sub_menu.add_command(label="Favorites random", command=self._play_favs)
              
        #FRAMES STRUCTURE
        
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
        
        #PLAYLIST
        
        vscrollbar = Scrollbar(self._top_left_frame, orient="vertical")
        hscrollbar = Scrollbar(self._top_left_frame, orient="horizontal")
        
        self._playlistbox = ttk.Treeview(self._top_left_frame, yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)  
        self._playlistbox["columns"] = ('FileName', 'Title', 'Band', 'Album', 'Length')
        self._playlistbox.heading("FileName", text="File Name",anchor=W)
        self._playlistbox.heading("Title", text="Title",anchor=W)
        self._playlistbox.heading("Band", text="Band",anchor=W)
        self._playlistbox.heading("Album", text="Album",anchor=W)
        self._playlistbox.heading("Length", text="Length",anchor=W)
        self._playlistbox.column("Length",minwidth=0,width=60)
        self._playlistbox["show"] = "headings" #This will remove the first column from the viewer (first column of this widget is the identifier of the row)
        
        vscrollbar.config(command=self._playlistbox.yview)
        #hscrollbar.config(command=self._playlistbox.xview) #TODO: optional horizontal scrollbar. Really needed?
        
        vscrollbar.pack(side="right", fill="y")
        #hscrollbar.pack(side="bottom", fill="x")
        
        self._playlistbox.pack(side="left", fill="y", expand=True) 
        
        #PLAYLIST POUP
        self._playlist_popup = tkinter.Menu(self._window_root, tearoff=0)
        self._playlist_popup.add_command(label="Add song to favorites", command=self._playlistbox_add_to_favorites)
        self._playlist_popup.add_separator()

        def do_playlist_popup(event):
            # display the _playlist_popup menu
            try:                
                self._playlist_popup.selection = self._playlistbox.identify_row(event.y)
                self._playlist_popup.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self._playlist_popup.grab_release()  
                
        def do_playlist_play_song(event):                         
            row = self._playlistbox.identify_row(event.y)
            self._play_music([(self._playlist[str(row)]).abs_path])
             
                
        #add popup to playlist treeview        
        self._playlistbox.bind("<Button-3>", do_playlist_popup)  
        self._playlistbox.bind('<Double-Button-1>', do_playlist_play_song)
        
        ##ADD DELETE BUTTONS                 
        self.add_button = ttk.Button(self._bottom_left_frame, text="+ Add", command=self._browse_file)
        self.delete_button = ttk.Button(self._bottom_left_frame, text="- Del", command=self._delete_song)

        self.add_button.pack(side=LEFT)
        self.delete_button.pack(side=RIGHT)
        
        ##PLAY/STOP BUTTONS       
            
        self._current_time_label = ttk.Label(self._top_right_frame, text='Current Time : --:--', relief=GROOVE)
        self._current_time_label.pack()
        
        self._middle_frame = Frame(self._right_frame)
        self._middle_frame.pack(pady=30, padx=30)
        
        #images must be 50x50 pix since I couldn't find the way to resize them by code
        gui_root = os.path.dirname(__file__)
        self._play_photo   = PhotoImage(file=os.path.join(gui_root, 'images/play_small.png'))
        self._stop_photo   = PhotoImage(file=os.path.join(gui_root, 'images/stop_small.png'))
        self._pause_photo  = PhotoImage(file=os.path.join(gui_root, 'images/pause_small.png'))        
        self._rewind_photo = PhotoImage(file=os.path.join(gui_root, 'images/rewind_small.png'))
        self._mute_photo   = PhotoImage(file=os.path.join(gui_root, 'images/mute_small.png'))
        self._volume_photo = PhotoImage(file=os.path.join(gui_root, 'images/volume_small.png'))
        
        self._play_button   = Button(self._middle_frame,       image=self._play_photo,   borderwidth=3, command=self._play_music)
        self._stop_button   = Button(self._middle_frame,       image=self._stop_photo,   borderwidth=3, command=self._stop_music)
        self._pause_button  = Button(self._middle_frame,       image=self._pause_photo,  borderwidth=3, command=self._pause_music)
        self._rewind_button = Button(self._bottom_right_frame, image=self._rewind_photo, borderwidth=3, command=self._rewind_music)
        self._volume_button = Button(self._bottom_right_frame, image=self._volume_photo, borderwidth=3, command=self._mute_music)
 
        self._play_button.grid(row=0, column=0, padx=10)        
        self._stop_button.grid(row=0, column=1, padx=10)        
        self._pause_button.grid(row=0, column=2, padx=10)
        
        self._rewind_button.grid(row=0, column=0)        
        self._volume_button.grid(row=0, column=1)        
        self._volume_scale = ttk.Scale(self._bottom_right_frame, from_=0, to=100, orient=HORIZONTAL, command=self._set_volume)
        self._volume_scale.grid(row=0, column=2, pady=15, padx=30)        
        
        #start the gui loop
        self._window_root.mainloop()
        
    
    def _init_albums_window_layout(self):        
        #TODO: do we need to call a toplevel?
        self._albums_window = tk.ThemedTk()
        self._albums_window.protocol("WM_DELETE_WINDOW", self._on_closing_album_window)
        
        self._albums_window.get_themes()                 # Returns a list of all themes that can be set
        self._albums_window.set_theme("radiance")        # Sets an available theme
        self._albums_window.title("Album Search")
           
        self._album_statusbar = ttk.Label(self._albums_window, text="Album library", relief=SUNKEN, anchor=W, font='Times 12')
        self._album_statusbar.pack(side=BOTTOM, fill=X)
                             
        #FRAMES STRUCTURE
        
        self._top_album_frame = Frame(self._albums_window)
        self._top_album_frame.pack(side=TOP)
        
        self._left_album_frame = Frame(self._top_album_frame)
        self._left_album_frame.pack(side=LEFT, padx=30, pady=30)
        
        self._right_album_frame = Frame(self._top_album_frame)
        self._right_album_frame.pack(side=RIGHT, padx=30, pady=30)
               
        self._bottom_album_frame = Frame(self._albums_window)
        self._bottom_album_frame.pack(side=BOTTOM)
        
        #ALBUM LIST
        
        vscrollbar = Scrollbar(self._left_album_frame, orient="vertical")
        hscrollbar = Scrollbar(self._left_album_frame, orient="horizontal")
        
        self._album_listbox = ttk.Treeview(self._left_album_frame, yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)  
        self._album_listbox["columns"] = ('Band', 'Title', 'Style', 'Year', 'Location', 'Type', 'Score', 'InBackup')
        self._album_listbox.heading("Band", text="Band",anchor=W)
        self._album_listbox.heading("Title", text="Title",anchor=W)
        self._album_listbox.heading("Style", text="Style",anchor=W)
        self._album_listbox.heading("Year", text="Year",anchor=W)
        self._album_listbox.heading("Location", text="Location",anchor=W)        
        self._album_listbox.heading("Type", text="Type",anchor=W)        
        self._album_listbox.heading("Score", text="Score",anchor=W)        
        self._album_listbox.heading("InBackup", text="In Backup",anchor=W)
        self._album_listbox["show"] = "headings" #This will remove the first column from the viewer (first column of this widget is the identifier of the row)
        for col in self._album_listbox["columns"]:
            self._album_listbox.heading(col, text=col, command=lambda _col=col: \
                     GUI._treeview_sort_column(self._album_listbox, _col, False))
        
        self._album_listbox.column("Band",     minwidth=0, width=140)
        self._album_listbox.column("Title",    minwidth=0, width=200)
        self._album_listbox.column("Style",    minwidth=0, width=120)
        self._album_listbox.column("Year",     minwidth=0, width=50)
        self._album_listbox.column("Location", minwidth=0, width=80)        
        self._album_listbox.column("Type",     minwidth=0, width=80)        
        self._album_listbox.column("Score",    minwidth=0, width=40)        
        self._album_listbox.column("InBackup", minwidth=0, width=20)
        
        vscrollbar.config(command=self._album_listbox.yview)
        #hscrollbar.config(command=self._album_listbox.xview) #TODO: optional horizontal scrollbar. Really needed?
        
        vscrollbar.pack(side="right", fill="y")
        #hscrollbar.pack(side="bottom", fill="x")
        
        self._album_listbox.pack(side="left", fill="y", expand=True) 
        
        def do_album_list_popup(event):
            # display the _album_list_popup menu
            try:                
                self._album_list_popup.selection = self._album_listbox.identify_row(event.y)
                self._album_list_popup.post(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                self._album_list_popup.grab_release()  
                           
                
        def do_album_list_play_album():                         
            row = self._album_list_popup.selection
            album = self._albums_list[row]            
            file_names = [f for f in listdir(album.path) if isfile(join(album.path, f))]
            for file_name in file_names:
                self._add_file_to_playlist(os.path.join(album.path, file_name), album) 
            
        def do_cover_art_show(event):
            selection = self._album_listbox.identify_row(event.y)
            try:
                album = self._albums_list[selection]
            except KeyError:
                #if selected row is from the band root then we do not continue
                pass
            else:
                #TODO: load image asynchronously and perhaps move this to another class
                #That class should look for a cover art from musicbrainz if not found here
                file_names = [f for f in listdir(album.path) if isfile(join(album.path, f))]
                image = None
                for file_name in file_names:
                    if "front" in file_name.casefold():
                        image = os.path.join(album.path, file_name)
                        break
                if image:
                    pil_image = PILImage.open(image)
                    pil_image = pil_image.resize((250, 250), PILImage.ANTIALIAS)
                    self._current_album_img = ImageTk.PhotoImage(pil_image, master=self._albums_window)  
                    self._album_workart_canvas.create_image(20, 20, anchor=NW, image=self._current_album_img) 
            
        #album_list POUP
        self._album_list_popup = tkinter.Menu(self._albums_window, tearoff=0)
        self._album_list_popup.add_command(label="Play this item", command=do_album_list_play_album)
                
        #add popup to album_list treeview        
        self._album_listbox.bind("<Button-3>", do_album_list_popup)  
        #add Covert art change to treeview selection      
        self._album_listbox.bind("<Button-1>", do_cover_art_show)  
        
        #album image
        self._album_workart_canvas = Canvas(self._top_album_frame, width = 300, height = 300)  
        self._album_workart_canvas.pack()  
        self._album_workart_canvas_frame = self._album_workart_canvas.create_window((0,0),
                                                                     window=self._right_album_frame, 
                                                                     anchor = NW)

        
     

        
    ################### MENU ACTIONS ######################################################

    def _browse_file(self):
        file_names = filedialog.askopenfilenames(parent=self._window_root, title="Choose files")
        self._window_root.tk.splitlist(file_names)
        for file_name in file_names:
            self._add_file_to_playlist(file_name, None) 
            
    def _play_favs(self):        
        try:
            #get favorite song list according to the parameters
            #TODO: show window to select quantity and score
            quantity = 5
            score = 5
            songs = AlbumManager.get_favorites(quantity, score)
            for song in songs:
                self._add_song_to_playlist(song) 
        except ApiException as e:
            logger.exception("Exception when calling PublicApi->api_songs_get_songs: %s\n" % e)
            
    def _show_album_list(self):
        #TODO: replace splash window by loading cursor or similar        
        #TODO: initialize the albums window layout after the call to the collection   
        splash = self.Splash(self._window_root)
        try:
            album_dict = AlbumManager.get_albums_from_collection()    
        except:
            #TODO: show warning window
            logger.exception("Exception when getting collection")
        else:      
            self._init_albums_window_layout()
            self._add_to_album_list(album_dict)
        splash.destroy()      
        
        

    ################### POP UP ACTIONS ######################################################
    
    ############### MAIN PLAYER #############

    def _playlistbox_add_to_favorites(self):
        #TODO: add command functionality and remove print
        song = self._playlist[self._playlist_popup.selection] 
        self._musicdb.api_songs_update_song(song)
        
        
    ################### BUTTONS ACTIONS ######################################################
         
    def _delete_song(self):
        selected_songs = self._playlistbox.selection()
        if selected_songs:
            selected_song = selected_songs[0]        
            self._playlistbox.delete(selected_song)
            self._playlist.pop(selected_song)
            
    def _play_music(self, file_list = None):
        if self._paused:            
            self._player.pause()
            self.statusbar['text'] = "Music Resumed"
            self._paused = FALSE
        else:
            try:
                if not file_list:
                    selected_songs_list = self._playlistbox.selection()
                    if selected_songs_list:
                        file_list = [(self._playlist[str(index_song)]).abs_path for index_song in selected_songs_list]
                    else:
                        file_list = [song.abs_path for song in self._playlist.values()]
         
                self._player.play_list(file_list)
            except Exception as ex:
                logger.exception('Exception while playing music: ' + str(ex)) 
                tkinter.messagebox.showerror('File not found', 'Player could not find the file. Please check again.')

    def _stop_music(self):        
        self._player.stop()
        self.statusbar['text'] = "Music stopped"
    
    
    def _pause_music(self):
        self._player.pause()
        if self._paused:
            self._paused = FALSE
            self.statusbar['text'] = "Music Resumed"
        else:
            self._paused = TRUE            
            self.statusbar['text'] = "Music paused"
    
    
    def _rewind_music(self):
        self._play_music()
        self.statusbar['text'] = "Music rewinded"
    
    
    def _set_volume(self, volume):
        self._player.set_volume(volume)
        
    
    def _mute_music(self):
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
        
        
    ####################### GUI EVENTS #################################
    def _on_closing(self):
        self._stop_music()
        self._stop_details_thread = True
        try:
            self._albums_window.destroy()
        except:
            pass
        self._window_root.destroy()
        
    def _on_closing_album_window(self):        
        self._albums_window.destroy()
  
        
    ######################### FUNCTION HELPERS #####################
    
    def _add_file_to_playlist(self, path_name, album):
        file_name = os.path.basename(path_name)
        song = Song()
        song.album = album
        try:
            song.update_song_data_from_file(path_name)  
        except:
            logger.exception("Failed to add song to the playlist")
        else:            
            index = 1         
            if album:
                album_title = album.title
            else:
                album_title = ""
            pl_index = self._playlistbox.insert("", index, text="Band Name", 
                                     values=(file_name, song.title, song.band, album_title, song.total_length)) 
            #add song to playlist dictionary, the index is the index in the playlist 
            self._playlist[pl_index] = song
            
    def _add_song_to_playlist(self, song):
        index = 1         
        pl_index = self._playlistbox.insert("", index, text="Band Name", 
                                     values=(song.file_name, song.title, song.band, song.album.title, song.total_length)) 
        #add song to playlist dictionary, the index is the index in the playlist 
        self._playlist[pl_index] = song
        
    def _add_to_album_list(self, album_dict):
        band_index = 1 
        for band, albums in album_dict.items():
            band_root = self._album_listbox.insert("", band_index, text=band,
                                           values=(band, 
                                                   "", 
                                                   "", 
                                                   "", 
                                                   "", 
                                                   "", 
                                                   "", 
                                                   ""))
            #print(band, band_root)
            band_index += 1            
            album_index = 1 
            for album_key, album in albums.items():
                #print(album)                
                album_id = self._album_listbox.insert(band_root, album_index, 
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
        
    def _show_details(self):
        self._details_thread.start()

    def _start_count(self, stop_thread):
        while stop_thread():
            #TODO: why it is not returning true when it should?
            while self._player.is_playing():     
                print("counting ")
                self._current_time_label['text'] = "Current Time" + ' - ' + self._player.get_time()
                time.sleep(1)
            time.sleep(1)
            
    @staticmethod
    def _treeview_sort_column(treeview, col, reverse):
        '''
        Function to sort the columns of a treeview when headings are clicked.
        @param: treeview, the treeview to sort
        @param: col, the column to sort
        @reverse: parameter to specify if it has to be sorted in reverse.        
        '''
        l = [(treeview.set(k, col), k) for k in treeview.get_children('')]
        l.sort(reverse=reverse)
    
        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            treeview.move(k, '', index)
    
        # reverse sort next time
        treeview.heading(col, command=lambda: \
                   GUI._treeview_sort_column(treeview, col, not reverse))


if __name__ == '__main__':
    gui = GUI()









