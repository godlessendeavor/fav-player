import requests
from os.path import join
import json

# api-endpoints
album_app_URL = "http://localhost:2020/music/fav_songs"
mstream_URL = "http://localhost:3000/db/rate-song"

fav_data = requests.get(url=album_app_URL, headers={'Authorization': 'Bearer 666'})
data = json.loads(fav_data.text)

for song in data['songs']:
    rating = song['score']
    rating = round(rating * 2) / 2
    file_name = song['file_name']
    album_path = join(song['album']['band'], str(song['album']['year']) + ' - ' + song['album']['title'])
    file_path = join('/media', album_path, file_name)
    json_input = {'rating':rating, 'filepath': file_path.encode('utf-8')}
    res = requests.post(url=mstream_URL,
                        json= json_input,
                        headers={'content-type':'application/json'})
    json_res = json.loads(res.text)
    if 'error' in json_res:
        error_val = json_res['error'].encode('utf-8')
        print('Error: {error_val}'.format(error_val=error_val))
        print(json_input)
    else:
        pass
        #print('Success with {}'.format(json_input))
