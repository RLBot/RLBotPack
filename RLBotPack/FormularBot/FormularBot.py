from tools import  *
from objects import *
from routines import *
from rlbot.utils.structures.quick_chats import QuickChats
# from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

# car_state = CarState(boost_amount=100)

# ball_state = BallState(Physics(location=Vector3(0,0,2000)))

# game_info_state = GameInfoState(world_gravity_z=0, game_speed=1)

# game_state = GameState(ball=ball_state, cars={agent.index: car_state}, game_info=game_info_state)

# agent.set_game_state(game_state)


class FormularBot(GoslingAgent):
    def run(agent):
        global stack
        distance_ball_friendly_goal = (agent.ball.location - agent.friend_goal.location).magnitude()
        distance_ball_foe_goal = (agent.ball.location - agent.foe_goal.location).magnitude()

        my_goal_to_ball,my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
        goal_to_me = agent.me.location - agent.friend_goal.location
        my_distance = my_goal_to_ball.dot(goal_to_me)
        me_onside = my_distance + 70 < my_ball_distance
        me_onside2 = agent.me.location.y > agent.ball.location.y if side(agent.team) == 0 else agent.me.location.y < agent.ball.location.y

        close = (agent.me.location - agent.ball.location).magnitude() < 1500
        very_close = (agent.me.location - agent.ball.location).magnitude() < 500
        distance_to_ball = (agent.me.location - agent.ball.location).flatten().magnitude()
        distance_to_friendly_goal = (agent.me.location - agent.friend_goal.location).flatten().magnitude()

        relative_target = agent.ball.location - agent.friend_goal.location
        distance_ball_friendly_goal = relative_target.magnitude()

        left_field = Vector3(4200*-side(agent.team),agent.ball.location.y + 1000*-side(agent.team),0)
        right_field = Vector3(4200*side(agent.team),agent.ball.location.y + 1000*-side(agent.team),0)
        near_left_corner = Vector3(2944*-side(agent.team),5000*side(agent.team),100)
        near_right_corner = Vector3(-2944*-side(agent.team),5000*side(agent.team),100)
        targets = {"goal": (agent.foe_goal.left_post,agent.foe_goal.right_post), "upfield": (left_field,right_field)}
        shots = find_hits(agent,targets)

        possession = agent.ball.latest_touched_team if agent.ball.latest_touched_team == 1 else -1
        have_possession = True if possession == side(agent.team) else False

        allies = agent.friends
        ally_to_ball = "none"
        ally_to_ball_distance = 99999
        ally_to_friendly_goal = "none"
        ally_to_friendly_goal_distance = 99999

        for item in allies:
            if item.location.y * - side(agent.team) < agent.ball.location.y * - side(agent.team):
                item_distance = (item.location - agent.ball.location).flatten().magnitude()
                item_goal_distance = (item.location - agent.friend_goal.location).flatten().magnitude()
                if item_distance < ally_to_ball_distance:
                    ally_to_ball = item
                    ally_to_ball_distance = item_distance
                if item_goal_distance < ally_to_friendly_goal_distance:
                    ally_to_friendly_goal = item
                    ally_to_friendly_goal_distance = item_goal_distance

        closest_ally_to_ball_distance = ally_to_ball_distance
        closest_ally_friendly_goal_distance = ally_to_friendly_goal_distance 

        closest_to_ball = distance_to_ball < closest_ally_to_ball_distance
        joint_closest_to_ball = distance_to_ball == closest_ally_to_ball_distance
        closest_ally_friendly_goal = distance_to_friendly_goal <= closest_ally_friendly_goal_distance

        #Works out kickoff position and passes that variable onto kickoff function in routines
        x_position = int(agent.me.location.x * side(agent.team))
        if x_position == 2047 or x_position == 2048:
            kickoff_position = 'diagonal_right'
        elif x_position == -2047 or x_position == -2048:
            kickoff_position = 'diagonal_left'
        elif x_position == -255 or x_position == -256:
            kickoff_position = 'back_left'
        elif x_position == 255 or x_position == 256:
            kickoff_position = 'back_right'
        elif x_position == 0:
            kickoff_position = 'back_centre'
        else:
            kickoff_position = 'unknown'

        if x_position > agent.ball.location.x:
            side_of_ball = 'right'
        else:
            side_of_ball = 'left'

        #Shoots if onside and (closest to ball or ball within 4000 of foe goal and between -1250 and 1250 x or ball is within 3000 of own goal)
        if me_onside and (closest_to_ball or (distance_ball_foe_goal < 4000 and -1250 < agent.ball.location.x < 1250 and closest_ally_to_ball_distance > 3000) or distance_ball_friendly_goal < 3000):
            shooting = True
        else:
            shooting = False    

        #Leaves goal to hit ball if onside and (closest to ball or ball within 3000 of goal. Stays in goal if that is false and closest to goal and not close and offside (to not score own goals))
        if not(me_onside and (closest_to_ball or distance_ball_friendly_goal < 3000)) and closest_ally_friendly_goal and not(close and not me_onside):
            goalie = True
        else:
            goalie = False
        
        #Only go for kickoff if closest or joint closest and on left side
        if agent.kickoff_flag and (closest_to_ball or (joint_closest_to_ball and (kickoff_position == 'diagonal_left' or kickoff_position == 'back_left'))):
            go_for_kickoff = True
        else:
            go_for_kickoff = False

        # if agent.index == 0: 
        #     print(agent.me.orientation[2][2])
        #     print(me_onside2)
        #     print(distance_ball_friendly_goal)
        #     agent.debug_stack()
        #     print(shooting,goalie)
        #     print(closest_to_ball)
        #     print(distance_to_ball,closest_ally_to_ball_distance)
        #     print(close)
        #     print(me_onside)
        #     agent.line(agent.foe_goal.left_post,agent.foe_goal.right_post)
        #     print(Vector3(agent.ball.location))
        #     print(closest_ally_friendly_goal_distance,distance_to_friendly_goal)
        #     agent.line(agent.friend_goal.location, agent.ball.location, [255,255,255])
        #     my_point = agent.friend_goal.location + (my_goal_to_ball * my_distance)
        #     agent.line(my_point - Vector3(0,0,100), my_point + Vector3(0,0,500), [0,255,0])
        #     agent.line(Vector3(near_left_corner.x, near_left_corner.y, near_left_corner.z - 200), Vector3(near_left_corner.x, near_left_corner.y, near_left_corner.z + 200))
        #     agent.line(Vector3(near_right_corner.x, near_right_corner.y, near_right_corner.z - 200), Vector3(near_right_corner.x, near_right_corner.y, near_right_corner.z + 200))

        #Decision making code
        if len(agent.stack) < 1:
            if go_for_kickoff and joint_closest_to_ball and len(agent.friends) > 0:
                agent.send_quick_chat(QuickChats.CHAT_EVERYONE,QuickChats.Information_IGotIt)
            if go_for_kickoff:
                stack = 'kickoff'
                agent.push(kickoff(kickoff_position))
            elif goalie:
                stack = 'goalie'
                agent.push(goto_friendly_goal())
            elif shooting:
                stack = 'shooting'
                # if closest_ally_friendly_goal and distance_ball_friendly_goal < 2000:
                #     if side_of_ball == 'left':
                #         agent.push(short_shot(near_left_corner))
                #     else:
                #         agent.push(short_shot(near_right_corner))
                if len(shots["goal"]) > 0:
                    agent.push(shots["goal"][0])
                elif len(shots["upfield"]) > 0 and abs(agent.friend_goal.location.y - agent.ball.location.y) < 8490:
                    agent.push(shots["upfield"][0])
                else:  
                    agent.push(short_shot(agent.foe_goal.location))
            elif distance_ball_foe_goal < 4000 and -1250 < agent.ball.location.x < 1250 and closest_ally_to_ball_distance < 3000 and have_possession:
                stack = 'demoing'
                agent.push(demo_enemy_closest_ball)
            elif distance_ball_friendly_goal > 6000:
                if agent.me.boost < 20:
                    stack = 'getting boost'
                    agent.push(get_nearest_big_boost)
                else:
                    stack = 'going centre'
                    agent.push(go_centre)
            else:
                if not very_close:
                    if goalie:
                        stack = 'goalie'
                        agent.push(goto_friendly_goal())
                    else:
                        stack = 'going centre'
                        agent.push(go_centre)
                else:
                    stack = 'getting boost'
                    agent.push(get_nearest_big_boost)

        #Stack clearing code (decides when to clear stack and do something else)
        if not(stack == 'kickoff') and not(stack == 'shooting' and me_onside) and not(stack == 'getting boost' and agent.me.boost < 20):
            if go_for_kickoff:
                if stack != 'kickoff':
                    agent.clear()
            elif goalie:
                if stack != 'goalie':
                    agent.clear()
            elif shooting:
                if stack != 'shooting':
                    agent.clear()
            elif distance_ball_foe_goal < 3000 and -1250 < agent.ball.location.x < 1250 and closest_ally_to_ball_distance < 4000 and have_possession:
                if stack != 'demoing':
                    agent.clear()
            elif distance_ball_friendly_goal > 6000:
                if agent.me.boost < 20:
                    if stack != 'getting boost':
                        agent.clear()
                elif stack != 'going centre':
                    agent.clear()
            else:
                if not very_close:
                    if goalie:
                        if stack != 'goalie':
                            agent.clear()
                    elif stack != 'going centre':
                        agent.clear()
                elif stack != 'getting boost':
                    agent.clear()

        #Jumps if turtling
        if agent.me.velocity[0] == 0 and agent.me.orientation[2][2] < 0:
            agent.controller.jump = True


        #Boost if going centre and offside (getting back)
        if stack == 'going centre':
                if not me_onside2:
                    agent.controller.boost = True
                else:
                    agent.controller.boost = False

        # if agent.index == 0:
        #     print(stack)