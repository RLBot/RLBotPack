THROTTLE_ACCELERATION_0 = 1600
THROTTLE_ACCELERATION_1400 = 160
THROTTLE_MID_SPEED = 1400

BOOST_ACCELERATION = 991.6667
BREAK_ACCELERATION = 3500
COAST_ACCELERATION = 525

MAX_CAR_SPEED = 2300

BOOST_CONSUMPTION_RATE = 33.3  # per second
BOOST_MIN_TIME = 14 / 120  # The minimum time window where boost takes effect
BOOST_MIN_ACCELERATION = BOOST_ACCELERATION * BOOST_MIN_TIME

# constants of the acceleration between 0 to 1400 velocity: acceleration = a * velocity + b
a = -(THROTTLE_ACCELERATION_0 - THROTTLE_ACCELERATION_1400) / THROTTLE_MID_SPEED
b = THROTTLE_ACCELERATION_0

DT = 1 / 120


def throttle_acceleration(vel: float, throttle: float = 1):
    throttle = min(1, max(-1, throttle))
    if throttle * vel < 0:
        return -BREAK_ACCELERATION * (int(vel > 0) - int(vel < 0))
    elif throttle == 0:
        return -COAST_ACCELERATION * (int(vel > 0) - int(vel < 0))
    elif abs(vel) < THROTTLE_MID_SPEED:
        return (a * min(abs(vel), THROTTLE_MID_SPEED) + b) * throttle
    else:
        return 0
