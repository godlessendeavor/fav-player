'''
Created on Nov 12, 2019

@author: thrasher
'''
#!/usr/bin/python
# -*- coding: utf-8 -*-

# config.py: configuration data of this app
#   - the config is first read from a json file
#   - env variables may override (in docker setup etc)

import json
import os

# first load config from a json file,
appconf = json.load(open(os.environ["MUSICDB_CONFIG_FILE"]))

# database config
DATABASE_HOST     = appconf['music_db']['DATABASE_HOST']
DATABASE_PORT     = appconf['music_db']['DATABASE_PORT']
DATABASE_NAME     = appconf['music_db']['DATABASE_NAME']
DATABASE_USER     = appconf['music_db']['DATABASE_USER']
DATABASE_PASSWORD = appconf['music_db']['DATABASE_PASSWORD']

SERVER_PORT = appconf['server']['PORT']

LOGGING_LEVEL = appconf['logging']['LOGGING_LEVEL']

