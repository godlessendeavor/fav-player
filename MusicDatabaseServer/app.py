'''
Created on Oct 22, 2019

@author: thrasher
'''

import connexion
from flask_injector import FlaskInjector
from connexion.resolver import RestyResolver
from providers.DatabaseProvider import DatabaseProvider
from config import config

from injector import Binder


def configure(binder: Binder) -> Binder:
    binder.bind(
        DatabaseProvider
    )


# TODO: get a generated token elsewhere
TOKENS = {
    config.ACCESS_TOKEN: 'music_player',
}


def token_info(access_token) -> dict:
    uid = TOKENS.get(access_token)
    if not uid:
        return None
    return {'uid': uid, 'scope': ['uid']}


def create_app():
    conn_app = connexion.App(__name__, specification_dir='open_api/')  # Provide the app and the directory of the docs
    conn_app.add_api(
        'app_definition.yaml',
        resolver=RestyResolver('api'),
        arguments={'title': 'DatabaseServer'},
        strict_validation=True)
    FlaskInjector(app=conn_app.app, modules=[configure])
    return conn_app


if __name__ == '__main__':
    app = create_app()
    app.run(port=config.SERVER_PORT, debug=True)
