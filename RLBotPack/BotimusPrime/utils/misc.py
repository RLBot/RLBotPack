from utils.math import clamp


def turn_radius(speed: float) -> float:
    spd = clamp(speed, 0, 2300)
    return 156 + 0.1*spd + 0.000069*spd**2 + 0.000000164*spd**3 + -5.62E-11*spd**4


def turning_speed(radius: float) -> float:
    return 10.219 * radius - 1.75404E-2 * radius**2 + 1.49406E-5 * radius**3 - 4.486542E-9 * radius**4 - 1156.05


