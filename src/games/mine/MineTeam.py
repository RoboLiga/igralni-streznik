from flask_restx import Api, fields

from src.classes.Team import Team
from src.classes.Timer import Timer


class MineTeam(Team):
    def __init__(self, robot_id: int, color: str, name: str, time_full: float):
        super().__init__(robot_id, color, name)
        self.time_full = time_full
        self.timer = Timer()
        self.charging_timer = Timer()
        self.charging: bool = False

    def start_charging(self):
        self.timer.pause()
        self.charging = True
        self.charging_timer.start()

    def stop_charging(self):
        self.charging = False
        self.timer.resume()

    def charge(self, charging_time, charging_amount):
        if not self.charging:
            self.start_charging()
        elif self.charging_timer.get() >= charging_time:
            self.time_full += charging_amount

    def to_json(self):
        result = super().to_json()
        result['time_left'] = self.time_full - self.timer.get()
        result['charging'] = self.charging
        return result

    @classmethod
    def to_model(cls, api: Api):
        result = super().to_model(api)
        result['time_left'] = fields.Float(required=True, description='Time left')
        result['charging'] = fields.Boolean(required=True, description='Is charging')
        return result
