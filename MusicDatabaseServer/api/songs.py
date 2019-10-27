'''
Created on Oct 22, 2019

@author: thrasher
'''
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get_song(data_provider=DatabaseProvider, quantity = 1, score = 0.0) -> str:
    return data_provider().get_song(quantity, score)
