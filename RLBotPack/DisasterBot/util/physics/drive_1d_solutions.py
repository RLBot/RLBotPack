import math
from collections import namedtuple
from numba import jit, f8

from util.special_lambertw import lambertw


THROTTLE_ACCELERATION_0 = 1600.0
THROTTLE_ACCELERATION_1400 = 160.0
THROTTLE_MID_SPEED = 1400.0

BOOST_ACCELERATION = 991.6667
BREAK_ACCELERATION = 3500.0

MAX_CAR_SPEED = 2300.0

BOOST_CONSUMPTION_RATE = 33.3  # per second

# constants of the acceleration between 0 to 1400 velocity: acceleration = a * velocity + b
a = -(THROTTLE_ACCELERATION_0 - THROTTLE_ACCELERATION_1400) / THROTTLE_MID_SPEED
b = THROTTLE_ACCELERATION_0
b2 = THROTTLE_ACCELERATION_0 + BOOST_ACCELERATION

fast_jit = jit(f8(f8, f8), nopython=True, fastmath=True, cache=True)

State = namedtuple("State", ["dist", "vel", "boost", "time"])


class VelocityRange:
    max_speed = None
    use_boost = None

    @staticmethod
    def distance_traveled(t: float, v0: float) -> float:
        raise NotImplementedError

    @staticmethod
    def velocity_reached(t: float, v0: float) -> float:
        raise NotImplementedError

    @staticmethod
    def time_reach_velocity(v: float, v0: float) -> float:
        raise NotImplementedError

    @staticmethod
    def time_travel_distance(d: float, v0: float) -> float:
        raise NotImplementedError


class Velocity0To1400(VelocityRange):
    max_speed = THROTTLE_MID_SPEED
    use_boost = False

    @staticmethod
    @fast_jit
    def distance_traveled(t: float, v0: float) -> float:
        return (b * (-a * t + math.expm1(a * t)) + a * v0 * math.expm1(a * t)) / (a * a)

    @staticmethod
    @fast_jit
    def velocity_reached(t: float, v0: float) -> float:
        return (b * math.expm1(a * t)) / a + v0 * math.exp(a * t)

    @staticmethod
    @fast_jit
    def time_reach_velocity(v: float, v0: float) -> float:
        return math.log((a * v + b) / (a * v0 + b)) / a

    @staticmethod
    @fast_jit
    def time_travel_distance(d: float, v: float) -> float:
        return (-d * a * a - b * lambertw(-((b + a * v) * math.exp(-(a * (v + a * d)) / b - 1)) / b) - a * v - b) / (
            a * b
        )


class Velocity0To1400Boost(VelocityRange):
    max_speed = THROTTLE_MID_SPEED
    use_boost = True

    @staticmethod
    @fast_jit
    def distance_traveled(t: float, v0: float) -> float:
        return (b2 * (-a * t + math.expm1(a * t)) + a * v0 * math.expm1(a * t)) / (a * a)

    @staticmethod
    @fast_jit
    def velocity_reached(t: float, v0: float) -> float:
        return (b2 * math.expm1(a * t)) / a + v0 * math.exp(a * t)

    @staticmethod
    @fast_jit
    def time_reach_velocity(v: float, v0: float) -> float:
        return math.log((a * v + b2) / (a * v0 + b2)) / a

    @staticmethod
    @fast_jit
    def time_travel_distance(d: float, v: float) -> float:
        return (
            -d * a * a - b2 * lambertw(-((b2 + a * v) * math.exp(-(a * (v + a * d)) / b2 - 1)) / b2) - a * v - b2
        ) / (a * b2)


class Velocity1400To2300(Velocity0To1400):
    """for when the only acceleration that applies is from boost."""

    max_speed = MAX_CAR_SPEED
    use_boost = True

    @staticmethod
    @fast_jit
    def distance_traveled(t: float, v0: float) -> float:
        return t * (BOOST_ACCELERATION * t + 2 * v0) / 2

    @staticmethod
    @fast_jit
    def velocity_reached(t: float, v0: float) -> float:
        return BOOST_ACCELERATION * t + v0

    @staticmethod
    @fast_jit
    def time_reach_velocity(v: float, v0: float) -> float:
        return (v - v0) / BOOST_ACCELERATION

    @staticmethod
    @fast_jit
    def time_travel_distance(d: float, v: float) -> float:
        return (-v + math.sqrt(2 * BOOST_ACCELERATION * d + math.pow(v, 2))) / BOOST_ACCELERATION


class VelocityNegative(VelocityRange):
    """for when the velocity is opposite the throttle direction,
    only the breaking acceleration applies, boosting has no effect.
    assuming throttle is positive, flip velocity signs if otherwise."""

    max_speed = 0.0
    use_boost = False

    @staticmethod
    @fast_jit
    def distance_traveled(t: float, v0: float) -> float:
        return t * (BREAK_ACCELERATION * t + 2 * v0) / 2

    @staticmethod
    @fast_jit
    def velocity_reached(t: float, v0: float) -> float:
        return BREAK_ACCELERATION * t + v0

    @staticmethod
    @fast_jit
    def time_reach_velocity(v: float, v0: float) -> float:
        return (v - v0) / BREAK_ACCELERATION

    @staticmethod
    @fast_jit
    def time_travel_distance(d: float, v: float) -> float:
        return (-v + math.sqrt(2 * BREAK_ACCELERATION * d + math.pow(v, 2))) / BREAK_ACCELERATION
