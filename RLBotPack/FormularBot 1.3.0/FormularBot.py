from tools import  *
from objects import *
from routines import *


class FormularBot(GoslingAgent):
    def run(agent):
        global stack
        relative_target = agent.ball.location - agent.friend_goal.location
        distance_ball_friendly_goal = relative_target.magnitude()

        if len(agent.foes) > 0:
            enemies = agent.foes
            closest = enemies[0]
            closest_distance = (enemies[0].location - agent.ball.location).magnitude()
            x = 0
            y = 0
            for item in enemies:
                item_distance = (item.location - agent.ball.location).magnitude()
                if item_distance < closest_distance:
                    closest = item
                    closest_distance = item_distance
                    y = x
                x =+ 1

        my_goal_to_ball,my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
        goal_to_me = agent.me.location - agent.friend_goal.location
        my_distance = my_goal_to_ball.dot(goal_to_me)
        me_onside = my_distance + 80 < my_ball_distance

        close = (agent.me.location - agent.ball.location).magnitude() < 1000
        very_close = (agent.me.location - agent.ball.location).magnitude() < 500
        distance_to_ball = (agent.me.location - agent.ball.location).flatten().magnitude()
        distance_to_friendly_goal = (agent.me.location - agent.friend_goal.location).flatten().magnitude()

        relative_target = agent.ball.location - agent.friend_goal.location
        distance_ball_friendly_goal = relative_target.magnitude()

        left_field = Vector3(4200*-side(agent.team),agent.ball.location.y + 1000*-side(agent.team),0)
        right_field = Vector3(4200*side(agent.team),agent.ball.location.y + 1000*-side(agent.team),0)
        targets = {"goal": (agent.foe_goal.left_post,agent.foe_goal.right_post), "upfield": (left_field,right_field)}
        shots = find_hits(agent,targets)

        allies = agent.friends
        cally_to_ball = "none"
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

        closest_to_ball = distance_to_ball <= closest_ally_to_ball_distance
        closest_to_friendly_goal = distance_to_friendly_goal <= closest_ally_friendly_goal_distance

        

        if me_onside and (closest_to_ball or (agent.ball.location.y * side(agent.team) * -1 > 2500 * side(agent.team) * -1 and agent.ball.location.x < 1500 and agent.ball.location.x > -1500)):
            shooting = True
        else:
            shooting = False    

        if not(me_onside and closest_to_ball) and closest_to_friendly_goal and len(agent.friends) > 0 and not(close and not me_onside):
            goalie = True
        else:
            goalie = False

        
        if len(agent.stack) < 1:
            if agent.kickoff_flag and closest_to_ball:
                stack = 'kickoff'
                agent.push(kickoff(int(agent.me.location.x * side(agent.team))))
            elif goalie:
                stack = 'goalie'
                agent.push(goto_friendly_goal)
            elif shooting:
                stack = 'shooting'
                if len(shots["goal"]) > 0:
                    agent.push(shots["goal"][0])
                    #send(random.choice(chat_ids))
                elif len(shots["upfield"]) > 0 and abs(agent.friend_goal.location.y - agent.ball.location.y) < 8490:
                    agent.push(shots["upfield"][0])
                else:  
                    agent.push(short_shot(agent.foe_goal.location))
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
                        agent.push(goto_friendly_goal)
                    else:
                        stack = 'going centre'
                        agent.push(go_centre)
                else:
                    stack = 'getting boost'
                    agent.push(get_nearest_big_boost)

        if not stack == kickoff and not(stack == 'shooting' and (close and (agent.me.airborne or me_onside or agent.me.location.y * side(agent.team > 2500 * -side(agent.team))))):
    
            if agent.kickoff_flag and closest_to_ball:
                if stack != 'kickoff':
                    agent.clear()
            elif goalie:
                if stack != 'goalie':
                    agent.clear()
            elif shooting:
                if stack != 'shooting':
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


        if agent.me.velocity[0] == 0 and int(agent.me.location.z) == 40:
            agent.controller.jump = True

        if stack == 'going centre':
                if not me_onside:
                    agent.controller.boost = True
                else:
                    agent.controller.boost = False