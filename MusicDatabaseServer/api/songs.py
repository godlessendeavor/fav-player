"""
Created on Oct 22, 2019

@author: thrasher
"""
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get_songs(data_provider=DatabaseProvider, quantity=None, score=0.0) -> str:
    return data_provider().get_songs(quantity, score)


@inject
def create_song(data_provider=DatabaseProvider, song=None):
    return data_provider().create_song(song)


@inject
def update_song(data_provider=DatabaseProvider, song=None):
    return data_provider().update_song(song)


@inject
def delete_song(data_provider=DatabaseProvider, song_id=None):
    return data_provider().delete_song(song_id)
