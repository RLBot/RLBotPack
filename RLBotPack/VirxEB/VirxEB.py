from traceback import print_exc

# from rlbot.utils.game_state_util import BallState, GameState, Physics
# from rlbot.utils.game_state_util import Vector3
from rlbot.utils.structures.quick_chats import QuickChats

from util.agent import math, VirxERLU, Vector
from util.routines import goto, goto_boost, recovery, short_shot, generic_kickoff, dynamic_backcheck, retreat, block_ground_shot
# from util.replays import back_left_kickoff, back_right_kickoff
from util.replays import back_kickoff, right_kickoff, left_kickoff
from util.tools import find_jump_shot, find_aerial, find_any_aerial, find_any_jump_shot
from util.utils import side, almost_equals, send_comm, get_weight, peek_generator


class VirxEB(VirxERLU):
    def init(self):
        self.playstyles_switch = {
            self.playstyles.Defensive: self.playstyle_defend,
            self.playstyles.Offensive: self.playstyle_attack,
            self.playstyles.Neutral: self.playstyle_neutral
        }

        self.panic_switch = {
            self.playstyles.Defensive: 1280,
            self.playstyles.Offensive: 1280,
            self.playstyles.Neutral: 640
        }

    def test(self):
        # Go to nearest boost testing
        """
        if self.is_clear():
            self.goto_nearest_boost()
        """
        # Block ground shot testing
        """
        if self.is_clear():
            if abs(self.ball.location.y) > 1000 and abs(self.me.location.y) > abs(self.ball.location.y):
                bgs = block_ground_shot()
                if bgs.is_viable(self):
                    self.push(bgs)
                    return
            else:
                self.backcheck()
        """
        # Backcheck testing
        """
        self.dbg_2d(self.ball.location)

        if self.is_clear():
            self.backcheck()
        """
        # Aerial testing
        """
        if not self.shooting and self.ball.location.z < 98:
            ball_state = BallState(Physics(location=Vector3(0, -3000 * side(self.team), self.ball.location.z), velocity=Vector3(0, 0, 2000), angular_velocity=Vector3(0, 0, 0)))
            game_state = GameState(ball=ball_state)
            self.set_game_state(game_state)

        if not self.shooting:
            self.smart_shot(())

        if self.is_clear():
            self.push(goto(Vector(), self.foe_goal.location, brake=True))
        """

    def run(self):
        if not self.kickoff_done:
            if self.is_clear():
                if len(self.friends) > 0:
                    if almost_equals(min(self.predictions['team_to_ball']), self.predictions['self_to_ball'], 5):
                        self.offensive_kickoff()
                    elif almost_equals(max(self.predictions['team_to_ball']), self.predictions['self_to_ball'], 5):
                        self.defensive_kickoff()
                elif almost_equals(self.predictions['closest_enemy'], self.predictions['self_to_ball'], 50):
                    self.offensive_kickoff()
                else:
                    self.defensive_kickoff()
        else:
            if self.can_shoot is not None and self.time - self.can_shoot >= 3:
                self.can_shoot = None

            # :D
            if side(self.team) * self.ball.location.y >= self.panic_switch[self.playstyle] or self.predictions['own_goal']:
                self.panic = True

                for shots in (self.defensive_shots, self.panic_shots):
                    for shot in shots:
                        self.line(*shot, self.renderer.team_color(alt_color=True))

                ball_loc = self.ball.location * side(self.team)
                self_loc = self.me.location * side(self.team)

                if self_loc.y <= ball_loc.y - 50 and not self.shooting and (self.is_clear() or self.stack[0].__class__.__name__ == 'goto_boost') and self.backcheck(clear_on_valid=True):
                    return

                # This is a list of all tm8s that are onside
                team_to_ball = [car.location.flat_dist(self.ball.location) for car in self.friends if car.location.y * side(self.team) >= ball_loc.y + 50 and abs(car.location.x) < abs(ball_loc.x)]
                self_to_ball = self.me.location.flat_dist(self.ball.location)
                team_to_ball.append(self_to_ball)
                team_to_ball.sort()

                if not self.shooting:
                    # What is 175?
                    # 175 is the radius of the ball rounded up (93) plus the half the length of the longest car rounded up (breakout; 66) with an extra 10% then rounded up
                    # Basicly it's the 'is an enemy dribbling the ball' detector
                    if self_loc.y > ball_loc.y and self.predictions['closest_enemy'] <= 175:
                        bgs = block_ground_shot()
                        if bgs.is_viable(self):
                            self.clear()
                            self.push(bgs)
                            return

                    if self_loc.y > ball_loc.y - 50 and ((ball_loc.x > 0 and ball_loc.x < 900 and self_loc.x > ball_loc.x and self.smart_shot(self.panic_shots[0])) or (ball_loc.x < -100 and ball_loc.x > -900 and self_loc.x < ball_loc.x and self.smart_shot(self.panic_shots[1]))):
                        return

                    if self.predictions['own_goal'] or (len(team_to_ball) > 1 and team_to_ball[math.ceil(len(team_to_ball) / 2)] + 10 > self_to_ball) or (len(team_to_ball) == 1 and self_to_ball < 2580):
                        if ball_loc.y < 1280:
                            for shot in self.defensive_shots:
                                if self.smart_shot(shot):
                                    return

                        if self_loc.y > ball_loc.y and team_to_ball[0] is self_to_ball and self.smart_shot(weight=self.max_shot_weight - 1):
                            return

                    self.backcheck()

                elif self.shooting and self.odd_tick == 0:
                    if ball_loc.y < 1280:
                        for i, d_shot in enumerate(self.defensive_shots):
                            shot_weight = get_weight(self, index=i)

                            if shot_weight < self.shot_weight:
                                break

                            shot = self.get_shot(d_shot, weight=shot_weight)

                            if shot is not None:
                                if shot_weight is self.shot_weight:
                                    if shot['intercept_time'] < self.shot_time - 0.05:
                                        self.shoot_from(shot, clear_on_valid=True)
                                elif shot['intercept_time'] <= min(self.shot_time + (shot_weight - self.shot_weight / 3), 5):
                                    self.shoot_from(shot, clear_on_valid=True)
                    else:
                        shot = None
                        if self.shot_weight is self.max_shot_weight:
                            if self_loc.y > ball_loc.y - 50:
                                if ball_loc.x > 100 and ball_loc.x < 900 and self_loc.x > ball_loc.x:
                                    shot = self.get_shot(self.panic_shots[0], weight=self.max_shot_weight)
                                elif ball_loc.x < -100 and ball_loc.x > -900 and self_loc.x < ball_loc.x:
                                    shot = self.get_shot(self.panic_shots[1], weight=self.max_shot_weight)
                        elif self_loc.y > ball_loc.y and team_to_ball[0] is self_to_ball:
                            shot = self.get_shot(weight=self.max_shot_weight - 1)

                        if shot is not None:
                            if self.shot_weight is shot['weight'] and shot['intercept_time'] < self.shot_time - 0.05:
                                self.shoot_from(shot, clear_on_valid=True)
            else:
                self.panic = False
                if not self.recover_from_air():
                    self.playstyles_switch[self.playstyle]()
        ""

    def handle_match_comm(self, msg):
        if msg.get("VirxEB") is not None and msg['VirxEB']['team'] is self.team:
            msg = msg['VirxEB']
            if self.playstyle is self.playstyles.Defensive:
                if msg.get("match_defender") and msg['index'] < self.index:
                    self.playstyle = self.playstyles.Neutral
                    self.clear()
                    self.goto_nearest_boost()
                    self.can_shoot = self.time - 0.5

                    self.print("You can defend")
            elif self.playstyle is self.playstyles.Offensive:
                if msg.get("attacking") and msg['index'] < self.index:
                    self.playstyle = self.playstyles.Neutral
                    self.clear()
                    self.goto_nearest_boost()
                    self.kickoff_done = True
                    self.can_shoot = self.time - 0.5

                    self.print("All yours!")

    def handle_quick_chat(self, index, team, quick_chat):
        try:
            if team is self.team and index is not self.index:
                if quick_chat is QuickChats.Information_IGotIt:
                    if side(self.team) * self.ball.location.y < 4200 and not self.predictions['own_goal'] and not self.shooting:
                        self.can_shoot = self.time
                        if side(self.team) * self.ball.location.y > 2560:
                            self.can_shoot += 2.5
                        elif side(self.team) * self.ball.location.y > 750:
                            self.can_shoot += 2
                        else:
                            self.can_shoot += 1
        except Exception:
            print_exc()

    def smart_shot(self, target=None, weight=None, cap=None):
        shot = self.get_shot(target, weight=weight, cap=cap)
        if shot is not None:
            self.shoot_from(shot, clear_on_valid=True)
            return True
        return False

    def playstyle_defend(self):
        if self.shooting and not self.predictions['own_goal'] and self.ball.location.z * side(self.team) < 750:
            self.clear()

        if self.is_clear():
            if self.predictions['self_from_goal'] > 2560:
                self.backcheck(simple=True)
            if self.me.boost < 72:
                self.goto_nearest_boost(only_small=self.ball.location.y * side(self.team) > -2560)
            elif self.predictions['self_from_goal'] > 750:
                self.backcheck(simple=True)

    def playstyle_neutral(self):
        if self.is_clear():
            if self.predictions['self_to_ball'] > 3840:
                self.backcheck()
            elif self.me.boost < 60 and self.ball.location.y * side(self.team) < -1280 and not self.predictions['goal'] and self.ball.location.flat_dist(self.foe_goal.location) > 1280:
                self.goto_nearest_boost()

            if self.is_clear():
                self.backcheck()
        elif self.odd_tick % 2 == 0 and self.shooting and not self.me.airborne and self.can_shoot is None:
            shot = self.get_shot(self.best_shot)
            if shot is None:
                shot = self.get_shot(self.offensive_shots[0], cap=2.5)

            if shot is not None:
                if shot['intercept_time'] < self.shot_time - 0.05:
                    self.shoot_from(shot, clear_on_valid=True)

        if self.is_clear() or self.stack[-1].__class__.__name__ in {"goto", "goto_boost", "brake", "dynamic_backcheck", "retreat"} and self.odd_tick == 0:
            if not self.smart_shot(self.best_shot) and not self.smart_shot(self.offensive_shots[0], cap=2.5) and self.is_clear():
                self.backcheck()

    def playstyle_attack(self):
        if not self.shooting or self.shot_weight == -1:
            if self.me.boost == 0:
                self.backcheck(clear_on_valid=True)
            else:
                if self.predictions['goal'] or (self.foe_goal.location.dist(self.ball.location) <= 5120 and (self.predictions['closest_enemy'] > 5120 or self.foe_goal.location.dist(self.me.location) < self.predictions['closest_enemy'] + 250)) or self.foe_goal.location.dist(self.ball.location) < 750:
                    self.line(*self.best_shot, self.renderer.team_color(alt_color=True))
                    shot = self.get_shot(self.best_shot)

                    if shot is not None:
                        self.shoot_from(shot, defend=False, clear_on_valid=True)
                elif self.can_shoot is None:
                    for o_shot in self.offensive_shots:
                        self.line(*o_shot, self.renderer.team_color(alt_color=True))

                    for i, o_shot in enumerate(self.offensive_shots):
                        shot = self.get_shot(self.best_shot) if i == 0 else None

                        if shot is None:
                            shot = self.get_shot(o_shot)

                        if shot is not None:
                            self.shoot_from(shot, defend=False, clear_on_valid=True)

            if self.is_clear():
                if abs(self.ball.location.y) > 2560 or self.predictions['self_to_ball'] > 1000:
                    self.push(short_shot(self.foe_goal.location))
                else:
                    self.backcheck()
        elif self.odd_tick % 2 == 0 and self.shooting:
            if self.predictions['goal'] or (self.foe_goal.location.dist(self.ball.location) <= 1500 and (self.predictions['closest_enemy'] > 1400 or self.foe_goal.location.dist(self.me.location) < self.predictions['closest_enemy'] + 250)):
                if self.odd_tick % 2 == 0:
                    self.line(*self.best_shot, self.renderer.team_color(alt_color=True))
                    shot = self.get_shot(self.best_shot)

                    if shot is not None:
                        if self.max_shot_weight is self.shot_weight:
                            if shot['intercept_time'] < self.shot_time - 0.05:
                                self.shoot_from(shot, clear_on_valid=True)
                        elif shot['intercept_time'] <= min(self.shot_time + (self.max_shot_weight - self.shot_weight / 3), 5):
                            self.shoot_from(shot, clear_on_valid=True)
            elif self.odd_tick == 0:
                for o_shot in self.offensive_shots:
                    self.line(*o_shot, self.renderer.team_color(alt_color=True))

                for i, o_shot in enumerate(self.offensive_shots):
                    shot = None
                    if i == 0:
                        shot_weight = self.max_shot_weight + 1
                        shot = self.get_shot(self.best_shot)

                    if shot is None:
                        shot_weight = get_weight(self, index=i)

                        if shot_weight < self.shot_weight:
                            break

                        shot = self.get_shot(o_shot, weight=shot_weight)

                    if shot is not None:
                        if shot_weight is self.shot_weight:
                            if shot['intercept_time'] < self.shot_time - 0.05:
                                self.shoot_from(shot, clear_on_valid=True)
                        elif shot['intercept_time'] <= min(self.shot_time + (shot_weight - self.shot_weight / 3), 5):
                            self.shoot_from(shot, clear_on_valid=True)

        if self.is_clear() or self.stack[-1].__class__.__name__ in {"goto", "goto_boost", "brake", "dynamic_backcheck", "retreat"} and self.odd_tick == 0:
            if not self.smart_shot(self.best_shot) and not self.smart_shot(self.offensive_shots[0]) and self.is_clear() and not self.me.airborne:
                if self.team == 1 and self.ball.location.y > self.me.location.y + 250:
                    self.backcheck()
                elif self.team == 0 and self.ball.location.y < self.ball.location.y - 250:
                    self.backcheck()

    def get_shot(self, target=None, weight=None, cap=None):
        if self.can_shoot is None:
            final = shot = aerial_shot = None

            if self.me.airborne or self.air_bud:
                if self.me.boost < 24:
                    return

                aerial_shot = find_any_aerial(self, cap_=3 if cap is None or cap > 3 else cap) if target is None else find_aerial(self, target, cap_=4 if cap is None or cap > 4 else cap)
            elif target is not None:
                shot = find_jump_shot(self, target, cap_=6 if cap is None else cap)
                aerial_shot = find_aerial(self, target, cap_=4 if cap is None or cap > 4 else cap) if self.me.boost > 24 else None
            else:
                shot = find_any_jump_shot(self, cap_=6 if cap is None else cap)
                aerial_shot = find_any_aerial(self, cap_=4 if cap is None or cap > 4 else cap) if self.me.boost > 24 else None

            if shot is not None:
                final = aerial_shot if aerial_shot is not None and aerial_shot.intercept_time <= shot.intercept_time else shot
            elif aerial_shot is not None:
                final = aerial_shot

            if final is None:
                return

            return {
                "weight": get_weight(self, target) if weight is None else weight,
                "intercept_time": final.intercept_time,
                "shot": final
            }

        return

    def shoot_from(self, shot, defend=True, clear_on_valid=False):
        if self.can_shoot is None or self.predictions['own_goal']:
            if (defend and not self.shooting and not self.is_clear()) or clear_on_valid:
                self.clear()

            if self.is_clear():
                self.shooting = True
                self.shot_time = shot['intercept_time']
                self.shot_weight = shot['weight']

                self.push(shot['shot'])
                self.send_quick_chat(QuickChats.CHAT_TEAM_ONLY, QuickChats.Information_IGotIt)

    def backcheck(self, simple=False, clear_on_valid=False):
        if self.is_clear() or clear_on_valid:
            if self.playstyle is not self.playstyles.Defensive and not simple and self.ball.location.y * side(self.team) < 2560:
                if clear_on_valid:
                    self.clear()

                self.push(dynamic_backcheck())
            elif self.me.location.dist(self.friend_goal.location + Vector(y=-250 * side(self.team))) > 500:
                if clear_on_valid:
                    self.clear()

                self.push(retreat())
            else:
                return False

        return True

    def recover_from_air(self):
        if self.is_clear() and self.me.airborne:
            self.push(recovery(self.friend_goal.location))
            return True
        return False

    def defensive_kickoff(self):
        self.playstyle = self.playstyles.Defensive
        self.can_shoot = self.time

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
        back_left = (-256 * side(self.team), 3840)
        back_right = (256 * side(self.team), 3840)

        def kickoff_check(pair):
            return almost_equals(pair[0], self.me.location.x, 50) and almost_equals(pair[1], abs(self.me.location.y), 50)

        if kickoff_check(back):
            self.push(back_kickoff())
        elif kickoff_check(left):
            self.push(left_kickoff())
        elif kickoff_check(right):
            self.push(right_kickoff())
        elif kickoff_check(back_left) or kickoff_check(back_right):
            self.push(generic_kickoff())
        else:
            self.print("Unknown kickoff position; skipping")
            self.kickoff_done = True
            return

        self.can_shoot = self.time

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
                large_boosts = (boost for boost in self.boosts if boost.large and boost.active and ((self.playstyle is self.playstyles.Offensive and boost.location.y * side(self.team) < -3000) or (self.playstyle is self.playstyles.Neutral and boost.location.y * side(self.team) > -100) or (self.playstyle is self.playstyles.Defensive and boost.location.y * side(self.team) > 3000)))

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

                    self.push(goto_boost(closest))
                    return

            small_boosts = (boost for boost in self.boosts if not boost.large and boost.active)

            closest = peek_generator(small_boosts)

            if closest is not None:
                closest_distance = closest.location.flat_dist(self.me.location)

                for item in small_boosts:
                    item_distance = item.location.flat_dist(self.me.location)

                    if item_distance < closest_distance:
                        item_loc = item.location.y * side(self.team)
                        if (self.playstyle is self.playstyles.Offensive and item_loc < -2560) or (self.playstyle is self.playstyles.Neutral and item_loc < -100) or (self.playstyle is self.playstyles.Defensive and item_loc > 1280):
                            closest = item
                            closest_distance = item_distance

                self.push(goto_boost(closest))
