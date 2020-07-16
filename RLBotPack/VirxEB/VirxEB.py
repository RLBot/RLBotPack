import itertools
from queue import Empty
from traceback import print_exc

# from rlbot.utils.game_state_util import BallState, GameState, Physics
# from rlbot.utils.game_state_util import Vector3 as GSVec3
from rlbot.utils.structures.quick_chats import QuickChats

from util.objects import GoslingAgent, Vector
from util.routines import goto, goto_boost, recovery, short_shot, atba, generic_kickoff, corner_kickoff
# from util.replays import left_kickoff, right_kickoff, back_kickoff, back_left_kickoff, back_right_kickoff
from util.replays import back_kickoff
from util.tools import find_hits, find_risky_hits
from util.utils import side, sign, almost_equals, send_comm, get_weight, peek_generator


class VirxEB(GoslingAgent):
    def init(self):
        self.playstyles_switch = {
            self.playstyles.Defensive: self.playstyle_defend,
            self.playstyles.Offensive: self.playstyle_attack,
            self.playstyles.Neutral: self.playstyle_neutral
        }

    def run(self):
        """
        This is for state setting the ball to high up for aerial testing
        ""
        if not self.shooting and self.ball.location.z < 98:
            ball_state = BallState(Physics(location=GSVec3(0, -3000, self.ball.location.z), velocity=GSVec3(0, 0, 2000), angular_velocity=GSVec3(0, 0, 0)))
            game_state = GameState(ball=ball_state)
            self.set_game_state(game_state)

        if not self.shooting:
            self.smart_shot((self.foe_goal.left_post, self.foe_goal.right_post))

        if self.is_clear():
            self.push(goto(Vector(), self.foe_goal.location))
        """
        self.dbg_3d(self.playstyle.name)

        for _ in range(len(self.friends) + len(self.foes) + 1):
            try:
                msg = self.matchcomms.incoming_broadcast.get_nowait()
            except Empty:
                break

            if msg.get("VirxEB") is not None and msg['VirxEB']['team'] is self.team:
                msg = msg['VirxEB']
                if self.playstyle is self.playstyles.Defensive:
                    if msg.get("match_defender") and msg['index'] < self.index:
                        self.playstyle = self.playstyles.Neutral
                        self.clear()
                        self.goto_nearest_boost()
                        self.can_shoot = self.time

                        self.print("You can defend")
                elif self.playstyle is self.playstyles.Offensive:
                    if msg.get("attacking") and msg['index'] < self.index:
                        self.playstyle = self.playstyles.Neutral
                        self.clear()
                        self.goto_nearest_boost()
                        self.kickoff_done = True
                        self.can_shoot = self.time

                        self.print("All yours!")

        if not self.kickoff_done:
            if self.is_clear():
                if len(self.friends) > 0:
                    try:
                        if almost_equals(min(self.predictions['teammates_to_ball']), self.predictions['self_to_ball'], 5):
                            self.offensive_kickoff()
                        elif almost_equals(max(self.predictions['teammates_to_ball']), self.predictions['self_to_ball'], 5):
                            self.defensive_kickoff()
                    except ValueError:
                        return
                elif almost_equals(self.predictions['closest_enemy'], self.predictions['self_to_ball'], 50):
                    self.offensive_kickoff()
                else:
                    self.can_shoot = self.time
                    self.defensive_kickoff()
        else:
            if self.can_shoot is not None and self.time - self.can_shoot >= 3:
                self.can_shoot = None

            if not self.is_clear() and self.stack[0].__class__.__name__ == "atba" and (self.predictions['closest_enemy'] < 1000 or self.ball_to_goal > 1500):
                self.clear()
            elif self.is_clear() and self.predictions['closest_enemy'] is not None and self.predictions['closest_enemy'] > 2500 and self.ball_to_goal < 1500 and side(self.team) is sign(self.me.location.y) and abs(self.me.location.y) > 5400:
                self.push(atba())

            self.playstyles_switch[self.playstyle]()

            if self.debug_ball_path:
                ball_prediction = self.predictions['ball_struct']

                if ball_prediction is not None:
                    for i in range(0, ball_prediction.num_slices - (ball_prediction.num_slices % self.debug_ball_path_precision) - self.debug_ball_path_precision, self.debug_ball_path_precision):
                        self.line(
                            ball_prediction.slices[i].physics.location,
                            ball_prediction.slices[i + self.debug_ball_path_precision].physics.location
                        )

            if self.shooting and self.shot_weight != -1:
                self.dbg_2d(self.stack[0].intercept_time - self.time)

        ""

    def handle_quick_chat(self, index, team, quick_chat):
        try:
            if team is self.team and index is not self.index:
                if quick_chat is QuickChats.Information_IGotIt:
                    self.can_shoot = self.time + 1
        except Exception:
            print_exc()

    def smart_shot(self, shot, weight=None, cap=None):
        shot = self.get_shot(shot, weight=weight, cap=cap)
        if shot is not None:
            self.clear()
            self.shoot_from(shot)
            return True
        return False

    def handle_panic(self, far_panic=5100, close_panic=1000):
        if self.ball_to_goal < far_panic or self.predictions['own_goal']:
            for d_shots in self.defensive_shots:
                # for d_shot in d_shots:
                self.line(*d_shots, self.renderer.team_color(alt_color=True))

            if not self.shooting:
                self.panic = True

                for shot in self.defensive_shots:
                    if self.smart_shot(shot, cap=4):
                        return

                if self.ball_to_goal < close_panic:
                    if not self.smart_shot((self.friend_goal.right_post, self.friend_goal.left_post), weight=0, cap=2):
                        if abs(self.me.location.y) > abs(self.ball.location.y):
                            self.is_clear()
                            self.push(short_shot(Vector(z=320)))
                        elif self.is_clear():
                            team = -1 if self.team == 0 else 1
                            self.push(goto(Vector(y=self.ball.location.y + (team * 200))))
        else:
            self.panic = False

    def playstyle_defend(self):
        if self.is_clear() and self.me.airborne:
            self.recover_from_air()
        else:
            self.handle_panic()

            if not self.me.airborne:
                if self.shooting and not self.predictions['own_goal'] and self.ball_to_goal > 5000:
                    self.clear()

                if self.is_clear():
                    if not self.panic and self.me.boost < 50 and self.ball.latest_touched_team is self.team:
                        self.goto_nearest_boost(only_small=True)
                    elif self.predictions['self_from_goal'] > 750:
                        self.backcheck(simple=True)

    def playstyle_neutral(self):
        if self.is_clear() and self.me.airborne:
            self.recover_from_air()
        else:
            self.handle_panic()

            if not self.me.airborne:
                if self.is_clear() and not self.panic:
                    if self.me.boost < 72 and ((self.team == 0 and self.ball.location.y > 2048) or (self.team == 1 and self.ball.location.y < -2048)):
                        if self.me.boost < 48:
                            self.goto_nearest_boost()
                        else:
                            self.goto_nearest_boost(only_small=True)
                    else:
                        self.backcheck()
                elif self.odd_tick % 2 == 0 and self.shooting and not self.me.airborne and self.can_shoot is None:
                    shot = self.get_shot(self.offensive_shots[0])

                    if shot is not None:
                        if shot['intercept_time'] < self.shot_time - 0.05:
                            self.clear()
                            self.shoot_from(shot)

                if self.is_clear() or self.stack[0].__class__.__name__ in {"goto", "goto_boost"} and self.odd_tick == 0:
                    if not self.smart_shot(self.offensive_shots[0]) and self.is_clear():
                        self.backcheck()

    def playstyle_attack(self):
        if self.is_clear() and self.me.airborne:
            self.recover_from_air()
        else:
            if not self.me.airborne:
                if not self.shooting and (self.is_clear() or self.stack[0].__class__.__name__ == "atba" or self.shot_weight == -1):
                    if self.me.boost == 0:
                        self.clear()
                        self.backcheck(simple=True)
                    else:
                        for o_shot in self.offensive_shots:
                            self.line(*o_shot, self.renderer.team_color(alt_color=True))

                        if self.predictions['goal'] or (self.foe_goal.location.dist(self.ball.location) <= 1500 and (self.predictions['closest_enemy'] > 1500 or self.foe_goal.location.dist(self.me.location) < self.predictions['closest_enemy'] + 250)):
                            shot = self.get_shot(self.offensive_shots[0])

                            if shot is not None:
                                self.clear()
                                self.shoot_from(shot, defend=False)
                        elif self.can_shoot is None:
                            for i, o_shot in enumerate(self.offensive_shots):
                                shot = self.get_shot(o_shot)
                                if shot is not None:
                                    self.clear()
                                    self.shoot_from(shot, defend=False)

                    if self.is_clear():
                        if 275 < abs(self.ball.location.y) and abs(self.ball.location.y) > 3750:
                            self.push(atba())
                        elif self.predictions['self_to_ball'] > 1000:
                            self.push(atba(exit_distance=750, exit_flip=False))
                elif self.odd_tick % 2 == 0 and self.shooting:
                    if self.predictions['goal'] or (self.foe_goal.location.dist(self.ball.location) <= 1500 and (self.predictions['closest_enemy'] > 1400 or self.foe_goal.location.dist(self.me.location) < self.predictions['closest_enemy'] + 250)):
                        shot = self.get_shot(self.offensive_shots[0], weight=self.max_shot_weight)

                        if shot is not None:
                            if self.max_shot_weight is self.shot_weight:
                                if shot['intercept_time'] < self.shot_time - 0.05:
                                    self.clear()
                                    self.shoot_from(shot)
                            elif shot['intercept_time'] <= min(self.shot_time + (self.max_shot_weight - self.shot_weight / 3), 5):
                                self.clear()
                                self.shoot_from(shot)
                    elif self.odd_tick == 0:
                        for i, o_shot in enumerate(self.offensive_shots):
                            shot_weight = get_weight(self, index=i)

                            if shot_weight < self.shot_weight:
                                break

                            shot = self.get_shot(o_shot, weight=shot_weight)

                            if shot is not None:
                                if shot_weight is self.shot_weight:
                                    if shot['intercept_time'] < self.shot_time - 0.05:
                                        self.clear()
                                        self.shoot_from(shot)
                                elif shot['intercept_time'] <= min(self.shot_time + (shot_weight - self.shot_weight / 3), 5):
                                    self.clear()
                                    self.shoot_from(shot)

                if self.is_clear() or self.stack[0].__class__.__name__ in {"goto", "goto_boost"} and self.odd_tick == 0:
                    if not self.smart_shot(self.offensive_shots[0]) and self.is_clear():
                        if self.team == 1 and self.ball.location.y > -750:
                            self.backcheck()
                        elif self.team == 0 and self.ball.location.y < 750:
                            self.backcheck()

    def get_shot(self, target, weight=None, cap=None):
        if self.can_shoot is None:
            shots = (find_hits(self, {"target": target}, cap_=6 if cap is None else cap))['target']

            if (len(self.friends) > 0 or len(self.foes) > 1) and self.me.boost > 24:
                shots = list(itertools.chain(shots, (find_risky_hits(self, {"target": target}, cap_=4 if cap is None or cap > 4 else cap))['target']))

            if len(shots) > 0:
                shots.sort(key=lambda shot: shot.intercept_time)

                shot = shots[0]

                return {
                    "weight": get_weight(self, target) if weight is None else weight,
                    "intercept_time": shot.intercept_time,
                    "shot": shot
                }

        return None

    def shoot_from(self, shot, defend=True):
        if defend and not self.shooting and not self.is_clear():
            self.clear()

        if self.is_clear() and self.can_shoot is None:
            self.shooting = True
            self.shot_time = shot['intercept_time']
            self.shot_weight = shot['weight']

            self.push(shot['shot'])
            self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

    def backcheck(self, simple=False):
        if self.is_clear():
            self_from_goal = self.predictions['self_from_goal']
            if self_from_goal > 500:

                if self.playstyle != self.playstyles.Defensive and not simple and ((self.team == 0 and self.ball.location.y > 2048) or (self.team == 1 and self.ball.location.y < -2048)):
                    bc_x = 0
                    bc_y = 0
                    ball_loc = self.ball.location.y * side(not self.team)

                    if ball_loc > 2560 * side(not self.team):
                        if self.ball.location.x > 2048:
                            bc_x = 2048
                        elif self.ball.location.x < -2048:
                            bc_x = -2048

                    if len(self.predictions['teammates_from_goal']) > 0 and max(self.predictions['teammates_from_goal']) is self_from_goal:
                        bc_y = max(1024, ball_loc - 1000) * side(not self.team)

                    self.push(goto(Vector(bc_x, bc_y, 17), self.ball.location))
                else:
                    self.push(goto(self.friend_goal.location))

                return True

            return False

        return True

    def recover_from_air(self):
        self.clear()
        self.push(recovery(self.friend_goal.location))

    def defensive_kickoff(self):
        self.playstyle = self.playstyles.Defensive

        self.print("Defending!")

        send_comm(self, {
            "match_defender": True
        })
        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)
        self.push(goto(self.friend_goal.location, self.foe_goal.location))
        self.kickoff_done = True

    def offensive_kickoff(self):
        # note that the second value may be positive or negative
        left = (-2048 * side(self.team), 2560)
        right = (2048 * side(self.team), 2560)
        back = (0, 4608)
        # back_left = (-256 * side(self.team), 3840)
        # back_right = (256 * side(self.team), 3840)

        def kickoff_check(pair):
            return almost_equals(pair[0], self.me.location.x, 50) and almost_equals(pair[1], abs(self.me.location.y), 50)

        if kickoff_check(back):
            self.push(back_kickoff())
        elif kickoff_check(left) or kickoff_check(right):
            self.push(corner_kickoff())
        else:
            self.push(generic_kickoff())

        # if kickoff_check(right):
        #     self.push(right_kickoff())
        # elif kickoff_check(left):
        #     self.push(left_kickoff())
        # elif kickoff_check(back):
        #     self.push(back_kickoff())
        # elif kickoff_check(back_left):
        #     self.push(back_left_kickoff())
        # elif kickoff_check(back_right):
        #     self.push(back_right_kickoff())

        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

        self.print("I got it!")

        send_comm(self, {
            "attacking": True
        })

        self.playstyle = self.playstyles.Offensive

    def goto_nearest_boost(self, only_small=False):
        if self.is_clear():
            self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_NeedBoost)

            if not only_small:
                large_boosts = (boost for boost in self.boosts if boost.large and boost.active and self.friend_goal.location.y - boost.location.y >= 0)

                closest = peek_generator(large_boosts)

                if closest is not None:
                    closest_distance = closest.location.flat_dist(self.friend_goal.location)

                    for item in large_boosts:
                        item_distance = item.location.flat_dist(self.friend_goal.location)
                        if item_distance is closest_distance:
                            if item.location.flat_dist(self.me.location) < closest.location.flat_dist(self.me.location):
                                closest = item
                                closest_distance = item_distance
                        elif item_distance < closest_distance:
                            closest = item
                            closest_distance = item_distance

                    self.push(goto_boost(closest, self.ball.location))

            small_boosts = (boost for boost in self.boosts if not boost.large and boost.active)

            closest = peek_generator(small_boosts)

            if closest is not None:
                closest_distance = closest.location.flat_dist(self.me.location)

                for item in small_boosts:
                    item_distance = item.location.flat_dist(self.me.location)

                    if item_distance < closest_distance and item.location.flat_dist(self.friend_goal.location) < self.ball_to_goal - 750:
                        closest = item
                        closest_distance = item_distance

                if closest.location.flat_dist(self.friend_goal.location) < self.ball_to_goal - 750:
                    self.push(goto_boost(closest, self.ball.location))
