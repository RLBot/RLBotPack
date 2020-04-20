from GoslingUtils.utils import side
from GoslingUtils.routines import *
from src.utils import *
from math import atan2
from src.Extra_routines import *


LEFT_GOES = False


class State:
    def __init__(self):
        pass


class Kickoff(State):
    def __init__(self):
        super().__init__()
        self.generated = False
        self.desired_set = False
        self.desired_path = []
        self.diagonal = False
        self.role = "go"

    def run(self, agent):
        if not self.generated:
            self.generate_stack(agent)
        if Vector3(agent.ball.location - agent.me.location).magnitude() < 600:
            botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                     agent.ball.location[0] - agent.me.location[0])
            yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
            if abs(botToTargetAngle + yaw2) < 0.1:
                if type(agent.stack[-1]) != flip: #and self.should_dodge(agent):
                    agent.push(flip(Vector3(agent.me.local(agent.ball.location - agent.me.location))))
        agent.debug_stack()

    def set_role(self, agent):
        if not len(agent.friends):
            self.role = "go"
            return
        ball = Vector3(0, 0, 0)
        own_distance = agent.me.location.flatten().magnitude()
        if LEFT_GOES:
            sorted_friends = agent.friends[:]
            sorted_friends.sort(key=lambda car: car.location.flatten().magnitude())
            if sorted_friends[0].location.flatten().magnitude() > own_distance:
                self.role = "go"
                agent.cheat = False
            elif sorted_friends[0].location.flatten().magnitude() == own_distance:
                if sorted_friends[0].location[0] * side(agent.team) < agent.me.location[0] * side(agent.team):
                    self.role = "cheat"
                    agent.cheat = True
                else:
                    self.role = "go"
            elif len(agent.friends) == 1:
                self.role = "cheat"
                agent.cheat = True
            elif sorted_friends[1].location.flatten().magnitude() > own_distance:
                self.role = "cheat"
                agent.cheat = True
            elif sorted_friends[1].location.flatten().magnitude() == own_distance:
                if sorted_friends[1].location[0] * side(agent.team) < agent.me.location[0] * side(agent.team):
                    self.role = "get boost"
                    agent.cheat = False
                else:
                    self.role = "cheat"
                    agent.cheat = True
            else:
                self.role = "get boost"
                agent.cheat = False
        else:
            if is_closest_kickoff(agent, agent.me):
                self.role = "go"
                agent.cheat = False
            elif is_second_closest_kickof(agent):
                self.role = "cheat"
                agent.cheat = True
            else:
                self.role = "get boost"
                agent.cheat = False

    def generate_stack(self, agent):
        self.set_role(agent)
        if self.role is not "get boost":
            if abs(agent.me.location[0]) > 900 and not agent.cheat:
                self.diagonal = True
                agent.push(goto_kickoff(Vector3(0,0,0), None, 1, 50))
                agent.push(speed_flip(-1 if agent.me.location[0] * side(agent.team) < 0 else 1))
                x = 1788 if agent.me.location[0] > 0 else -1788
                y = 2300 * side(agent.team)
                agent.push(goto_kickoff(Vector3(x, y, 0), None, 1, 250))
            else:
                # agent.push(goto(Vector3(2000, 2000, 0)))
                # """
                if not self.desired_set:
                    self.assign_desired(agent)

                agent.push(goto_kickoff(Vector3(0,0,0), None, 1, 50))
                if not agent.me.location[0] == 0 and abs(agent.me.location[0]) < 900:
                    direction = 1 if agent.me.location[0] * side(agent.team) > 0 else -1
                    if not agent.cheat:
                        agent.push(speed_flip(direction, False))
                    agent.push(goto_kickoff(Vector3(0.0,  2900.0 * side(agent.team), 70.0), Vector3(0,0,0), 1, 475))
                    # """

            self.generated = True

    def next_state(self, agent):
        if self.role == "get boost":
            return "GetBoost"

        if agent.ball.location[0] == 0.0 and agent.ball.location[1] == 0.0:
            return "Kickoff"

        if self.diagonal and len(agent.stack) > 1:
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


    def should_dodge(self, agent):
        foes = agent.foes[:]
        foes.sort(key=lambda car: (car.location - Vector3(0, 0, 0)).magnitude())
        own_distance = (agent.me.location - Vector3(0, 0, 0)).magnitude()
        foe_distance = (foes[0].location - Vector3(0, 0, 0)).magnitude()
        print(foe_distance - own_distance)
        if foe_distance - own_distance > 200:
            return False
        return True
