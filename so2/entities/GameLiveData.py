import logging
from timeit import default_timer as timer
from typing import Dict, List

from shapely.geometry import Point as SPoint
from shapely.geometry.polygon import Polygon as SPolygon
from sledilnik.classes.Field import Field
from sledilnik.classes.MovableObject import MovableObject
from sledilnik.classes.Point import Point

from so2.entities.ConfigMap import ConfigMap
from so2.entities.Hive import Hive
from so2.entities.StateLiveData import StateLiveData
from so2.entities.Team import Team
from so2.enums.ConfigEnum import Config
from so2.enums.FieldsNamesEnum import FieldsNames
from so2.enums.HiveTypeEnum import HiveType


class GameLiveData:
    def __init__(self, team1RobotId, team2RobotId):
        self.logger = logging.getLogger('sledenje-objektom.GameLiveData')
        self.gameOn: bool = False
        self.gameTime: int = 100
        self.startTime: float = timer()
        self.pauseTotalTime: float = 0.0
        self.pauseStartTime: float = 0.0
        self.config = ConfigMap()

        self.robots: Dict[int, MovableObject] = {}
        self.teams: Dict[Config, Team] = {}
        self.addTeam(Config.TEAM1, team1RobotId)
        self.addTeam(Config.TEAM2, team2RobotId)
        self.time: float = timer()

        self.alterScore: List[int] = [0, 0]

        self.hivesStartingZones: Dict[int, FieldsNames] = {}
        self.hiveZones: Dict[int, List[FieldsNames]] = {}

    def addTeam(self, team: Config, robotId):
        if str(robotId) in self.config.teams:
            self.teams[team] = Team(robotId, self.config.teams[str(robotId)])
        else:
            logging.error("Team with specified id does not exist in config!")

    def pauseGame(self):
        if self.gameOn:
            self.pauseStartTime = timer()
            self.gameOn = False

    def unpauseGame(self):
        if not self.gameOn:
            self.gameOn = True
            self.pauseTotalTime += timer() - self.pauseStartTime
            self.pauseStartTime = 0.0

    def startGame(self):

        for team in self.teams.values():
            team.score = 0

        self.startTime = timer()
        self.pauseStartTime = 0.0
        self.pauseTotalTime = 0.0
        self.hiveZones = {}
        self.gameOn = True

    def checkTimeLeft(self):
        if self.gameOn:
            return self.gameTime - (timer() - self.startTime) + self.pauseTotalTime
        return self.gameTime

    def checkHiveZones(self, stateLiveData: StateLiveData):
        for hive in stateLiveData.hives:
            if hive.hiveType == HiveType.HIVE_HEALTHY:
                zone = self.hiveZone(hive, stateLiveData)
                if zone is not None:
                    if hive.id not in self.hiveZones:
                        self.hiveZones[hive.id] = [zone]
                    else:
                        self.hiveZones[hive.id].append(zone)

    def hiveZone(self, hive: Hive, stateLiveData: StateLiveData):
        if self.checkIfObjectInArea(hive.pos, stateLiveData.fields[FieldsNames.TEAM1_ZONE.value]):
            # print(str(hive.id) + "is in zone: " + str(FieldsNames.TEAM1_ZONE))
            return FieldsNames.TEAM1_ZONE
        elif self.checkIfObjectInArea(hive.pos, stateLiveData.fields[FieldsNames.TEAM2_ZONE.value]):
            # print(str(hive.id) + "is in zone: " + str(FieldsNames.TEAM2_ZONE))
            return FieldsNames.TEAM2_ZONE
        elif self.checkIfObjectInArea(hive.pos, stateLiveData.fields[FieldsNames.NEUTRAL_ZONE.value]):
            # print(str(hive.id) + "is in zone: " + str(FieldsNames.NEUTRAL_ZONE))
            return FieldsNames.NEUTRAL_ZONE
        else:
            print(str(hive.pos.reprTuple()) + str(hive.id) + "is NOT in ZONE!")
            return None

    @staticmethod
    def checkIfObjectInArea(objectPos: Point, field: Field):
        """Checks if object in area of map.
        Args:
            field: polygon defining the area
            objectPos (list): object x and y coordinates
        Returns:
            bool: True if object in area
        """
        point = SPoint(objectPos.reprTuple())

        (topLeft, topRight, bottomLeft, bottomRight) = field.reprTuple()

        polygon = SPolygon((bottomLeft, topLeft, topRight, bottomRight))

        return polygon.contains(point)

    def computeScore(self, stateLiveData: StateLiveData):
        team1DiseasedHivesCount = 0
        team2DiseasedHivesCount = 0

        for hive in stateLiveData.hives:
            # if there is a hive in team1 basket
            if self.checkIfObjectInArea(hive.pos, stateLiveData.fields[FieldsNames.TEAM1_BASKET.value]):
                # if it's healthy, increase score accordingly
                if hive.hiveType == HiveType.HIVE_HEALTHY:
                    self.teams[Config.TEAM1].healthyHives[hive.id] = hive.getPoints(Config.TEAM1, stateLiveData.config,
                                                                                    self.hiveZones)
                # if it's not healthy, increase count
                else:
                    team1DiseasedHivesCount += 1

            # if there is a hive in team2 basket
            elif self.checkIfObjectInArea(hive.pos, stateLiveData.fields[FieldsNames.TEAM2_BASKET.value]):
                # if it's healthy, increase score accordingly
                if hive.hiveType == HiveType.HIVE_HEALTHY:
                    self.teams[Config.TEAM2].healthyHives[hive.id] = hive.getPoints(Config.TEAM2, stateLiveData.config,
                                                                                    self.hiveZones)
                # if it's not healthy, increase count
                else:
                    team2DiseasedHivesCount += 1

        # compute scores for both teams
        self.teams[Config.TEAM1].score = \
            sum(self.teams[Config.TEAM1].healthyHives.values()) \
            + team1DiseasedHivesCount * self.config.points['diseased'] \
            + self.alterScore[0]
        self.teams[Config.TEAM2].score = \
            sum(self.teams[Config.TEAM2].healthyHives.values()) \
            + team2DiseasedHivesCount * self.config.points['diseased'] \
            + self.alterScore[1]

    def reprJSON(self, stateLiveData: StateLiveData):
        return {
            "objects": {
                "hives": {str(stateLiveData.idRandomization[hive.id]): hive.reprJSON(stateLiveData.config, self.hiveZones, idOverride=stateLiveData.idRandomization[hive.id]) for hive in
                          stateLiveData.hives},
                "robots": {str(robot.id): robot.reprJSON() for robot in stateLiveData.robots}
            },
            "fields": {
                "baskets": {
                    "team1": stateLiveData.fields[FieldsNames.TEAM1_BASKET.value].reprJSON(),
                    "team2": stateLiveData.fields[FieldsNames.TEAM2_BASKET.value].reprJSON()
                },
                "zones": {
                    "team1": stateLiveData.fields[FieldsNames.TEAM1_ZONE.value].reprJSON(),
                    "team2": stateLiveData.fields[FieldsNames.TEAM2_ZONE.value].reprJSON(),
                    "neutral": stateLiveData.fields[FieldsNames.NEUTRAL_ZONE.value].reprJSON()
                },
                "field": stateLiveData.fields[FieldsNames.FIELD.value].reprJSON()
            },
            "teams": {
                "team1": self.teams[Config.TEAM1].reprJSON(),
                "team2": self.teams[Config.TEAM2].reprJSON()
            },
            "timeLeft": self.checkTimeLeft(),
            "gameOn": self.gameOn
        }
