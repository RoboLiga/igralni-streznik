from classes.Team import Team


class ConstructionTeam(Team):
    def __init__(self, robot_id: int, color: str, name: str, fuel_full: float):
        super().__init__(robot_id, color, name)