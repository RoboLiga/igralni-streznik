import time
import random

from sledilnik.classes.Field import Field

from games.construction.ConstructionTeam import ConstructionTeam
from servers.GameServer import GameServer
from typing import Dict, List

from utils import create_logger, distance_squared, bilinear_point

BUILDER_COLOR = 'orange'

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
        self.tree_fields = self.generate_tree_fields()

    def generate_tree_fields(self) -> Dict[str, Field]:
        """
        Splits game_field into a grid of Field cells, using bilinear interpolation of its
        four corners so the grid stays correct even if the field isn't a perfect rectangle.
        """
        game_field = self.state_data.fields['game_field']
        tree_field_config = self.game_config['tree_fields']
        cols = tree_field_config['columns']
        rows = tree_field_config['rows']

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

    def set_teams(self, teams: List[int]):
        colors = [BUILDER_COLOR, 'green']
        self.teams = {team: self.init_team(team, color) for team, color in zip(teams, colors)}

    def init_team(self, robot_id: int, color: str):
        if robot_id in self.game_config['robots']:
            return ConstructionTeam(robot_id, color, self.game_config['robots'][robot_id])
        else:
            self.logger.error("Team with specified id does not exist in config!")
            raise Exception("Team with specified id does not exist in config!")

    def update_game_state(self):
        self.update_trees()

    def update_trees(self):
        """
        Adds planted trees if a tree hasn't moved for more the time set in game config and hasn't been run over yet
        """
        for tree_id, movement_data in self.tree_last_movement.items():
            if tree_id not in self.state_data.objects['trees']:
                self.logger.warning(f"Tracked tree (ID: {tree_id}) is not in the state data!")
                continue
            tree_position = self.state_data.objects['trees'][tree_id].position
            if distance_squared(movement_data[1], tree_position) > self.game_config['plant_min_distance_moved']:
                self.tree_last_movement[tree_id] = (time.time(), tree_position)
                if tree_id in self.planted_trees:
                    self.planted_trees.remove(tree_id)
                    self.logger.info(f"Tracked tree (ID: {tree_id}) has been unplanted.")

        for tree_id in [k for k, v in self.tree_last_movement.items() if
                        k not in self.ran_over_trees and time.time() -
                        self.tree_last_movement[k][0] > self.game_config['plant_min_time_seconds']]:
            self.planted_trees.add(tree_id)
            self.logger.info(f"Tracked tree (ID: {tree_id}) has been planted.")

