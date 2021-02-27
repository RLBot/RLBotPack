import itertools

# from rlbot.utils.game_state_util import CarState, BallState, GameState, Physics, Vector3
from rlbot.utils.structures.quick_chats import QuickChats

import virxrlcu
from util.agent import Vector, VirxERLU, math
from util.routines import (ball_recovery, boost_down, corner_kickoff, corner_kickoff_boost,
                           face_target, generic_kickoff, goto, goto_boost, recovery, retreat, shadow,
                           short_shot, wave_dash, flip, ground_shot, back_offset_kickoff, back_offset_kickoff_boost, back_kickoff)
from util.tools import find_any_shot, find_shot
from util.utils import (almost_equals, cap, get_weight, peek_generator,
                        send_comm, side, sign)


class VirxEB(VirxERLU):
    def init(self):
        foe_team = -1 if self.team == 1 else 1
        team = -foe_team

        # note that the second value may be positive or negative
        self.kickoff_left = (-2048 * side(self.team), 2560)
        self.kickoff_right = (2048 * side(self.team), 2560)
        self.kickoff_back = (0, 4608)
        self.kickoff_back_left = (-256 * side(self.team), 3840)
        self.kickoff_back_right = (256 * side(self.team), 3840)

        self.offensive_shots = (
            (Vector(foe_team * 893, foe_team * 5120, 321.3875), Vector(foe_team * -893, foe_team * 5120, 321.3875)),
            (Vector(foe_team * 893, foe_team * 5120, 321.3875), Vector(foe_team * 893, foe_team * 6000, 321.3875)),
            (Vector(foe_team * -893, foe_team * 5120, 321.3875), Vector(foe_team * -893, foe_team * 6000, 321.3875))
        )

        self.defensive_shots = (
            self.offensive_shots[0],
            (Vector(4096, foe_team * 3968, 1900), Vector(2944, foe_team * 5120, 1900)),
            (Vector(-4096, foe_team * 3968, 1900), Vector(-2944, foe_team * 5120, 1900))
        )

        self.best_shot = (Vector(foe_team * 793, foe_team * 5213, 321.3875), Vector(-foe_team * 793, foe_team * 5213, 321.3875))
        self.anti_shot = (Vector(-team * 2048, team * 5120, 2000), Vector(team * 2048, team * 5120, 2000))

        self.max_shot_weight = 4
        self.playstyles_switch = {
            self.playstyles.Defensive: self.defend,
            self.playstyles.Neutral: self.neutral,
            self.playstyles.Offensive: self.attack
        }

        self.defense_switch = {
            self.playstyles.Defensive: 1920,
            self.playstyles.Neutral: 1280,
            self.playstyles.Offensive: 640
        }

    def update_predictions(self):
        len_friends = len(self.friends)
        can_shoot = True

        if len(self.foes) > 0:
            foe_distances = tuple(self.ball.location.flat_dist(foe.location) for foe in self.foes if not foe.demolished)
            self_dist = self.ball.location.flat_dist(self.me.location)
            if len(foe_distances) > 0:
                if self.odd_tick == 0:
                    self.predictions['enemy_time_to_ball'] = min(tuple(self.time_to_ball(foe) for foe in self.foes))

                self.predictions['closest_enemy'] = min(foe_distances)
            else:
                self.predictions['enemy_time_to_ball'] = 7
                self.predictions['closest_enemy'] = math.inf
        else:
            self.predictions['enemy_time_to_ball'] = 7
            self.predictions['closest_enemy'] = math.inf

        self.future_ball_location_slice = cap(round(self.predictions['enemy_time_to_ball'] * 60), 0, len(self.ball_prediction_struct.slices) - 1)
        self.dbg_2d(f"Predicted enemy time to ball: {round(self.predictions['enemy_time_to_ball'], 1)}")

        self.predictions['self_from_goal'] = self.friend_goal.location.flat_dist(self.me.location)
        self.predictions['self_to_ball'] = self.ball.location.flat_dist(self.me.location)

        if not self.predictions['was_down']:
            self.predictions['was_down'] = self.game.friend_score - self.game.foe_score > 1

        if len_friends > 0:
            teammates = tuple(itertools.chain(self.friends, [self.me]))

            self.predictions["team_from_goal"] = sorted(tuple(self.friend_goal.location.flat_dist(teammate.location) if not teammate.demolished else math.inf for teammate in teammates))
            self.predictions["team_to_ball"] = sorted(tuple(self.ball.location.flat_dist(teammate.location) if not teammate.demolished else math.inf for teammate in teammates))
            if len_friends >= 2 and can_shoot:
                can_shoot = self.predictions['self_from_goal'] != self.predictions["team_from_goal"][0]

        if self.odd_tick == 0:
            self.predictions['self_min_time_to_ball'] = self.time_to_ball(self.me)
        self.min_intercept_slice = cap(round(self.predictions['self_min_time_to_ball'] * 60), 0, len(self.ball_prediction_struct.slices) - 1)

        if self.odd_tick % 2 == 0:
            if self.goalie:
                self.playstyle = self.playstyles.Defensive
            # elif len_friends > 0:
            #     ball_loc_y = self.ball.location.y * side(self.team)

            #     if ball_loc_y < 2560:
            #         # If we're down or up by 2 goals in 2's, then start playing more defensive
            #         self_time_to_ball = self.predictions['self_min_time_to_ball'] * 1.05
            #         team_time_to_ball = min(tuple(self.time_to_ball(teammate) for teammate in self.friends)) * 1.05
            #         if ball_loc_y < -1280 and self_time_to_ball < team_time_to_ball and self.predictions['self_from_goal'] != self.predictions["team_from_goal"][0]:
            #             self.playstyle = self.playstyles.Offensive if len_friends > 1 or (len_friends == 1 and (self.predictions['was_down'] or abs(self.game.friend_score - self.game.foe_score) <= 1)) else self.playstyles.Neutral
            #         elif self.predictions['self_from_goal'] == self.predictions["team_from_goal"][0]:
            #             self.playstyle = self.playstyles.Defensive if len_friends > 1 else self.playstyles.Neutral
            #         else:
            #             self.playstyle = self.playstyles.Neutral
            #     else:
            #         self.playstyle = self.playstyles.Defensive
            else:
                self_time_to_ball = self.predictions['self_min_time_to_ball'] * 1.05

                if self.ball.location.y * side(self.team) < 640:
                    self.playstyle = self.playstyles.Offensive if self_time_to_ball < self.predictions['enemy_time_to_ball'] else self.playstyles.Neutral
                else:
                    self.playstyle = self.playstyles.Neutral if self_time_to_ball < self.predictions['enemy_time_to_ball'] else self.playstyles.Defensive

            is_own_goal = False
            is_goal = False

            if self.ball_prediction_struct is not None:
                for ball_slice in self.ball_prediction_struct.slices[30::12]:
                    location = ball_slice.physics.location.y * side(self.team)

                    if location >= 5212.75:
                        is_own_goal = True
                        break

                    if location <= -5212.75:
                        is_goal = True
                        break

            if is_own_goal and not self.predictions['own_goal']:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_NiceShot)

            if is_goal and not self.predictions['goal']:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)

            self.predictions["own_goal"] = is_own_goal
            self.predictions["goal"] = is_goal

        self.dbg_2d(f"Minimum time to ball: {round(self.predictions['self_min_time_to_ball'], 1)}")

        if not can_shoot and self.can_shoot is None:
            self.can_shoot = self.time - 2.9

        if self.can_shoot is not None and (self.time - self.can_shoot >= 3 or self.predictions['own_goal']):
            self.can_shoot = None

    def test(self):
        # slope testing
        """
        ball_state = BallState(Physics(location=Vector3(*self.debug_vector), velocity=Vector3(0, 0, 0), angular_velocity=Vector3(0, 0, 0)))
        self.set_game_state(GameState(ball=ball_state))

        car_to_ball = self.ball.location - self.me.location
        direction = car_to_ball.normalize()
        shot_vector = direction.clamp2D((self.foe_goal.left_post - self.ball.location).normalize(), (self.foe_goal.right_post - self.ball.location).normalize())
        car_to_ball = car_to_ball.flatten()
        shot_vector = shot_vector.flatten()
        
        d = shot_vector.dot(car_to_ball)
        e = abs(shot_vector.cross((0, 0, 1)).dot(car_to_ball))

        slope = 10 * sign(d) if (e == 0) else max(min(d / e, 3), -3)
        self.dbg_2d(f"Slope: {slope}")

        shot = self.get_shot(self.offensive_shots[0], cap=6)
        if shot is not None:
            self.dbg_2d(f"Time: {shot['intercept_time'] - self.time}")
        else:
            self.dbg_2d(f"Time: impossible")
        """
        # Enemy intercept prediction testing
        """
        if self.predictions['enemy_time_to_ball'] != 7:
            intercept_slice = self.future_ball_location_slice
            intercept_location = self.ball_prediction_struct.slices[intercept_slice].physics.location
            intercept_location = Vector(intercept_location.x, intercept_location.y, intercept_location.z)
            self.sphere(intercept_location, 92.75, self.renderer.black())
        """
        # Backcheck testing
        """
        self.dbg_2d(round(self.ball.location))

        if self.is_clear():
            self.backcheck()
        """
        # Shot testing
        """
        self.line(*self.best_shot, color=self.renderer.team_color(alt_color=True))
        if not self.smart_shot(self.anti_shot, cap=6) and not self.shooting:
            if self.is_clear() and not self.me.airborne and self.me.location.flat_dist(self.debug_vector * side(self.team)) > 250:
                self.push(face_target(ball=True))
                self.push(goto(self.debug_vector.flatten() * side(self.team), brake=True))
        """
        # Any shot testing
        """
        if self.shooting:
            if self.odd_tick == 0:
                self.smart_shot(cap=6)
        else:
            if self.is_clear() and not self.me.airborne and (self.me.boost < 60 or not self.smart_shot(cap=6)) and self.me.location.flat_dist(self.debug_vector * side(self.team)) > 250:
                self.push(face_target(ball=True))
                self.push(goto(self.debug_vector.flatten() * side(self.team), brake=True))

            if self.ball.location.z < 150 and not self.predictions['goal']:
                ball_state = BallState(Physics(location=Vector3(0, -4096 * side(self.team), self.ball.location.z), velocity=Vector3(0, 0, 2000), angular_velocity=Vector3(0, 0, 0)))
                self.set_game_state(GameState(ball=ball_state))
        """
        # Recovery testing
        """
        if not self.me.airborne and self.me.velocity.magnitude() < 10:
            cars = {
                self.index: CarState(Physics(location=Vector3(0, 0, 17.1), velocity=Vector3(*self.debug_vector), angular_velocity=Vector3(0, 0, 0)))
            }
            self.set_game_state(GameState(cars=cars))
        elif self.me.airborne and self.is_clear():
            self.push(ball_recovery())
        """
        # Ceiling aerial testing
        """
        if not self.shooting and self.ball.location.z < 100 and not self.predictions['goal']:
            ball_state = BallState(Physics(location=Vector3(self.debug_vector.x * side(self.team), self.debug_vector.y * side(self.team), self.ball.location.z), velocity=Vector3(0, 0, 2000), angular_velocity=Vector3(0, 0, 0)))
            game_state = GameState(ball=ball_state)
            self.set_game_state(game_state)

        if self.is_clear():
            self.push(ceiling_shot())
        """

    def time_to_ball(self, car):
        if car.demolished:
            return 7

        # Assemble data in a form that can be passed to C
        me = car.get_raw(self)
        g_me = car.get_raw(self, car.location.z < 300)
        is_on_ground = g_me[5] == 0

        game_info = (
            self.boost_accel,
            self.best_shot_value
        )

        gravity = tuple(self.gravity)

        # check every 12th slice
        for ball_slice in self.ball_prediction_struct.slices[12::6]:
            # Gather some data about the slice
            time_remaining = ball_slice.game_seconds - self.time

            if time_remaining <= 0:
                return 7

            ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

            if abs(ball_location[1]) > 5212.75:
                return 7  # abandon search if ball is scored at/after this point

            ball_info = (ball_location, (ball_slice.physics.velocity.x, ball_slice.physics.velocity.y, ball_slice.physics.velocity.z))

            # Check if we can make a shot at this slice
            # This operation is very expensive, so we use C to improve run time
            shot = virxrlcu.parse_slice_for_shot(is_on_ground, is_on_ground, is_on_ground, 1, time_remaining, *game_info, gravity, ball_info, g_me)

            if shot['found'] == 1:
                return time_remaining

        return 7

    def run(self):
        # predictions
        self.update_predictions()

        # act on the predictions
        if not self.kickoff_done:
            if self.is_clear():
                if len(self.friends) > 0:
                    if almost_equals(self.predictions['team_to_ball'][0], self.predictions['self_to_ball'], 5):
                        self.offensive_kickoff()
                    elif almost_equals(self.predictions['team_to_ball'][-1], self.predictions['self_to_ball'], 5):
                        self.defensive_kickoff()
                elif len(self.foes) == 0 or almost_equals(self.predictions['closest_enemy'], self.predictions['self_to_ball'], 10):
                    self.offensive_kickoff()
                else:
                    self.defensive_kickoff()
            return
        
        if self.can_shoot is None:
            self.dbg_3d("Can shoot: 0")
        else:
            self.dbg_3d(f"Can shoot: {round(3 - (self.time - self.can_shoot), 2)}")

        enemy_intercept_location = self.ball_prediction_struct.slices[self.future_ball_location_slice].physics.location
        enemy_intercept_location = Vector(enemy_intercept_location.x, enemy_intercept_location.y, enemy_intercept_location.z)
        if self.predictions['enemy_time_to_ball'] != 7:
            self.sphere(enemy_intercept_location, 92.75, self.renderer.red())

        self_intercept_location = self.ball_prediction_struct.slices[self.min_intercept_slice].physics.location
        self_intercept_location = Vector(self_intercept_location.x, self_intercept_location.y, self_intercept_location.z)
        if self.predictions['self_min_time_to_ball'] != 7:
            self.sphere(self_intercept_location, 92.75, self.renderer.green())

        if side(self.team) * enemy_intercept_location.y >= self.defense_switch[self.playstyle] or self.predictions['own_goal']:
            for shot in self.defensive_shots:
                self.line(*shot, self.renderer.team_color(alt_color=True))

            self.dbg_3d("(Defending)")

            if self.predictions['enemy_time_to_ball'] > self.predictions['self_min_time_to_ball'] + (3 if self.shooting else 1) and self.me.boost < 36 and not self.is_clear() and self.get_stack_name() == 'goto_boost':
                return

            ball_loc = self_intercept_location * side(self.team)
            self_loc = self.me.location * side(self.team)

            # This is a list of all tm8s that are onside
            team_to_ball = [car.location.flat_dist(self.ball.location) for car in self.friends if car.location.y * side(self.team) >= ball_loc.y + 95 and abs(car.location.x) < abs(self.ball.location.x) - 320]
            self_to_ball = self.me.location.flat_dist(self.ball.location)
            team_to_ball.append(self_to_ball)
            team_to_ball.sort()

            if len(team_to_ball) == 1 or team_to_ball[math.ceil(len(team_to_ball) / 2)] + 10 > self_to_ball:
                self.can_shoot = None

            if self.can_shoot is None and (self.is_clear() or self.odd_tick == 0):
                if self_loc.y > ball_loc.y + 95 and self.smart_shot(self.best_shot, cap=4):
                    return

                if ball_loc.y - self_loc.y > (ball_loc.x - self_loc.x) * 1.5 and (self.predictions['own_goal'] or (len(team_to_ball) > 1 and team_to_ball[math.ceil(len(team_to_ball) / 2)] + 10 > self_to_ball) or (len(team_to_ball) == 1 and self_to_ball < 2560) or (abs(ball_loc.x) < 900 and ball_loc.y > 1280)) and team_to_ball[0] is self_to_ball and self.smart_shot(self.anti_shot, weight=self.max_shot_weight - 3, cap=4):
                    return

                if self_loc.y > ball_loc.y + 95:
                    for i, shot in enumerate(self.defensive_shots if self.predictions['self_min_time_to_ball'] * 2 < self.predictions['enemy_time_to_ball'] else self.defensive_shots[1:]):
                        shot_weight = get_weight(self, index=i)

                        if self.shooting and shot_weight < self.shot_weight:
                            break

                        shot = self.get_shot(shot, weight=shot_weight, cap=4)

                        if shot is not None:
                            if self.shooting:
                                self.upgrade_shot(shot)
                            else:
                                self.shoot_from(shot, clear_on_valid=True)
                            return

                    if self.smart_shot(self.anti_shot, weight=self.max_shot_weight - 3, cap=3):
                        return

            if not self.me.airborne and (not self.shooting or self.shot_weight == -1):
                if self.predictions['enemy_time_to_ball'] > self.predictions['self_min_time_to_ball'] + (3 if self.shooting else 1) and self.me.boost < 36 and (self.is_clear() or self.get_stack_name() != 'goto_boost') and self.goto_nearest_boost(clear_on_valid=True):
                    return

                if not self.predictions['own_goal'] and self_loc.y <= ball_loc.y - 50 and not self.is_clear() and self.get_stack_name() == 'goto_boost' and abs(ball_loc.x) > 1024 and self.backcheck(clear_on_valid=True):
                    return

                if self.is_clear() and not self.backcheck():
                    face_target_routine = face_target(ball=True)
                    ball_f = face_target_routine.get_ball_target(self)
                    if ball_f.y * side(self.team) > -3840 and abs(Vector(x=1).angle2D(self.me.local_location(ball_f))) >= 1 and self.me.velocity.magnitude() < 100:
                        self.push(face_target_routine)
                        return

            return

        if self.me.airborne and self.is_clear():
            self.push(recovery())

        if not self.is_clear() and self.get_stack_name() == "short_shot" and self.me.location.y * side(self.team) < self.ball.location.y * side(self.team):
            self.clear()

        self.playstyles_switch[self.playstyle]()
        ""

    def handle_match_comm(self, msg):
        if not self.kickoff_done and msg.get("VirxERLU") is not None and msg['VirxERLU']['team'] is self.team:
            msg = msg['VirxERLU']
            if msg.get("attacking", False) and msg['index'] < self.index and self.get_stack_name() in {"corner_kickoff", "back_offset_kickoff", "generic_kickoff"}:
                self.clear()
                self.defensive_kickoff()

    def handle_quick_chat(self, index, team, quick_chat):
        if self.kickoff_done and team is self.team and index is not self.index and len(self.friends) != 0:
            if quick_chat is QuickChats.Information_IGotIt:
                if side(self.team) * self.ball.location.y < 4200 and not self.predictions['own_goal'] and not self.shooting:
                    self.can_shoot = self.time
                    if side(self.team) * self.ball.location.y < 2560:
                        self.can_shoot -= 2.5
                    elif side(self.team) * self.ball.location.y < 750:
                        self.can_shoot -= 2
                    else:
                        self.can_shoot -= 1.5

                    if self.shooting and self.shot_weight == -1:
                        self.clear()
                        self.backcheck()
            elif quick_chat is QuickChats.Information_GoForIt:
                if self.playstyle is self.playstyles.Neutral:
                    self.can_shoot = None
                    if not self.shooting and self.me.boost >= 36:
                        if not self.smart_shot(self.best_shot, cap=6) and not self.smart_shot(self.offensive_shots[0], cap=6) and not self.smart_shot(self.anti_shot, cap=6) and len(self.friends) > 1:
                            self.push(short_shot(self.foe_goal.location))

    def defend(self):
        if not self.me.airborne:
            if self.shooting and not self.predictions['own_goal'] and self.ball.location.y * side(self.team) < self.defense_switch[self.playstyle]:
                self.clear()

            if self.is_clear():
                ball = self.ball_prediction_struct.slices[cap(round(self.predictions['enemy_time_to_ball'] * 0.95) * 60, 0, len(self.ball_prediction_struct.slices) - 1)].physics.location
                ball = Vector(ball.x, ball.y, ball.z)
                if self.predictions['self_from_goal'] > 2560:
                    self.backcheck()
                if self.me.boost < 72 and ball.y * side(self.team) < -1280:
                    self.goto_nearest_boost(only_small=ball.y * side(self.team) > -2560)
                elif self.predictions['self_from_goal'] > 750:
                    self.backcheck()
                else:
                    face_target_routine = face_target(ball=True)
                    ball_f = face_target_routine.get_ball_target(self)
                    if ball_f.y * side(self.team) > -3840 and abs(Vector(x=1).angle2D(self.me.local_location(ball_f))) >= 1 and self.me.velocity.magnitude() < 100:
                        self.push(face_target_routine)
                        return

    def neutral(self):
        if self.can_shoot is None and (self.is_clear() or self.odd_tick == 0) and self.smart_shot(self.best_shot, cap=5):
            return
                
        if not self.me.airborne and not self.shooting and self.me.boost < 12:
            if self.is_clear():
                self.goto_nearest_boost()

            if not self.is_clear():
                return

        if self.can_shoot is None and (self.is_clear() or self.odd_tick == 0):
            for i, shot in enumerate(self.defensive_shots if self.ball.location.y * side(self.team) > -2560 and len(self.friends) != 0 else self.offensive_shots):
                shot_weight = get_weight(self, index=i)

                if self.shooting and shot_weight < self.shot_weight:
                    break

                shot = self.get_shot(shot, weight=shot_weight, cap=4)

                if shot is not None:
                    if self.shooting:
                        self.upgrade_shot(shot)
                    else:
                        self.shoot_from(shot, clear_on_valid=True)
                    return

        if (self.is_clear() or self.get_stack_name() == "ball_recovery") and self.boost_amount == 'unlimited' and self.gravity.z > -700 and self.me.location.z > 750 and self.predictions['self_to_ball'] > 2560:
            if not self.is_clear():
                self.clear()

            self.push(boost_down())
            return

        if self.is_clear() and not self.me.airborne:
            if self.can_shoot is not None and self.me.boost < 50:
                self.goto_nearest_boost()

                if not self.is_clear():
                    return

            self.backcheck()

    def attack(self):
        if self.can_shoot is None and (self.is_clear() or self.odd_tick == 0) and self.smart_shot(self.best_shot, cap=6):
            return

        if (self.is_clear() or self.get_stack_name() == "short_shot") and not self.me.airborne and self.me.boost < 12:
            self.goto_nearest_boost(clear_on_valid=True)

            if not self.is_clear() and self.get_stack_name() == "goto_boost":
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_GoForIt)
                return

        if not self.is_clear() and self.get_stack_name() == "goto_boost" and self.me.boost < 24:
            return

        if self.can_shoot is None and (self.is_clear() or self.odd_tick == 0):
            for i, shot in enumerate(self.defensive_shots if self.ball.location.y * side(self.team) > -2560 and len(self.friends) != 0 else self.offensive_shots):
                shot_weight = get_weight(self, index=i)

                if self.shooting and shot_weight < self.shot_weight:
                    break

                shot = self.get_shot(shot, weight=shot_weight, cap=6)

                if shot is not None:
                    if self.shooting:
                        self.upgrade_shot(shot)
                    else:
                        self.shoot_from(shot, clear_on_valid=True)
                    return

            if not self.predictions['goal'] and (self.is_clear() or self.shot_weight == self.max_shot_weight - 3) and self.me.location.y * side(self.team) > (self.ball.location.y * side(self.team)) + 1280:
                shot = self.get_shot(self.anti_shot, weight=self.max_shot_weight - 3, cap=6)
                if shot is not None:
                    if self.shooting:
                        self.upgrade_shot(shot)
                    else:
                        self.shoot_from(shot, clear_on_valid=True)
                    return

        if self.is_clear():
            self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_GoForIt)

        if (self.is_clear() or self.get_stack_name() == "ball_recovery") and self.boost_amount == 'unlimited' and self.gravity.z > -700 and self.me.location.z > 750 and self.predictions['self_to_ball'] > 2560:
            if not self.is_clear():
                self.clear()

            self.push(boost_down())
            return

        if self.is_clear() and not self.me.airborne:
            if self.can_shoot is not None and self.me.boost < 50:
                self.goto_nearest_boost()

                if not self.is_clear():
                    return

            self.backcheck()

    def get_shot(self, target=None, weight=None, cap=None):
        if self.predictions['self_min_time_to_ball'] == 7:
            return

        if self.can_shoot is None or self.predictions['own_goal'] or (self.playstyle is self.playstyles.Neutral and target is self.best_shot):
            if weight is None:
                weight = get_weight(self, target)

            can_aerial = self.aerials
            can_double_jump = self.double_jump
            can_jump = self.jump
            can_ground = self.ground_shot

            if len(self.friends) == 0:
                can_aerial = can_aerial and (self.predictions['own_goal'] or (self.me.location.z > 300 and self.me.airborne))
                self_intercept_location = self.ball_prediction_struct.slices[self.min_intercept_slice].physics.location
                self_intercept_location = Vector(abs(self_intercept_location.x), self_intercept_location.y * side(self.team))
                can_double_jump = can_double_jump and (self_intercept_location.x < 1300 or self_intercept_location.y > 3840)

            if not can_aerial and not can_double_jump and not can_jump and not can_ground:
                return

            if target is self.anti_shot and self.me.location.y * side(self.team) > 5120:
                target = None
            
            shot = find_shot(self, target, weight=weight, cap_=6 if cap is None else cap, can_aerial=can_aerial, can_double_jump=can_double_jump, can_jump=can_jump, can_ground=can_ground) if target is not None else find_any_shot(self, cap_=3 if cap is None else cap, can_aerial=can_aerial, can_double_jump=can_double_jump, can_jump=can_jump, can_ground=can_ground)

            if shot is not None:
                return {
                    "weight": weight,
                    "intercept_time": shot.intercept_time,
                    "is_best_shot": target is self.best_shot,
                    "shot": shot
                }

    def shoot_from(self, shot, defend=True, clear_on_valid=False):
        if self.can_shoot is None or self.predictions['own_goal'] or (self.playstyle is self.playstyles.Neutral and shot['is_best_shot']):
            if clear_on_valid or (defend and not self.shooting and not self.is_clear()):
                self.clear()

            if self.is_clear():
                self.shooting = True
                self.shot_time = shot['intercept_time']
                self.shot_weight = shot['weight']

                self.push(shot['shot'])
                self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

    def get_stack_name(self):
        return self.stack[0].__class__.__name__

    def smart_shot(self, target=None, weight=None, cap=None):
        shot = self.get_shot(target, weight, cap)
        if shot is not None:
            if self.shooting:
                self.shooting = True
                self.shot_time = shot['intercept_time']
                self.shot_weight = shot['weight']
                self.upgrade_shot(shot)
            else:
                self.shoot_from(shot, clear_on_valid=True)
            return True
        return False

    def upgrade_shot(self, shot):
        current_shot_name = self.get_stack_name()
        new_shot_name = shot.__class__.__name__

        if new_shot_name is current_shot_name:
            self.shot_time = shot['intercept_time']
            self.shot_weight = shot['weight']
            self.stack[0].update(shot)
        else:
            self.clear()

            self.shooting = True
            self.shot_time = shot['intercept_time']
            self.shot_weight = shot['weight']

            self.push(shot['shot'])

    def kickoff_check(self, pair):
        return almost_equals(pair[0], self.me.location.x, 50) and almost_equals(pair[1], abs(self.me.location.y), 50)

    def defensive_kickoff(self):
        if self.kickoff_check(self.kickoff_back) or self.boost_amount != "default" or self.game_mode == "heatseeker":
            self.backcheck()
            self.can_shoot = self.time
            self.kickoff_done = True
        elif self.kickoff_check(self.kickoff_left) or self.kickoff_check(self.kickoff_right):
            self.push(corner_kickoff_boost())
        elif self.kickoff_check(self.kickoff_back_left) or self.kickoff_check(self.kickoff_back_right):
            self.push(back_offset_kickoff_boost())
        else:
            self.print("Unknown kickoff position; skipping")
            self.kickoff_done = True
            return

        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)
        self.print("Defending!")

        send_comm(self, {
            "match_defender": True
        })

    def offensive_kickoff(self):
        if self.game_mode == "heatseeker" or self.game_mode == "hoops":
            self.print(f"Skipping the kickoff due to the gamemode")
            self.kickoff_done = True
            return

        if self.kickoff_check(self.kickoff_back):
            if not almost_equals(-self.gravity.z, 650, 50) or self.boost_amount != "default":
                self.push(generic_kickoff())
            else:
                self.push(back_kickoff())
        elif self.kickoff_check(self.kickoff_left):
            if not almost_equals(-self.gravity.z, 650, 50) or self.boost_amount != "default":
                self.push(generic_kickoff())
            else:
                self.push(corner_kickoff(-1))
        elif self.kickoff_check(self.kickoff_right):
            if not almost_equals(-self.gravity.z, 650, 50) or self.boost_amount != "default":
                self.push(generic_kickoff())
            else:
                self.push(corner_kickoff(1))
        elif self.kickoff_check(self.kickoff_back_left) or self.kickoff_check(self.kickoff_back_right):
            if not almost_equals(-self.gravity.z, 650, 50) or self.boost_amount != "default":
                self.push(generic_kickoff())
            else:
                self.push(back_offset_kickoff())
        else:
            self.print("Unknown kickoff position; skipping")
            self.kickoff_done = True
            return

        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

        self.print("I got it!")

        send_comm(self, {
            "attacking": True
        })

    def backcheck(self, clear_on_valid=False):
        if self.is_clear() or clear_on_valid:
            routine_shadow = shadow()
            if routine_shadow.is_viable(self):
                if clear_on_valid: self.clear()

                self.push(routine_shadow)
                return True

            routine_retreat = retreat()
            if routine_retreat.is_viable(self):
                if clear_on_valid: self.clear()

                self.push(routine_retreat)
                return True

        return False

    def goto_nearest_boost(self, only_small=False, clear_on_valid=False):
        if self.is_clear() or clear_on_valid:
            self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_NeedBoost)

            ball_slice = self.ball_prediction_struct.slices[min(round(self.future_ball_location_slice * 1.1), 6)].physics
            ball = Vector(ball_slice.location.x, ball_slice.location.y, ball_slice.location.z)
            ball_v = Vector(ball_slice.velocity.x, ball_slice.velocity.y, ball_slice.velocity.z)
            ball_y = ball.y * side(self.team)

            if not only_small:
                if len(self.friends) > 0:
                    large_boosts = (boost for boost in self.boosts if boost.large and boost.active and ((self.playstyle is self.playstyles.Offensive and boost.location.y * side(self.team) < -3000) or (self.playstyle is self.playstyles.Neutral and boost.location.y * side(self.team) > -100) or (self.playstyle is self.playstyles.Defensive and boost.location.y * side(self.team) > 3000)))
                else:
                    if (ball_v.angle2D(self.foe_goal.location - ball) < 1 and ball_y > 0) or abs(ball.x) < 900 or self.predictions['own_goal']:
                        large_boosts = None
                    else:
                        ball_x = sign(ball.x)
                        large_boosts = (boost for boost in self.boosts if boost.large and boost.active and (boost.location.y * side(self.team) > ball_y - 50) and sign(boost.location.x) == ball_x)

                if large_boosts is not None:
                    closest = peek_generator(large_boosts)

                    if closest is not None:
                        closest_distance = closest.location.flat_dist(self.me.location)

                        for item in large_boosts:
                            item_distance = item.location.flat_dist(self.me.location)
                            if item_distance is closest_distance:
                                if item.location.flat_dist(self.me.location) < closest.location.flat_dist(self.me.location):
                                    closest = item
                                    closest_distance = item_distance
                            elif item_distance < closest_distance:
                                closest = item
                                closest_distance = item_distance

                        if clear_on_valid: self.clear()
                        self.push(goto_boost(closest))
                        return True

            if (ball_v.angle2D(self.foe_goal.location - ball) < 1 and ball_y > 0) or self.predictions['own_goal']:
                return False
            
            ball_x = sign(ball.x)
            small_boosts = (boost for boost in self.boosts if not boost.large and boost.active and boost.location.y * side(self.team) > ball_y - 50 and sign(boost.location.x) == ball_x)

            closest = peek_generator(small_boosts)

            if closest is not None:
                closest_distance = closest.location.flat_dist(self.me.location) + (closest.location.flat_dist(self.friend_goal.location) / 400)

                for item in small_boosts:
                    item_distance = item.location.flat_dist(self.me.location) + (item.location.flat_dist(self.friend_goal.location) / 400)

                    if item_distance < closest_distance:
                        item_loc = item.location.y * side(self.team)
                        if (self.playstyle is self.playstyles.Offensive and item_loc < -2560) or (self.playstyle is self.playstyles.Neutral and item_loc < -100) or (self.playstyle is self.playstyles.Defensive and item_loc > 1280):
                            closest = item
                            closest_distance = item_distance

                if clear_on_valid: self.clear()
                self.push(goto_boost(closest))
                return True

        return False
