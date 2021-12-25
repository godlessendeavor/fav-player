import requests
from json import loads
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--ip', help='IP address of mstream')
args = parser.parse_args()

if not args.ip:
    mstream_base_url = "http://localhost:6680"
else:
    mstream_base_url = args.ip

amount_mstream_URL = f"{mstream_base_url}/db/amount-rated-songs"
login_mstream_URL = f"{mstream_base_url}/login"
ping_mstream_URL = f"{mstream_base_url}/ping"

login_res = requests.post(url=login_mstream_URL,
                          json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
                          headers={'content-type': 'application/json'})
login_data = loads(login_res.text)
print(login_data)
access_token = login_data['token']
ping_res = requests.post(url=login_mstream_URL,
              json={'username': "godlessendeavor", 'password': os.environ.get('MSTREAM_PASSWORD')},
              headers={'content-type': 'application/json', 'x-access-token': access_token})
ping_data = loads(ping_res.text)
access_token = ping_data['token']
mstream_path = ping_data['vpaths'][0]

headers = {'content-type': 'application/json', 'x-access-token': access_token}

res = requests.get(url=amount_mstream_URL,
                       headers=headers)

json_res = loads(res.text)
print(json_res)

