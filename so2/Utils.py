def check_if_object_in_area(object_pos: Point, field: Field):
    """Checks if object in area of map.
    Args:
        field: polygon defining the area
        object_pos (list): object x and y coordinates
    Returns:
        bool: True if object in area
    """
    point = SPoint(object_pos.to_tuple())

    (topLeft, topRight, bottomLeft, bottomRight) = field.to_tuple()

    polygon = SPolygon((bottomLeft, topLeft, topRight, bottomRight))

    return polygon.contains(point)