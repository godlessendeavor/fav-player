import requests
from os.path import join
import simplejson as json
import os

local = False
# api-endpoints
if local:
    mstream_base_url = "http://localhost:3000"
else:
    mstream_base_url="http://192.168.1.107:6680"

album_app_URL = "http://localhost:2020/music/fav_songs"
mstream_URL = f"{mstream_base_url}/db/rate-song"
login_mstream_URL = f"{mstream_base_url}/login"
ping_mstream_URL = f"{mstream_base_url}/ping"

mstream_access_token = None
login_res = requests.post(url=login_mstream_URL,
              json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
              headers={'content-type': 'application/json'})
login_data = json.loads(login_res.text)
mstream_access_token = login_data['token']

if local:
    mstream_path = "media"
else:
    ping_res = requests.post(url=login_mstream_URL,
                             json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                             headers={'content-type': 'application/json', 'x-access-token' : mstream_access_token})
    ping_data = json.loads(ping_res.text)
    mstream_access_token = ping_data['token']
    mstream_path = ping_data['vpaths'][0]

fav_data = requests.get(url=album_app_URL, headers={'Authorization': 'Bearer '+os.environ.get('ACCESS_TOKEN')})
data = json.loads(fav_data.text)

if local:
    headers = {'content-type': 'application/json', 'x-access-token': mstream_access_token}
else:
    headers = {'content-type': 'application/json'}

for song in data['songs']:
    rating = song['score']
    rating = round(rating * 2) / 2
    file_name = song['file_name']
    album_path = join(song['album']['band'], str(song['album']['year']) + ' - ' + song['album']['title'])
    file_path = join(mstream_path, album_path, file_name)
    #json_input = {'rating': rating, 'filepath': file_path.encode('utf-8')}
    json_input = {'rating': rating, 'filepath': file_path}
    res = requests.post(url=mstream_URL,
                        json=json_input,
                        headers=headers)

    json_res = json.loads(res.text)
    if 'error' in json_res:
        error_val = json_res['error']
        print(f'Error: {error_val}')
        print(json_input)
    else:
        pass
        #print('Success with {}'.format(json_input))
