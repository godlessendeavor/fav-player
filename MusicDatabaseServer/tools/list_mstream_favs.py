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

amount_mstream_URL = f"{mstream_base_url}/db/amount-rated-songs"
login_mstream_URL = f"{mstream_base_url}/login"
ping_mstream_URL = f"{mstream_base_url}/ping"

if local:
    mstream_path = "media"
else:
    login_res = requests.post(url=login_mstream_URL,
                              json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                              headers={'content-type': 'application/json'})
    login_data = json.loads(login_res.text)
    print(login_data)
    access_token = login_data['token']
    ping_res = requests.post(url=login_mstream_URL,
                  json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                  headers={'content-type': 'application/json', 'x-access-token': access_token})
    ping_data = json.loads(ping_res.text)
    access_token = ping_data['token']
    mstream_path = ping_data['vpaths'][0]

if local:
    headers = {'content-type': 'application/json'}
else:
    headers = {'content-type': 'application/json', 'x-access-token': access_token}

res = requests.get(url=amount_mstream_URL,
                       headers=headers)

json_res = json.loads(res.text)
print(json_res)

