from classes.Team import Team
from games.construction.Construction import BUILDER_COLOR


class ConstructionTeam(Team):
    def __init__(self, robot_id: int, color: str, name: str):
        super().__init__(robot_id, color, name)

    def is_builder(self):
        return self.color == BUILDER_COLOR