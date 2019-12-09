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
    app = connexion.App(__name__, specification_dir='open_api/')  # Provide the app and the directory of the docs
    app.add_api(
        'app_definition.yaml', 
        resolver  = RestyResolver('api'), #TODO: change api to music and remove the operationId from the API definitions and 'music' from the path resolutions
        arguments = {'title': 'DatabaseServer'},
        strict_validation=True)
    FlaskInjector(app=app.app, modules=[configure])
    #TODO: get port from config
    app.run(port=2020, debug=True)
    