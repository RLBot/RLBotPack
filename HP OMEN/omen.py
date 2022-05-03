from gettext import find
from tools import  *
from objects import *
from routines import *
from threading import local
from utils import *
import time
from tools import *
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
#This file is for strategy


class omen(GoslingAgent):
    def run(agent):

        if len(agent.friends) == 0:
            if agent.team > 0.1:
                team_multiplier = 1
            if agent.team < 0.1:
                team_multiplier = -1

            if agent.team == 0:
                team_lol = 0
            else:
                team_lol = 1

            left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)), 0)
            right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * side(agent.team)), 0)
            future_ball = Vec3(0, 0, 0)
            future_ball_2 = 0
            ball_in_future = 0
            ball_in_future_2 = 0
            packet = GameTickPacket()
            ball_prediction = agent.get_ball_prediction_struct()
            ball_in_future = find_slice_at_time(ball_prediction, agent.time + 1)
            ball_in_future_2 = find_slice_at_time(ball_prediction, agent.time + 2)
            if ball_in_future is not None:
                future_ball = Vec3(ball_in_future.physics.location)
            elif ball_in_future_2 is not None:
                future_ball = Vec3(ball_in_future_2.physics.location)
            my_goal_to_ball,my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
            goal_to_me = agent.me.location - agent.friend_goal.location
            my_distance = my_goal_to_ball.dot(goal_to_me)
            large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
            foe_goal_to_ball,foe_ball_distance = (agent.ball.location - agent.foe_goal.location).normalize(True)
            foe_goal_to_foe = agent.foes[0].location - agent.foe_goal.location
            foe_distance = foe_goal_to_ball.dot(foe_goal_to_foe)
            closest_foe_to_ball = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe_to_ball.location - agent.ball.location).magnitude() > (foe.location - agent.ball.location).magnitude():
                    closest_foe = foe
            left_field = Vector3(4200*-side(agent.team),agent.ball.location.y + (1000*-side(agent.team)),0)
            right_field = Vector3(4200*side(agent.team),agent.ball.location.y + (1000*side(agent.team)),0)
            targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post),
                       "upfield": (left_field, right_field),
                       "not_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}


            shots = find_hits(agent, targets)
            x = 1
            me_onside = my_distance - 200 < my_ball_distance
            foe_onside = foe_distance - 200 < foe_ball_distance
            close = (agent.me.location - agent.ball.location).magnitude() < 3000
            foe_close = (closest_foe_to_ball.location - agent.ball.location).magnitude() < 3000
            have_boost = agent.me.boost > 20
            defense_location = Vector3(agent.ball.location.x, agent.ball.location.y + (4000 * team_multiplier), 0)

            closest_foe = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe.location - agent.me.location).magnitude() > (foe.location - agent.me.location).magnitude():
                    closest_foe = foe

            x = 1
            if agent.team == 0:
                agent.debug_stack()
                agent.line(agent.friend_goal.location, agent.ball.location, [255,255,255])
                my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
                agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0,255,0])



            def get_closest_boost(agent):
                large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
                closest_boost = large_boosts[0]
                for item in large_boosts:
                    if (closest_boost.location - agent.me.location).magnitude() > (
                            item.location - agent.me.location).magnitude():
                        closest_boost = item
                agent.stack = []
                agent.push(goto_boost(closest_boost))

            def demo(agent):
                relative_target = closest_foe.location - agent.me.location
                local_target = agent.me.local(relative_target)
                defaultPD(agent, local_target)
                defaultThrottle(agent, 2300)
                if (agent.me.location - closest_foe.location).magnitude() < 200:
                    agent.push(flip(agent.me.local(closest_foe.location - agent.me.location)))


            if agent.team == 0:
                agent.debug_stack()
                agent.line(agent.friend_goal.location, agent.ball.location, [255,255,255])
                my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
                agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0,255,0])

            if agent.team == 0:
                agent.debug_stack()
            if len(agent.stack) < 1:
                if agent.kickoff_flag:
                        if agent.me.location.x > 300 or agent.me.location.x < -300:
                            agent.push(kickoff())
                        else:
                            agent.controller.throttle = 0




                elif (agent.me.location - agent.friend_goal.location).magnitude() < 2000 and -1000 < agent.ball.location.x < 1000 and -1000 < closest_foe_to_ball.location.x < 1000:
                    if len(shots["not_my_net"]) > 0:
                        agent.push(shots["not_my_net"][0])

                elif (close and me_onside) and (foe_onside and foe_close) and (agent.me.location - agent.ball.location).magnitude() > 50 and agent.ball.location.z < 200:
                    while (agent.me.location - agent.ball.location).magnitude() > 50:
                        relative_target = agent.ball.location - agent.me.location
                        local_target = agent.me.local(relative_target)
                        defaultPD(agent, local_target)
                        defaultThrottle(agent, 2300)
                        break

                elif (close and me_onside) or me_onside and (closest_foe_to_ball.location - agent.ball.location).magnitude() > (agent.me.location - agent.ball.location).magnitude():


                    if len(shots["goal"]) > 0:
                        agent.push(shots["goal"][0])

                    elif len(shots["upfield"]) > 0:
                        agent.push(shots["upfield"][0])



                elif (agent.ball.location - agent.friend_goal.location).magnitude() > 6000:
                    agent.push(goto(defense_location))

                elif (agent.ball.location - agent.friend_goal.location).magnitude() > 4000 and (closest_foe.location - agent.ball.location).magnitude() > 3000 and agent.me.boost < 30 or (agent.ball.location - agent.friend_goal.location).magnitude() > 8000 and agent.me.boost < 30:
                    closest_boost = large_boosts[0]
                    for item in large_boosts:
                        if (closest_boost.location - agent.me.location).magnitude() > (
                                item.location - agent.me.location).magnitude():
                            closest_boost = item
                    agent.stack = []
                    agent.push(goto_boost(closest_boost))

                elif (agent.ball.location - agent.friend_goal.location).magnitude() < 5000 and len(shots["not_my_net"]) > 0:
                        agent.push(shots["not_my_net"][0])

                else:
                    demo(agent)


        elif len(agent.friends) > 0:

            if agent.team > 0.1:
                team_multiplier = 1
            if agent.team < 0.1:
                team_multiplier = -1

            if agent.team == 0:
                team_lol = 0
            else:
                team_lol = 1
            if len(agent.friends) > 0:
                for friend in agent.friends:
                    if (agent.me.location - agent.ball.location).magnitude() > (friend.location - agent.ball.location).magnitude():
                        is_closest_friend_to_ball = False
                    else:
                        is_closest_friend_to_ball = True
            closest_foe = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe.location - agent.me.location).magnitude() > (foe.location - agent.me.location).magnitude():
                    closest_foe = foe
            left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)), 0)
            right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * side(agent.team)), 0)
            future_ball = Vec3(0, 0, 0)
            future_ball_2 = 0
            ball_in_future = 0
            ball_in_future_2 = 0
            packet = GameTickPacket()
            ball_prediction = agent.get_ball_prediction_struct()
            ball_in_future = find_slice_at_time(ball_prediction, agent.time + 1)
            ball_in_future_2 = find_slice_at_time(ball_prediction, agent.time + 2)
            if ball_in_future is not None:
                future_ball = Vec3(ball_in_future.physics.location)
            elif ball_in_future_2 is not None:
                future_ball = Vec3(ball_in_future_2.physics.location)
            my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
            goal_to_me = agent.me.location - agent.friend_goal.location
            my_distance = my_goal_to_ball.dot(goal_to_me)
            large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
            foe_goal_to_ball, foe_ball_distance = (agent.ball.location - agent.foe_goal.location).normalize(True)
            foe_goal_to_foe = agent.foes[0].location - agent.foe_goal.location
            foe_distance = foe_goal_to_ball.dot(foe_goal_to_foe)
            closest_foe_to_ball = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe_to_ball.location - agent.ball.location).magnitude() > (
                        foe.location - agent.ball.location).magnitude():
                    closest_foe_to_ball = foe
            if len(agent.friends) > 0:
                closest_friend_to_ball = agent.friends[0]
                for friend in agent.friends:
                    if (closest_friend_to_ball.location - agent.ball.location).magnitude() > (
                            friend.location - agent.ball.location).magnitude():
                        closest_friend_to_ball = friend
            closest_friend_to_goal = agent.friends[0]
            for friend in agent.friends:
                if (closest_friend_to_goal.location - agent.friend_goal.location).magnitude() > (
                        friend.location - agent.friend_goal.location).magnitude():
                    closest_friend_to_goal = friend
                closest_friend = agent.friends[0]
                for friend in agent.friends:
                    if (closest_friend.location - agent.me.location).magnitude() > (
                            friend.location - agent.me.location).magnitude():
                        closest_friend = friend

            closest_foe = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe_to_ball.location - agent.me.location).magnitude() > (
                        foe.location - agent.me.location).magnitude():
                    closest_foe = foe
            left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)), 0)
            right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * side(agent.team)), 0)
            targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post),
                       "upfield": (left_field, right_field),
                       "not_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}

            shots = find_hits(agent, targets)
            x = 1
            me_onside = my_distance - 200 < my_ball_distance
            foe_onside = foe_distance - 200 < foe_ball_distance
            close = (agent.me.location - agent.ball.location).magnitude() < 3000
            foe_close = (closest_foe_to_ball.location - agent.ball.location).magnitude() < 3000
            have_boost = agent.me.boost > 20
            defense_location = Vector3(agent.ball.location.x, agent.ball.location.y + (4000 * team_multiplier), 0)
            x = 1
            if agent.team == 0:
                agent.debug_stack()
                agent.line(agent.friend_goal.location, agent.ball.location, [255, 255, 255])
                my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
                agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0, 255, 0])


            def get_closest_boost(agent):
                large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
                closest_boost = large_boosts[0]
                for item in large_boosts:
                    if (closest_boost.location - agent.me.location).magnitude() > (
                            item.location - agent.me.location).magnitude():
                        closest_boost = item
                agent.stack = []
                agent.push(goto_boost(closest_boost))

            def demo(agent):
                relative_target = closest_foe.location - agent.me.location
                local_target = agent.me.local(relative_target)
                defaultPD(agent, local_target)
                defaultThrottle(agent, 2300)
                if (agent.me.location - closest_foe.location).magnitude() < 200:
                    agent.push(flip(agent.me.local(closest_foe.location - agent.me.location)))


            if agent.team == 0:
                agent.debug_stack()
                agent.line(agent.friend_goal.location, agent.ball.location, [255, 255, 255])
                my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
                agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0, 255, 0])

            if agent.team == 0:
                agent.debug_stack()
            if len(agent.stack) < 1:
                if agent.kickoff_flag:
                    if (closest_friend_to_ball.location - agent.ball.location).magnitude() > (agent.me.location - agent.ball.location).magnitude() or (closest_friend_to_ball.location - agent.ball.location).magnitude() == (agent.me.location - agent.ball.location).magnitude() and closest_friend_to_ball.location.x < agent.me.location.x:
                        agent.push(kickoff())
                    else:
                        get_closest_boost(agent)


                elif (close and me_onside) and (foe_onside and foe_close) and (
                        agent.me.location - agent.ball.location).magnitude() > 50 and agent.ball.location.z < 200 and (closest_friend_to_ball.location - agent.ball.location).magnitude() > 1000:
                    while (agent.me.location - agent.ball.location).magnitude() > 50:
                        relative_target = agent.ball.location - agent.me.location
                        local_target = agent.me.local(relative_target)
                        defaultPD(agent, local_target)
                        defaultThrottle(agent, 2300)
                        break

                elif (close and me_onside) or (not foe_onside and me_onside) or (agent.me.location - agent.ball.location).magnitude() < (closest_friend_to_ball.location - agent.ball.location).magnitude() and me_onside:

                    if len(shots["goal"]) > 0:
                        agent.push(shots["goal"][0])

                    elif len(shots["upfield"]) > 0:
                        agent.push(shots["upfield"][0])




                elif (agent.ball.location - agent.friend_goal.location).magnitude() > 4000 and (
                        closest_foe.location - agent.ball.location).magnitude() > 3000 and agent.me.boost < 30 or (
                        agent.ball.location - agent.friend_goal.location).magnitude() > 8000 and agent.me.boost < 30:
                            get_closest_boost(agent)

                elif (agent.ball.location - agent.friend_goal.location).magnitude() > 5000 and (closest_friend_to_ball.location - agent.ball.location).magnitude() < (agent.me.location - agent.ball.location).magnitude():
                        demo(agent)

                elif (agent.ball.location.y - agent.friend_goal.location.y) > 4000:
                    agent.push(goto(defense_location))

                elif (agent.ball.location - agent.friend_goal.location).magnitude() < 4000 and len(shots["not_my_net"]) > 0:
                        agent.push(shots["not_my_net"][0])
                else:
                    demo(agent)

