import time
import random

from servers.GameServer import GameServer
from typing import List

from utils import create_logger, distance_squared


class Construction(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Construction', game_config['log_level'])
        self.cherry = random.choice(self.game_config['objects']['trees'])
        self.steel = random.choice(self.game_config['objects']['construction_material'])

        self.tree_last_movement = {tree_id: (time.time(), tree.position) for tree_id, tree in
                                   self.state_data.objects['trees'].items()}
        self.planted_trees = set()
        self.ran_over_trees = set()

    def update_game_state(self):
        self.update_tree_movement()
        self.update_planted_trees()

    def update_tree_movement(self):
        """
        Updates tree movement data if a tree has moved more than the distance set in game config
        """
        for tree_id, movement_data in self.tree_last_movement.items():
            tree_position = self.state_data.objects['trees'][tree_id].position
            if distance_squared(movement_data[1], tree_position) > self.game_config['plant_min_distance_moved']:
                self.tree_last_movement[tree_id] = (time.time(), tree_position)

    def update_planted_trees(self):
        """
        Adds planted trees if a tree hasn't moved for more the time set in game config and hasn't been run over yet
        """
        for tree_id in [k for k, v in self.tree_last_movement.items() if
                        k not in self.ran_over_trees and time.time() -
                        self.tree_last_movement[k][0] > self.game_config['plant_min_time_seconds']]:
            self.planted_trees.add(tree_id)
