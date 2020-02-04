'''
Created on Aug 12, 2019

@author: thrasher
'''
# config.py: configuration data of this app
#   - the config is first read from a json file
#   - env variables may override

import json
import os
import logging
from musicdb_client.configuration import Configuration as Musicdb_config

dir_path = os.path.dirname(os.path.realpath(__file__))

# first load config from a json file,
mpconf = None
try:
    mpconf = json.load(open(os.environ["MUSIC_CONFIG_FILE"]))
except KeyError:
    mpconf = json.load(open(os.path.join(dir_path, 'defaults/music.conf.default')))

# database config
LOGGING_LEVEL_NAME = mpconf['logging']['LOGGING_LEVEL']
MUSIC_PATH = mpconf['music_player']['MUSIC_PATH']
MUSIC_DB_HOST = mpconf['music_db']['HOST']    
MUSIC_DB_TOKEN = '666' # TODO: add from config

# non-compliances files
NON_COMPLIANT_ALBUMS_LOG = mpconf['non_compliances_log']['ALBUMS']  
NON_COMPLIANT_SONGS_LOG = mpconf['non_compliances_log']['SONGS'] 

LOGGING_FORMAT = '[%(asctime)-15s] [%(name)s] %(levelname)s]: %(message)s'
LOGGING_LEVEL = logging.getLevelName(LOGGING_LEVEL_NAME)


def get_musicdb_client_config(logger):    
    _musicdb_config = Musicdb_config()
    _musicdb_config.host = MUSIC_DB_HOST
    if LOGGING_LEVEL == logging.DEBUG:
        _musicdb_config.debug = True
    _musicdb_config.access_token = MUSIC_DB_TOKEN
    _musicdb_config.logger_file_handler = logger
    print(_musicdb_config.auth_settings())
    return _musicdb_config
