from GoslingUtils.utils import side
from GoslingUtils.routines import *
from src.utils import *
from math import atan2

class State:
    def __init__(self):
        pass


class Kickoff(State):
    def __init__(self):
        self.generated = False
        self.desired_set = False
        self.desired_path = []

    def run(self, agent):
        if not self.generated:
            self.generate_stack(agent)
        if Vector3(agent.ball.location - agent.me.location).magnitude() < 800:
            botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                     agent.ball.location[0] - agent.me.location[0])
            yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
            if abs(botToTargetAngle + yaw2) < 0.1:
                if type(agent.stack[-1]) != flip:
                    agent.push(flip(Vector3(agent.me.local(agent.ball.location - agent.me.location))))
        agent.debug_stack()

    def generate_stack(self, agent):
        agent.cheat = is_second_closest(agent)
        if is_closest(agent, agent.me, True):
            agent.cheat = False
        if is_closest(agent, agent.me, True) or is_second_closest(agent):
            if abs(agent.me.location[0]) > 900 and not agent.cheat:
                agent.push(kickoff())
            else:
                if not self.desired_set:
                    self.assign_desired(agent)

                agent.push(goto_kickoff(Vector3(0, 0, 0)))
                for loc in self.desired_path:
                    agent.push(goto_kickoff(loc, agent.cheat))

            self.generated = True

    def next_state(self, agent):
        if len(agent.friends) > 0 and not is_closest(agent, agent.me, True) and not is_second_closest(agent):
            return "GetBoost"

        if agent.ball.location[0] == 0.0 and agent.ball.location[1] == 0.0:
            return "Kickoff"

        # somehow defending is the best follow-up for kick-offs
        if agent.cheat:
            return "Attacking"

        elif not agent.me.airborne:
            if ((agent.ball.location[1] > 0 and agent.team == 1) or (
                    agent.ball.location[1] < 0 and agent.team == 0)):
                return "Defending"
            elif ((agent.ball.location[1] < 0 and agent.team == 1) or
                  (agent.ball.location[1] > 0 and agent.team == 0)):
                if is_closest(agent, agent.me) or (agent.me.location - agent.ball.location).magnitude() < 500:
                    return "Attacking"
                else:
                    return "GetBoost"
        return "Kickoff"

    def assign_desired(self, agent):
        if not self.desired_set:

            desired_y = 800 * side(agent.team)
            if agent.me.location[0] > 900:
                desired_x = 250
                desired_y = 825 * side(agent.team)
            elif agent.me.location[0] < -900:
                desired_x = -250
                desired_y = 825 * side(agent.team)
            else:
                desired_x = 0
            self.desired_path.append(Vector3(desired_x, desired_y, 17))
            if self.is_off_center(agent):
                self.desired_path.append(Vector3(0, 2816 * side(agent.team), 17))
            self.desired_set = True

    def is_off_center(self, agent):
        return abs(agent.me.location[1]) <= 3850 and abs(agent.me.location[1]) >= 3830


class goto_kickoff():
    # Drives towards a designated (stationary) target
    # Optional vector controls where the car should be pointing upon reaching the target
    # TODO - slow down if target is inside our turn radius
    def __init__(self, target, cheat=False, vector=None, direction=1):
        self.target = target
        self.vector = vector
        self.direction = direction

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
        if distance_remaining < 350:
            agent.pop()
        elif abs(angles[1]) < 0.05 and velocity > 600 and velocity < 2150 and distance_remaining / velocity > 2.0 and agent.cheat:
            agent.push(flip(local_target))
        elif agent.me.airborne:
            agent.push(recovery(self.target))
