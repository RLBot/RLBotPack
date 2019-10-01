import math
import time
import numpy as np
import bot_functions

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket


# malicious code, beware :p EXTERMINATE EXTERMINATE EXTERMENATE

class SkyBot(BaseAgent):
    def initialize_agent(self):
        self.controller = SimpleControllerState()
        self.num_cars = 0
        # Controller inputs
        self.controller.throttle = 0
        self.controller.steer = 0
        self.controller.pitch = 0
        self.controller.yaw = 0
        self.controller.roll = 0
        self.controller.boost = False
        self.controller.jump = False
        self.controller.handbrake = False
        # Game values
        self.bot_loc_x = 0
        self.bot_loc_y = 0
        self.bot_loc_z = 0
        self.bot_speed_x = 0
        self.bot_speed_y = 0
        self.bot_speed_z = 0
        self.bot_rot_yaw = 0
        self.bot_rot_roll = 0
        self.bot_rot_pitch = 0
        self.bot_jumped = False
        self.bot_doublejumped = False
        self.bot_ground = False
        self.bot_sonic = False
        self.bot_dodge = False
        self.bot_boost = 0
        self.bot_max_speed = [1410, 2300]  # normal, boost
        self.bot_boost_to_max_speed = [27, 57, 30]  # to normal, to boost, from normal to boost
        self.ball_loc_x = 0
        self.ball_loc_y = 0
        self.ball_loc_z = 0
        self.ball_speed_x = 0
        self.ball_speed_y = 0
        self.ball_speed_z = 0
        self.ball_ang_speed_x = 0
        self.ball_ang_speed_y = 0
        self.ball_ang_speed_z = 0
        self.ball_lt_x = 0
        self.ball_lt_y = 0
        self.ball_lt_z = 0
        self.ball_lt_time = 0
        self.game_time = 0
        self.game_ball_touched = False
        # game values converted
        self.bot_yaw = 0
        self.bot_pitch = 0
        self.bot_roll = 0
        self.angle_front_to_target = 0
        self.angle_car_ball = 0
        # custom values
        self.angle_car_ball = 0
        self.distance_car_ball = 0
        self.bot_speed_linear = 0
        self.ball_initial_speed_z = 0
        self.ball_initial_pos_z = 0
        self.ball_test_for_start = False

        self.ttt = 0.00
        self.lt_time = 0.00
        # ([self.game_time],[[self.ball_loc_x],[self.ball_loc_y],[self.ball_loc_z]],[[self.ball_speed_x],[self.ball_speed_y],[self.ball_speed_z]],[[self.ball_ang_speed_x],[self.ball_ang_speed_y],[self.ball_ang_speed_z]])
        self.prediction = [[], []]
        self.printed = False

        # self.predicted_loc=[[0,0,0],[[0,0,0],[0,0,0],[0,0,0]],[0,0,0]]
        self.predicted_loc = [[0, 0, 0], [[0, 0, 0], [0, 0, 0], [0, 0, 0]], [0], [[0, 0, 0], [0, 0, 0], [0, 0, 0]]]
        self.game_time_lst = []
        self.ball_speed_x_lst = []
        self.ball_speed_y_lst = []
        self.ball_speed_z_lst = []
        self.ball_ang_speed_x_lst = []
        self.ball_ang_speed_y_lst = []
        self.ball_ang_speed_z_lst = []
        self.ball_loc_x_lst = []
        self.ball_loc_y_lst = []
        self.ball_loc_z_lst = []

        self.bounce_n = 0
        self.hit = False
        self.realtime = [[], []]
        self.time_to_hit = 1
        self.jump_time_end = 0
        self.flick_time = 0
        self.stop_flick = False
        self.last_predict = 0

    def get_values(self, values):
        self.controller.boost = False

        if self.jump_time_end < self.game_time:
            self.controller.jump = False

        if self.stop_flick:
            self.controller.pitch = 0
            self.controller.roll = 0
            self.flick_time = 0
            self.stop_flick = False
            # print('flip stopped')

        if self.flick_time < self.game_time and self.flick_time != 0:
            self.controller.jump = True
            self.stop_flick = True
            # print('stopping flick')

        # Update game data variables
        self.bot_team = values.game_cars[self.index].team

        self.bot_loc = values.game_cars[self.index].physics.location
        self.bot_rot = values.game_cars[self.index].physics.rotation
        self.ball_loc = values.game_ball.physics.location
        self.ball_lt = values.game_ball.latest_touch
        # get game values
        self.bot_loc_x = values.game_cars[self.index].physics.location.x
        self.bot_loc_y = values.game_cars[self.index].physics.location.y
        self.bot_loc_z = values.game_cars[self.index].physics.location.z
        self.bot_speed_x = values.game_cars[self.index].physics.velocity.x
        self.bot_speed_y = values.game_cars[self.index].physics.velocity.y
        self.bot_speed_z = values.game_cars[self.index].physics.velocity.z
        self.bot_jumped = values.game_cars[self.index].jumped
        self.bot_doublejumped = values.game_cars[self.index].double_jumped
        self.bot_sonic = values.game_cars[self.index].is_super_sonic
        self.bot_ground = values.game_cars[self.index].has_wheel_contact
        self.bot_boost = values.game_cars[self.index].boost

        self.ball_loc_x = values.game_ball.physics.location.x
        self.ball_loc_x_lst += [self.ball_loc_x]
        self.ball_loc_y = values.game_ball.physics.location.y
        self.ball_loc_y_lst += [self.ball_loc_y]
        self.ball_loc_z = values.game_ball.physics.location.z
        self.ball_loc_z_lst += [self.ball_loc_z]
        self.ball_speed_x = values.game_ball.physics.velocity.x
        self.ball_speed_x_lst += [self.ball_speed_x]
        self.ball_speed_y = values.game_ball.physics.velocity.y
        self.ball_speed_y_lst += [self.ball_speed_y]
        self.ball_speed_z = values.game_ball.physics.velocity.z
        self.ball_speed_z_lst += [self.ball_speed_z]
        self.ball_ang_speed_x = values.game_ball.physics.angular_velocity.x
        self.ball_ang_speed_x_lst += [self.ball_ang_speed_x]
        self.ball_ang_speed_y = values.game_ball.physics.angular_velocity.y
        self.ball_ang_speed_y_lst += [self.ball_ang_speed_y]
        self.ball_ang_speed_z = values.game_ball.physics.angular_velocity.z
        self.ball_ang_speed_z_lst += [self.ball_ang_speed_z]
        self.ball_lt_x = values.game_ball.latest_touch.hit_location.x
        self.ball_lt_y = values.game_ball.latest_touch.hit_location.y
        self.ball_lt_z = values.game_ball.latest_touch.hit_location.z
        self.ball_lt_time = values.game_ball.latest_touch.time_seconds
        self.ball_lt_normal_x = values.game_ball.latest_touch.hit_normal.x
        self.ball_lt_normal_y = values.game_ball.latest_touch.hit_normal.y
        self.ball_lt_normal_z = values.game_ball.latest_touch.hit_normal.z

        self.game_time = values.game_info.seconds_elapsed
        self.game_time_lst += [self.game_time]
        self.game_time_left = values.game_info.game_time_remaining
        self.game_overtime = values.game_info.is_overtime
        self.game_active = values.game_info.is_round_active
        self.game_ended = values.game_info.is_match_ended
        # self.game_ball_touched = values.game_info.is_kickoff_pause
        if values.game_info.is_kickoff_pause:
            self.game_ball_touched = False
        else:
            self.game_ball_touched = True

        self.num_cars = values.num_cars

        # get custom values
        self.realime = [self.game_time_lst, [[self.ball_loc_x_lst], [self.ball_loc_y_lst], [self.ball_loc_z_lst]]]
        self.angle_car_ball = math.degrees(
            math.atan2(self.ball_loc_y - self.bot_loc.y, self.ball_loc_x - self.bot_loc.x)) - self.bot_rot_yaw
        self.distance_car_ball = self.distance(self.bot_loc_x, self.bot_loc_y, self.bot_loc_z, self.ball_loc_x,
                                               self.ball_loc_y, self.ball_loc_z) - 93
        self.bot_speed_linear = self.distance(self.bot_speed_x, self.bot_speed_y, self.bot_speed_z, 0, 0, 0)

        # Convert car's yaw, pitch and roll and convert from Unreal Rotator units to degrees
        self.bot_rot_yaw = abs(self.bot_rot.yaw) / (2 * math.pi) * 360
        if self.bot_rot.yaw < 0:
            self.bot_rot_yaw *= -1
        self.bot_rot_pitch = abs(self.bot_rot.pitch) / (2 * math.pi) * 360
        if self.bot_rot.pitch < 0:
            self.bot_rot_pitch *= -1
        self.bot_rot_roll = abs(self.bot_rot.roll) / (2 * math.pi) * 360
        if self.bot_rot.roll < 0:
            self.bot_rot_roll *= -1

    def distance(self, x1, y1, z1, x2, y2, z2):
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
        return distance

    def aim(self, target_x, target_y, speed_needed=0):
        self.renderer.begin_rendering('aim')
        if self.bot_team == 0:
            color = self.renderer.create_color(255, 0, 0, 255)
        else:
            color = self.renderer.create_color(255, 255, 0, 0)
        self.renderer.draw_line_3d((target_x, target_y, 0), (target_x, target_y, 200), color)
        self.renderer.end_rendering()

        self.controller.throttle = 1
        self.distance_to_target = self.distance(self.bot_loc_x, self.bot_loc_y, 0, target_x, target_y, 0)
        angle_between_bot_and_target = math.degrees(math.atan2(target_y - self.bot_loc_y, target_x - self.bot_loc_x))
        self.angle_front_to_target = angle_between_bot_and_target - self.bot_rot_yaw
        # Correct the values
        if self.angle_front_to_target < -180:
            self.angle_front_to_target += 360
        if self.angle_front_to_target > 180:
            self.angle_front_to_target -= 360

        if self.angle_front_to_target < -10:
            # If the target is more than 10 degrees right from the centre, steer left
            self.controller.steer = -1
        elif self.angle_front_to_target > 10:
            # If the target is more than 10 degrees left from the centre, steer right
            self.controller.steer = 1
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controller.steer = self.angle_front_to_target / 10

        if -3 < self.angle_front_to_target < 3 and not self.bot_sonic:
            self.controller.boost = True
        else:
            self.controller.boost = False
        if abs(self.angle_front_to_target) > 100:
            self.controller.handbrake = 1
        else:
            self.controller.handbrake = 0
        if (self.bot_team == 0 and self.bot_loc_y < -5000) or (self.bot_team == 1 and self.bot_loc_y > 5000):
            # Blue team's goal is located at (0, -5000)
            # Orange team's goal is located at (0, 5000)
            self.controller.handbrake = 0

        if speed_needed == self.bot_max_speed[1] and self.bot_boost == 0 and abs(
                self.angle_front_to_target) < 3 and self.distance_to_target > 3000:
            self.flick(jump_timeout=0.05, flick_timeout=0.1)
            print(4)

        if self.game_state == 'kickoff' and self.distance_to_target < 3000 and self.bot_boost <= 15: # TODO : fix straight kickoff to enter goal
            self.flick(jump_timeout=0.05, flick_timeout=0.1)
            print(5)

        if speed_needed != 0:
            if speed_needed > self.bot_max_speed[0]:
                self.controller.throttle = 1
                self.controller.boost = 1
            elif self.bot_speed_linear < speed_needed:
                self.controller.throttle = 1
                self.controller.boost = 0
                if self.distance_to_target < 20:
                    self.controller.throttle = self.distance_to_target / 20
        if speed_needed < self.bot_speed_linear:
            self.controller.throttle = -1
            self.controller.boost = 0
            if self.distance_to_target < 20:
                self.controller.throttle = -self.distance_to_target / 20
            if self.distance_to_target < 10:
                self.controller.throttle = -self.distance_to_target / 10
        if self.bot_sonic:
            self.controller.boost = 0

    def was_hit(self):
        if len(self.game_time_lst) > 3:
            if self.game_ball_touched and self.game_time_lst[-3] == self.ball_lt_time:
                self.hit = True
            else:
                self.hit = False
        else:
            self.hit = False

    def predict(self, force_refresh=False):
        if self.time_to_hit < 0.5:
            force_refresh = True
        if self.hit or force_refresh:
            data_loc_speed = ([self.game_time],
                              [[self.ball_loc_x], [self.ball_loc_y], [self.ball_loc_z]],
                              [[self.ball_speed_x], [self.ball_speed_y], [self.ball_speed_z]],
                              [[self.ball_ang_speed_x], [self.ball_ang_speed_y], [self.ball_ang_speed_z]])

            self.predicted_loc = bot_functions.ball_path_predict(data_loc_speed)
            # self.predicted_loc=
            # [time_l,
            # [predic_loc_x_t, predic_loc_y_t, predic_loc_z_t]
            # ground_t,
            # [ground_loc_x, ground_loc_y, ground_loc_z]
            # goal_time,
            # [loc_x, loc_y, loc_z]]
            self.bounce_n = 0
            points = 0
            line_multiplier = 20
            self.renderer.begin_rendering('path')
            while points < len(self.predicted_loc[0]) - line_multiplier:
                self.renderer.draw_line_3d((self.predicted_loc[1][0][points],
                                            self.predicted_loc[1][1][points], self.predicted_loc[1][2][points]),
                                           (self.predicted_loc[1][0][points + line_multiplier],
                                            self.predicted_loc[1][1][points + line_multiplier],
                                            self.predicted_loc[1][2][points + line_multiplier]),
                                           self.renderer.create_color(255, 0, 0, 0))
                points = points + line_multiplier
            self.renderer.end_rendering()
            # redo = False
            # if not (self.predicted_loc[2][0] + 2/10 > self.last_predict and self.last_predict > self.predicted_loc[2][0] - 2/10):
            #     redo = True
            # print(redo)
            # redo = True
            # #print(self.last_predict)
            # #print(self.predicted_loc[2][0])
            # self.last_predict = self.predicted_loc[2][0]
            # if redo:
            #     self.renderer.begin_rendering('path')
            #     while self.predicted_loc[0][points] < self.predicted_loc[2][0]:
            #         self.renderer.draw_line_3d((self.predicted_loc[1][0][points],
            #             self.predicted_loc[1][1][points], self.predicted_loc[1][2][points]),
            #             (self.predicted_loc[1][0][points+line_multiplier], self.predicted_loc[1][1][points+line_multiplier],
            #             self.predicted_loc[1][2][points+line_multiplier]), self.renderer.create_color(255, 0, 0, 0))
            #         points = points+line_multiplier
            #     self.renderer.end_rendering()

    def time_to_impact(self):
        if (self.bounce_n + 1) < len(self.predicted_loc[2]) > 0:
            if self.predicted_loc[2][self.bounce_n] < self.game_time:
                self.bounce_n += 1
            self.time_to_hit = self.predicted_loc[2][self.bounce_n] - self.game_time
            print('hit {} in {} seconds'.format(self.bounce_n, round(self.time_to_hit, 3)))
            # if self.game_time_lst[-2]<self.predicted_loc[2][self.bounce_n-1]<self.game_time_lst[-1]:
            if self.time_to_hit <= 0:
                print('########################   predicted hit   ###############')
                print(self.predicted_loc[3][0][self.bounce_n - 1], self.predicted_loc[3][1][self.bounce_n - 1],
                      self.predicted_loc[3][2][self.bounce_n - 1])
            if self.ball_speed_z_lst[-2] < 0 and self.ball_speed_z_lst[-1] > 0:
                print('real hit')
                print(self.ball_loc_x, self.ball_loc_y, self.ball_loc_z)

    def get_game_state(self):
        if self.game_active and self.game_ball_touched:
            self.game_state = 'active'
        if self.game_active and not self.game_ball_touched:
            self.game_state = 'kickoff'
        if not self.game_active and self.game_ball_touched:
            self.game_state = 'goal_replay'
        if not self.game_active and not self.game_ball_touched:
            self.game_state = 'inactive'
        if self.game_ended:
            self.game_state = 'ended'
        if self.game_overtime:
            self.game_state += '_overtime'

    def boost_needed(self, initial_speed, goal_speed):
        p1 = 6.31e-06
        p2 = 0.010383
        p3 = 1.3183
        boost_initial = p1 * initial_speed ** 2 + p2 * initial_speed + p3
        boost_goal = p1 * goal_speed ** 2 + p2 * goal_speed + p3
        boost_needed = boost_goal - boost_initial
        return boost_needed

    def what_to_do(self):  # todo: add goal destinction, add decision to attack or not, add defence mechanism
        self.predict(True)
        speed_needed = self.bot_max_speed[1]
        n_hit = -1
        ball_vector = self.goal_to_ball_vector()
        distance_multiplier = 35
        x = ball_vector[0] * distance_multiplier
        y = ball_vector[1] * distance_multiplier * ball_vector[2]
        if self.game_state == 'active':
            for n_hit in range(len(self.predicted_loc[2])):
                distance_to_hit = self.distance(self.predicted_loc[3][0][n_hit] + x,
                                                self.predicted_loc[3][1][n_hit] + y, self.predicted_loc[3][2][n_hit],
                                                self.bot_loc_x, self.bot_loc_y, self.bot_loc_z)
                self.bot_speed_linear
                if (self.predicted_loc[2][n_hit] - self.game_time) == 0:
                    break
                speed_needed = (distance_to_hit - 0) / (
                            self.predicted_loc[2][n_hit] - self.game_time)  # -20 fot it to go slightly slower
                if (speed_needed < self.bot_max_speed[1]):
                    if speed_needed > self.bot_max_speed[0]:
                        if (self.bot_boost + 1) >= self.boost_needed(self.bot_speed_linear, speed_needed):
                            break
                    else:
                        break
        if ((self.bot_team == 1 and self.bot_loc_y + 500 > self.ball_loc_y) or (
                self.bot_team == 0 and self.bot_loc_y - 500 < self.ball_loc_y)):  # or self.distance_car_ball<600:
            if self.predicted_loc[3][0]:
                self.aim(self.predicted_loc[3][0][n_hit] + x, self.predicted_loc[3][1][n_hit] + y, speed_needed)
            else:
                self.aim(self.ball_loc_x + x, self.ball_loc_y + y, speed_needed)

            if self.distance_car_ball < 100 and \
                    ((self.bot_team == 0 and self.distance(0, self.ball_loc_y, 0, 0, 5000, 0) < 200 and self.distance(
                    self.ball_loc_x, self.ball_loc_y, 0, 0, 5000, 0) < 1000)  or
                     (self.bot_team == 1 and self.distance(0, self.ball_loc_y, 0, 0, -5000, 0) < 200) and self.distance(
                    self.ball_loc_x, self.ball_loc_y, 0, 0, -5000, 0) < 1000) \
                    and self.ball_loc_z > 120:
                self.flick(-ball_vector[0], ball_vector[1], jump_timeout=0.10, flick_timeout=0.20)
                print(1)
        else:
            if self.bot_team == 0:
                # Blue team's goal is located at (0, -5000)
                self.aim(0, -5000, speed_needed=self.bot_max_speed[1])
            else:
                # Orange team's goal is located at (0, 5000)
                self.aim(0, 5000, speed_needed=self.bot_max_speed[1])

        if abs(self.angle_front_to_target) > 150 and self.distance_to_target > 3000 and self.flick_time == 0:
            self.flick(1, 0, jump_timeout=0.25, flick_timeout=0.30)
            print(2)

            # print("I'm too lazy to search for the function to skeap empty functions because this function was acting up")

        if self.bot_state == 'dribbling' and abs(self.angle_front_to_target) < 90:
            angle_car_vector = math.degrees(math.atan2(ball_vector[1], ball_vector[0])) - self.bot_rot_yaw
            angle_car_vector = math.radians(angle_car_vector)
            print(angle_car_vector)
            xv=math.cos(angle_car_vector)*math.sqrt(ball_vector[0]**2+ball_vector[1]**2)
            yv=math.sin(angle_car_vector)*math.sqrt(ball_vector[0]**2+ball_vector[1]**2)
            self.flick(xv, -yv, jump_timeout=0.2, flick_timeout=0.25) #TODO: map vectors to car directions properly
            print('xxxxxxxx')
            print(xv)
            print(yv)
            print(3)

    def get_bot_state(self):
        # print(self.distance_car_ball,abs(self.ball_speed_z),self.distance(self.bot_loc_z,0,0,self.ball_loc_z,0,0))
        if 30 < self.distance_car_ball < 60 and abs(self.ball_speed_z) < 15 and 120 < self.distance(self.bot_loc_z, 0,
                                                                                                    0, self.ball_loc_z,
                                                                                                    0, 0) < 127:
            self.bot_state = 'dribbling'
        else:
            self.bot_state = 'normal'
        # print(self.bot_state)

    def avoid_enemy_colision(self, values):
        enemy_avoid = False
        for enemy_index in range(self.num_cars):
            if self.bot_team != values.game_cars[enemy_index].team:  # aka enemy
                self.enemy_loc_x = values.game_cars[enemy_index].physics.location.x
                self.enemy_loc_y = values.game_cars[enemy_index].physics.location.y
                self.enemy_loc_z = values.game_cars[enemy_index].physics.location.z
                self.enemy_speed_x = values.game_cars[enemy_index].physics.velocity.x
                self.enemy_speed_y = values.game_cars[enemy_index].physics.velocity.y
                self.enemy_speed_z = values.game_cars[enemy_index].physics.velocity.z
                self.enemy_rot = values.game_cars[enemy_index].physics.rotation
                self.enemy_rot_yaw = abs(self.bot_rot.yaw) % 65536 / 65536 * 360
                if self.enemy_rot.yaw < 0:
                    self.enemy_rot_yaw *= -1

                self.enemy_distance = self.distance(self.enemy_loc_x, self.enemy_loc_y, 0, self.bot_loc_x,
                                                    self.bot_loc_y, 0)
                self.enemy_speed = self.distance(self.enemy_speed_x, self.enemy_speed_y, 0, self.bot_speed_x,
                                                 self.bot_speed_y, 0)

                angle_between_enemy_and_bot = math.degrees(
                    math.atan2(self.bot_loc_y - self.enemy_loc_y, self.bot_loc_y - self.enemy_loc_y))
                self.angle_enemy_to_bot = angle_between_enemy_and_bot - self.enemy_rot_yaw
                # Correct the values
                if self.angle_enemy_to_bot < -180:
                    self.angle_enemy_to_bot += 360
                if self.angle_enemy_to_bot > 180:
                    self.angle_enemy_to_bot -= 360

                if (self.enemy_distance * self.enemy_speed) < 1 and abs(self.angle_enemy_to_bot) < 50:
                    enemy_avoid = True

        if self.bot_state == 'dribbling' and enemy_avoid:
            a = self.goal_to_ball_vector()
            x = a[0]
            y = a[1]
            self.flick(pitch=-y, roll=-x)
            print(6)
        elif enemy_avoid:
            self.controller.jump = True
            # self.jump_time_end=self.game_time+0.3

    def flick(self, pitch=-1, roll=0.05, jump_timeout=0.1, flick_timeout=0.15):
        if self.flick_time == 0 and self.bot_ground:
            print('###################################jump')
            self.controller.jump = True
            # print('jumped')
            self.jump_time_end = self.game_time + jump_timeout
            self.flick_time = self.game_time + flick_timeout
            if pitch > 1: pitch =1
            elif pitch <-1: pitch = -1
            self.controller.pitch = pitch
            roll = roll*1.3
            if roll > 1: roll =1
            elif roll <-1: roll = -1
            self.controller.roll = roll
            # print("Flicking")
            # print(self.flick_time)

    def goal_to_ball_vector(self):
        if self.bot_team == 0:
            # Blue team's goal is located at (0, -5000)
            distance_ball_to_goal = self.distance(self.ball_loc_x, self.ball_loc_y, 0, 0, 5400, 0)
            x = self.distance(self.ball_loc_x, 0, 0, 0, 0, 0)
            y = -self.distance(0, self.ball_loc_y, 0, 0, 5400, 0)
        else:  # elif self.bot_team == 1:
            # Orange team's goal is located at (0, 5000)
            distance_ball_to_goal = self.distance(self.ball_loc_x, self.ball_loc_y, 0, 0, -5400, 0)
            x = self.distance(self.ball_loc_x, 0, 0, 0, 0, 0)
            y = self.distance(0, self.ball_loc_y, 0, 0, -5400, 0)
        x = x / distance_ball_to_goal
        if self.ball_loc_x < 0:
            x = -x
        y = y / distance_ball_to_goal
        if abs(self.ball_loc_x) < 1200 and distance_ball_to_goal < 800:
            m = 2.5
        else:
            m = 1
        return [x, y, m]

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.get_values(packet)
        self.get_bot_state()
        self.get_game_state()
        self.was_hit()
        self.what_to_do()
        self.avoid_enemy_colision(packet)

        return self.controller
