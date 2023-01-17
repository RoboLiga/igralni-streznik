# -*- coding: utf-8 -*-
import logging
from timeit import default_timer as timer
from typing import Dict, List
from uuid import uuid4

import gevent

from so2.entities.StateLiveData import StateLiveData
from so2.servers.Server import Server
from so2.entities.Team import Team
from so2.servers.StateServer import StateServer


class GameServer(Server):
    """Game state for particular game

    Pulls information from a state server and computers a game state.

    Attributes:
        id (UUID): Game id
        key (string): Key for write permissions
    """

    def __init__(self, state_server: StateServer, config: Dict, team_1: int, team_2: int):
        Server.__init__(self)

        self.logger = logging.getLogger('sledenje-objektom.GameServer')
        self.config = config

        self.state_server: StateServer = state_server
        self.id: str = str(uuid4())[:4]
        self.key: str = "very_secret_key"

        self.game_on: bool = False
        self.game_time: int = config['game_time']
        self.start_time: float = timer()
        self.pause_total_time: float = 0.0
        self.pause_start_time: float = 0.0

        self.time: float = timer()
        self.alter_score: List[int] = [0, 0]

        self.team_1 = self.init_team(team_1)
        self.team_2 = self.init_team(team_2)

    def _run(self):
        self.logger.info("Started a new game server with id: %s" % self.id)
        while True:
            # Wait for state server to update state
            self.state_server.updated.wait()
            self.stateData: StateLiveData = self.state_server.state

            # print(self.id, self.gameData.gameOn)
            if self.game_data.game_on:
                # TODO: Compute score
                # self.game_data.check_hive_zones(self.stateData)
                # self.game_data.compute_score(self.stateData)
                # stop the game when no time left
                if self.game_data.check_time_left() <= 0:
                    self.game_data.game_on = False
                    self.game_data.start_time = timer()
                    break
            else:
                self.game_data.start_time = timer()

            self.updated.set()
            gevent.sleep(0.01)
            self.updated.clear()

    def set_teams(self, team_1, team_2):
        self.team_1 = self.init_team(team_1)
        self.team_2 = self.init_team(team_2)

    def init_team(self, robot_id: int):
        if robot_id in self.config['robots']:
            return Team(robot_id, self.config['robots'][robot_id])
        else:
            logging.error("Team with specified id does not exist in config!")
            raise Exception("Team with specified id does not exist in config!")

    def alter_score(self, scores: Dict[str, int]):

        self.game_data.alter_score[0] = scores['team1']
        self.game_data.alter_score[1] = scores['team2']

        return {
            'team1': self.game_data.team_1.score,
            'team2': self.game_data.team_2.score
        }

    def start_game(self):
        self.team_1.score = 0
        self.team_2.score = 0
        self.start_time = timer()
        self.pause_start_time = 0.0
        self.pause_total_time = 0.0
        self.game_on = True

    def pause_game(self):
        if self.game_on:
            self.pause_start_time = timer()
            self.game_on = False

    def unpause_game(self):
        if not self.game_on:
            self.game_on = True
            self.pause_total_time += timer() - self.pause_start_time
            self.pause_start_time = 0.0

    def stop_game(self):
        self.game_data.game_on = False

    def check_time_left(self):
        if self.game_on:
            return self.game_time - (timer() - self.start_time) + self.pause_total_time
        return self.game_time

    def set_game_time(self, game_time: int):
        self.game_time = game_time

    def to_json(self, state_live_data: StateLiveData):
        return {
            "objects": {
                "robots": {str(robot.id): robot.to_json() for robot in state_live_data.robots}
            },
            "fields": {
                "field": state_live_data.fields_names["field"].to_json()
            },
            "teams": {
                "team_1": self.team_1.to_json(),
                "team_2": self.team_2.to_json()
            },
            "time_left": self.check_time_left(),
            "game_on": self.game_on
        }
