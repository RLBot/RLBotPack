import itertools
from threading import Event, Thread
from traceback import print_exc

from rlbot.utils.structures.quick_chats import QuickChats


class Prediction(Thread):
    def __init__(self, agent):
        super().__init__(daemon=True)
        self.agent = agent
        self.event = Event()

    def run(self):
        while 1:
            try:
                self.event.wait()

                len_friends = len(self.agent.friends)

                can_shoot = True

                if len(self.agent.foes) > 0:
                    foe_distances = tuple(self.agent.ball.location.flat_dist(foe.location) for foe in self.agent.foes)

                    shoot_threshold = 4000

                    if len_friends == 1:
                        shoot_threshold = 3500
                    elif len_friends == 2:
                        shoot_threshold = 3000
                    elif len_friends > 2:
                        shoot_threshold = 2750

                    if len_friends == 0:
                        for i, foe_dist in enumerate(foe_distances):
                            if foe_dist < 500 and self.agent.ball_to_goal > shoot_threshold and self.agent.foes[i].location.y - 200 < self.agent.ball.location.y and self.agent.ball.location.y < self.agent.foes[i].location.y + 200:
                                can_shoot = False

                    self.agent.predictions['closest_enemy'] = min(foe_distances)

                self.agent.predictions['self_from_goal'] = self.agent.friend_goal.location.flat_dist(self.agent.me.location)
                self.agent.predictions['self_to_ball'] = self.agent.ball.location.flat_dist(self.agent.me.location)

                if len_friends > 0 and self.agent.ball_to_goal > 3750:
                    teammates = tuple(itertools.chain(self.agent.friends, [self.agent.me]))

                    self.agent.predictions["teammates_from_goal"] = tuple(self.agent.friend_goal.location.flat_dist(teammate.location) for teammate in teammates)
                    self.agent.predictions["teammates_to_ball"] = tuple(self.agent.ball.location.flat_dist(teammate.location) for teammate in teammates)

                    if can_shoot:
                        can_shoot = self.agent.predictions['self_from_goal'] != min(self.agent.predictions["teammates_from_goal"])

                    if self.agent.ball_to_goal > 4250 and self.agent.predictions['self_to_ball'] == min(self.agent.predictions['teammates_to_ball']):
                        self.agent.playstyle = self.agent.playstyles.Offensive
                    elif self.agent.ball_to_goal > 3750 and self.agent.predictions['self_to_ball'] == max(self.agent.predictions['teammates_to_ball']):
                        self.agent.playstyle = self.agent.playstyles.Defensive
                    else:
                        self.agent.playstyle = self.agent.playstyles.Neutral
                elif self.agent.playstyle != self.agent.playstyles.Neutral:
                    self.agent.playstyle = self.agent.playstyles.Neutral

                if can_shoot:
                    self.can_shoot = self.agent.time - 2.9

                is_own_goal = False
                is_goal = False

                if self.agent.predictions['ball_struct'] is not None:
                    for i in range(0, self.agent.predictions['ball_struct'].num_slices, 2):
                        prediction_slice = self.agent.predictions['ball_struct'].slices[i]
                        location = prediction_slice.physics.location

                        if (self.agent.team == 0 and location.y <= -7680) or (self.agent.team == 1 and location.y >= 7680):
                            is_own_goal = True
                        elif (self.agent.team == 0 and location.y >= 7680) or (self.agent.team == 1 and location.y <= -7680):
                            is_goal = True

                if is_own_goal:
                    if not self.agent.predictions['own_goal']:
                        self.agent.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_NiceShot)

                self.agent.predictions["own_goal"] = is_own_goal
                self.agent.predictions["goal"] = is_goal

                self.event.clear()
            except Exception:
                print_exc()
