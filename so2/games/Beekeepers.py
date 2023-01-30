import logging

from so2.servers.GameServer import GameServer


class Beekeepers(GameServer):
    def __init__(self, state_server, config, team_1, team_2):
        GameServer.__init__(self, state_server, config, team_1, team_2)

        self.logger = logging.getLogger('sledenje-objektom.Beekeepers')

    def compute_score(self):
        """
        Computes score for each team
        """
        self.team_1.score = 123
        self.team_2.score = 456
