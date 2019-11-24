'''
Created on Oct 22, 2019

@author: thrasher
'''

import connexion
from flask_injector import FlaskInjector
from connexion.resolver import RestyResolver
from providers.DatabaseProvider import DatabaseProvider

from injector import Binder

def configure(binder: Binder) -> Binder:
    binder.bind(
        DatabaseProvider
    )


if __name__ == '__main__':
    print(connexion.__version__)
    app = connexion.App(__name__, specification_dir='open_api/')  # Provide the app and the directory of the docs
    app.add_api(
        'app_definition.yaml', 
        resolver  = RestyResolver('api'),
        arguments = {'title': 'DatabaseServer'},
        strict_validation=True)
    FlaskInjector(app=app.app, modules=[configure])
    #TODO: get port from config
    app.run(port=2020, debug=True)
    