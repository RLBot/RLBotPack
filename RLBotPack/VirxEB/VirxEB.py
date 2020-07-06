from queue import Empty

# from rlbot.utils.game_state_util import BallState, GameState, Physics
# from rlbot.utils.game_state_util import Vector3 as GSVec3
from rlbot.utils.structures.quick_chats import QuickChats

from util.objects import GoslingAgent, Vector3
from util.routines import goto, goto_boost, generic_kickoff, recovery, short_shot, atba, back_kickoff, corner_kickoff
from util.tools import find_hits, find_risky_hits
from util.utils import side, sign


class VirxEB(GoslingAgent):
    def init(self):
        foe_team = -1 * side(self.team)

        self.defensive_shots = (
            (self.foe_goal.left_post, self.foe_goal.right_post),
            (Vector3(3100, foe_team * 3250, 100), Vector3(2900, foe_team * 3250, 100)),
            (Vector3(-3100, foe_team * 3250, 100), Vector3(-2900, foe_team * 3250, 100)),
            (Vector3(-3600, 0, 100), Vector3(-2900, 0, 100)),
            (Vector3(3600, 0, 100), Vector3(2900, 0, 100)),
        )

        self.offensive_shots = (
            (self.foe_goal.left_post, self.foe_goal.right_post),
            (Vector3(foe_team * 893, foe_team * 5120, 100), Vector3(foe_team * 893, foe_team * 4720, 320)),
            (Vector3(-foe_team * 893, foe_team * 5120, 100), Vector3(-foe_team * 893, foe_team * 4720, 320))
        )

        self.defensive_shot = None

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
            self.push(goto(Vector3(0, 0, 0), self.foe_goal.location))
        """

        if not self.kickoff_done:
            if self.is_clear():
                self.do_kickoff()
        else:
            self.handle_matchcomms()

            if self.can_shoot != None and self.time - self.can_shoot >= 3:
                self.can_shoot = None

            if self.predictions['can_shoot'] == False and self.can_shoot == None:
                self.can_shoot = self.time + 2.75

            if not self.is_clear() and self.stack[0].__class__.__name__ == "atba" and self.predictions['closest_enemy'] < 1000:
                self.clear()
            elif self.is_clear() and self.predictions['closest_enemy'] != None and self.predictions['closest_enemy'] > 2500 and self.ball_to_goal < 1500 and side(self.team) == sign(self.me.location.y) and abs(self.me.location.y) > 5400:
                self.push(atba())
            elif self.playstyle == self.playstyles.Defensive:
                self.playstyle_defend()
            elif self.playstyle == self.playstyles.Offensive:
                self.playstyle_attack()
            else:
                self.playstyle_neutral()

            if self.is_clear() and self.playstyle == self.playstyles.Offensive:
                self.clear()

                if not self.shooting:
                    if self.team == 1 and self.me.location.y > 5100:
                        self.backcheck()
                    elif self.team == 0 and self.me.location.y < -5100:
                        self.backcheck()

            if self.debug_ball_path:
                ball_prediction = self.predictions['ball_struct']

                if ball_prediction != None:
                    for i in range(0, ball_prediction.num_slices - (ball_prediction.num_slices % self.debug_ball_path_precision) - self.debug_ball_path_precision, self.debug_ball_path_precision):
                        self.line(
                            ball_prediction.slices[i].physics.location,
                            ball_prediction.slices[i + self.debug_ball_path_precision].physics.location
                        )

            if self.shooting and not self.shooting_short:
                self.dbg_val(self.stack[0].intercept_time - self.time)

        ""

    def handle_quick_chat(self, index, team, quick_chat):
        if team != self.team and index != self.index:
            if quick_chat == QuickChats.Information_IGotIt:
                self.can_shoot = self.time

    def smart_shot(self, shot, cap=6):
        shot = self.get_shot(shot, cap=cap)
        if shot is not None:
            self.shoot_from(shot)
            return True
        return False

    def panic_at(self, far_panic, close_panic):
        if self.ball_to_goal < far_panic or self.predictions['own_goal']:
            for d_shot in self.defensive_shots:
                self.line(*d_shot, self.renderer.red())

            if not self.shooting:

                self.panic = True

                if not self.is_clear():
                    self.clear()

                if self.defensive_shot == None:
                    self.defensive_shot = 0

                if self.defensive_shot >= len(self.defensive_shots):
                    self.defensive_shot = None
                    return

                if self.smart_shot(self.defensive_shots[self.defensive_shot], cap=4):
                    self.defensive_shot = None
                    return

                if self.ball_to_goal < close_panic:
                    if not self.smart_shot((self.friend_goal.right_post, self.friend_goal.left_post), cap=2):
                        if abs(self.me.location.y) > abs(self.ball.location.y):
                            self.push(short_shot(Vector3(0, 0, 320)))
                        else:
                            team = -1 if self.team == 0 else 1
                            self.push(goto(Vector3(0, self.ball.location.y + (team * 200), 0)))

                self.defensive_shot += 1
            else:
                self.panic = False
        else:
            self.panic = False

        if not self.panic:
            self.defensive_shot = None

    def playstyle_defend(self):
        self.panic_at(5000, 1000)

        if not self.shooting:
            if self.is_clear():
                if self.me.airborne:
                    self.recover_from_air()
                elif self.me.boost < 50 and self.ball.latest_touched_team == self.team:
                    self.goto_nearest_boost(only_small=True)
                else:
                    self.backcheck(simple=True)

    def playstyle_neutral(self):
        self.panic_at(5000, 1000)

        if self.is_clear():
            if self.me.airborne:
                self.recover_from_air()
            elif self.me.boost < 72 and ((self.team == 0 and self.ball.location.y > 2048) or (self.team == 1 and self.ball.location.y < -2048)):
                if self.me.boost < 48:
                    self.goto_nearest_boost()
                else:
                    self.goto_nearest_boost(only_small=True)
            else:
                self.backcheck()

        if self.is_clear() or self.stack[0].__class__.__name__ == "goto":
            self.smart_shot(self.offensive_shots[0])

    def playstyle_attack(self):
        self.panic_at(2500, 1500)

        method_name = None

        if not self.is_clear():
            method_name = self.stack[0].__class__.__name__

        if not self.shooting and (self.is_clear() or method_name == "atba" or self.shooting_short):
            if self.me.airborne and self.is_clear():
                self.recover_from_air()
            elif self.me.boost == 0:
                self.backcheck(simple=True)
            else:
                for o_shot in self.offensive_shots:
                    self.line(*o_shot, self.renderer.team_color(alt_color=True))

                if self.predictions['goal'] == True or (self.foe_goal.location.dist(self.ball.location) <= 1500 and (self.predictions['closest_enemy'] > 1500 or self.foe_goal.location.dist(self.me.location) < self.predictions['closest_enemy'] + 250)):
                    shot = self.get_shot(self.offensive_shots[0])

                    if shot != None:
                        self.clear()
                        self.shoot_from(shot, defend=False)
                elif self.can_shoot == None:
                    for o_shot in self.offensive_shots:
                        shot = self.get_shot(o_shot)
                        if shot != None:
                            self.clear()
                            self.shoot_from(shot, defend=False)

            if self.is_clear():
                self.push(atba())

    def get_shot(self, target, cap=6):
        shots = []

        shots += (find_hits(self, {"target": target}))['target']

        if (len(self.friends) > 0 or len(self.foes) > 1) and self.me.boost > 40:
            shots += (find_risky_hits(self, {"target": target}))['target']

        def sort_function(shot):
            return shot.intercept_time

        shots.sort(key=sort_function)

        if len(shots) > 0:
            intercept = None
            for shot in shots:
                shot_class = shot.__class__.__name__

                if shot_class == "Aerial":
                    intercept = shot.target
                elif shot_class == "aerial_shot":
                    intercept = shot.intercept
                elif shot_class == "jump_shot":
                    intercept = shot.dodge_point

                if intercept != None and shot.intercept_time - self.time <= min(cap, self.me.location.dist(intercept) / 500):
                    return shot

        return None

    def handle_matchcomms(self):
        for _ in range(32):
            try:
                msg = self.matchcomms.incoming_broadcast.get_nowait()
            except Empty:
                break

            if msg.get("VirxEB") != None and msg['VirxEB']['team'] == self.team:
                msg = msg['VirxEB']
                if self.playstyle == self.playstyles.Defensive:
                    if msg.get("match_defender"):
                        if msg['index'] < self.index:
                            self.playstyle = self.playstyles.Neutral
                            self.clear()
                            self.goto_nearest_boost()
                            print(f"VirxEB ({self.index}): You can defend")
                else:
                    if msg.get("attacking"):
                        if msg['index'] < self.index:
                            self.playstyle = self.playstyles.Neutral
                            self.clear()
                            self.goto_nearest_boost()

                            print(f"VirxEB ({self.index}): All yours!")

    def shoot_from(self, shot, defend=True):
        if defend and not self.shooting and not self.is_clear():
            self.clear()

        if self.is_clear():
            self.push(shot)
            self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

    def send_comm(self, msg):
        message = {
            "index": self.index,
            "team": self.team
        }
        msg.update(message)
        self.matchcomms.outgoing_broadcast.put_nowait({
            "VirxEB": msg
        })

    def backcheck(self, simple=False):
        self_from_goal = self.predictions['self_from_goal']
        if self_from_goal > 500:
            self_is_farthest = max(self.predictions['teammates_from_goal']) == self_from_goal if len(self.predictions['teammates_from_goal']) > 0 else False

            if self.playstyle != self.playstyles.Defensive and not simple and ((self.team == 0 and self.ball.location.y > 2048) or (self.team == 1 and self.ball.location.y < -2048)):
                bc_x = 0
                bc_y = 0
                ball_loc = self.ball.location.y * side(not self.team)

                if ball_loc > 2560 * side(not self.team):
                    if self.ball.location.x > 2048:
                        bc_x = 2048
                    elif self.ball.location.x < -2048:
                        bc_x = -2048

                if self_is_farthest:
                    bc_y = max(1024, ball_loc - 1000) * side(not self.team)

                self.push(goto(Vector3(bc_x, bc_y, 17)))
            else:
                self.push(goto(self.friend_goal.location))

            return True

        return False

    def recover_from_air(self):
        self.clear()
        self.push(recovery(self.friend_goal.location))

    def do_kickoff(self):
        if len(self.friends) > 0:
            try:
                min_distance = min(self.predictions['teammates_to_ball'])
                max_distance = max(self.predictions['teammates_to_ball'])
            except ValueError:
                return

            if min_distance - 5 < self.predictions['self_to_ball'] and self.predictions['self_to_ball'] < min_distance + 5:
                self.offensive_kickoff()
            elif max_distance - 5 < self.predictions['self_to_ball'] and self.predictions['self_to_ball'] < max_distance + 5:
                self.clear()

                self.playstyle = self.playstyles.Defensive

                print(f"VirxEB ({self.index}): Defending!")

                self.send_comm({
                    "match_defender": True
                })
                self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_Defending)
                self.push(goto(self.friend_goal.location, self.foe_goal.location))
                self.kickoff_done = True
        else:
            self.offensive_kickoff()

    def offensive_kickoff(self):
        # note that the second value may be positive or negative
        left = (-2048, 2056)
        right = (2048, 2056)
        back_right = (256, 3840)
        back_left = (-256, 3840)
        back = (0, 4608)

        def kickoff_check(pair, threshold=100):
            if pair[0] - threshold < self.me.location.x and self.me.location.x < pair[0] + threshold and pair[1] - threshold < abs(self.me.location.y) and abs(self.me.location.y) < pair[1] + threshold:
                return True

            return False

        if kickoff_check(back):
            self.push(back_kickoff())
        elif kickoff_check(right) or kickoff_check(left):
            self.push(corner_kickoff())
        else:
            self.push(generic_kickoff())

        self.kickoff_done = True

        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

        print(f"VirxEB ({self.index}): I got it!")

        self.send_comm({
            "attacking": True
        })
        self.playstyle = self.playstyles.Offensive

    def goto_nearest_boost(self, only_small=False):
        self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_NeedBoost)

        if not only_small:
            large_boosts = [
                boost for boost in self.boosts if boost.large and boost.active and boost.location.dist(self.friend_goal.location) < 8000]

            if len(large_boosts) > 0:
                closest = large_boosts[0]
                closest_distance = large_boosts[0].location.dist(
                    self.friend_goal.location)

                for item in large_boosts:
                    item_disatance = item.location.dist(
                        self.friend_goal.location)
                    if item_disatance < closest_distance:
                        closest = item
                        closest_distance = item_disatance

                if closest_distance < 2500:
                    self.push(goto_boost(closest, self.ball.location))

        small_boosts = [boost for boost in self.boosts if not boost.large and boost.active]

        if len(small_boosts) > 0:
            closest = small_boosts[0]
            closest_distance = (small_boosts[0].location - self.me.location).magnitude()

            for item in small_boosts:
                item_distance = (item.location - self.me.location).magnitude()

                if item_distance < closest_distance:
                    closest = item
                    closest_distance = item_distance

            if closest_distance < 1000:
                self.push(goto_boost(closest, self.ball.location))
