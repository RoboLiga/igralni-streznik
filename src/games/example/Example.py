import logging
from random import randint

from src.servers.GameServer import GameServer


class Example(GameServer):
    def __init__(self, state_server, game_config, teams):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = logging.getLogger('games.Example')

    def update_game_state(self):
        """
        Computes score for each team
        """
        for team_key in self.teams:
            team = self.teams[team_key]
            team.score = randint(-100, 100)
