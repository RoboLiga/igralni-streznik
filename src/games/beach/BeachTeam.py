from flask_restx import Api, fields

from src.classes.Team import Team
from src.classes.Timer import Timer


class BeachTeam(Team):
    def __init__(self, robot_id: int, color: str, name: str, fuel_full: float):
        super().__init__(robot_id, color, name)
        self.fuel_full = fuel_full
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

    def charge(self, charging_time):
        if not self.charging:
            self.start_charging()
        elif self.charging_timer.get() >= charging_time:
            self.timer.start()
            self.timer.pause()

    def fuel(self):
        return max(self.fuel_full - self.timer.get(), 0)

    def to_json(self):
        result = super().to_json()
        result['fuel'] = self.fuel()
        result['charging'] = self.charging
        return result

    @classmethod
    def to_model(cls, api: Api):
        result = super().to_model(api)
        result['fuel'] = fields.Float(required=True, description='Fuel')
        result['charging'] = fields.Boolean(required=True, description='Is charging')
        return result
