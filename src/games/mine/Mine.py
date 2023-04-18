import logging
from typing import Dict, List
from uuid import uuid4

from flask_restx import Api, fields

from sledilnik.classes.ObjectTracker import ObjectTracker
from src.games.mine.MineTeam import MineTeam
from src.servers.GameServer import GameServer
from src.utils import check_if_object_in_area, create_logger


class Mine(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Mine', game_config['log_level'])

        self.charging_stations = {
            1: None,
            2: None
        }
        self.objects_uuid = {}
        self.generate_objects_uuids()

    def init_team(self, robot_id: int, color: str):
        if robot_id in self.config['robots']:
            new_team = MineTeam(robot_id, color, self.config['robots'][robot_id], self.config['robot_time'])
            return new_team
        else:
            logging.error("Team with specified id does not exist in config!")
            raise Exception("Team with specified id does not exist in config!")

    def start_game(self):
        # Generate new uuids for objects
        self.generate_objects_uuids()

        # Reset charging stations
        for charging_station_id in self.charging_stations:
            self.charging_stations[charging_station_id] = None

        # Start timers
        for team_key in self.teams:
            team = self.teams[team_key]
            team.timer.start()

        super().start_game()

    def generate_objects_uuids(self):
        # Map each object id to a random uuid
        for ot in self.config['objects']:
            for o in self.config['objects'][ot]:
                self.objects_uuid[str(o)] = str(uuid4())[:8]

    def pause_game(self):
        for team_key in self.teams:
            team = self.teams[team_key]
            team.timer.pause()

        super().pause_game()

    def resume_game(self):
        for team_key in self.teams:
            team = self.teams[team_key]
            team.timer.resume()

        super().resume_game()

    def update_game_state(self):
        self.check_robots()
        self.compute_score()

    def check_robots(self):
        for team_key in self.teams:
            team = self.teams[team_key]
            # Check if robot is alive and has fuel
            if team.robot_id in self.state_data.robots and team.fuel() > 0:
                robot = self.state_data.robots[team.robot_id]

                # Check if robot is charging
                if check_if_object_in_area(robot.position, self.state_data.fields['charging_station_1']) and \
                        (self.charging_stations[1] is None or self.charging_stations[1] == robot.id):
                    self.teams[robot.id].charge(self.config['charging_time'])
                    self.charging_stations[1] = robot.id
                elif check_if_object_in_area(robot.position, self.state_data.fields['charging_station_2']) and \
                        (self.charging_stations[2] is None or self.charging_stations[2] == robot.id):
                    self.teams[robot.id].charge(self.config['charging_time'])
                    self.charging_stations[2] = robot.id
                else:
                    if self.charging_stations[1] == robot.id:
                        self.charging_stations[1] = None
                    elif self.charging_stations[2] == robot.id:
                        self.charging_stations[2] = None
                    self.teams[robot.id].stop_charging()

    def compute_score(self):

        scores = {}
        for team_key in self.teams:
            team = self.teams[team_key]
            scores[team.robot_id] = 0

        for good_ore_key in self.state_data.objects['good_ore']:
            good_ore = self.state_data.objects['good_ore'][good_ore_key]
            for team_key in self.teams:
                team = self.teams[team_key]
                if check_if_object_in_area(good_ore.position, self.state_data.fields[f'{team.color}_basket']):
                    scores[team.robot_id] += self.config['points']['good']

        for bad_ore_key in self.state_data.objects['bad_ore']:
            bad_ore = self.state_data.objects['bad_ore'][bad_ore_key]
            for team_key in self.teams:
                team = self.teams[team_key]
                if check_if_object_in_area(bad_ore.position, self.state_data.fields[f'{team.color}_basket']):
                    scores[team.robot_id] += self.config['points']['bad']

        for team_key in self.teams:
            team = self.teams[team_key]
            team.score = scores.get(team.robot_id, 0)

    def to_json(self):
        result = super().to_json()
        merged_objects = {}
        for ot in result['objects']:
            for o in result['objects'][ot]:
                tmp = result['objects'][ot][o]
                tmp['id'] = self.objects_uuid[o]
                merged_objects[self.objects_uuid[o]] = tmp

        result['objects'] = merged_objects
        return result

    @classmethod
    def to_model(cls, api: Api, game_config: Dict):
        result = super().to_model(api, game_config)
        result['objects'] = fields.Nested(
            api.model('Objects', {
                str(o): fields.Nested(
                    ObjectTracker.to_model(api),
                    required=False
                )
                for ot in game_config['objects']
                for o in game_config['objects'][ot]

            })
        )
        result['teams'] = fields.Nested(api.model(
            'Teams',
            {str(t): fields.Nested(MineTeam.to_model(api)) for t in game_config['robots']})
        )
        return result
