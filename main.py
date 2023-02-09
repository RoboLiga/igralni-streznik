# -*- coding: utf-8 -*-
import importlib
import logging
from json import JSONEncoder
from multiprocessing import freeze_support

import yaml
from gevent.pywsgi import WSGIServer

from so2.restapi.GameApi import create_api
from so2.servers import GameServer
from so2.servers.StateServer import StateServer
from so2.servers.TrackerServer import TrackerServer


def read_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_logger(log_level: int) -> logging.Logger:
    # create a logger
    l = logging.getLogger('sledenje-objektom')
    l.setLevel(log_level)

    # create a file handler
    file_handler = logging.FileHandler('slednje-objektom.log')
    file_handler.setLevel(log_level)

    # create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # add handlers to the logger
    l.addHandler(file_handler)
    l.addHandler(console_handler)

    return l


if __name__ == '__main__':
    logger = create_logger(logging.DEBUG)
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

    GameClass = getattr(
        importlib.import_module(f"so2.games.{game_config['game'].lower()}.{game_config['game']}"),
        game_config['game']
    )
    new_game: GameServer = GameClass(state_server, game_config, 0, 2)
    new_game.game_time = 99999
    new_game.id = 'test'

    game_servers[new_game.id] = new_game
    new_game.start()
    new_game.start_game()

    rest_app = create_api(game_servers, state_server, tracker_config, game_config)
    rest_server = WSGIServer(('0.0.0.0', 8088), rest_app)
    rest_server.serve_forever()
