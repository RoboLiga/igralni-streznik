import logging
from random import randint

from src.servers.GameServer import GameServer


class Example(GameServer):
    def __init__(self, state_server, game_config, team_1, team_2):
        GameServer.__init__(self, state_server, game_config, team_1, team_2)
        self.logger = logging.getLogger('games.Example')

    def compute_score(self):
        """
        Computes score for each team
        """
        self.team_1.score = randint(0, 100)
        self.team_2.score = randint(0, 100)
        pass
