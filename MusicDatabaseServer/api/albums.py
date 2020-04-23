"""
Created on Oct 22, 2019

@author: thrasher
"""
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get_albums(data_provider=DatabaseProvider, quantity=None, album_id=None) -> str:
    return data_provider().get_albums(quantity, album_id)


@inject
def create_album(data_provider=DatabaseProvider, album=None):
    return data_provider().create_album(album)


@inject
def update_album(data_provider=DatabaseProvider, album=None):
    return data_provider().update_album(album)


@inject
def delete_album(data_provider=DatabaseProvider, album_id=None):
    return data_provider().delete_album(album_id)
