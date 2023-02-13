from flask_restx import Api, fields


class Team:
    def __init__(self, robot_id: int, color: str, name: str):
        self.robot_id = robot_id
        self.color = color
        self.name = name
        self.score = 0
        self.score_bias = 0

    def to_json(self):
        return {
            "id": self.robot_id,
            "color": self.color,
            "name": self.name,
            "score": self.score + self.score_bias
        }

    @classmethod
    def to_model(cls, api: Api):
        return api.model('Team', {
            'id': fields.Integer(required=True, description='Team ID'),
            'color': fields.String(required=True, description='Team color'),
            'name': fields.String(required=True, description='Team name'),
            'score': fields.Integer(required=True, description='Team score'),
        })
