"""
Created on Jan 22, 2020

@author: thrasher
"""
from flask_injector import inject
from providers.DatabaseProvider import DatabaseProvider


@inject
def get(data_provider=DatabaseProvider) -> str:
    return data_provider().get()

