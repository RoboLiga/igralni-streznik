import time
import random

from sledilnik.classes.Field import Field

from servers.GameServer import GameServer
from typing import Dict, List

from utils import create_logger, distance_squared, bilinear_point


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
        self.tree_fields = None

    def generate_tree_fields(self) -> Dict[str, Field]:
        """
        Splits game_field into a 5x4 grid of Field cells, using bilinear interpolation of its
        four corners so the grid stays correct even if the field isn't a perfect rectangle.
        """
        game_field = self.state_data.fields['game_field']
        cols, rows = 5, 4

        tree_fields: Dict[str, Field] = {}
        for row in range(rows):
            for col in range(cols):
                u0, u1 = col / cols, (col + 1) / cols
                v0, v1 = row / rows, (row + 1) / rows
                tree_fields[f'game_field_{row}_{col}'] = Field(
                    top_left=bilinear_point(game_field.top_left, game_field.top_right,
                                             game_field.bottom_left, game_field.bottom_right, u0, v0),
                    top_right=bilinear_point(game_field.top_left, game_field.top_right,
                                              game_field.bottom_left, game_field.bottom_right, u1, v0),
                    bottom_left=bilinear_point(game_field.top_left, game_field.top_right,
                                                game_field.bottom_left, game_field.bottom_right, u0, v1),
                    bottom_right=bilinear_point(game_field.top_left, game_field.top_right,
                                                 game_field.bottom_left, game_field.bottom_right, u1, v1),
                )

        return tree_fields

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
