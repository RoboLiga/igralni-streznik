from flask_restx import Api, fields
from sledilnik.classes.Field import Field
from sledilnik.classes.ObjectTracker import ObjectTracker

from src.games.construction.ConstructionTeam import ConstructionTeam, BUILDER_COLOR
from src.servers.GameServer import GameServer
from typing import Dict, List, Optional, cast

from src.utils import create_logger, bilinear_point, check_if_object_in_area


def tree_field_name(row: int, col: int) -> str:
    return f'tree_field_{row}_{col}'


def is_tree_field(row: int, col: int, rows: int, cols: int) -> bool:
    """
    The first and last rows span the whole width, in the rows between them
    the first and last columns are bases, so they aren't tree fields.
    """
    is_middle_row = 0 < row < rows - 1
    is_edge_col = col == 0 or col == cols - 1
    return not (is_middle_row and is_edge_col)


class Construction(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Construction', game_config['log_level'])
        self.cherry = self.game_config['cherry']
        self.steel = self.game_config['steel']
        if self.cherry not in self.game_config['objects']['trees']:
            raise ValueError(f'Cherry id {self.cherry} is not listed in objects.trees')
        if self.steel not in self.game_config['objects']['construction_material']:
            raise ValueError(f'Steel id {self.steel} is not listed in objects.construction_material')

        # State data is only available once the game loop runs, so these are filled in on the first update.
        # Times are game time (self.timer), which stands still while the game is paused.
        # When each tree entered the tree field it's in (None while it's outside all tree fields).
        # The trees in a field queue up in this order.
        self.tree_timers: dict[int, tuple[float, Optional[Field]]] = dict()
        # The planting timer of each tree field: the first tree in its queue and since when it has been timed
        self.plant_timers: dict[Field, tuple[int, float]] = dict()
        self.planted_trees: dict[int, Field] = dict()
        self.ran_over_trees: int = 0
        # Tree fields the builder has lost points in and hasn't left since
        self.penalized_fields: set[Field] = set()
        self.used_planted_trees: set[int] = set()
        self.delivered_materials: set[int] = set()

    def reset_game_state(self):
        self.tree_timers.clear()
        self.plant_timers.clear()
        self.planted_trees.clear()
        self.ran_over_trees = 0
        self.penalized_fields.clear()
        self.used_planted_trees.clear()
        self.delivered_materials.clear()

    def _run(self):
        # Fields are only known once the state server has parsed at least one tracker frame
        self.state_server.updated.wait()
        self.tree_fields = self.generate_tree_fields()
        super()._run()

    def start_game(self):
        if not self.game_on:
            # A new game starts from scratch, and game time restarts from zero so earlier times would be in the future
            self.reset_game_state()
        super().start_game()

    def generate_tree_fields(self) -> Dict[str, Field]:
        """
        Splits game_field into a grid of Field cells, using bilinear interpolation of its
        four corners so the grid stays correct even if the field isn't a perfect rectangle.
        """
        game_field = self.state_server.state.fields['game_field']
        tree_field_config = self.game_config['tree_fields']
        cols = tree_field_config['columns']
        rows = tree_field_config['rows']

        tree_fields: Dict[str, Field] = {}
        for row in range(rows):
            for col in range(cols):
                if not is_tree_field(row, col, rows, cols):
                    continue
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
        self.update_trees()
        self.update_builder()

    def update_trees(self):
        """
        Plants trees, one per tree field. The trees in a field queue up in the order they entered it, and only
        the first one is timed: it is planted once it has been timed for the time set in game config. When it
        leaves the field, the next tree's timer starts. When the builder runs it over, it stays first and its
        own timer starts again (see update_builder).
        """
        # Start tracking trees the first time they are seen
        for tree_id, tree in self.state_data.objects['trees'].items():
            if tree_id not in self.tree_timers:
                self.tree_timers[tree_id] = (self.timer.get(), self.find_tree_field(tree.position))

        for tree_id, (entered_at, timer_field) in list(self.tree_timers.items()):
            if tree_id not in self.state_data.objects['trees']:
                self.logger.warning(f"Tracked tree (ID: {tree_id}) is not in the state data!")
                continue
            field = self.find_tree_field(self.state_data.objects['trees'][tree_id].position)
            # Moving inside a tree field keeps the tree's place in the queue, leaving it unplants the tree
            if field is not timer_field:
                self.tree_timers[tree_id] = (self.timer.get(), field)
                if tree_id in self.planted_trees:
                    self.planted_trees.pop(tree_id)
                    self.logger.info(f"Tracked tree (ID: {tree_id}) has been unplanted.")

        for field in self.tree_fields.values():
            queue = sorted((entered_at, tree_id) for tree_id, (entered_at, tree_field) in self.tree_timers.items()
                           if tree_field is field)
            if not queue:
                self.plant_timers.pop(field, None)
                continue
            tree_id = queue[0][1]
            # The first tree just entered an empty field, or the one before it left: its timer starts now
            if self.plant_timers.get(field, (None, None))[0] != tree_id:
                self.plant_timers[field] = (tree_id, self.timer.get())
            if tree_id in self.planted_trees:
                continue

            # Plant eligible trees
            if self.timer.get() - self.plant_timers[field][1] > self.game_config['plant_min_time_seconds']:
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
            # Leaving a field lets the builder be penalized in it again
            self.penalized_fields = {field for field in self.penalized_fields
                                     if check_if_object_in_area(robot.position, field)}
            newly_penalized_fields: set[Field] = set()
            for tree_id, field in list(self.planted_trees.items()):
                if not check_if_object_in_area(robot.position, field):
                    continue
                # A tree replanted while the builder is still sitting in the field doesn't cost them again
                if field in self.penalized_fields:
                    continue
                newly_penalized_fields.add(field)
                self.planted_trees.pop(tree_id)
                # The tree stays first in its field's queue, it just has to wait out the timer again
                self.plant_timers[field] = (tree_id, self.timer.get())
                self.ran_over_trees += self.game_config['points']['cherry'] if tree_id == self.cherry else \
                    self.game_config['points']['pine']
                self.logger.info(f"Tracked tree (ID: {tree_id}) has been ran over.")
            self.penalized_fields |= newly_penalized_fields

        # Each material only scores the first time it is delivered, it keeps its points even if it leaves the site
        construction_site_field = self.state_data.fields['construction_site']
        for material_id, material in self.state_data.objects['construction_material'].items():
            if material_id in self.delivered_materials:
                continue
            if not check_if_object_in_area(material.position, construction_site_field):
                continue
            self.delivered_materials.add(material_id)
            self.logger.info(f"Construction material (ID: {material_id}) has been delivered.")

        # Now calculate the current score
        team.score = sum(
            self.game_config['points']['steel'] if material_id == self.steel else self.game_config['points']['brick']
            for material_id in self.delivered_materials
        ) - self.ran_over_trees

    def find_tree_field(self, position) -> Optional[Field]:
        return next(filter(lambda tree_field: check_if_object_in_area(position, tree_field),
                           self.tree_fields.values()), None)

    def is_tree_field_planted(self, tree_field: Field) -> bool:
        return any(field is tree_field for field in self.planted_trees.values())

    def to_json(self):
        result = super().to_json()
        # Tree fields are generated from game_field, so they are kept separate from the tracker's fields
        result['tree_fields'] = {
            name: {**field.to_json(), 'planted': self.is_tree_field_planted(field)}
            for name, field in (self.tree_fields or {}).items()
        }
        # Everyone can see which tree is the cherry and which material is the steel
        object_types = self.get_objects_with_types()
        for objects in result['objects'].values():
            for object_id, object_json in objects.items():
                object_json['type'] = object_types[object_id]
        return result

    @classmethod
    def to_model(cls, api: Api, game_config: Dict):
        result = super().to_model(api, game_config)
        rows, cols = game_config['tree_fields']['rows'], game_config['tree_fields']['columns']
        tree_field_model = api.inherit('TreeField', Field.to_model(api), {
            'planted': fields.Boolean(required=True, description='Whether a tree is planted in this field'),
        })
        result['tree_fields'] = fields.Nested(api.model(
            'TreeFields',
            {
                tree_field_name(row, col): fields.Nested(tree_field_model, required=False)
                for row in range(rows)
                for col in range(cols)
                if is_tree_field(row, col, rows, cols)
            })
        )
        typed_object_model = api.inherit('TypedObjectTracker', ObjectTracker.to_model(api), {
            'type': fields.String(required=True, enum=['cherry', 'pine', 'steel', 'brick'],
                                  description='Which kind of tree or construction material this object is'),
        })
        result['objects'] = fields.Nested(api.model(
            'ConstructionObjects',
            {
                str(object_type): fields.Nested(api.model(
                    f'ConstructionObjectType_{object_type}',
                    {str(o): fields.Nested(typed_object_model, required=False) for o in object_ids}
                ))
                for object_type, object_ids in game_config['objects'].items()
            })
        )
        return result
