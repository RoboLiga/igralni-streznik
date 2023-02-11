import logging
from typing import Dict

from sledilnik.classes.Field import Field
from sledilnik.classes.ObjectTracker import ObjectTracker
from sledilnik.classes.TrackerLiveData import TrackerLiveData


class StateLiveData:
    def __init__(self, config):
        self.logger = logging.getLogger('sledenje-objektom.StateLiveData')
        self.config = config
        self.fields: Dict[str, Field] = {}
        self.robots: Dict[int, ObjectTracker] = {}
        self.objects: Dict[str, Dict[int, ObjectTracker]] = {}

    def parse(self, data: TrackerLiveData):
        self.fields = data.fields
        self.robots = {}
        self.objects = {}

        # Loop through all objects
        for key, obj in data.objects.items():
            # Check if object is a robot
            if key in self.config['robots']:
                self.robots[key] = obj
            else:
                # Loop through all object types
                for object_type in self.config['objects']:
                    if object_type not in self.objects:
                        self.objects[object_type] = {}
                    # Check if object is of this type
                    if key in self.config['objects'][object_type]:
                        self.objects[object_type][key] = obj
