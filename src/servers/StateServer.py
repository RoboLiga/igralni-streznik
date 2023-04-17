# -*- coding: utf-8 -*-import logging
import logging
import math

import gevent
from sledilnik.classes import Point

from src.classes.StateLiveData import StateLiveData
from src.servers.Server import Server
from src.servers.TrackerServer import TrackerServer
from src.utils import create_logger


class StateServer(Server):
    """Server that stores abstract board information

    Server pulls information from the tracker server and serves the abstract description of the game board.

    Attributes:
        tracker: Tracker server
    """

    def __init__(self, tracker_server: TrackerServer, game_config: dict):
        Server.__init__(self)
        self.logger = create_logger('servers.StateServer', game_config['log_level'])
        self.tracker: TrackerServer = tracker_server
        self.state: StateLiveData = StateLiveData(game_config)

    def _run(self):
        self.logger.info('State server started.')
        while True:
            self.tracker.updated.wait()

            self.state.parse(self.tracker.state)

            self.updated.set()

            gevent.sleep(0.01)
            self.updated.clear()

    # def get_distance(self, p1: Point, p2: Point) -> float:
    #     """
    #     Evklidska razdalja med dvema točkama na poligonu.
    #     """
    #     return math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
