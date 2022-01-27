"""
Created on Oct 22, 2019

@author: thrasher
"""
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get_all_bands(data_provider=DatabaseProvider) -> str:
    return data_provider().get_all_bands()