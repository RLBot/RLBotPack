from tools import *
from objects import *
from routines import *


# This file is for strategy

class BroccoliBot(GoslingAgent):
    def run(agent):

        my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
        my_goal_to_me = agent.me.location - agent.friend_goal.location
        my_distance = my_goal_to_ball.dot(my_goal_to_me)

        ball_to_me_distance = (agent.me.location - agent.ball.location).magnitude()

        closest_foe = agent.me
        foes_back = 0
        for foe in agent.foes:
            foe_distance = (foe.location - agent.ball.location).magnitude()
            closest_foe_distance = (closest_foe.location - agent.ball.location).magnitude()

            enemy_goal_to_foe = foe.location - agent.foe_goal.location
            foe_distance_is_back = my_goal_to_ball.dot(enemy_goal_to_foe)
            foe_back = False
            if foe_distance_is_back - 200 < my_ball_distance:
                foe_back = True
                foes_back += 1
            if foe_distance < closest_foe_distance and foe_back:
                closest_foe = foe
        closest_foe_distance = (closest_foe.location - agent.ball.location).magnitude()

        foe_goal_to_ball, foe_ball_distance = (agent.ball.location - agent.foe_goal.location).normalize(True)
        foe_goal_to_foe = closest_foe.location - agent.foe_goal.location
        foe_distance = foe_goal_to_ball.dot(foe_goal_to_foe)

        defending = my_goal_to_me.magnitude() < (agent.me.location - agent.foe_goal.location).magnitude()
        me_far_back = my_goal_to_me.magnitude() < ball_to_me_distance
        me_back = my_goal_to_me.magnitude() < my_ball_distance
        foe_back = foe_goal_to_foe.magnitude() < foe_ball_distance
        close = (agent.ball.location - agent.me.location).magnitude() < 1500
        have_boost = (agent.me.boost > 30)

        left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                             0)
        left_mid_field = Vector3(1000 * -side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                                 0)
        right_mid_field = Vector3(1000 * side(agent.team), agent.ball.location.y + (1500 * -side(agent.team)),
                                  0)
        right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)),
                              0)

        agent.rotation_index = 0
        friends_close = 0

        ball_too_close = my_ball_distance < 1500 or (
                    agent.ball.location + agent.ball.velocity - agent.me.location).magnitude() < 2000

        ball_close = (agent.ball.location - agent.foe_goal.location).magnitude() > (
                    agent.ball.location - agent.friend_goal.location).magnitude()

        going_toward = agent.friend_goal.location

        friends_back = 0
        for friend in agent.friends:
            friend_to_ball_distance = (friend.location - agent.ball.location).magnitude()

            my_goal_to_friend = friend.location - agent.friend_goal.location
            friend_distance = my_goal_to_ball.dot(my_goal_to_friend)
            friend_back = False
            if friend_distance - 200 < my_ball_distance:
                friends_back += 1
                friend_back = True

            if find_rotation(agent, friend):
                agent.rotation_index += 1
            if friend_to_ball_distance < 1500 and friend_back:
                friends_close += 1

        ball_in_enemy_corner = not ball_close and abs(agent.ball.location.x) > 3000 and abs(agent.ball.location.y) > 4000


        attacking = False
        clearing = False
        saving = False
        shadowing = False
        return_to_goal = False
        getting_boost = False
        getting_pads = False

        if agent.index == 0:
            agent.debug_stack()

        if len(agent.friends) == 0:
            if len(agent.stack) < 1:
                if agent.kickoff_flag and agent.rotation_index == 0:
                    agent.push(kickoff(agent.me.location.x))
                elif ball_too_close:
                    saving = True
                elif ball_close and me_back:
                    clearing = True
                elif not ball_in_enemy_corner and ((me_back and not foe_back) or my_ball_distance < foe_ball_distance):
                    attacking = True
                elif not have_boost and my_ball_distance * 2 < foe_ball_distance:
                    getting_boost = True
                    going_toward = agent.friend_goal.location
                elif not ball_close and foe_ball_distance > 1500 and close:
                    agent.push(demo(closest_foe))
                else:
                    return_to_goal = True
        else:
            if len(agent.stack) < 1:
                if agent.kickoff_flag:
                    if agent.rotation_index == 0:
                        agent.push(kickoff(agent.me.location.x))
                    elif agent.rotation_index == 1:
                        shadowing = True
                    else:
                        return_to_goal = True
                elif agent.rotation_index == 0:
                    if not ball_close:
                        attacking = True
                    elif not ball_too_close:
                        clearing = True
                    else:
                        saving = True
                elif agent.rotation_index == 1:
                    if friends_back == 1 and me_back:
                        return_to_goal = True
                    elif not have_boost and not me_back:
                        getting_boost = True
                        going_toward = agent.friend_goal.location
                    elif not me_back and have_boost and friends_back > 0:
                        agent.push(demo(closest_foe))
                    else:
                        shadowing = True
                else:
                    return_to_goal = True

        if saving:
            if closest_foe_distance < 300 and abs(
                    closest_foe.velocity.magnitude() - agent.ball.velocity.magnitude()) < 600 and agent.ball.location.z < 200:
                agent.push(save())
            else:
                agent.push(find_best_save(agent, closest_foe))

        if getting_boost:
            boosts = [boost for boost in agent.boosts if boost.large and boost.active and abs(
                agent.friend_goal.location.y - boost.location.y) - 200 < abs(
                agent.friend_goal.location.y - agent.me.location.y)]
            if len(boosts) > 0:
                closest = boosts[0]
                for boost in boosts:
                    if (boost.location - agent.me.location).magnitude() < (
                            closest.location - agent.me.location).magnitude():
                        closest = boost
                agent.push(goto_boost(closest, going_toward))
            elif agent.rotation_index == 0:
                agent.push(short_shot(agent.foe_goal.location))
            else:
                return_to_goal = True


        if clearing:
            if (closest_foe_distance < 300 and abs(closest_foe.velocity.magnitude() - agent.ball.velocity.magnitude())
                    < 600 and agent.ball.location.z < 200):
                agent.push(save())
            else:
                agent.push(find_best_shot(agent, closest_foe))

        if attacking:
            if (closest_foe_distance > 1500 > closest_foe.velocity.magnitude() and ball_to_me_distance < 1000 and agent.ball.velocity.magnitude() < 800) or \
                    (ball_to_me_distance < 300 and (closest_foe_distance > 1000 or agent.ball.location.z < 300)):
                agent.push(dribble(agent.foe_goal.location))
            else:
                agent.push(find_best_shot(agent, closest_foe))

        if shadowing:
            target = Vector3(-(agent.friend_goal.location.x + agent.ball.location.x + closest_foe.location.x) / 6,
                                (agent.friend_goal.location.y + agent.ball.location.y + closest_foe.location.y) / 3, 320)
            distance = (target - agent.me.location).magnitude()
            relative_target = target - agent.me.location
            local_target = agent.me.local(relative_target)
            if 1500 > distance > 500:
                getting_pads = True
                going_toward = target
            else:
                defaultThrottle(agent, cap(0, 2300, distance))
                angles = defaultPD(agent, local_target)
                agent.controller.boost = True if distance > 1500 and (
                        abs(angles[1]) < 0.5 or agent.me.airborne) else False
                agent.controller.handbrake = True if abs(angles[1]) > 2.8 else False

        if getting_pads:
            boosts = [boost for boost in agent.boosts if not boost.large and boost.active and abs(
                agent.friend_goal.location.y - boost.location.y) - 200 < abs(
                agent.friend_goal.location.y - agent.me.location.y)]
            if len(boosts) > 0:
                closest = boosts[0]
                for boost in boosts:
                    if (boost.location - agent.me.location).magnitude() + (boost.location - going_toward).magnitude() < \
                            (closest.location - agent.me.location).magnitude() + (closest.location - going_toward).magnitude():
                        closest = boost
                agent.push(goto_pad(closest, going_toward))
            elif agent.rotation_index == 0:
                agent.push(short_shot(agent.foe_goal.location))
            else:
                return_to_goal = True

        if return_to_goal:
            relative_target = agent.friend_goal.location - agent.me.location
            distance_to_goal = relative_target.magnitude()
            friend_goal_to_ball = (agent.friend_goal.location - agent.ball.location).flatten().normalize()
            ideal_position = (agent.friend_goal.location - friend_goal_to_ball * 700).flatten()
            ideal_position_to_me = ideal_position - agent.me.location
            ideal_distance = ideal_position_to_me.magnitude()

            if distance_to_goal < 600 or ideal_distance < 100:
                agent.push(align_in_goal())
            else:
                angles = defaultPD(agent, agent.me.local(relative_target))
                defaultThrottle(agent, cap(distance_to_goal + 400, 0, 1400 + (2 - friends_back) * 450))
                agent.controller.boost = False if abs(angles[1]) > 0.5 or agent.me.airborne else agent.controller.boost
                agent.controller.handbrake = True if abs(angles[1]) > 2.5 else False



