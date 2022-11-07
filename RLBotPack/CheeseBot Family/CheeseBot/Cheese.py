from turtle import Vec2D
from tools import  *
from objects import *
from routines import *
from cutil.ctools import determine_shot, find_intercept_time
from cutil.croutines import *
from cutil.cutils import *
from cutil.control_panel import *
from math import atan2, pi
import math


#This file is for strategy

class ExampleBot(GoslingAgent):
    def init(self):
        self.shot = None
        self.shot_alignment = None
        self.foe_goal_shot = (self.foe_goal.left_post, self.foe_goal.right_post)
        self.__left_field = Vector3(7000 * -utils.side(self.team), (8000*-utils.side(self.team)), 0)
        self.__right_field = Vector3(7000 * utils.side(self.team), (8000*-utils.side(self.team)), 0)
        self.upfield_shot = (self.__left_field, self.__right_field)
        self.anti_target = (self.friend_goal.right_post, self.friend_goal.left_post)
        self.last_touch_car_name = None
        self.last_touch_time = -1.0
        self.should_clear_stack = False
        self.ball_going_into_our_net = False
        self.ball_going_into_danger_zone = False
        self.pull_back = False
        self.closest_to_our_goal = False
        self.left_side_shot = (self.friend_goal.left_post + Vector3(4200 * -utils.side(self.team), (500*utils.side(self.team)), 0), self.foe_goal.left_post)
        self.right_side_shot = (self.friend_goal.right_post + Vector3(4200 * utils.side(self.team), (500*utils.side(self.team)), 0), self.foe_goal.right_post)
        self.closest_onside_to_ball = False
        self.first_routine_pushed_after_kickoff = False
        self.push_reposition = True
        self.offense_defense_switch = 0
        self.current_shot_condition = None


    def aboutToCrashIntoOneAnother(self):
        pass


    def process(self):
        self.closest_to_our_goal = check_if_closest_to_goal(self)
        self.offense_defense_switch = ones_defense_offense_switch_test(self)

        self.closest_onside_to_ball = True
        if align(self.me.location, self.ball.location, self.foe_goal.location) < 0:
            self.closest_onside_to_ball = False
        else:
            my_distance_to_ball = (self.me.location - self.ball.location).flatten().magnitude()
            for car in self.friends:
                if (car.location - self.ball.location).flatten().magnitude() < my_distance_to_ball and align(car.location, self.ball.location, self.foe_goal.location) > 0:
                    self.closest_onside_to_ball = False

        if len(self.friends) > 0:
            average_teammate_y = 0
            for car in self.friends:
                average_teammate_y += car.location.y

            average_teammate_y = average_teammate_y / len(self.friends)
            self.pull_back = -utils.side(self.team) * average_teammate_y > -utils.side(self.team) * MAIN_PULL_BACK_AVERAGE_TEAMMATE_Y_MAX or self.closest_to_our_goal
        else:
            self.pull_back = self.offense_defense_switch < 0

        self.ball_going_into_our_net = ball_going_into_our_net(self)
        self.ball_going_into_danger_zone = ball_going_into_danger_zone(self)

        if (self.odd_tick == 0) and not self.shooting or self.ball_going_into_our_net:
            self.shot = determine_shot(self, min_shot_speed=MAIN_MIN_SHOT_SPEED if not self.ball_going_into_our_net or not self.ball_going_into_danger_zone else 0, max_shot_time=MAIN_MAX_SHOT_TIME_DEFAULT if not self.ball_going_into_our_net else MAIN_MAX_SHOT_TIME_PANIC)


            if self.shot is not None:
                self.shot_alignment = align(self.me.location, self.shot.ball_location, self.foe_goal.location)
            else:
                self.shot_alignment = -1

        if self.kickoff_flag:
            self.first_routine_pushed_after_kickoff = False

        if not self.shooting:
            self.current_shot_condition = None

    def get_nearest_boost(self):
        ball_velocity = self.ball.velocity if MAIN_GET_BOOST_CONSIDER_BALL_VELOCITY else Vector3(0.0, 0.0, 0.0)

        boosts = tuple(boost for boost in self.boosts if boost.active and boost.large and
                       (-side(self.team) * boost.location.y) - ((-side(self.team) * self.ball.location.y + ball_velocity.y)) < MAIN_GET_BOOST_MAX_Y_DIST_IN_FRONT_OF_BALL)

        if len(boosts) > 0:
            closest_boost = min(boosts, key=lambda boost: boost.location.dist(self.me.location))
            return closest_boost
        else:
            return None

    def should_go_for_shot(self):
        if len(self.friends) < 1 or DEBUG_ALWAYS_GO_FOR_SHOT:
            return True
        else:
            slices = get_slices(self, 6)

            time_limit = 99999

            proactivity_bonus = MAIN_SHOULD_GO_FOR_SHOT_PROACTIVITY_BONUS

            our_intercept = None
            our_intercept_time, our_intercept_location = find_intercept_time(self.me, self, ball_prediction_slices = slices, return_intercept_location_too=True)
            if our_intercept_time is not None:
                our_alignment = align(self.me.location, our_intercept_location, self.foe_goal.location)
                our_intercept = [our_intercept_time, our_intercept_location, self.me.location, our_alignment]
                time_limit = our_intercept[0] - self.time

            teammate_intercepts = []


            for friend in self.friends:
                intercept_time, intercept_location = find_intercept_time(friend, self, ball_prediction_slices = slices, return_intercept_location_too=True)
                if intercept_time is not None:
                    friend_alignment = align(friend.location, intercept_location, self.foe_goal.location)
                    friend_velocity = friend.velocity
                    teammate_intercepts.append([intercept_time + proactivity_bonus, intercept_location, friend.location, friend_alignment, friend_velocity])
                    if intercept_time - self.time < time_limit:
                        time_limit = intercept_time - self.time

            if our_intercept is not None:
                teammate_intercepts.append(our_intercept)

            good_intercepts = [intercept for intercept in teammate_intercepts if intercept[3] >= MAIN_SHOULD_GO_FOR_SHOT_MIN_ALIGN_FOR_GOOD_INTERCEPT] #was 0.0

            if len(good_intercepts) > 0:
                best_intercept = min(good_intercepts, key=lambda intercept: intercept[0])

            elif len(teammate_intercepts) > 0:
                best_intercept = min(teammate_intercepts, key=lambda intercept: intercept[0])

            else:
                best_intercept = None


            if best_intercept is not None and our_intercept is not None:
                if best_intercept[0] == our_intercept[0]:
                    return True
                else:
                   
                    car_to_intercept = best_intercept[1] - best_intercept[2]
                    if abs(best_intercept[4].angle(car_to_intercept)) < math.pi/3:
                        return False
                    else:
                        return True

            else:
                return False


    def run(agent):
        targets = {"goal": (agent.foe_goal.left_post, agent.foe_goal.right_post), "not_my_net": (agent.friend_goal.right_post, agent.friend_goal.left_post)}
        shots = find_hits(agent, targets)
        controls = SimpleControllerState()
        agent.process()
        friends = len(agent.friends)
        friends_distance_to_ball = []

        if agent.ball.latest_touched_player_name != agent.last_touch_car_name or agent.ball.latest_touched_time != agent.last_touch_time:
            if agent.ball.latest_touched_player_name != agent.me.name:
                pass

            agent.last_touch_car_name = agent.ball.latest_touched_player_name
            agent.last_touch_time = agent.ball.latest_touched_time

            agent.should_clear_stack = True

        if agent.should_clear_stack and not agent.me.airborne:
            if not agent.is_clear():
                if "shot" in agent.stack[0].__class__.__name__:
                    pass
                else:
                    agent.clear()
                    agent.should_clear_stack = False
                    agent.shot = determine_shot(agent, min_shot_speed=MAIN_MIN_SHOT_SPEED if not agent.ball_going_into_our_net or not agent.ball_going_into_danger_zone else 0, max_shot_time=MAIN_MAX_SHOT_TIME_DEFAULT if not agent.ball_going_into_our_net else MAIN_MAX_SHOT_TIME_PANIC)

            else:
                agent.clear()
                agent.should_clear_stack = False
                agent.shot = determine_shot(agent, min_shot_speed=MAIN_MIN_SHOT_SPEED if not agent.ball_going_into_our_net or not agent.ball_going_into_danger_zone else 0, max_shot_time=MAIN_MAX_SHOT_TIME_DEFAULT if not agent.ball_going_into_our_net else MAIN_MAX_SHOT_TIME_PANIC)

        if not agent.is_clear():
            if agent.stack[0].__class__.__name__ is "goto_boost" and (agent.ball_going_into_our_net or agent.ball_going_into_danger_zone) and not agent.me.airborne:
                agent.clear()

        if not agent.is_clear() and agent.shot is not None:
            if agent.stack[0].__class__.__name__ is "reposition" and agent.shot is not None and not (agent.me.airborne or agent.me.location.z > 300):
                if agent.should_go_for_shot():
                    agent.clear()
                    agent.push(agent.shot)

            if "shot" in agent.stack[0].__class__.__name__:
                if agent.current_shot_condition != agent.offense_defense_switch:
                    if agent.should_go_for_shot():
                        if len(agent.friends) != 0:
                            friends = len(agent.friends)
                            for i in range(friends):
                                friends_distance_to_ball = []
                                friends_distance_to_ball.append(agent.ball.location.dist(agent.friends[i-1].location))
                                my_distance_to_ball = agent.ball.location.dist(agent.me.location)
                                if min(friends_distance_to_ball) > my_distance_to_ball or min(friends_distance_to_ball) == my_distance_to_ball:
                                    agent.clear()
                                    agent.push(agent.shot)
                                    agent.current_shot_condition = agent.offense_defense_switch
                                else:
                                    agent.pop()
                                    agent.push(goto_goal())
                                    if agent.me.location.dist(agent.ball.location) < 2000 or agent.me.location.dist(agent.friend_goal.location) < 1000:
                                        if agent.is_clear():
                                            if len(shots["goal"]) > 0:
                                                agent.push(shots["goal"][0])
                                            elif len(shots["not_my_net"]) > 0:
                                                agent.push(shots["not_my_net"][0])
                                            else:
                                                agent.push(short_shot())

                        else:
                            agent.clear()
                            agent.push(agent.shot)

        if agent.is_clear():
            if agent.kickoff_flag:
                controls.throttle = 0
                controls.boost = False
                if len(agent.friends) == 0:
                    agent.push(cheese_kickoff())

                else:
                    friends = len(agent.friends)
                    for i in range(friends):
                        friends_distance_to_ball = []
                        friends_distance_to_ball.append(agent.ball.location.dist(agent.friends[i].location))
                        my_distance_to_ball = agent.ball.location.dist(agent.me.location)
                        if min(friends_distance_to_ball) >= my_distance_to_ball:
                            if min(friends_distance_to_ball) == my_distance_to_ball:
                                if agent.team == 0 and agent.me.location.x > 0:
                                    agent.push(cheese_kickoff())
                                if agent.team == 1 and agent.me.location.x < 0:
                                    agent.push(cheese_kickoff())
                            else:
                                agent.push(cheese_kickoff())
                        else:
                            nearest_boost = agent.get_nearest_boost()
                            if nearest_boost is not None:
                                agent.push(goto_boost(nearest_boost))

                        return


        if agent.is_clear():

            if agent.me.airborne:
                agent.push(recovery())
                return

            nearest_boost = agent.get_nearest_boost()
            if nearest_boost is not None and agent.me.boost < 25:
                if agent.me.boost < MAIN_GET_BOOST_MIN_VALUE and not (agent.ball_going_into_our_net or agent.ball_going_into_danger_zone) and (2 > agent.offense_defense_switch >= 0 or (nearest_boost.location - agent.me.location).magnitude() < 900):
                    agent.push(goto_boost(nearest_boost))
                    return


            if agent.shot is not None and not agent.shooting and not (agent.me.airborne or agent.me.location.z > 200):
                if agent.should_go_for_shot():
                    agent.push(agent.shot)
                    agent.current_shot_condition = agent.offense_defense_switch
                    return


            agent.push(reposition(desired_distance = MAIN_REPOSITION_DISTANCE_DEFAULT if not agent.pull_back else MAIN_REPOSITION_DISTANCE_PULL_BACK, ball_going_into_our_net=agent.ball_going_into_our_net or agent.ball_going_into_danger_zone, offense_defense=agent.offense_defense_switch)) #2000/3000 default
            agent.push_reposition = False
            return
