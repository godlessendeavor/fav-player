import os
from os.path import join

import requests
import simplejson as json
import time

local = True
clear = False
# api-endpoints
if local:
    mstream_base_url = "http://localhost:3000"
else:
    mstream_base_url="http://192.168.1.107:6680"

album_app_URL = "http://localhost:2020/music/fav_songs"
mstream_URL = f"{mstream_base_url}/db/rate-song"
login_mstream_URL = f"{mstream_base_url}/login"
ping_mstream_URL = f"{mstream_base_url}/ping"
mstream_get_rated_URL = f"{mstream_base_url}/db/rated-song"
mstream_rated_amount_URL = f"{mstream_base_url}/db/amount-rated-songs"
mstream_all_rated_URL = f"{mstream_base_url}/db/all-rated-songs"
mstream_clear_rated_URL = f"{mstream_base_url}/db/clear-rated"

if local:
    mstream_path = "media"
    headers = {'content-type': 'application/json'}
else:
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
    mstream_path = ping_data['vpaths'][0]
    headers = {'content-type': 'application/json', 'x-access-token': mstream_access_token}

fav_data = requests.get(url=album_app_URL, headers={'Authorization': 'Bearer '+os.environ.get('ACCESS_TOKEN')})
data = json.loads(fav_data.text)

if clear:
    res = requests.post(url=mstream_clear_rated_URL, headers=headers)


print(f'There are {len(data["songs"])} favorites in my app')

seen_titles = set()
song_list = []
for obj in data["songs"]:
    if obj['file_name'] not in seen_titles:
        song_list.append(obj)
        seen_titles.add(obj['file_name'])

print(f'There are {len(song_list)} favorites in my app after deduplicating')


res = requests.get(url=mstream_all_rated_URL, headers=headers)
json_res = json.loads(res.text)

print(f'Length all rated songs {len(json_res["rated"])}')

count_songs_not_found = 0
for song in json_res['rated']:
    try:
        song["right"]["filepath"]
    except:
        count_songs_not_found += 1

rated_files_mstream = [song["right"]["filepath"] for song in json_res['rated'] if "filepath" in song["right"]]
rated_files_mstream = [file.lower() for file in rated_files_mstream]

for song in song_list:
    rating = song['score']
    rating = round(rating * 2) / 2
    file_name = song['file_name']
    album_path = join(song['album']['band'], str(song['album']['year']) + ' - ' + song['album']['title'])
    file_path = join(album_path, file_name)
    file_path_mstream = join(mstream_path, album_path, file_name)

    if file_path.lower() not in rated_files_mstream:
        print(f'!!!!!!File {file_path} was not found in mstream')

        time.sleep(0.1)
        json_input = {'rating': rating, 'filepath': file_path_mstream}
        res = requests.post(url=mstream_URL, json=json_input, headers=headers)

        json_res = json.loads(res.text)
        if 'error' in json_res:
            error_val = json_res['error']
            print(f'Error: {error_val}')
            print(json_input)
        #elif 'typeSave' in json_res and json_res['typeSave'] == 'update':
        #    print(f'This was an updateeeee!!!')
        #    break
        else:
            print('Success with {}'.format(json_res))

