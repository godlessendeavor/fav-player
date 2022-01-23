"""
Created on Oct 22, 2019

@author: thrasher
"""
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get_all_albums(data_provider=DatabaseProvider) -> str:
    return data_provider().get_all_albums()


@inject
def get_album(data_provider=DatabaseProvider, album_title=None, band=None) -> str:
    return data_provider().get_album(album_title=album_title, band=band)

@inject
def get_album_by_id(data_provider=DatabaseProvider, id=None) -> str:
    return data_provider().get_album_by_id(album_id=id)


@inject
def get_random_albums(data_provider=DatabaseProvider, quantity=None) -> str:
    return data_provider().get_random_albums(quantiy=quantity)


@inject
def create_album(data_provider=DatabaseProvider, album=None):
    return data_provider().create_album(album=album)


@inject
def update_album(data_provider=DatabaseProvider, album=None):
    return data_provider().update_album(album=album)


@inject
def delete_album_by_id(data_provider=DatabaseProvider, id=None):
    return data_provider().delete_album(album_id=id)

@inject
def delete_album(data_provider=DatabaseProvider, album_title=None, band=None):
    return data_provider().delete_album(album_title=album_title, band=band)
