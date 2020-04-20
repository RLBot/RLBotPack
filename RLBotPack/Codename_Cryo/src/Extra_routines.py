from GoslingUtils.utils import *
from GoslingUtils.routines import *
from src.utils import *
from math import atan2, pi

class steal_boost():
    # slightly tweaked version of GoslingUtils goto_boost class
    # very similar to goto() but designed for grabbing boost
    # if a target is provided the bot will try to be facing the target as it passes over the boost
    def __init__(self, boost, target=None):
        self.boost = boost
        self.target = target
        self.demo = None
        self.attempted_demo = False

    def run(self, agent):
        if self.boost is None:
            boost_cpy = agent.boosts[:]
            if agent.team == 0:
                boosts = [boost_cpy[18], boost_cpy[30], boost_cpy[15], boost_cpy[29]]
            else:
                boosts = [boost_cpy[18], boost_cpy[15], boost_cpy[3], boost_cpy[4]]
            boosts.sort(key=lambda boost: (agent.me.location + (2 * agent.me.velocity) - boost.location).magnitude())
            found = False
            for bp in boosts:
                if bp.active:
                    found = True
                    self.boost = bp
            if not found:
                agent.pop()

        agent.line(self.boost.location - Vector3(0, 0, 500), self.boost.location + Vector3(0, 0, 500), [0, 255, 0])
        car_to_boost = self.boost.location - agent.me.location
        distance_remaining = car_to_boost.flatten().magnitude()

        agent.line(self.boost.location - Vector3(0, 0, 500), self.boost.location + Vector3(0, 0, 500), [0, 255, 0])

        if self.target != None:
            vector = (self.target - self.boost.location).normalize()
            side_of_vector = sign(vector.cross((0, 0, 1)).dot(car_to_boost))
            car_to_boost_perp = car_to_boost.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_boost.angle(vector) * distance_remaining / 3.14
            final_target = self.boost.location + (car_to_boost_perp * adjustment)
            car_to_target = (self.target - agent.me.location).magnitude()
        else:
            adjustment = 9999
            car_to_target = 0
            final_target = self.boost.location

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        #if abs(agent.me.location[1]) > 5120: final_target[0] = cap(final_target[0], -750, 750)
        if in_goal_area(agent):
            final_target[0] = cap(final_target[0], -750, 750)
            final_target[1] = cap(final_target[1], -5050, 5050)

        local_target = agent.me.local(final_target - agent.me.location)

        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

        agent.controller.boost = self.boost.large if abs(angles[1]) < 0.3 else False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake

        velocity = 1 + agent.me.velocity.magnitude()

        """
        demo_coming, democar = detect_demo(agent)
        if demo_coming:
            agent.push(avoid_demo(democar))
        """

        go, index = demo_rotation(agent)
        if are_no_bots_back(agent) or friends_ahead_of_ball(agent) > 0:
            agent.pop()

        elif go and not self.attempted_demo and friends_ahead_of_ball(agent) == 0:
            agent.push(demo(index))
            self.boost = None
            self.attempted_demo = True

        elif self.boost.active == False or agent.me.boost >= 99.0 or distance_remaining < 350:
            agent.pop()
        elif agent.me.airborne:
            agent.push(recovery(self.target))
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and (
                distance_remaining / velocity > 2.0 or (adjustment < 90 and car_to_target / velocity > 2.0)):
            if abs(agent.controller.yaw) < 0.2:
                agent.push(flip(local_target))


class demo():
    def __init__(self, target):
        self.target_index = target

    def run(self, agent):
        car = opponent_car_by_index(agent, self.target_index)
        distance_to_target = (agent.me.location - car.location).magnitude()
        velocity = (agent.me.velocity).magnitude()
        velocity_needed = 2200 - velocity
        time_boosting_required = velocity_needed / 991.666
        boost_required = 33.3 * time_boosting_required
        distance_required = velocity * time_boosting_required + 0.5 * 991.666 * (time_boosting_required**2)
        time_to_target = distance_to_target / velocity
        local_target = agent.me.local(car.location + (car.velocity * time_to_target) - agent.me.location)
        if abs(agent.me.location[1]) > 5120 - 42.10: local_target[0] = cap(local_target[0], -750, 750)

        defaultPD(agent, local_target)
        defaultThrottle(agent, 2300)

        agent.line(car.location - Vector3(0, 0, 500), car.location + Vector3(0, 0, 500), [255, 0, 0])

        # when to stop
        if are_no_bots_back(agent) or friends_ahead_of_ball(agent) > 0:
            agent.pop()
        if car.location[1] * side(agent.team) > -3000 or car.location[2] > 200:
            agent.pop()
        elif agent.me.airborne:
            agent.pop()
            agent.push(recovery())
        elif velocity < 2200:
            if agent.me.boost < boost_required:
                agent.pop()
            elif distance_required > distance_to_target:
                agent.pop()


class goto_kickoff():
    # Drives towards a designated (stationary) target
    # Optional vector controls where the car should be pointing upon reaching the target
    # TODO - slow down if target is inside our turn radius
    def __init__(self, target, vector=None, direction=1, margin=350):
        self.target = target
        self.vector = vector
        self.direction = direction
        self.margin = margin

    def run(self, agent):
        car_to_target = self.target - agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        agent.line(self.target - Vector3(0, 0, 500), self.target + Vector3(0, 0, 500), [255, 0, 255])

        if self.vector != None:
            # See commends for adjustment in jump_shot or aerial for explanation
            side_of_vector = sign(self.vector.cross((0, 0, 1)).dot(car_to_target))
            car_to_target_perp = car_to_target.cross((0, 0, side_of_vector)).normalize()
            adjustment = car_to_target.angle(self.vector) * distance_remaining / 3.14
            final_target = self.target + (car_to_target_perp * adjustment)
        else:
            final_target = self.target

        # Some adjustment to the final target to ensure it's inside the field and we don't try to dirve through any goalposts to reach it
        if abs(agent.me.location[1] > 5150): final_target[0] = cap(final_target[0], -750, 750)

        local_target = agent.me.local(Vector3(final_target - agent.me.location))

        angles = defaultPD(agent, local_target, self.direction)
        defaultThrottle(agent, 2300, self.direction)

        agent.controller.boost = not agent.cheat

        velocity = 1 + agent.me.velocity.magnitude()
        botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                 agent.ball.location[0] - agent.me.location[0])
        yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
        if distance_remaining < self.margin:
            agent.pop()
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0 and agent.cheat:
            agent.push(flip(local_target))
        elif distance_remaining / velocity > 2 and velocity > 1000 and not agent.cheat and abs(botToTargetAngle + yaw2) < 0.1:
            if agent.controller.yaw < 0.2 and not agent.cheat:
                agent.push(boost_wave_dash())
        elif agent.me.airborne:
            agent.push(recovery(self.target))


class diagonal_kickoff():
    def __init__(self, agent):
        self.step = 0
        self.side = 1 if agent.me.location[0] > 0 else 0
        self.target0 = Vector3(1788 * side(self.side),  2300 * side(agent.team), 0)
        self.target1 = Vector3(1740 * side(self.side), 2187 * side(agent.team), 0)
        self.target2 = Vector3(80 * side(self.side), 470 * side(agent.team), 0)
    def run(self, agent):
        if len(agent.stack) <= 1:
            if self.step == 0:
                self.target0[0] = (agent.me.location[0] + 2 * self.target0[0]) / 3
                self.target0[1] = (agent.me.location[1] + 2 * self.target0[1]) / 3
                agent.push(goto_kickoff(self.target0))
                self.step += 1
            elif self.step == 1:
                agent.push(goto_kickoff(self.target1))
                self.step += 1
            elif self.step == 2:
                local_target1 = agent.me.local(self.target2 - agent.me.location)
                agent.push(diag_flip(Vector3(1, -2 * side(agent.team) * side(self.side), 0)))
                self.step += 1
            elif self.step == 3:
                self.side = 1 if agent.me.location[0] > 0 else 0
                local_target2 = agent.me.local(agent.ball.location - agent.me.location)
                local_target2[0] *= 5
                agent.push(diag_flip(local_target2))


class diag_flip():
    def __init__(self, vector, cancel=False):
        self.vector = vector.normalize()
        self.pitch = abs(self.vector[0]) * -sign(self.vector[0])
        self.yaw = abs(self.vector[1]) * sign(self.vector[1])
        self.cancel = cancel
        # the time the jump began
        self.time = -1
        # keeps track of the frames the jump button has been released
        self.counter = 0

    def run(self, agent):
        if self.time == -1:
            elapsed = 0
            self.time = agent.time
        else:
            elapsed = agent.time - self.time
        if elapsed < 0.09:
            agent.controller.jump = True
            agent.controller.boost = True
        elif elapsed < 0.15:
            agent.controller.jump = False
            agent.controller.yaw = self.yaw
            agent.controller.jump = False
            agent.controller.boost = True
        elif elapsed < 0.25 or (not self.cancel and elapsed < 0.9):
            if elapsed < 0.25:
                agent.controller.boost = True
            agent.controller.jump = True
            agent.controller.pitch = self.pitch
            agent.controller.yaw = self.yaw
        else:
            agent.pop()
            agent.push(recovery(Vector3(0, 0, 0)))
        # agent.controller.boost = True


class speed_flip():
    def __init__(self, direction, turn = True):
        self.direction = direction  # -1 = left, 1 = right
        self.start = -1
        self.turn = turn

    def run(self, agent):
        agent.controller.throttle = 1
        if self.start == -1:
            self.start = agent.time
            elapsed = 0
        else:
            elapsed = agent.time - self.start
            if not self.turn:
                elapsed += 0.065
        agent.controller.throttle = 1
        agent.controller.boost = True
        if elapsed < 0.065:
            agent.controller.handbrake = True
            agent.controller.steer = -1 * self.direction
        elif elapsed < 0.15:
            agent.controller.jump = True
        elif elapsed < 0.20:
            agent.controller.jump = False
            agent.controller.pitch = -1
            agent.controller.yaw = self.direction
        elif elapsed < 0.25:
            agent.controller.jump = True
            agent.controller.pitch = -1
            agent.controller.yaw = self.direction
        elif elapsed < 0.85:
            agent.controller.pitch = 1
            agent.controller.yaw = self.direction * 0.2
            agent.controller.jump = False
        elif elapsed < 1.20:
            agent.controller.roll = self.direction
            agent.controller.handbrake = True
            agent.controller.pitch = 1
            agent.controller.yaw = self.direction * 0.70
        elif agent.me.airborne:
            agent.push(recovery())
        elif not agent.me.airborne and elapsed > 0.3:
            agent.pop()
        elif elapsed > 2:
            agent.pop()
