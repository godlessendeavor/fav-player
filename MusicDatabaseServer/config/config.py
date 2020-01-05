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

dir_path = os.path.dirname(os.path.realpath(__file__))
# first load config from a json file
appconf = None
try:
    appconf = json.load(open(os.environ.get("MUSICDB_CONFIG_FILE")))
except KeyError:
    appconf = json.load(open(os.path.join(dir_path, 'defaults/musicdb.conf.default')))

# database config
DATABASE_HOST     = os.environ.get('DATABASE_HOST')
DATABASE_PORT     = os.environ.get('DATABASE_PORT')
DATABASE_NAME     = os.environ.get('DATABASE_NAME')
DATABASE_USER     = os.environ.get('DATABASE_USER')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')

SERVER_PORT = int(os.environ.get('APP_PORT'))

LOGGING_LEVEL = appconf['logging']['LOGGING_LEVEL']
