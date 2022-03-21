import os
from collections import defaultdict

import requests
import json
import difflib
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--musicdbip', help='IP address of musicdbserver')
args = parser.parse_args()

if not args.musicdbip:
    musicdb_URL = "http://localhost:2020"
else:
    musicdb_URL = args.musicdbip

musicdb_URL_post_fav = musicdb_URL + '/music/song'
musicdb_URL_get_album = musicdb_URL + '/music/album'
musicdb_URL_all_albums = musicdb_URL + '/music/album/all'

missing_songs = []

def get_all_albums():
    res_musicdb = requests.get(url=musicdb_URL_all_albums)
    if res_musicdb.status_code == 200:
        return json.loads(res_musicdb.text)

def organize_missing_songs(songs_file_name):
    global missing_songs
    organized_songs = defaultdict(lambda: defaultdict(list))
    with open(songs_file_name) as songs_file:
        songs = json.load(songs_file)
        for song_data in songs:
            title = song_data['title']
            file_name = os.path.basename(song_data['filepath'])
            score = song_data['score']
            track_number = song_data['track']
            req_obj = {'title': title,
                             'file_name': file_name,
                             'track_number': track_number,
                             'score': score,
                             'type': 'NA'}
            song_obj = {}
            song_obj['album'] = song_data['album']
            song_obj['band'] = song_data['artist']
            song_obj['request'] = req_obj
            if song_data['artist'] and song_data['album']:
                organized_songs[song_data['artist']][song_data['album']].append(song_obj)
            else:
                missing_songs.append(song_obj)
    return organized_songs


def send_missing_favs_to_musicdb(organized_songs, all_albums):
    global missing_songs
    for band in organized_songs.keys():
        for album in organized_songs[band].keys():
            song_data = organized_songs[band][album][0]
            song_found = False
            for musicdb_album in all_albums:
                try:
                    if musicdb_album['band'].casefold() == band.casefold():
                        print(f"Band {band} found as {musicdb_album['band']}")
                        print(f"Is album \"{musicdb_album['title']}\" matching \"{album}\"?")
                        answer = str(input())
                        if answer == 'y':
                            for song_data in organized_songs[band][album]:
                                song_json_obj = song_data['request']
                                song_json_obj['album'] = {'id': musicdb_album['id']}
                                res_musicdb = requests.post(url=musicdb_URL_post_fav, json=song_json_obj)
                                if res_musicdb.status_code != 200:
                                    print(f"Some error when posting fav {res_musicdb.text}")
                                    missing_songs.append(song_data)
                                else:
                                    song_found = True
                            break
                except Exception as ex:
                    missing_songs.append(song_data)
                    print(f"Got exception {ex} with song {song_data}")
            if not song_found:
                for song_data in organized_songs[band][album]:
                    print(f"Song {song_data} was not found")
                    missing_songs.append(song_data)

all_albums = get_all_albums()
if all_albums:
    organized_songs = organize_missing_songs('secondary_failures_on_musicdb.json')
    send_missing_favs_to_musicdb(organized_songs, all_albums)
    with open('3rd_failures_on_musicdb.json', 'w') as errors_file:
        print(f'{json.dumps(missing_songs)}', file=errors_file)
