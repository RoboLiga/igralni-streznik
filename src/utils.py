import math

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

def distance_squared(p1: Point, p2: Point) -> float:
    """
    Returns the squared distance between two points.
    Args:
        p1: first point
        p2: second point

    Returns: distance between p1 and p2

    """
    return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2

def bilinear_point(top_left: Point, top_right: Point, bottom_left: Point, bottom_right: Point,
                    u: float, v: float) -> Point:
    """
    Interpolates a point inside the quadrilateral defined by four corners.
    Args:
        top_left: top left corner of the quadrilateral
        top_right: top right corner of the quadrilateral
        bottom_left: bottom left corner of the quadrilateral
        bottom_right: bottom right corner of the quadrilateral
        u: fraction across the top/bottom edge, 0 (left) to 1 (right)
        v: fraction down the left/right edge, 0 (top) to 1 (bottom)

    Returns: interpolated point

    """
    x = ((1 - u) * (1 - v) * top_left.x + u * (1 - v) * top_right.x +
         (1 - u) * v * bottom_left.x + u * v * bottom_right.x)
    y = ((1 - u) * (1 - v) * top_left.y + u * (1 - v) * top_right.y +
         (1 - u) * v * bottom_left.y + u * v * bottom_right.y)
    return Point(x, y)
