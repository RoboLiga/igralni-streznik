import time
import random

from flask_restx import Api, fields
from sledilnik.classes.Field import Field

from src.games.construction.ConstructionTeam import ConstructionTeam, BUILDER_COLOR
from src.servers.GameServer import GameServer
from typing import Dict, List, Optional, cast

from src.utils import create_logger, distance_squared, bilinear_point, check_if_object_in_area


def tree_field_name(row: int, col: int) -> str:
    return f'game_field_{row}_{col}'


class Construction(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Construction', game_config['log_level'])
        self.cherry = random.choice(self.game_config['objects']['trees'])
        self.steel = random.choice(self.game_config['objects']['construction_material'])

        # State data is only available once the game loop runs, so these are filled in on the first update
        self.tree_last_movement: dict[int, tuple] = dict()
        self.tree_fields: Optional[Dict[str, Field]] = None
        self.planted_trees: dict[int, Field] = dict()
        self.ran_over_trees: int = 0
        self.used_planted_trees: set[int] = set()

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
                tree_fields[tree_field_name(row, col)] = Field(
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

    def get_objects_with_types(self) -> Dict[str, str]:
        # Object ids aren't randomized in this game, so they are returned as-is (as strings, matching to_json keys).
        # Types reveal which tree is the cherry and which material is the steel.
        object_ids_with_types = {}
        for tree_id in self.game_config['objects']['trees']:
            object_ids_with_types[str(tree_id)] = 'cherry' if tree_id == self.cherry else 'pine'
        for material_id in self.game_config['objects']['construction_material']:
            object_ids_with_types[str(material_id)] = 'steel' if material_id == self.steel else 'brick'
        return object_ids_with_types

    def update_game_state(self):
        if self.tree_fields is None:
            self.tree_fields = self.generate_tree_fields()
        self.update_trees()
        self.update_builder()

    def update_trees(self):
        """
        Adds planted trees if a tree hasn't moved for more the time set in game config and hasn't been run over yet
        """
        # Start tracking trees the first time they are seen
        for tree_id, tree in self.state_data.objects['trees'].items():
            if tree_id not in self.tree_last_movement:
                self.tree_last_movement[tree_id] = (time.time(), tree.position)

        for tree_id, movement_data in self.tree_last_movement.items():
            if tree_id not in self.state_data.objects['trees']:
                self.logger.warning(f"Tracked tree (ID: {tree_id}) is not in the state data!")
                continue
            tree_position = self.state_data.objects['trees'][tree_id].position
            # Update tree movement data if changed
            if distance_squared(movement_data[1], tree_position) > self.game_config['plant_min_distance_moved'] ** 2:
                self.tree_last_movement[tree_id] = (time.time(), tree_position)
                if tree_id in self.planted_trees:
                    self.planted_trees.pop(tree_id)
                    self.logger.info(f"Tracked tree (ID: {tree_id}) has been unplanted.")
                continue

            if tree_id in self.planted_trees:
                continue

            # Plant eligible trees
            if time.time() - movement_data[0] > self.game_config['plant_min_time_seconds']:
                field = next(filter(lambda tree_field: check_if_object_in_area(tree_position, tree_field),
                                    self.tree_fields.values()), None)
                if field is None:
                    continue
                self.planted_trees[tree_id] = field
                self.logger.info(f"Tracked tree (ID: {tree_id}) has been planted.")

                # Each tree only scores the first time it is planted
                if tree_id in self.used_planted_trees:
                    continue
                self.used_planted_trees.add(tree_id)
                team = next(filter(lambda i_team: not cast(ConstructionTeam, i_team).is_builder(), self.teams.values()),
                            None)
                if team is None:
                    self.logger.error("Could not find green team and could not assign points to it!")
                    continue
                team = cast(ConstructionTeam, team)
                team.score += self.game_config['points']['cherry'] if tree_id == self.cherry else \
                    self.game_config['points']['pine']

    def update_builder(self) -> None:
        team = next(filter(lambda i_team: cast(ConstructionTeam, i_team).is_builder(), self.teams.values()), None)
        if team is None:
            return
        team = cast(ConstructionTeam, team)
        robot = self.state_data.robots.get(team.robot_id)

        # Check if any trees were ran over (skipped while the builder isn't detected)
        if robot is not None:
            for tree_id, field in list(self.planted_trees.items()):
                if not check_if_object_in_area(robot.position, field):
                    continue
                self.planted_trees.pop(tree_id)
                tree = self.state_data.objects['trees'].get(tree_id)
                tree_position = tree.position if tree is not None else self.tree_last_movement[tree_id][1]
                self.tree_last_movement[tree_id] = (time.time(), tree_position)
                self.ran_over_trees += self.game_config['points']['cherry'] if tree_id == self.cherry else \
                    self.game_config['points']['pine']
                self.logger.info(f"Tracked tree (ID: {tree_id}) has been ran over.")

        # Now calculate the current score
        team.score = 0
        # Check if materials delivered
        construction_site_field = self.state_data.fields['construction_site']
        for material_id, material in self.state_data.objects['construction_material'].items():
            if not check_if_object_in_area(material.position, construction_site_field):
                continue
            team.score += self.game_config['points']['steel'] if material_id == self.steel else \
                self.game_config['points']['brick']

        # Calculate ran over trees
        team.score -= self.ran_over_trees

    def to_json(self):
        result = super().to_json()
        # Tree fields are generated from game_field, so they are merged here instead of into the tracker's fields
        if self.tree_fields:
            result['fields'].update({name: field.to_json() for name, field in self.tree_fields.items()})
        return result

    @classmethod
    def to_model(cls, api: Api, game_config: Dict):
        result = super().to_model(api, game_config)
        tree_field_config = game_config['tree_fields']
        field_names = game_config['fields_names'] + [
            tree_field_name(row, col)
            for row in range(tree_field_config['rows'])
            for col in range(tree_field_config['columns'])
        ]
        result['fields'] = fields.Nested(api.model(
            'Fields',
            {f: fields.Nested(Field.to_model(api), required=False) for f in field_names})
        )
        return result
