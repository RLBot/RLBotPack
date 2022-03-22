from routines import *
from cutil.ctools import *
from cutil.cutils import *

class reposition:
    def __init__(self, desired_distance = 3000, ball_going_into_our_net = False, offense_defense = 0):
        self.goto = goto(Vector3(0, 0, 0))
        self.target = None
        self.intercept_location = None
        self.intercept_time = None
        self.direction_vector = None
        self.desired_distance = desired_distance
        self.unmodded_reposition_target = None
        self.returning_to_goal = False
        self.ball_going_into_our_net = ball_going_into_our_net
        self.offense_defense = offense_defense

    def run(self, agent):
        if self.target is None:
            self.find_target(agent)
        if self.target.flat_dist(agent.me.location) < 100:
            self.target = self.intercept_location
            self.goto.arrival_time = self.intercept_time
        if self.returning_to_goal and self.offense_defense < 0:
            self.goto.urgent = True
            self.goto.slow_down = True
        if agent.time > self.intercept_time:
            agent.pop()

        car_to_final_target = (self.target - agent.me.location).flatten()
        distance_remaining = car_to_final_target.magnitude()

        self.goto.target = self.target
        self.goto.vector = self.direction_vector
        #print(self.goto.slow)
        agent.line(self.intercept_location - Vector3(0,0,500),self.intercept_location + Vector3(0,0,500),[255,0,0])
        agent.line(self.unmodded_reposition_target - Vector3(0, 0, 500), self.unmodded_reposition_target + Vector3(0,0,500), [0, 255, 0])

        self.goto.run(agent)

    def find_target(self, agent):
        slices = get_slices(agent, 6)

        earliest_intercept, intercept_vector_location = find_intercept_time_with_detour(agent.me, agent, return_intercept_location_too=True, ball_prediction_slices=slices, time_to_subtract=0.5)
        if earliest_intercept is None:
            intercept_location = slices[-1].physics.location
            earliest_intercept = slices[-1].game_seconds
            intercept_vector_location = Vector3(intercept_location.x, intercept_location.y, intercept_location.z)


        my_goal_to_ball = (intercept_vector_location - agent.friend_goal.location).flatten().normalize()
        ball_to_their_goal = (agent.foe_goal.location - intercept_vector_location).flatten().normalize()
        car_to_ball, car_to_ball_distance = (intercept_vector_location - agent.me.location).flatten().normalize(True)
        ball_to_goal_magnitude = (intercept_vector_location - agent.friend_goal.location).flatten().magnitude()

        if agent.closest_onside_to_ball and not agent.pull_back and len(agent.friends) >= 1 or (len(agent.friends) == 0 and self.offense_defense == 1):
            direction_vector = lerp(-ball_to_their_goal, -my_goal_to_ball, 0.75)
        else:
            direction_vector = -my_goal_to_ball

        reposition_target = intercept_vector_location.flatten() + direction_vector * min(self.desired_distance, ball_to_goal_magnitude - 150)

        # print("Intercept location: " + str(intercept_vector_location))
        # print("Reposition target: " + str(reposition_target))
        reposition_target.x = cap(reposition_target.x, -3796, 3796)
        reposition_target.y = cap(reposition_target.y, -5120, 5120)
        final_target = reposition_target
        self.unmodded_reposition_target = reposition_target

        # near_goal = abs(agent.me.location[1] - agent.friend_goal.location[1]) < 3000
        # side_shift = 400 if near_goal else 1800
        # points = [reposition_target + Vector3(side_shift, 0, 0), reposition_target - Vector3(side_shift, 0, 0)]
        # #print("Points: " + str(points))
        # final_target = closest_point(reposition_target, points) if near_goal else furthest_point(reposition_target, points)
        # if abs(intercept_vector_location[0]) < 1000 or car_to_ball_distance < 1000:
        #     final_target = closest_point(agent.me.location, points)
        # #print("Final Target: " + str(final_target))
        #
        if (final_target.y * side(agent.team)) > 4000 or self.ball_going_into_our_net:
            final_target = agent.friend_goal.location
            #final_target.y = 4400 * utils.side(agent.team)
            self.returning_to_goal = True
        else:
            final_target.x = cap(final_target.x, -3400, 3400)
            final_target.y = cap(final_target.y, -4800, 4800)

        car_to_final_target = (final_target - agent.me.location).flatten()
        final_target_to_intercept_direction = -(final_target - intercept_vector_location).flatten().normalize()




        self.target = final_target
        if self.offense_defense > -1:
            self.direction_vector = final_target_to_intercept_direction
        self.intercept_location = intercept_vector_location.flatten()
        self.intercept_time = earliest_intercept