# -*- coding: utf-8 -*-import logging
import logging
import math

import gevent
from sledilnik.classes import Point

from so2.classes.StateLiveData import StateLiveData
from so2.servers.Server import Server
from so2.servers.TrackerServer import TrackerServer


class StateServer(Server):
    """Server that stores abstract board information

    Server pulls information from the tracker server and serves the abstract description of the game board.

    Attributes:
        tracker: Tracker server
    """

    def __init__(self, tracker_server: TrackerServer, config: dict):
        Server.__init__(self)
        self.logger = logging.getLogger('sledenje-objektom.StateServer')
        self.tracker: TrackerServer = tracker_server
        self.state: StateLiveData = StateLiveData(config)

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
