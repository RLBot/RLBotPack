import math
import time

from rlbot.agents.base_agent import SimpleControllerState


def celebrate(bot) -> SimpleControllerState:
    controls = SimpleControllerState()
    controls.steer = math.sin(time.time() * 4)
    controls.throttle = -1
    return controls


def is_heading_towards(ang: float, dist: float) -> bool:
    # The further away the car is the less accurate the angle is required
    required_ang = 0.05 + 0.0001 * dist
    return abs(ang) <= required_ang


def turn_radius(vf: float) -> float:
    if vf == 0:
        return 0
    return 1.0 / turn_curvature(vf)


def turn_curvature(vf: float) -> float:
    if 0.0 <= vf < 500.0:
        return 0.006900 - 5.84e-6 * vf
    elif 500.0 <= vf < 1000.0:
        return 0.005610 - 3.26e-6 * vf
    elif 1000.0 <= vf < 1500.0:
        return 0.004300 - 1.95e-6 * vf
    elif 1500.0 <= vf < 1750.0:
        return 0.003025 - 1.10e-6 * vf
    elif 1750.0 <= vf < 2500.0:
        return 0.001800 - 0.40e-6 * vf
    else:
        return 0.0
