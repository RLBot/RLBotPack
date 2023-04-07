import tools
from tools import *
from objects import *
from routines import *
from tmcp import TMCPHandler, TMCPMessage, ActionType

class BitBot(GoslingAgent):
    def run(agent):
        if len(agent.friends) != 0:
            agent.tmcp_handler = TMCPHandler(agent)
            if agent.team > 0.1:
                team_multiplier = 1
            if agent.team < 0.1:
                team_multiplier = -1
            agent.friend_goal = goal_object(agent.team)
            left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)), 0)
            right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * side(agent.team)), 0)
            global item_distance
            my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
            goal_to_me = agent.me.location - agent.friend_goal.location
            my_distance = my_goal_to_ball.dot(goal_to_me)
            targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post), "upfeild": (left_field, right_field), "not_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}
            shots = find_hits(agent, targets)
            agent.line(agent.friend_goal.location, agent.ball.location, [255, 255, 255])
            my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
            agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0, 255, 0])
            closest_friend = agent.friends[0]
            for friend in agent.friends:
                if (closest_friend.location - agent.me.location).magnitude() > (
                        friend.location - agent.me.location).magnitude():
                    closest_friend = friend
            for friend in agent.friends:
                if (agent.me.location - agent.ball.location).magnitude() > (
                        friend.location - agent.ball.location).magnitude():
                    is_closest_friend_to_ball = False
                else:
                    is_closest_friend_to_ball = True
            closest_friend_to_ball = agent.friends[0]
            for friend in agent.friends:
                if (closest_friend_to_ball.location - agent.ball.location).magnitude() > (friend.location - agent.ball.location).magnitude():
                    closest_friend_to_ball = friend
            closest_foe_to_ball = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe_to_ball.location - agent.ball.location).magnitude() > (
                        foe.location - agent.ball.location).magnitude():
                    closest_foe_to_ball = foe
            closest_foe = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe_to_ball.location - agent.me.location).magnitude() > (
                        foe.location - agent.me.location).magnitude():
                    closest_foe = foe
            foe_is_close = (closest_foe.location - agent.me.location).magnitude() < 1000
            if (closest_foe.location - agent.ball.location).magnitude() < 2000:
                foe_is_close_to_ball = True
            else:
                foe_is_close_to_ball = False
            defense_location = Vector3(agent.ball.location.x, agent.ball.location.y + (4000 * team_multiplier), 0)
            if len(agent.stack) == 0:
                agent.special_list.clear()
            me_onside = agent.me.location.y < agent.ball.location.y
            foe_onside = abs(agent.foe_goal.location.y - agent.foes[0].location.y) - 200 > abs(
                agent.foe_goal.location.y - agent.ball.location.y)
            agent.friend_goal = goal_object(agent.team)
            closest_foe = agent.foes[0]
            for foe in agent.foes:
                if (closest_foe.location - agent.me.location).magnitude() > (
                        foe.location - agent.me.location).magnitude():
                    closest_foe = foe
            #TEAM MATCH COMMUNICATION PROTOCOL
            new_messages: [TMCPMessage] = agent.tmcp_handler.recv()
            # Handle TMCPMessages.
            for message in new_messages:
                if message.action_type == ActionType.BALL and len(agent.special_list) != 0:
                    if (closest_foe.location - agent.me.location).magnitude() < 4000 and agent.ball.location.y < -1000 and agent.ball.location.y < 2500 and agent.team == 1 or (closest_foe.location - agent.me.location).magnitude() < 4000 and agent.ball.location.y > 1000 and agent.team == 0 and agent.ball.location.y > -2500:
                        agent.stack.clear()
                        relative_target = closest_foe.location - agent.me.location
                        local_target = agent.me.local(relative_target)
                        defaultPD(agent, local_target)
                        defaultThrottle(agent, 2300)
                        agent.controller.boost = True
                    else:
                        agent.stack.clear()
                        agent.push(goto(agent.friend_goal.location))

            def get_closest_boost(agent):
                large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
                closest_boost = large_boosts[0]
                for item in large_boosts:
                    if (closest_boost.location - agent.me.location).magnitude() > (
                            item.location - agent.me.location).magnitude():
                        closest_boost = item
                agent.stack = []
                agent.push(goto_boost(closest_boost))

            if agent.team == 0:
                agent.debug_stack()
            if len(agent.stack) < 1:

                if agent.kickoff_flag:
                    if is_closest_friend_to_ball:
                        agent.push(kickoff())
                    else:
                        get_closest_boost(agent)

                elif (agent.ball.location - agent.friend_goal.location).magnitude() < 4000 and foe_is_close_to_ball or (agent.ball.location - agent.friend_goal.location).magnitude() < 4000 and len(shots["goal"]) == 0 and len(shots["upfeild"]) == 0:
                    if len(shots["not_my_net"]) > 0:
                        agent.push(shots["not_my_net"][0])
                        agent.tmcp_handler.send_ball_action()
                        agent.special_list.append('APPENDDDD')
                    else:
                        agent.push(short_shot(agent.foe_goal.location))

                elif agent.friends == 1 and agent.friends[1].location < 5120 and agent.team == 1 or agent.friends == 1 and agent.friends[1].location > 5120 and agent.team == 0 or agent.friends == 2 and agent.friends[1].location < 5120 and agent.friends[2].location < 5120 and agent.team == 1 or agent.friends == 2 and agent.friends[1].location > 5120 and agent.friends[2].location > 5120 and agent.team == 0:
                    agent.push(goto(agent.friend_goal.location))
                    print("OGAAA")

                elif (agent.ball.location - agent.friend_goal.location).magnitude() < 4000:
                    if len(shots["goal"]) > 0:
                        agent.push(shots["goal"][0])
                        agent.tmcp_handler.send_ball_action()
                    elif len(shots["upfeild"]) > 0:
                        agent.push(shots["upfeild"][0])
                        agent.tmcp_handler.send_ball_action()
                    agent.special_list.append("APPENNDDDFDF")


                elif foe_is_close:
                    relative_target = closest_foe.location - agent.me.location
                    local_target = agent.me.local(relative_target)
                    defaultPD(agent, local_target)
                    defaultThrottle(agent, 2300)
                    agent.controller.boost = True
                    agent.tmcp_handler.send_demo_action(agent.index)

                elif is_closest_friend_to_ball or agent.team == 0 and closest_friend_to_ball.location.y > agent.ball.location.y or agent.team == 1 and closest_friend_to_ball.location.y < agent.ball.location.y:
                    if len(shots["goal"]) > 0:
                        agent.push(shots["goal"][0])
                        agent.tmcp_handler.send_ball_action()
                    elif len(shots["upfeild"]) > 0:
                        agent.push(shots["upfeild"][0])
                        agent.tmcp_handler.send_ball_action()

                elif agent.me.boost < 20 and (agent.ball.location - agent.friend_goal.location).magnitude() > 4000 and foe_is_close_to_ball == False:
                    large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
                    closest_boost = large_boosts[0]
                    for item in large_boosts:
                        if (closest_boost.location - agent.me.location).magnitude() > (
                                item.location - agent.me.location).magnitude():
                            closest_boost = item
                    agent.stack = []
                    agent.push(goto_boost(closest_boost))
                    agent.tmcp_handler.send_boost_action(1)

                elif (agent.ball.location - agent.friend_goal.location).magnitude() > 4000:
                    relative_target = closest_foe.location - agent.me.location
                    local_target = agent.me.local(relative_target)
                    defaultPD(agent, local_target)
                    defaultThrottle(agent, 2300)
                    agent.controller.boost = True
                    if (agent.me.location - local_target).magnitude() < 400:
                        agent.push(flip(agent.me.local(agent.me.location - closest_foe.location)))
                        agent.tmcp_handler.send_demo_action(agent.index)

                elif (agent.ball.location.y - agent.friend_goal.location.y) > 4000:
                    agent.push(goto(defense_location))
                    agent.tmcp_handler.send_defend_action()

                

        else:

             if agent.team > 0.1:
                 team_multiplier = 1
             if agent.team < 0.1:
                 team_multiplier = -1

             agent.friend_goal = goal_object(agent.team)
             left_field = Vector3(4200 * -side(agent.team), agent.ball.location.y + (1000 * -side(agent.team)), 0)
             right_field = Vector3(4200 * side(agent.team), agent.ball.location.y + (1000 * side(agent.team)), 0)
             global item_distance
             large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
             my_goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
             goal_to_me = agent.me.location - agent.friend_goal.location
             my_distance = my_goal_to_ball.dot(goal_to_me)
             targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post), "upfeild": (left_field, right_field),
                        "not_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}
             shots = find_hits(agent, targets)
             agent.line(agent.friend_goal.location, agent.ball.location, [255, 255, 255])
             my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
             agent.line(my_point - Vector3(0, 0, 100), my_point + Vector3(0, 0, 100), [0, 255, 0])
             closest_foe = agent.foes[0]
             for foe in agent.foes:
                 if (closest_foe.location - agent.me.location).magnitude() > (foe.location - agent.me.location).magnitude():
                     closest_foe = foe
             defense_location = Vector3(0, agent.ball.location.y + (3000 * team_multiplier), 0)
             if agent.team == 0:
                 agent.debug_stack()
             if len(agent.stack) < 1:

                 if agent.kickoff_flag:
                     agent.push(kickoff())

                 elif (agent.ball.location - agent.friend_goal.location).magnitude() < 4000:
                     if len(shots["not_my_net"]) > 0:
                         agent.push(shots["not_my_net"][0])

                 elif len(shots["goal"]) > 0:
                     agent.push(shots["goal"][0])

                 elif agent.me.boost < 20 and (agent.ball.location - agent.friend_goal.location).magnitude() > 5000:
                     closest_boost = large_boosts[0]
                     for item in large_boosts:
                         if (closest_boost.location - agent.me.location).magnitude() > (
                                 item.location - agent.me.location).magnitude():
                             closest_boost = item
                     agent.stack = []
                     agent.push(goto_boost(closest_boost))


                 elif agent.team == 1 and agent.ball.location.y < 2120 or agent.team == 0 and agent.ball.location.y > -2120:
                     agent.push(goto(defense_location))

                 else:
                     agent.push(short_shot(agent.foe_goal.location))