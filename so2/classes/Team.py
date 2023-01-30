from flask_restx import Api, fields


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

    @classmethod
    def to_model(cls, api: Api):
        return api.model('Team', {
            'id': fields.Integer(required=True, description='Team ID'),
            'name': fields.String(required=True, description='Team name'),
            'score': fields.Integer(required=True, description='Team score'),
        })
