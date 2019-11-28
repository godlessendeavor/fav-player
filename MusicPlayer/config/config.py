'''
Created on Aug 12, 2019

@author: thrasher
'''
# config.py: configuration data of this app
#   - the config is first read from a json file
#   - env variables may override

import json
import os

# first load config from a json file,
mpconf = json.load(open(os.environ["MUSIC_CONFIG_FILE"]))

# database config
LOGGING_LEVEL = mpconf['logging']['LOGGING_LEVEL']
        