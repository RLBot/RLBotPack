import itertools
import math
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
                        shoot_threshold = 3840

                        if len_friends == 1:
                            shoot_threshold = 2560
                        elif len_friends == 2:
                            shoot_threshold = 1280
                        elif len_friends > 2:
                            shoot_threshold = 640

                        if len_friends == 0:
                            for i, foe_dist in enumerate(foe_distances):
                                if foe_dist + 50 < self_dist and self.agent.ball_to_goal > shoot_threshold and self.agent.foes[i].location.y * side < self.agent.ball.location.y * side:
                                    can_shoot = False

                        self.agent.predictions['closest_enemy'] = min(foe_distances)
                    else:
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

                if not can_shoot:
                    self.agent.can_shoot = self.agent.time - 2.95

                if self.agent.odd_tick == 0:
                    is_own_goal = False
                    is_goal = False

                    if self.agent.predictions['ball_struct'] is not None:
                        for ball_slice in self.agent.predictions['ball_struct'].slices[30::6]:
                            location = ball_slice.physics.location.y * side

                            if location >= 5212:
                                is_own_goal = True
                                break

                            if location <= -5212:
                                is_goal = True
                                break

                    if is_own_goal and not self.agent.predictions['own_goal']:
                        self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_NiceShot)

                    self.agent.predictions["own_goal"] = is_own_goal
                    self.agent.predictions["goal"] = is_goal

                self.agent.predictions['done'] = True

                self.event.clear()
            except Exception:
                print_exc()
