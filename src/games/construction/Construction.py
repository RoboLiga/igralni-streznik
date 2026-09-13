import random

from servers.GameServer import GameServer
from typing import Dict, List

from utils import create_logger

class Construction(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Construction', game_config['log_level'])
        self.cherry = random.choice(self.game_config['objects']['trees'])
        self.steel = random.choice(self.game_config['objects']['construction_material'])

    def update_game_state(self):
        pass