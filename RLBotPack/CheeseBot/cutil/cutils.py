import utils
from objects import Vector3
import math

def align(point_location, ball_location, goal_location):
    position_to_ball = (ball_location - point_location).normalize().flatten()
    ball_to_goal_center = (goal_location - ball_location).normalize().flatten()
    ball_to_goal_left_post = (goal_location + Vector3(800, 0, 0) - ball_location).normalize().flatten()
    ball_to_goal_right_post = (goal_location + Vector3(-800, 0, 0) - ball_location).normalize().flatten()
    best_case = min(position_to_ball.dot(ball_to_goal_center), position_to_ball.dot(ball_to_goal_right_post), position_to_ball.dot(ball_to_goal_left_post))
    return best_case

def align_goalposts(point_location, ball_location, left_post, right_post):
    position_to_ball = position_to_ball = (ball_location - point_location).normalize().flatten()
    ball_to_goal_left_post = (left_post - ball_location).normalize().flatten()
    ball_to_goal_right_post = (right_post - ball_location).normalize().flatten()
    ball_to_goal_center = (utils.lerp(left_post, right_post, 0.5) - ball_location).normalize().flatten()
    best_case = min(position_to_ball.dot(ball_to_goal_center), position_to_ball.dot(ball_to_goal_right_post), position_to_ball.dot(ball_to_goal_left_post))
    return best_case

def cap(x, low, high):
    # caps/clamps a number between a low and high value
    return low if x < low else (high if x > high else x)

def closest_point(point, target_points):
    #print("Comparison Point: " + str(point))
    #print("Points to Compare: " + str(target_points))
    closest_point = None
    closest_distance = 99999
    for target_point in target_points:
        if closest_point is None:
            closest_point = target_point
            closest_distance = (target_point - point).flatten().magnitude()
        else:
            current_distance = (target_point - point).flatten().magnitude()
            if current_distance < closest_distance:
                closest_point = target_point
                closest_distance = current_distance
    #print("Point being returned: " + str(closest_point))
    return closest_point

def furthest_point(point, target_points):
    #print("Comparison Point: " + str(point))
    #print("Points to Compare: " + str(target_points))
    furthest_point = None
    furthest_distance = -1
    for target_point in target_points:
        if closest_point is None:
            furthest_point = target_point
            furthest_distance = (target_point - point).flatten().magnitude()
        else:
            current_distance = (target_point - point).flatten().magnitude()
            if current_distance > furthest_distance:
                furthest_point = target_point
                furthest_distance = current_distance

    #print("Point being returned: " + str(furthest_point))
    return furthest_point

def get_back_post_vector(agent, future_ball_location = None):
    #returns the location of our goal's back post.
    y = 4400 * utils.side(agent.team)
    z = 0
    ball_location = future_ball_location if future_ball_location is not None else agent.ball.location
    if ball_location[0] > 0:
        x = -850
    else:
        x = +850
    back_post = Vector3(x, y, z)
    return back_post

def get_closest_post_vector(agent, future_ball_location = None):
    y = 4400 * utils.side(agent.team)
    z = 0
    closest_post = closest_point(agent.me.location, [agent.friend_goal.left_post, agent.friend_goal.right_post])
    return_value = Vector3(closest_post.x, y, z)
    return return_value