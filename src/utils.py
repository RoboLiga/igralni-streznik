import yaml
import logging

from shapely.geometry import Point as SPoint
from shapely.geometry.polygon import Polygon as SPolygon

from sledilnik.classes.Field import Field
from sledilnik.classes.Point import Point


def check_if_object_in_area(object_pos: Point, field: Field):
    """
    Checks if object in area of map.
    :param field: field object defining a polygon
    :param object_pos: point object defining the object position
    :return: True if object in area
    """

    point = SPoint(object_pos.to_tuple())

    (topLeft, topRight, bottomRight, bottomLeft) = field.to_tuple()

    polygon = SPolygon((bottomLeft, topLeft, topRight, bottomRight))

    return polygon.contains(point)


def read_config(config_path):
    """
    Reads config file
    :param config_path: path to config file
    :return: config dictionary
    """
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_logger(name: str, log_level: str) -> logging.Logger:
    # create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(log_level))

    # create a file handler
    file_handler = logging.FileHandler('game-server.log')
    file_handler.setLevel(log_level)

    # create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
