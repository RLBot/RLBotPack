from GoslingUtils.routines import *
from src.utils import *
from math import atan2, pi
from src.Extra_routines import *


class State:
    def __init__(self):
        pass


class Attacking(State):
    def __init__(self):
        pass

    def run(self, agent):
        self.generate_stack(agent)
        agent.debug_stack()

    def generate_stack(self, agent):
        if agent.cheat and not len(agent.stack):
            agent.cheat_attack_time = agent.time
            return self.take_shot(agent)

        elif agent.cheat:
            if agent.time - agent.cheat_attack_time > 2:
                agent.cheat = False

        if len(agent.stack) < 1 or type(agent.stack[-1]) == goto:
            if is_ball_on_back_wall(agent):
                if (not len(agent.friends)
                        or (not is_closest(agent, agent.me, True)
                            and len(agent.friends)
                            and is_second_closest(agent))):
                    agent.stack.clear()
                    path = Vector3(agent.ball.location[0], side(agent.team) * -3000, 0)
                    face = Vector3(agent.foe_goal.location)
                    agent.push(goto(path, face))
                    return
                if len(agent.friends) and is_closest(agent, agent.me, True):
                    agent.stack.clear()
                    agent.push(short_shot(agent.foe_goal.location))

            if len(agent.friends):
                if not is_closest(agent, agent.me, True) or is_ahead_of_ball(agent):
                    if abs(agent.ball.location[0]) >= 1500 or abs(agent.ball.location[1]) <= 3000 or is_ahead_of_ball(
                            agent) or not is_second_closest(agent):
                        zone = get_desired_zone(agent)
                        if zone == get_location_zone(agent.me.location):
                            botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                                     agent.ball.location[0] - agent.me.location[0])
                            yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
                            if len(agent.stack): agent.pop()
                            if abs(botToTargetAngle + yaw2) > pi / 3:
                                agent.push(goto(zone_center(zone), agent.ball.location))
                            return

                        if zone is not -1:
                            path = Vector3(zone_center(zone))
                            if len(agent.stack): agent.pop()
                            agent.push(goto(path, agent.ball.location))
                        else:
                            path = agent.friend_goal.location
                            if len(agent.stack): agent.pop()
                            agent.push(goto(path, agent.ball.location))

                        if is_ahead_of_ball(agent):
                            self.steal_boost(agent)
                        return
            return self.take_shot(agent)

    def next_state(self, agent):
        if agent.cheat:
            return "Attacking"
        if is_ball_going_towards_goal(agent):
            return "Defending"
        if len(agent.friends) == 1 and not is_closest(agent, agent.me, True) and agent.me.boost < 24:
            return "GetBoost"
        if len(agent.friends) >= 2 and not is_second_closest(agent) and agent.me.boost < 24:
            return "GetBoost"
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
        if (agent.me.boost < 24 and not is_closest(agent, agent.me) and
                (agent.me.location - agent.ball.location).magnitude() > 2000):
            if not (len(agent.friends) >= 1 and is_closest(agent, agent.me, True)):
                return "GetBoost"

        return "Attacking"

    def take_shot(self, agent):
        target = agent.foe_goal.location
        if (agent.ball.location[0]) < 980:
            target[1] -= 2000 * side(agent.team)
        # agent.push(short_shot(target))
        left_post_reduced = Vector3(agent.foe_goal.left_post)
        right_post_reduced = Vector3(agent.foe_goal.right_post)
        if agent.team == 0:
            left_post_reduced[0] -= 250
            right_post_reduced[0] += 250
        if agent.team == 1:
            left_post_reduced[0] += 250
            right_post_reduced[0] -= 250
        targets = {"1": (left_post_reduced, right_post_reduced),
                   "2": (agent.foe_goal.left_post, agent.foe_goal.right_post)}
        determine_shot(agent, target, targets, 2)

    def steal_boost(self, agent):
        if agent.me.airborne:
            return
        if are_no_bots_back(agent):
            return
        if agent.me.velocity[0] > 0:
            if agent.team == 0:
                boosts = [agent.boosts[18], agent.boosts[30]]
            else:
                boosts = [agent.boosts[4], agent.boosts[18]]
        else:
            if agent.team == 1:
                boosts = [agent.boosts[18], agent.boosts[30]]
            else:
                boosts = [agent.boosts[3], agent.boosts[15]]
        boosts.sort(key=lambda boost: (agent.me.location - boost.location).magnitude())
        for bp in boosts:
            if bp.active:
                agent.push(steal_boost(bp))
                return



