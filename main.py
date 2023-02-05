# -*- coding: utf-8 -*-

import logging
from json import JSONEncoder
from multiprocessing import freeze_support

import yaml
from gevent.pywsgi import WSGIServer

from so2.restapi.GameApi import create_api
from so2.servers.StateServer import StateServer
from so2.servers.TrackerServer import TrackerServer


def read_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_logger() -> logging.Logger:
    # create a logger
    l = logging.getLogger('sledenje-objektom')
    l.setLevel(logging.ERROR)

    # create a file handler
    file_handler = logging.FileHandler('slednje-objektom.log')
    file_handler.setLevel(logging.ERROR)

    # create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # add handlers to the logger
    l.addHandler(file_handler)
    l.addHandler(console_handler)

    return l


if __name__ == '__main__':
    logger = create_logger()
    logger.info('Started')

    tracker_config = read_config('./tracker_config.yaml')
    game_config = read_config('./game_config.yaml')

    freeze_support()
    game_servers = {}

    tracker_server = TrackerServer()
    # tracker_server.tracker.config['video_source'] = 0
    tracker_server.start()

    state_server = StateServer(tracker_server, game_config)
    state_server.start()

    rest_app = create_api(game_servers, state_server, tracker_config, game_config)
    rest_server = WSGIServer(('0.0.0.0', 8088), rest_app)
    rest_server.serve_forever()