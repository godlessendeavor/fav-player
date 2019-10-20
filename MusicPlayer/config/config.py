'''
Created on Aug 12, 2019

@author: thrasher
'''
import configparser

class PlayerConfig():
    
    def __init__(self):
        self._config = configparser.ConfigParser()
        self._set_defaults()
        self._read_config()
        
    def _set_defaults(self):
        self._config['MusicDiscography'] = {'DefaultPath' : '~'}
        
    def _read_config(self):
        self._config.read('player.cfg')
        
    def get_default_path(self):
        return self._config['MusicDiscography']['DefaultPath']
        
        