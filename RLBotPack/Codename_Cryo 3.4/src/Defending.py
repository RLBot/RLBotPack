from GoslingUtils.routines import *
from src.utils import *
from math import atan2,pi


class State:
    def __init__(self):
        pass


class Defending(State):
    def __init__(self):
        pass

    def run(self, agent):
        self.generate_stack(agent)
        agent.debug_stack()

    def generate_stack(self, agent):
        if len(agent.stack) < 1 or type(agent.stack[-1]) == goto:
            # rotate to zone
            if len(agent.friends):
                # get back on defense if all bots ahead of ball
                if are_no_bots_back(agent) and abs(agent.ball.location[1]) < 4500:
                    return self.back_post_rotation(agent)

                if not abs(agent.ball.location[1]) > 4500 and not(is_closest(agent, agent.me, True)):
                    if not is_ball_going_towards_goal(agent):
                        if not is_closest(agent, agent.me, True) or is_ahead_of_ball(agent):
                            if abs(agent.ball.location[0]) >= 1500 or abs(agent.ball.location[1]) <= 2000 or is_ahead_of_ball(
                                    agent):
                                zone = get_desired_zone(agent)
                                if zone == get_location_zone(agent.me.location):
                                    botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                                             agent.ball.location[0] - agent.me.location[0])
                                    yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
                                    if len(agent.stack): agent.pop()
                                    if abs(botToTargetAngle + yaw2) > pi/3:
                                        agent.push(goto(zone_center(zone), agent.ball.location))
                                    return
                                if zone is not -1:
                                    path = Vector3(zone_center(zone))
                                    if len(agent.stack): agent.pop()
                                    agent.push(goto(path, agent.ball.location))
                                else:
                                    if len(agent.stack): agent.pop()
                                    path = agent.friend_goal.location
                                    agent.push(goto(path, agent.ball.location))
                                return
            # back post rotation in 1's
            if not len(agent.friends):
                if not is_ball_going_towards_goal(agent) and not is_closest(agent, agent.me) and abs(agent.ball.location[1]) < 4500 and is_ahead_of_ball(agent):
                    return self.back_post_rotation(agent)



            target = agent.foe_goal.location
            if (agent.ball.location[0]) < 980:
                target[1] -= 2000 * side(agent.team)
            # agent.push(short_shot(target))
            forward_left = Vector3(agent.ball.location[0] - 2000*side(agent.team), agent.ball.location[1] - 5000 * side(agent.team), 0)
            forward_right = Vector3(agent.ball.location[0] + 2000*side(agent.team), agent.ball.location[1] - 5000 * side(agent.team), 0)
            side_left = Vector3(agent.ball.location[0], agent.ball.location[1], 0)
            side_right = Vector3(agent.ball.location[0], agent.ball.location[1], 0)
            if agent.me.location[0] > agent.ball.location[0]:
                side_left[0] -= 3000
                side_right[0] -= 3000
                if agent.team == 0:
                    side_left[1] += 5000
                else:
                    side_right[1] -= 5000
            else:
                side_left[0] += 3000
                side_right[0] += 3000
                if agent.team == 0:
                    side_right[1] += 5000
                else:
                    side_left[1] -= 5000
            if len(agent.foes) > 1:
                targets = {"3": (agent.foe_goal.left_post, agent.foe_goal.right_post),
                           "2": (forward_left, forward_right),
                           "1": (side_left, side_right)}
            else:
                targets = {"1": (agent.foe_goal.left_post, agent.foe_goal.right_post),
                           "2": (forward_left, forward_right),
                           "3": (side_left, side_right)}
            determine_shot(agent, target, targets, 3)

    def next_state(self, agent):
        if is_ball_going_towards_goal(agent):
            return "Defending"
        if agent.team == 1:
            if agent.ball.location[1] > 3500:
                return "Defending"
            if agent.ball.velocity[1] > 100:
                if abs(agent.ball.velocity[0]) < agent.ball.velocity[1]:
                    return "Defending"
                elif agent.ball.location[1] > 0:
                    return "Defending"
            if agent.ball.location[1] < -3500:
                return "Attacking"
        if agent.team == 0:
            if agent.ball.location[1] < -3500:
                return "Defending"
            if agent.ball.velocity[1] < -100:
                if abs(agent.ball.velocity[0]) < abs(agent.ball.velocity[1]):
                    return "Defending"
                elif agent.ball.location[1] < 0:
                    return "Defending"
            if agent.ball.location[1] > 3500:
                return "Attacking"
        return "Defending"


    def back_post_rotation(self, agent):
        y = 4500 * side(agent.team)
        z = 0
        if agent.ball.location[0] > 0:
            x = -850
        else:
            x = +850
        path = Vector3(x, y, z)
        if len(agent.stack): agent.pop()
        agent.push(goto(path, agent.ball.location, True))
