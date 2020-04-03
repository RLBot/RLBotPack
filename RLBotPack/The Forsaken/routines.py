from __future__ import annotations

import math
from typing import TYPE_CHECKING

from objects import Vector3, Routine
from utils import cap, defaultPD, defaultThrottle, sign, backsolve, shot_valid

if TYPE_CHECKING:
    from hive import MyHivemind
    from objects import CarObject, BoostObject


# This file holds all of the mechanical tasks, called "routines", that the bot can do

class Atba(Routine):
    # An example routine that just drives towards the ball at max speed
    def __init__(self):
        super().__init__()

    def run(self, drone: CarObject, agent: MyHivemind):
        relative_target = agent.ball.location - drone.location
        local_target = drone.local(relative_target)
        defaultPD(drone, local_target)
        defaultThrottle(drone, 2300)


class AerialShot(Routine):
    # Very similar to jump_shot(), but instead designed to hit targets above 300uu
    # ***This routine is a WIP*** It does not currently hit the ball very hard,
    # nor does it like to be accurate above 600uu or so
    def __init__(self, ball_location: Vector3, intercept_time: float, shot_vector: Vector3):
        super().__init__()
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # The point we hit the ball at
        self.intercept = self.ball_location - (self.shot_vector * 110)
        # dictates when (how late) we jump, much later than in jump_shot because we can take advantage of a double jump
        self.jump_threshold = 600
        # what time we began our jump at
        self.jump_time = 0
        # If we need a second jump we have to let go of the jump button for 3 frames,
        # this counts how many frames we have let go for
        self.counter = 0

    def run(self, drone: CarObject, agent: MyHivemind):
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.01, 10.0)

        car_to_ball = self.ball_location - drone.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0, 0, 1)).dot(car_to_ball))

        car_to_intercept = self.intercept - drone.location
        car_to_intercept_perp = car_to_intercept.cross((0, 0, side_of_shot))  # perpendicular
        distance_remaining = car_to_intercept.flatten().magnitude()

        speed_required = distance_remaining / time_remaining
        # When still on the ground we pretend gravity doesn't exist, for better or worse
        acceleration_required = backsolve(self.intercept, drone, time_remaining, 0 if self.jump_time == 0 else 325)
        local_acceleration_required = drone.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_intercept.angle(self.shot_vector) * distance_remaining / 1.57  # size of adjustment
        adjustment *= (cap(self.jump_threshold - (acceleration_required[2]), 0.0,
                           self.jump_threshold) / self.jump_threshold)  # factoring in how close to jump we are
        # we don't adjust the final target if we are already jumping
        final_target = self.intercept + ((car_to_intercept_perp.normalize() * adjustment) if self.jump_time == 0 else 0)

        # Some extra adjustment to the final target to ensure it's inside the field and
        # we don't try to drive through any goalposts to reach it
        if abs(drone.location[1] > 5150):
            final_target[0] = cap(final_target[0], -750, 750)

        local_final_target = drone.local(final_target - drone.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(drone.location, self.intercept)
        agent.line(self.intercept - Vector3(0, 0, 100), self.intercept + Vector3(0, 0, 100), [255, 0, 0])
        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [0, 255, 0])

        angles = defaultPD(drone, local_final_target)

        if self.jump_time == 0:
            defaultThrottle(drone, speed_required)
            drone.controller.boost = False if abs(angles[1]) > 0.3 or drone.airborne else drone.controller.boost
            drone.controller.handbrake = True if abs(angles[1]) > 2.3 else drone.controller.handbrake
            if acceleration_required[2] > self.jump_threshold:
                # Switch into the jump when the upward acceleration required reaches our threshold,
                # hopefully we have aligned already...
                self.jump_time = agent.time
        else:
            time_since_jump = agent.time - self.jump_time

            # While airborne we boost if we're within 30 degrees of our local acceleration requirement
            if drone.airborne and local_acceleration_required.magnitude() * time_remaining > 100:
                angles = defaultPD(drone, local_acceleration_required)
                if abs(angles[0]) + abs(angles[1]) < 0.5:
                    drone.controller.boost = True
            if self.counter == 0 and (time_since_jump <= 0.2 and local_acceleration_required[2] > 0):
                # hold the jump button up to 0.2 seconds to get the most acceleration from the first jump
                drone.controller.jump = True
            elif time_since_jump > 0.2 and self.counter < 3:
                # Release the jump button for 3 ticks
                drone.controller.jump = False
                self.counter += 1
            elif local_acceleration_required[2] > 300 and self.counter == 3:
                # the acceleration from the second jump is instant, so we only do it for 1 frame
                drone.controller.jump = True
                drone.controller.pitch = 0
                drone.controller.yaw = 0
                drone.controller.roll = 0
                self.counter += 1

        if raw_time_remaining < -0.25 or not shot_valid(agent, self):
            drone.pop()
            drone.push(Recovery())


class Wait(Routine):
    def __init__(self, duration: float = 0.1):
        super().__init__()
        self.duration = duration
        self.time = -1

    def run(self, drone: CarObject, agent: MyHivemind):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed >= self.duration:
            drone.pop()
            drone.push(Flip(drone.local(agent.ball.location - drone.location)))


class Flip(Routine):
    # Flip takes a vector in local coordinates and flips/dodges in that direction
    def __init__(self, vector: Vector3, duration: float = 0.1, delay: float = 0.1):
        super().__init__()
        self.vector = vector.normalize()
        self.pitch = abs(self.vector[0]) * -sign(self.vector[0])
        self.yaw = abs(self.vector[1]) * sign(self.vector[1])
        self.delay = delay if delay >= duration else duration
        self.duration = duration
        # the time the jump began
        self.time = -1
        # keeps track of the frames the jump button has been released
        self.counter = 0

    def run(self, drone: CarObject, agent: MyHivemind):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < self.delay:
            if elapsed < self.duration:
                drone.controller.jump = True
            else:
                drone.controller.jump = False
                self.counter += 1
            robbies_constant = (self.vector * 1.5 * 2200 - drone.velocity * 1.5) * 2 * 1.5 ** -2
            robbies_boost_constant = drone.forward.flatten().normalize().dot(
                robbies_constant.flatten().normalize()) > (0.3 if not drone.airborne else 0.1)
            drone.controller.boost = robbies_boost_constant and not drone.supersonic
        elif elapsed >= self.delay and self.counter < 3:
            drone.controller.jump = False
            self.counter += 1
        elif elapsed < 0.9:
            drone.controller.jump = True
            defaultPD(drone, self.vector)
            drone.controller.pitch = self.pitch
            if abs(self.vector[1]) < 0.175:
                drone.controller.yaw = self.yaw
            drone.controller.roll = 0
        else:
            drone.pop()
            drone.push(Recovery(self.vector, target_local=True))


class SpeedFlip(Routine):
    # Flip takes a vector in local coordinates and flips/dodges in that direction
    def __init__(self, vector: Vector3, duration: float = 0.1, delay: float = 0.1, angle: float = 0,
                 boost: bool = False):
        super().__init__()
        self.vector = vector.normalize()
        self.pitch = abs(self.vector[0]) * -sign(self.vector[0])
        self.yaw = abs(self.vector[1]) * sign(self.vector[1])
        self.delay = delay if delay >= duration else duration
        self.duration = duration
        self.boost = boost
        self.angle = math.radians(angle) if boost else 0
        x = math.cos(self.angle) * self.vector.x - math.sin(self.angle) * self.vector.y
        y = math.sin(self.angle) * self.vector.x + math.cos(self.angle) * self.vector.y
        self.preorientation = Vector3(x, y, 0)
        # the time the jump began
        self.time = -1
        # keeps track of the frames the jump button has been released
        self.counter = 0

    def run(self, drone: CarObject, agent: MyHivemind):
        # An example of pushing routines to the stack:
        agent.line(Vector3(0, 0, 50), 2000 * self.vector.flatten(), color=[255, 0, 0])
        agent.line(Vector3(0, 0, 50), 2000 * drone.forward.flatten(), color=[0, 255, 0])
        robbies_constant = (self.vector * 1.5 * 2200 - drone.velocity * 1.5) * 2 * 1.5 ** -2
        robbies_boost_constant = drone.forward.flatten().normalize().dot(robbies_constant.flatten().normalize()) > (
            0.3 if not drone.airborne else 0.1)
        drone.controller.boost = robbies_boost_constant and self.boost and not drone.supersonic
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < self.delay:
            if elapsed < self.duration:
                drone.controller.jump = True
            else:
                drone.controller.jump = False
                self.counter += 1
            defaultPD(drone, self.preorientation)
        elif elapsed >= self.delay and self.counter < 3:
            drone.controller.jump = False
            defaultPD(drone, self.preorientation)
            self.counter += 1
        elif elapsed < self.delay + 0.05:
            drone.controller.jump = True
            defaultPD(drone, self.vector)
        else:
            drone.pop()
            drone.push(Recovery(boost=self.boost, time=agent.time))


class Goto(Routine):
    # Drives towards a designated (stationary) target
    # Optional vector controls where the car should be pointing upon reaching the target
    # TODO - slow down if target is inside our turn radius
    def __init__(self, target: Vector3, vector: Vector3 = None, direction: float = 1):
        super().__init__()
        self.target = target
        self.vector = vector
        self.direction = direction

    def run(self, drone: CarObject, agent: MyHivemind):
        car_to_target = self.target - drone.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(self.target - Vector3(0, 0, 500), self.target + Vector3(0, 0, 500), [255, 0, 255])

        if self.vector is not None:
            # See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0, 0, 1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        # Some adjustment to the final target to ensure it's inside the field and
        # we don't try to drive through any goalposts to reach it
        if abs(drone.location[1]) > 5150:
            final_target[0] = cap(final_target[0], -750, 750)

        local_target = drone.local(final_target - drone.location)

        angles = defaultPD(drone, local_target, self.direction)
        defaultThrottle(drone, 2300, self.direction)

        drone.controller.boost = False
        drone.controller.handbrake = True if abs(angles[1]) > 2.3 else drone.controller.handbrake

        velocity = 1 + drone.velocity.magnitude()
        if distance_remaining < 350:
            drone.pop()
        elif abs(angles[1]) < 0.05 and 600 < velocity < 2150 and distance_remaining / velocity > 2.0:
            drone.push(Flip(local_target))
        # TODO Halfflip
        # elif abs(angles[1]) > 2.8 and velocity < 200:
        #     agent.push(flip(local_target, True))
        elif drone.airborne:
            drone.push(Recovery(self.target))


class Shadow(Routine):
    # Drives towards a designated (stationary) target
    # Optional vector controls where the car should be pointing upon reaching the target
    # TODO - slow down if target is inside our turn radius
    def __init__(self, vector: Vector3 = None, direction: float = 1):
        super().__init__()
        self.vector = vector
        self.direction = direction

    def run(self, drone: CarObject, agent: MyHivemind):
        target = agent.friend_goal.location + (agent.ball.location - agent.friend_goal.location) / 2
        car_to_target = target - drone.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(target - Vector3(0, 0, 500), target + Vector3(0, 0, 500), [255, 0, 255])

        if self.vector is not None:
            # See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0, 0, 1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = target + (car_to_target_perp * adjustment)
        else:
            final_target = target

        # Some adjustment to the final target to ensure it's inside the field and
        # we don't try to drive through any goalposts to reach it
        if abs(drone.location[1]) > 5150:
            final_target[0] = cap(final_target[0], -750, 750)

        local_target = drone.local(final_target - drone.location)

        angles = defaultPD(drone, local_target, self.direction)
        defaultThrottle(drone, 2300, self.direction)

        drone.controller.boost = False
        drone.controller.handbrake = True if abs(angles[1]) > 2.3 else drone.controller.handbrake

        velocity = 1 + drone.velocity.magnitude()
        if distance_remaining < 350:
            drone.pop()
        elif abs(angles[1]) < 0.05 and 600 < velocity < 2150 and distance_remaining / velocity > 2.0:
            drone.push(Flip(local_target))
        # TODO Halfflip
        # elif abs(angles[1]) > 2.8 and velocity < 200:
        #     agent.push(flip(local_target, True))
        elif drone.airborne:
            drone.push(Recovery(target))


class GotoBoost(Routine):
    # very similar to goto() but designed for grabbing boost
    # if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self, boost: BoostObject, target: Vector3 = None):
        super().__init__()
        self.boost: BoostObject = boost
        self.target: Vector3 = target

    def run(self, drone: CarObject, agent: MyHivemind):
        if self.boost is None:
            drone.pop()
            return
        car_to_boost = self.boost.location - drone.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector3(0, 0, 500), self.boost.location + Vector3(0, 0, 500), [0, 255, 0])

        if self.target is not None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0, 0, 1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            car_to_target = (self.target - drone.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location

        # Some adjustment to the final target to ensure it's inside the field and
        # we don't try to dirve through any goalposts to reach it
        if abs(drone.location[1]) > 5150:
            final_target[0] = cap(final_target[0], -750, 750)

        local_target = drone.local(final_target - drone.location)

        angles = defaultPD(drone, local_target)
        defaultThrottle(drone, 2300)

        drone.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        drone.controller.handbrake = True if abs(angles[1]) > 2.3 else drone.controller.handbrake

        velocity = 1 + drone.velocity.magnitude()
        if not self.boost.active or drone.boost >= 99.0 or distance_remaining < 350:
            drone.pop()
        elif drone.airborne:
            drone.push(Recovery(self.target))
        elif abs(angles[1]) < 0.05 and 600 < velocity < 2150 and (
                distance_remaining / velocity > 2.0 or (adjustment < 90 and car_to_target / velocity > 2.0)):
            drone.push(Flip(local_target))


class JumpShot(Routine):
    # Hits a target point at a target time towards a target direction
    # Target must be no higher than 300uu unless you're feeling lucky
    # TODO - speed
    def __init__(self, ball_location: Vector3, intercept_time: float, shot_vector: Vector3, ratio: float,
                 direction: float = 1, speed: float = 2300):
        super().__init__()
        self.ball_location = ball_location
        self.intercept_time = intercept_time
        # The direction we intend to hit the ball in
        self.shot_vector = shot_vector
        # The point we dodge at
        # 173 is the 93uu ball radius + a bit more to account for the car's hitbox
        self.dodge_point = self.ball_location - (self.shot_vector * 173)
        # Ratio is how aligned the car is. Low ratios (<0.5) aren't likely to be hit properly
        self.ratio = ratio
        # whether the car should attempt this backwards
        self.direction = direction
        # Intercept speed not implemented
        self.speed_desired = speed
        # controls how soon car will jump based on acceleration required. max 584
        # bigger = later, which allows more time to align with shot vector
        # smaller = sooner
        self.jump_threshold = 400
        # Flags for what part of the routine we are in
        self.jumping = False
        self.dodging = False
        self.counter = 0
        self.p = 0
        self.y = 0

    def run(self, drone: CarObject, agent: MyHivemind):
        raw_time_remaining = self.intercept_time - agent.time
        # Capping raw_time_remaining above 0 to prevent division problems
        time_remaining = cap(raw_time_remaining, 0.001, 10.0)
        car_to_ball = self.ball_location - drone.location
        # whether we are to the left or right of the shot vector
        side_of_shot = sign(self.shot_vector.cross((0, 0, 1)).dot(car_to_ball))

        car_to_dodge_point = self.dodge_point - drone.location
        car_to_dodge_perp = car_to_dodge_point.cross((0, 0, side_of_shot))  # perpendicular
        distance_remaining = car_to_dodge_point.magnitude()

        speed_required = distance_remaining / time_remaining
        acceleration_required = backsolve(self.dodge_point, drone, time_remaining, 0 if not self.jumping else 650)
        local_acceleration_required = drone.local(acceleration_required)

        # The adjustment causes the car to circle around the dodge point in an effort to line up with the shot vector
        # The adjustment slowly decreases to 0 as the bot nears the time to jump
        adjustment = car_to_dodge_point.angle(self.shot_vector) * distance_remaining / 2.0  # size of adjustment
        adjustment *= (cap(self.jump_threshold - (acceleration_required[2]), 0.0,
                           self.jump_threshold) / self.jump_threshold)  # factoring in how close to jump we are
        # we don't adjust the final target if we are already jumping
        final_target = self.dodge_point + (
            (car_to_dodge_perp.normalize() * adjustment) if not self.jumping else 0) + Vector3(0, 0, 50)
        # Ensuring our target isn't too close to the sides of the field,
        # where our car would get messed up by the radius of the curves

        # Some adjustment to the final target to ensure it's inside the field and
        # we don't try to dirve through any goalposts to reach it
        if abs(drone.location[1]) > 5150:
            final_target[0] = cap(final_target[0], -750, 750)

        local_final_target = drone.local(final_target - drone.location)

        # drawing debug lines to show the dodge point and final target (which differs due to the adjustment)
        agent.line(drone.location, self.dodge_point)
        agent.line(self.dodge_point - Vector3(0, 0, 100), self.dodge_point + Vector3(0, 0, 100), [255, 0, 0])
        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [0, 255, 0])

        # Calling our drive utils to get us going towards the final target
        angles = defaultPD(drone, local_final_target, self.direction)
        defaultThrottle(drone, speed_required, self.direction)

        agent.line(drone.location, drone.location + (self.shot_vector * 200), [255, 255, 255])

        drone.controller.boost = False if abs(angles[1]) > 0.3 or drone.airborne else drone.controller.boost
        drone.controller.handbrake = True if abs(
            angles[1]) > 2.3 and self.direction == 1 else drone.controller.handbrake

        if not self.jumping:
            if raw_time_remaining <= 0.0 or (speed_required - 2300) * time_remaining > 45 or not shot_valid(agent,
                                                                                                            self):
                # If we're out of time or not fast enough to be within 45 units of target at the intercept time, we pop
                drone.pop()
                if drone.airborne:
                    drone.push(Recovery())
            elif local_acceleration_required[2] > self.jump_threshold \
                    and local_acceleration_required[2] > local_acceleration_required.flatten().magnitude():
                # Switch into the jump when the upward acceleration required reaches our threshold,
                # and our lateral acceleration is negligible
                self.jumping = True
        else:
            if (raw_time_remaining > 0.2 and not shot_valid(agent, self, 150)) or raw_time_remaining <= -0.9 or (
                    not drone.airborne and self.counter > 0):
                drone.pop()
                drone.push(Recovery())
            elif self.counter == 0 and local_acceleration_required[2] > 0.0 and raw_time_remaining > 0.083:
                # Initial jump to get airborne + we hold the jump button for extra power as required
                drone.controller.jump = True
            elif self.counter < 3:
                # make sure we aren't jumping for at least 3 frames
                drone.controller.jump = False
                self.counter += 1
            elif 0.1 >= raw_time_remaining > -0.9:
                # dodge in the direction of the shot_vector
                drone.controller.jump = True
                if not self.dodging:
                    vector = drone.local(self.shot_vector)
                    self.p = abs(vector[0]) * -sign(vector[0])
                    self.y = abs(vector[1]) * sign(vector[1]) * self.direction
                    self.dodging = True
                # simulating a deadzone so that the dodge is more natural
                drone.controller.pitch = self.p if abs(self.p) > 0.2 else 0
                drone.controller.yaw = self.y if abs(self.y) > 0.3 else 0


class CenterKickoff(Routine):
    def __init__(self):
        super().__init__()

    def run(self, drone: CarObject, agent: MyHivemind):
        target = Vector3(0, 3800 * agent.side(), 0)
        local_target = drone.local(target - drone.location)
        defaultPD(drone, local_target)
        defaultThrottle(drone, 2300)
        if local_target.magnitude() < 100:
            drone.pop()
            drone.push(DiagonalKickoff())
            drone.push(Flip(Vector3(1, 0, 0)))


class OffCenterKickoff(Routine):
    def __init__(self):
        super().__init__()

    def run(self, drone: CarObject, agent: MyHivemind):
        target = Vector3(0, 3116 * agent.side(), 0)
        local_target = drone.local(target - drone.location)
        defaultPD(drone, local_target)
        defaultThrottle(drone, 2300)
        if local_target.magnitude() < 400:
            drone.pop()
            drone.push(DiagonalKickoff())
            drone.push(Flip(drone.local(agent.ball.location - drone.location)))


class DiagonalKickoff(Routine):
    def __init__(self):
        super().__init__()

    def run(self, drone: CarObject, agent: MyHivemind):
        target = agent.ball.location + Vector3(0, 200 * agent.side(), 0)
        local_target = drone.local(target - drone.location)
        defaultPD(drone, local_target)
        defaultThrottle(drone, 2300)
        if local_target.magnitude() < 650:
            drone.pop()
            drone.push(Flip(drone.local(agent.foe_goal.location - drone.location)))


class Recovery(Routine):
    # Point towards our velocity vector and land upright, unless we aren't moving very fast
    # A vector can be provided to control where the car points when it lands
    def __init__(self, target: Vector3 = None, target_local: bool = False, boost: bool = False, time: float = 0):
        super().__init__()
        self.target = target
        self.target_local = target_local
        self.boost = boost
        self.start_time = time

    def run(self, drone: CarObject, agent: MyHivemind):
        if self.target is not None:
            if self.target_local:
                local_target = self.target
            else:
                local_target = drone.local((self.target - drone.location).flatten())
        else:
            local_target = drone.local(drone.velocity.flatten())

        defaultPD(drone, local_target)
        drone.controller.throttle = 1
        t = (-drone.velocity.z - (
                drone.velocity.z ** 2 + 2 * -650 * -(max(drone.location.z - 17.01, 0.01))) ** 0.5) / -650
        if self.target is not None:
            robbies_constant = (self.target.normalize() * t * 2200 - drone.velocity * t) * 2 * t ** -2
        else:
            robbies_constant = (drone.velocity.normalize() * t * 2200 - drone.velocity * t) * 2 * t ** -2
        agent.line(drone.location, robbies_constant, color=[255, 255, 255])
        robbies_boost_constant = drone.forward.normalize().dot(robbies_constant.normalize()) > 0.5
        drone.controller.boost = robbies_boost_constant and self.boost and not drone.supersonic
        if not drone.airborne:
            drone.pop()


class ShortShot(Routine):
    # This routine drives towards the ball and attempts to hit it towards a given target
    # It does not require ball prediction and kinda guesses at where the ball will be on its own
    def __init__(self, target: Vector3):
        super().__init__()
        self.target = target

    def run(self, drone: CarObject, agent: MyHivemind):
        car_to_ball, distance = (agent.ball.location - drone.location).normalize(True)
        ball_to_target = (self.target - agent.ball.location).normalize()

        relative_velocity = car_to_ball.dot(drone.velocity - agent.ball.velocity)
        if relative_velocity != 0.0:
            eta = cap(distance / cap(relative_velocity, 400, 2300), 0.0, 1.5)
        else:
            eta = 1.5

        # If we are approaching the ball from the wrong side the car will try to only hit the very edge of the ball
        left_vector = car_to_ball.cross((0, 0, 1))
        right_vector = car_to_ball.cross((0, 0, -1))
        target_vector = -ball_to_target.clamp(left_vector, right_vector)
        final_target = agent.ball.location + (target_vector * (distance / 2))

        # Some adjustment to the final target to ensure we don't try to drive through any goalposts to reach it
        if abs(drone.location[1]) > 5150:
            final_target[0] = cap(final_target[0], -750, 750)

        agent.line(final_target - Vector3(0, 0, 100), final_target + Vector3(0, 0, 100), [255, 255, 255])

        angles = defaultPD(drone, drone.local(final_target - drone.location))
        defaultThrottle(drone, 2300 if distance > 1600 else 2300 - cap(1600 * abs(angles[1]), 0, 2050))
        drone.controller.boost = False if drone.airborne or abs(angles[1]) > 0.3 else drone.controller.boost
        drone.controller.handbrake = True if abs(angles[1]) > 2.3 else drone.controller.handbrake

        if abs(angles[1]) < 0.05 and (eta < 0.45 or distance < 150):
            drone.pop()
            drone.push(Flip(drone.local(car_to_ball)))
