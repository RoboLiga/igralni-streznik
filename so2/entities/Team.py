from typing import Dict


class Team:
    def __init__(self, team_id: int, name: str):
        self.id = team_id
        self.name = name
        self.score = 0
        self.scoreAdjust = 0
        # self.healthyHives: Dict[int, int] = {}

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "score": self.score
        }
