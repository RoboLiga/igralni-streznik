from typing import List, Dict

from sledilnik.classes.MovableObject import MovableObject

from so2.entities.ConfigMap import ConfigMap
from so2.enums.ConfigEnum import Config
from so2.enums.FieldsNamesEnum import FieldsNames
from so2.enums.HiveTypeEnum import HiveType


class Hive(MovableObject):
    def __init__(self, obj: MovableObject, hiveType: HiveType):
        super().__init__(obj.id, obj.pos.x, obj.pos.y, 0)
        self.direction = obj.direction
        self.hiveType: HiveType = hiveType

    def update(self, obj):
        self.pos = obj.pos

    def getPoints(self, team: Config, config: ConfigMap, hiveZones: Dict[int, List[FieldsNames]]) -> int:
        if team == Config.TEAM1:
            if self.id in hiveZones and FieldsNames.TEAM2_ZONE in hiveZones[self.id]:
                return config.points[Config.ENEMY.value]
            elif self.id in hiveZones and FieldsNames.NEUTRAL_ZONE in hiveZones[self.id]:
                return config.points[Config.NEUTRAL.value]
            else:
                return config.points[Config.HOME.value]
        elif team == Config.TEAM2:
            if self.id in hiveZones and FieldsNames.TEAM1_ZONE in hiveZones[self.id]:
                return config.points[Config.ENEMY.value]
            elif self.id in hiveZones and FieldsNames.NEUTRAL_ZONE in hiveZones[self.id]:
                return config.points[Config.NEUTRAL.value]
            else:
                return config.points[Config.HOME.value]

    def reprJSON(self, config: ConfigMap, hiveZones: Dict[int, List[FieldsNames]], idOverride: int):
        json = super().reprJSON()
        json["type"] = self.hiveType.value
        json["points"] = {
            "team1": self.getPoints(Config.TEAM1, config, hiveZones),
            "team2": self.getPoints(Config.TEAM2, config, hiveZones)
        }
        json["id"] = idOverride
        return json
