from GoslingUtils.routines import *
from GoslingUtils.tools import *
from src.utils import *
from math import atan2, pi
from src.Extra_routines import *


class State:
    def __init__(self):
        pass


class Attacking(State):
    def __init__(self):
        self.attempted_shot = True

    def run(self, agent):
        self.generate_stack(agent)
        agent.debug_stack()

    def generate_stack(self, agent):
        if agent.aerialing and agent.stopped_aerial:
            self.stopped_aerial = False
            if not self.follow_up(agent):
                agent.aerialing = False
                agent.push(recovery())
            return

        if agent.cheat and not len(agent.stack):
            agent.cheat_attack_time = agent.time
            return self.take_shot(agent)

        elif agent.cheat:
            if agent.time - agent.cheat_attack_time > 3:
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
                        if zone == get_location_zone(agent.me.location) and zone is not 5:
                            botToTargetAngle = atan2(agent.ball.location[1] - agent.me.location[1],
                                                     agent.ball.location[0] - agent.me.location[0])
                            yaw2 = atan2(agent.me.orientation[1][0], agent.me.orientation[0][0])
                            if len(agent.stack): agent.pop()
                            if abs(botToTargetAngle + yaw2) > pi / 4:
                                agent.push(goto(zone_center(zone), agent.ball.location))
                            else:
                                defaultThrottle(agent, 0)
                                """
                                demo_coming, democar = detect_demo(agent)
                                if demo_coming:
                                    agent.push(avoid_demo(democar))
                                """
                            return

                        if zone is not -1:
                            if zone == 5:
                                path, center = zone_5_positioning(agent)
                                if center and (is_second_closest(agent) or is_closest(agent, agent.me, True)) and not is_last_one_back(agent):
                                    if not len(agent.stack) or (len(agent.stack) and type(agent.stack[-1]) == goto):
                                        if self.take_shot(agent, True):
                                            return
                                if not is_second_closest(agent):
                                    path = zone_center(zone)
                            else:
                                path = Vector3(zone_center(zone))
                            if len(agent.stack): agent.pop()
                            agent.push(goto(path, agent.ball.location))
                        else:
                            path = agent.friend_goal.location
                            if len(agent.stack): agent.pop()
                            agent.push(goto(path, agent.ball.location))

                        if is_ahead_of_ball(agent) and self.attempted_shot:
                            self.steal_boost(agent)
                            self.attempted_shot = False
                        return
            ball_zone = get_location_zone(agent.ball.location)
            if not self.take_shot(agent, center= (ball_zone == 2) if agent.team == 0 else (ball_zone == 8)):
                self.take_shot(agent)
            return

    def next_state(self, agent):
        if agent.cheat:
            return "Attacking"
        if is_ball_going_towards_goal(agent) or are_no_bots_back(agent):
            return "Defending"
        if len(agent.friends) == 1 and not is_closest(agent, agent.me, True) and agent.me.boost < 24:
            return "GetBoost"
        if len(agent.friends) >= 2 and not (is_second_closest(agent) or is_closest(agent, agent.me, True)) and agent.me.boost < 24 and not self.is_going_to_steal_boost(agent):
            return "GetBoost"
        if agent.team == 1:
            if agent.ball.location[1] > 3500:
                return "Defending"
            if agent.ball.location[1] < -3500:
                return "Attacking"
            if agent.ball.velocity[1] > 300:
                if abs(agent.ball.velocity[0]) < agent.ball.velocity[1]:
                    return "Defending"
                elif agent.ball.location[1] > 0:
                    return "Defending"

        if agent.team == 0:
            if agent.ball.location[1] < -3500:
                return "Defending"
            if agent.ball.location[1] > 3500:
                return "Attacking"
            if agent.ball.velocity[1] < -300:
                if abs(agent.ball.velocity[0]) < abs(agent.ball.velocity[1]):
                    return "Defending"
                elif agent.ball.location[1] < 0:
                    return "Defending"

        if (agent.me.boost < 24 and not is_closest(agent, agent.me) and
                (agent.me.location - agent.ball.location).magnitude() > 2000) and not self.is_going_to_steal_boost(agent):
            if not (len(agent.friends) >= 1 and is_closest(agent, agent.me, True)):
                return "GetBoost"

        return "Attacking"

    def take_shot(self, agent, center=False):
        self.attempted_shot = True
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

        counter = 2

        targets = {"1": (left_post_reduced, right_post_reduced),
                   "2": (agent.foe_goal.left_post, agent.foe_goal.right_post)}

        if center:
            return determine_shot(agent, target, targets, counter, False, True)

        # infield pass
        if abs(agent.ball.location[0]) > 1000 and len(agent.friends):
            counter += 1
            side_left = Vector3(0, agent.ball.location[1], 0)
            side_right = Vector3(0, agent.ball.location[1], 0)
            if agent.ball.location[0] > 0:
                if agent.team == 0:
                    side_left[1] += 1000
                    side_right[1] -= 500
                else:
                    side_left[1] += 500
                    side_right[1] -= 1000
            else:
                if agent.team == 0:
                    side_right[1] += 1000
                    side_left[1] -= 500
                else:
                    side_right[1] += 500
                    side_left[1] -= 1000
            if abs(agent.ball.location[1] > 4500):
                # infield pass is 3rd option
                targets[str(counter)] = (side_left, side_right)
                counter += 1
            else:
                # infield pass is 4th option
                targets[str(counter + 1)] = (side_left, side_right)
        if (counter < 3): counter = 3
        if abs(agent.ball.location[0]) > 4098 - 1152:
            forward_left = Vector3(agent.ball.location[0] - 500 * side(agent.team),
                                   agent.ball.location[1] - 5000 * side(agent.team),
                                   0)
            forward_right = Vector3(agent.ball.location[0] + 500 * side(agent.team),
                                    agent.ball.location[1] - 5000 * side(agent.team),
                                    0)
        else:
            forward_left = Vector3(0, 0, 0)
            forward_right = Vector3(0, 0, 0)
        targets[str(counter)] = (forward_left, forward_right)


        return determine_shot(agent, target, targets, counter)

    def steal_boost(self, agent):
        if agent.me.airborne:
            return
        if are_no_bots_back(agent):
            return

        if agent.team == 0:
            boosts = [agent.boosts[18], agent.boosts[30], agent.boosts[15], agent.boosts[29]]
        else:
            boosts = [agent.boosts[18], agent.boosts[15], agent.boosts[3], agent.boosts[4]]
        boosts.sort(key=lambda boost: (agent.me.location + (2 * agent.me.velocity) - boost.location).magnitude())
        for bp in boosts:
            if bp.active:
                agent.push(steal_boost(bp))
                return



    def is_going_to_steal_boost(self, agent):
        for routine in agent.stack:
            if type(routine) == steal_boost:
                return True
        return False

    def follow_up(self, agent):
        self.attempted_shot = True
        left_post_reduced = Vector3(agent.foe_goal.left_post)
        right_post_reduced = Vector3(agent.foe_goal.right_post)
        if agent.team == 0:
            left_post_reduced[0] -= 250
            right_post_reduced[0] += 250
        if agent.team == 1:
            left_post_reduced[0] += 250
            right_post_reduced[0] -= 250

        counter = 2

        targets = {"1": (left_post_reduced, right_post_reduced),
                   "2": (agent.foe_goal.left_post, agent.foe_goal.right_post)}

        # infield pass
        if abs(agent.ball.location[0]) > 1000 and len(agent.friends):
            counter += 1
            side_left = Vector3(0, agent.ball.location[1], 0)
            side_right = Vector3(0, agent.ball.location[1], 0)
            if agent.ball.location[0] > 0:
                if agent.team == 0:
                    side_left[1] += 1000
                    side_right[1] -= 500
                else:
                    side_left[1] += 500
                    side_right[1] -= 1000
            else:
                if agent.team == 0:
                    side_right[1] += 1000
                    side_left[1] -= 500
                else:
                    side_right[1] += 500
                    side_left[1] -= 1000
            if abs(agent.ball.location[1] > 4500):
                # infield pass is 3rd option
                targets[str(counter)] = (side_left, side_right)
                counter += 1
            else:
                # infield pass is 4th option
                targets[str(counter + 1)] = (side_left, side_right)
        if (counter < 3): counter = 3
        if abs(agent.ball.location[0]) > 4098 - 1152:
            forward_left = Vector3(agent.ball.location[0] - 500 * side(agent.team),
                                   agent.ball.location[1] - 5000 * side(agent.team),
                                   0)
            forward_right = Vector3(agent.ball.location[0] + 500 * side(agent.team),
                                    agent.ball.location[1] - 5000 * side(agent.team),
                                    0)
        else:
            forward_left = Vector3(0, 0, 0)
            forward_right = Vector3(0, 0, 0)
        targets[str(counter)] = (forward_left, forward_right)
        return determine_follow_up_shot(agent, targets, counter)
