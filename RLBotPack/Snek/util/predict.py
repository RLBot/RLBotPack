import math

from util.info import GRAVITY, Ball, Field, Goal
from util.rlmath import clip, lerp, clip01
from util.vec import norm, proj_onto_size, xy, Vec3


class DummyObject:
    """ Holds a position and velocity. The base can be either a physics object from the rlbot framework or any object
     that has a pos and vel attribute. """

    def __init__(self, base=None):
        if base is not None:
            # Position
            if hasattr(base, "location"):
                self.pos = Vec3(base.location.x,
                                base.location.y,
                                base.location.z)
            else:
                self.pos = Vec3(base.pos)

            # Velocity
            if hasattr(base, "velocity"):
                self.vel = Vec3(base.velocity.x,
                                base.velocity.y,
                                base.velocity.z)
            else:
                self.vel = Vec3(base.vel)

        else:
            self.pos = Vec3(0, 0, 0)
            self.vel = Vec3(0, 0, 0)


class UncertainEvent:
    """ UncertainEvents are used by prediction methods to describe their result: If something happens and when
     The class contains a few useful methods to compare UncertainEvents """

    def __init__(self, happens, time, data=None):
        self.happens = happens
        self.time = time
        self.data = data

    def happens_before_time(self, time: float) -> bool:
        return self.happens and self.time < time

    def happens_before(self, other) -> bool:
        return (self.happens and not other.happens) or (other.happens and self.happens_before_time(other.time))

    def happens_after_time(self, time: float) -> bool:
        return not self.happens or self.time > time

    def happens_after(self, other) -> bool:
        return self.happens and (not other.happens or other.time < self.time)


def fall(obj, time: float, g=GRAVITY):
    """ Moves the given object as if were falling. The position and velocity will be modified """
    obj.pos = 0.5 * g * time * time + obj.vel * time + obj.pos
    obj.vel = g * time + obj.vel
    return obj


def ball_predict(bot, time: float) -> DummyObject:
    """ Returns a DummyObject describing the expected position and velocity of the ball """
    path = bot.get_ball_prediction_struct()
    t = int(clip(360 * time / 6, 1, path.num_slices)) - 1
    return DummyObject(path.slices[t].physics)


def next_ball_landing(bot, obj=None, size=Ball.RADIUS) -> UncertainEvent:
    """ Returns a UncertainEvent describing the next ball landing. If obj==None the current ball is used, otherwise the
    given obj is used. """
    if obj is None:
        obj = bot.info.ball
        landing = arrival_at_height(obj, size, "DOWN")
        t = landing.time if landing.happens else 0
        moved_obj = ball_predict(bot, t)

    else:
        landing = arrival_at_height(obj, size, "DOWN")
        t = landing.time if landing.happens else 0
        moved_obj = fall(obj, t)

    return UncertainEvent(landing.happens, t, data={"obj": moved_obj})


def arrival_at_height(obj, height: float, dir: str="ANY", g=GRAVITY.z) -> UncertainEvent:
    """ Returns if and when the ball arrives at a given height. The dir argument can be set to a string
    saying ANY, DOWN, or UP to specify which direction the ball should be moving when arriving. """

    is_close = abs(height - obj.pos.z) < 3
    if is_close and dir == "ANY":
        return UncertainEvent(True, 0)

    D = 2 * g * height - 2 * g * obj.pos.z + obj.vel.z ** 2

    # Check if height is above current pos.z, because then it might never get there
    if obj.pos.z < height and dir != "DOWN":
        turn_time = -obj.vel.z / (2 * g)
        turn_point_height = fall(DummyObject(obj), turn_time).pos.z

        # Return false if height is never reached or was in the past
        if turn_point_height < height or turn_time < 0 or D < 0:
            return UncertainEvent(False, 1e300)

        # The height is reached on the way up
        return UncertainEvent(True, (-obj.vel.z + math.sqrt(D)) / g)

    if dir != "UP" and 0 < D:
        # Height is reached on the way down
        return UncertainEvent(True, -(obj.vel.z + math.sqrt(D)) / g)
    else:
        # Never fulfils requirements
        return UncertainEvent(False, 1e300)


def time_till_reach_ball(car, ball):
    """ Rough estimate about when we can reach the ball in 2d. """
    car_to_ball = xy(ball.pos - car.pos)
    dist = norm(car_to_ball) - Ball.RADIUS / 2
    vel_c_f = proj_onto_size(car.vel, car_to_ball)
    vel_b_f = proj_onto_size(ball.vel, car_to_ball)
    vel_c_amp = lerp(vel_c_f, norm(car.vel), 0.58)
    vel_f = vel_c_amp - vel_b_f
    dist_long_01 = clip01(dist / 10_000.0)
    time_normal = dist / max(220, vel_f)
    time_long = dist / max(norm(car.vel), 1410)
    time = lerp(time_normal, time_long, dist_long_01)
    arrive_time = time * 0.95
    # Combine slightly with old prediction to negative rapid changes
    result = lerp(arrive_time, car.last_expected_time_till_reach_ball, 0.22)
    car.last_expected_time_till_reach_ball = arrive_time
    return result


def will_ball_hit_goal(bot):
    ball = bot.info.ball
    if ball.vel.y == 0:
        return UncertainEvent(False, 1e306)

    time = (Field.LENGTH2 - abs(ball.pos.y)) / abs(ball.vel.y)
    hit_pos = ball_predict(bot, time).pos
    hits_goal = abs(hit_pos.x) < Goal.WIDTH2 + Ball.RADIUS

    return UncertainEvent(hits_goal, time)
