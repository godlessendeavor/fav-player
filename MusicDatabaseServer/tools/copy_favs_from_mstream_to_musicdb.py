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
    missing_data = []
    for song in rated_files_mstream:
        try:
            song_data = song['right']
            title = song_data['title']
            file_name = os.path.basename(song_data['filepath'])
            params = {'album_title': song_data['album'],
                      'band': song_data['artist']}
            score = song['left']['rating']
            song_data['score'] = score
            track_number = song_data['track']
            res = requests.get(url=musicdb_URL_get_album, params=params)
            album = json.loads(res.text)
            if album and res.status_code == 200:
                song_json_obj = {'title': title,
                                 'file_name': file_name,
                                 'track_number': track_number,
                                 'score': score,
                                 'type': 'NA',
                                 'album': {'id': album[0]['id']}}

                res_musicdb = requests.post(url=musicdb_URL_post_fav, json=song_json_obj)
                if res_musicdb.status_code != 200:
                    missing_data.append(song_data)
            else:
                missing_data.append(song_data)
            time.sleep(0.1)
        except Exception as ex:
            print(ex)
            print(song)
    with open('failures_on_musicdb.json', 'w') as errors_file:
        print(f'Could not find album for song with data {json.dumps(missing_data)}', file=errors_file)



#rated_mstream = get_mstream_favs()
#with open('rated_mstream_songs.json', 'w') as outfile:
#    json.dump(rated_mstream, outfile)

with open('rated_mstream_songs.json') as json_file:
    data = json.load(json_file)
    send_favs_to_musicdb(data)