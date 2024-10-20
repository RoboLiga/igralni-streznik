import logging
from typing import Dict, List
from uuid import uuid4

from flask_restx import Api, fields

from sledilnik.classes.ObjectTracker import ObjectTracker
from src.classes.Timer import Timer
from src.games.beach.BeachTeam import BeachTeam
from src.servers.GameServer import GameServer
from src.utils import check_if_object_in_area, create_logger


class Beach(GameServer):
    def __init__(self, state_server, game_config, teams: List[int]):
        GameServer.__init__(self, state_server, game_config, teams)
        self.logger = create_logger('games.Beach', game_config['log_level'])

        self.charging_stations = {
            1: None,
            2: None,
            3: None,
            4: None
        }
        self.objects_uuid = {}
        self.generate_objects_uuids()

    def init_team(self, robot_id: int, color: str):
        if robot_id in self.game_config['robots']:
            new_team = BeachTeam(robot_id, color, self.game_config['robots'][robot_id], self.game_config['robot_time'])
            return new_team
        else:
            logging.error("Team with specified id does not exist in config!")
            raise Exception("Team with specified id does not exist in config!")

    def start_game(self):
        if not self.game_on:
            # Generate new uuids for objects
            self.generate_objects_uuids()

            # Reset charging stations
            self.charging_stations = {
                1: None,
                2: None,
                3: None,
                4: None
            }

            # Start timers
            for team_key in self.teams:
                team = self.teams[team_key]
                team.timer = Timer()
                team.charging_timer = Timer()
                team.charging = False
                team.timer.start()

            super().start_game()

    def generate_objects_uuids(self):
        # Map each object id to a random uuid
        for ot in self.game_config['objects']:
            for o in self.game_config['objects'][ot]:
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
                
                # TODO: Refactor to clean up

                # Check if robot is charging
                if check_if_object_in_area(robot.position, self.state_data.fields['blue_plastic']) and \
                        (self.charging_stations[1] is None or self.charging_stations[1] == robot.id):
                    self.teams[robot.id].charge(self.game_config['charging_time'])
                    self.charging_stations[1] = robot.id
                elif check_if_object_in_area(robot.position, self.state_data.fields['blue_glass']) and \
                        (self.charging_stations[2] is None or self.charging_stations[2] == robot.id):
                    self.teams[robot.id].charge(self.game_config['charging_time'])
                    self.charging_stations[2] = robot.id
                elif check_if_object_in_area(robot.position, self.state_data.fields['red_plastic']) and \
                        (self.charging_stations[3] is None or self.charging_stations[3] == robot.id):
                    self.teams[robot.id].charge(self.game_config['charging_time'])
                    self.charging_stations[3] = robot.id
                elif check_if_object_in_area(robot.position, self.state_data.fields['red_glass']) and \
                        (self.charging_stations[4] is None or self.charging_stations[4] == robot.id):
                    self.teams[robot.id].charge(self.game_config['charging_time'])
                    self.charging_stations[4] = robot.id
                else: # If robot is not in charging area, stop charging
                    if self.charging_stations[1] == robot.id:
                        self.charging_stations[1] = None
                    elif self.charging_stations[2] == robot.id:
                        self.charging_stations[2] = None
                    elif self.charging_stations[3] == robot.id:
                        self.charging_stations[3] = None
                    elif self.charging_stations[4] == robot.id:
                        self.charging_stations[4] = None
                    self.teams[robot.id].stop_charging()

            # If robot is dead or has no fuel, stop charging and release charging station
            else:
                if self.charging_stations[1] == team.robot_id:
                    self.charging_stations[1] = None
                elif self.charging_stations[2] == team.robot_id:
                    self.charging_stations[2] = None
                elif self.charging_stations[3] == team.robot_id:
                    self.charging_stations[3] = None
                elif self.charging_stations[4] == team.robot_id:
                    self.charging_stations[4] = None
                self.teams[team.robot_id].stop_charging()

    def compute_score(self):

        scores = {}
        for team_key in self.teams:
            team = self.teams[team_key]
            scores[team.robot_id] = 0

        # If 'plastic' is in the plastic container, add points to the team, if 'plastic' is in the glass container, subtract points from the team
        if 'plastic' in self.state_data.objects:
            for plastic_key in self.state_data.objects['plastic']:
                plastic = self.state_data.objects['plastic'][plastic_key]
                for team_key in self.teams:
                    team = self.teams[team_key]
                    if check_if_object_in_area(plastic.position, self.state_data.fields[f'{team.color}_plastic']):
                        scores[team.robot_id] += self.game_config['points']['good']
                    elif check_if_object_in_area(plastic.position, self.state_data.fields[f'{team.color}_glass']):
                        scores[team.robot_id] += self.game_config['points']['bad']

        # If 'glass' is in the glass container, add points to the team, if 'glass' is in the plastic container, subtract points from the team
        if 'glass' in self.state_data.objects:
            for glass_key in self.state_data.objects['glass']:
                glass = self.state_data.objects['glass'][glass_key]
                for team_key in self.teams:
                    team = self.teams[team_key]
                    if check_if_object_in_area(glass.position, self.state_data.fields[f'{team.color}_glass']):
                        scores[team.robot_id] += self.game_config['points']['good']
                    elif check_if_object_in_area(glass.position, self.state_data.fields[f'{team.color}_plastic']):
                        scores[team.robot_id] += self.game_config['points']['bad']

        # If 'shells' is in any container, subtract points from the team
        if 'shells' in self.state_data.objects:
            for shells_key in self.state_data.objects['shells']:
                shells = self.state_data.objects['shells'][shells_key]
                for team_key in self.teams:
                    team = self.teams[team_key]
                    if (check_if_object_in_area(shells.position, self.state_data.fields[f'{team.color}_plastic']) or
                        check_if_object_in_area(shells.position, self.state_data.fields[f'{team.color}_glass'])):
                        scores[team.robot_id] += self.game_config['points']['bad']

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
        result['charging_time'] = self.game_config['charging_time']
        result['charging_amount'] = self.game_config['charging_amount']
        result['robot_time'] = self.game_config['robot_time']
        result['game_time'] = self.game_config['game_time']
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
            {str(t): fields.Nested(BeachTeam.to_model(api)) for t in game_config['robots']})
        )
        result['charging_time'] = fields.Integer()
        result['charging_amount'] = fields.Integer()
        result['robot_time'] = fields.Integer()
        result['game_time'] = fields.Integer()
        return result
