import os
from os.path import join

import requests
import json
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--mstreamip', help='IP address of mstream')
parser.add_argument('--musicdbip', help='IP address of musicdbserver')
args = parser.parse_args()

# api-endpoints
if not args.mstreamip:
    mstream_base_url = "http://localhost:6680"
else:
    mstream_base_url = args.mstreamip

if not args.musicdbip:
    musicdb_URL = "http://localhost:2020"
else:
    musicdb_URL = args.musicdbip

musicdb_URL_post_fav = musicdb_URL + '/music/song'
musicdb_URL_get_album = musicdb_URL + '/music/album'

mstream_URL = f"{mstream_base_url}/db/rate-song"
login_mstream_URL = f"{mstream_base_url}/login"
ping_mstream_URL = f"{mstream_base_url}/ping"
mstream_get_rated_URL = f"{mstream_base_url}/db/rated-song"
mstream_all_rated_URL = f"{mstream_base_url}/db/all-rated-songs"
mstream_clear_rated_URL = f"{mstream_base_url}/db/clear-rated"


def get_mstream_favs():
    login_res = requests.post(url=login_mstream_URL,
                              json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                              headers={'content-type': 'application/json'})
    login_data = json.loads(login_res.text)
    mstream_access_token = login_data['token']
    ping_res = requests.post(url=login_mstream_URL,
                             json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                             headers={'content-type': 'application/json', 'x-access-token' : mstream_access_token})
    ping_data = json.loads(ping_res.text)
    mstream_access_token = ping_data['token']
    headers = {'content-type': 'application/json', 'x-access-token': mstream_access_token}

    res = requests.get(url=mstream_all_rated_URL, headers=headers)
    json_res = json.loads(res.text)

    print(f'Length all rated songs in old mstream {len(json_res["rated"])}')

    return json_res['rated']


def send_favs_to_musicdb(rated_files_mstream):
    for song in rated_files_mstream:
        song_data = song['right']
        title = song_data['title']
        file_name = song_data['file_name']
        params = {'album_title': song_data['album'],
                  'band': song_data['artist']}
        score = song['left']['rating']
        track_number = song_data['track']
        res = requests.get(url=musicdb_URL, params=params, headers={'Authorization': 'Bearer ' + os.environ.get('ACCESS_TOKEN')})
        album = json.loads(res.text)
        if album:
            song_json_obj = {'title': title,
                             'file_name': file_name,
                             'track_number': track_number,
                             'score': score,
                             'type': 'NA',
                             'album_id': album['id']}

            requests.post(url=musicdb_URL_post_fav,
                         json=song_json_obj,
                         headers={'Authorization': 'Bearer ' + os.environ.get('ACCESS_TOKEN')})


rated_mstream = get_mstream_favs()
with open('rated_mstream_songs.json', 'w') as outfile:
    json.dump(rated_mstream, outfile)

#with open('rated_mstream_songs.json') as json_file:
#    data = json.load(json_file)
#    send_favs_to_musicdb(data)