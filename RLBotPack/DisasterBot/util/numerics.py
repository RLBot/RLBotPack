import math

PI = math.pi


def clip(x: float, lower_cap: float = -1, higher_cap: float = 1):
    """Returns a clipped value in the range [lower_cap, higher_cap]"""
    if x < lower_cap:
        return lower_cap
    elif x > higher_cap:
        return higher_cap
    else:
        return x


def normalize_angle(angle, pi_unit=PI):
    """Limits any angle to [-pi, pi] range, example: normalize_angle(270, 180) = -90"""
    if abs(angle) >= 2 * pi_unit:
        angle -= abs(angle) // (2 * pi_unit) * 2 * pi_unit * sign(angle)
    if abs(angle) > pi_unit:
        angle -= 2 * pi_unit * sign(angle)
    return angle


def sign(x: float):
    """Retuns 1 if x > 0 else -1. > instead of >= so that sign(False) returns -1"""
    return 1 if x > 0 else -1
