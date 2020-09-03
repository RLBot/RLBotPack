import itertools
import math
import virxrlcu
from threading import Event, Thread
from traceback import print_exc

from rlbot.utils.structures.quick_chats import QuickChats


class Prediction(Thread):
    def __init__(self, agent):
        super().__init__(daemon=True)
        self.agent = agent
        self.event = Event()
        self.online = 1

    def stop(self):
        self.online = 0
        self.event.set()

    def run(self):
        while self.online:
            try:
                self.event.wait()

                len_friends = len(self.agent.friends)
                side = 1 if self.agent.team is 1 else -1

                can_shoot = True

                if len(self.agent.foes) > 0:
                    foe_distances = tuple(self.agent.ball.location.flat_dist(foe.location) for foe in self.agent.foes if not foe.demolished)
                    self_dist = self.agent.ball.location.flat_dist(self.agent.me.location)
                    if len(foe_distances) > 0:
                        if self.agent.odd_tick == 0:
                            cars = sorted((foe for foe in self.agent.foes if not foe.demolished), key=lambda foe: self.agent.ball.location.flat_dist(foe.location))
                            found = False

                            for car in cars:
                                me = (
                                    car.location.tuple(),
                                    car.forward.tuple(),
                                    car.boost if self.agent.boost_amount != 'unlimited' else 100000,
                                    car.local_velocity().x
                                )

                                game_info = (
                                    self.agent.best_shot_value,
                                    self.agent.boost_accel
                                )

                                me_a = (
                                    me[0],
                                    self.agent.me.velocity.tuple(),
                                    self.agent.me.up.tuple(),
                                    me[1],
                                    1 if self.agent.me.airborne else -1,
                                    me[2]
                                )

                                gravity = self.agent.gravity.tuple()

                                ground = not car.airborne or car.location.z < 300

                                # check every 12th slice
                                for ball_slice in self.agent.ball_prediction_struct.slices[12::12]:
                                    intercept_time = ball_slice.game_seconds
                                    time_remaining = intercept_time - self.agent.time

                                    if time_remaining <= 0:
                                        break

                                    ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

                                    if abs(ball_location[1]) > 5212:
                                        break

                                    if ground and ball_location[2] < 300:
                                        shot = virxrlcu.parse_slice_for_jump_shot(time_remaining, *game_info, ball_location, *me)

                                        if shot['found'] == 1:
                                            self.agent.predictions['enemy_time_to_ball'] = intercept_time + 0.1
                                            found = True
                                            break
                                    
                                    if ground and ball_location[2] < 490 or ball_location[2] > 300:
                                        shot = virxrlcu.parse_slice_for_double_jump(time_remaining, *game_info, ball_location, *me)

                                        if shot['found'] == 1:
                                            self.agent.predictions['enemy_time_to_ball'] = intercept_time + 0.1
                                            found = True
                                            break

                                    if 500 < ball_location[2]:
                                        shot = virxrlcu.parse_slice_for_aerial_shot(time_remaining, *game_info, gravity, ball_location, me_a)

                                        if shot['found'] == 1:
                                            self.agent.predictions['enemy_time_to_ball'] = intercept_time + 0.1
                                            found = True
                                            break
                                
                                if found:
                                    break
                            
                            if not found:
                                self.agent.predictions['enemy_time_to_ball'] = math.inf

                        self.agent.predictions['closest_enemy'] = min(foe_distances)
                    else:
                        self.agent.predictions['enemy_time_to_ball'] = math.inf
                        self.agent.predictions['closest_enemy'] = math.inf

                self.agent.predictions['self_from_goal'] = self.agent.friend_goal.location.flat_dist(self.agent.me.location) if not self.agent.me.demolished else math.inf
                self.agent.predictions['self_to_ball'] = self.agent.ball.location.flat_dist(self.agent.me.location) if not self.agent.me.demolished else math.inf
                if not self.agent.predictions['was_down']:
                    self.agent.predictions['was_down'] = self.agent.game.friend_score - self.agent.game.foe_score > 1

                if self.agent.goalie:
                    self.agent.playstyle = self.agent.playstyles.Defensive
                elif len_friends > 0:
                    teammates = tuple(itertools.chain(self.agent.friends, [self.agent.me]))

                    self.agent.predictions["team_from_goal"] = sorted(tuple(self.agent.friend_goal.location.flat_dist(teammate.location) if not teammate.demolished else math.inf for teammate in teammates))
                    self.agent.predictions["team_to_ball"] = sorted(tuple(self.agent.ball.location.flat_dist(teammate.location) if not teammate.demolished else math.inf for teammate in teammates))

                    if len_friends >= 2 and can_shoot:
                        can_shoot = self.agent.predictions['self_from_goal'] != self.agent.predictions["team_from_goal"][0]

                    side = 1 if self.agent.team == 1 else -1

                    ball_loc_y = self.agent.ball.location.y * side

                    if ball_loc_y < 2560:
                        # If we're down or up by 2 goals in 2's, then start playing more defensive
                        if ball_loc_y < -1280 and self.agent.predictions['self_to_ball'] == self.agent.predictions['team_to_ball'][0] and self.agent.predictions['self_from_goal'] != self.agent.predictions["team_from_goal"][0]:
                            self.agent.playstyle = self.agent.playstyles.Offensive if len_friends > 1 or (len_friends == 1 and (self.agent.predictions['was_down'] or abs(self.agent.game.friend_score - self.agent.game.foe_score) <= 1)) else self.agent.playstyles.Neutral
                        elif self.agent.predictions['self_from_goal'] == self.agent.predictions["team_from_goal"][0]:
                            self.agent.playstyle = self.agent.playstyles.Defensive if len_friends > 1 or (len_friends == 1 and (self.agent.predictions['was_down'] or abs(self.agent.game.friend_score - self.agent.game.foe_score) > 1)) else self.agent.playstyles.Neutral
                        else:
                            self.agent.playstyle = self.agent.playstyles.Neutral
                    else:
                        self.agent.playstyle = self.agent.playstyles.Defensive
                else:
                    self.agent.playstyle = self.agent.playstyles.Neutral if self.agent.ball.location.y * side < 1280 else self.agent.playstyles.Defensive

                if not can_shoot and self.agent.can_shoot is None:
                    self.agent.can_shoot = self.agent.time - 2.95

                if self.agent.odd_tick == 0:
                    is_own_goal = False
                    is_goal = False

                    if self.agent.ball_prediction_struct is not None:
                        for ball_slice in self.agent.ball_prediction_struct.slices[30::12]:
                            location = ball_slice.physics.location.y * side

                            if location >= 5212:
                                is_own_goal = True
                                break

                            if location <= -5212:
                                is_goal = True
                                break

                    if is_own_goal and not self.agent.predictions['own_goal']:
                        self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_NiceShot)
                    
                    if is_goal and not self.agent.predictions['goal']:
                        self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)

                    self.agent.predictions["own_goal"] = is_own_goal
                    self.agent.predictions["goal"] = is_goal

                self.agent.predictions['done'] = True

                self.event.clear()
            except Exception:
                print_exc()
