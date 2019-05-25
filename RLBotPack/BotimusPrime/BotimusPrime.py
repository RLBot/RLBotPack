import math, time
from Unreal import Rotator, Vector3
from Objects import *
from Utils import *
from Preprocess import preprocess
from Actions import dodge, halfflip, arrive_with_angle
from Prediction import predict

from rlbot.utils.structures.quick_chats import QuickChats
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket


class StrategyState:
    Kickoff = "Kickoff"
    Aiming = "Aiming"
    Shooting = "Shooting"
    Clearing = "Clearing"
    Centering = "Centering"
    Dribbling = "Dribbling"
    Fallback = "Fallback"
    Saving = "Saving"
    Demolishing = "Demolishing"

class Agent(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.oldTime = time.time()

        self.halfflipping = False
        self.flip_start_time = 0.0
        self.dodging = False
        self.dodge_target = None
        self.dodge_pitch = 0
        self.dodge_roll = 0
        self.next_dodge_time = 0
        self.location = Vector3()
        self.rotation = Rotator()
        self.velocity = Vector3()
        self.speed = 0
        self.output = SimpleControllerState()
        self.boost_pads = list()
        self.boost_locations = list()
        self.boost = 0
        self.supersonic = False
        self.on_ground = True

        if self.team == 0:
            self.goal = blue_goal
            self.enemy_goal = orange_goal
        else:
            self.goal = orange_goal
            self.enemy_goal = blue_goal

        self.start = time.time()
        self.opponents = list()
        self.teammates = list()

    def get_output(self, data: GameTickPacket):

        preprocess(self, data)

        target = None
        time_left = 0.01

        dd = ( #forward or backward
            -1.0
            if abs(angle_to(self, self.location + self.velocity)) > 150
            and self.speed > 200
            else 1.0
        )
        dt = 1 / 60
        goal = self.goal
        enemy_goal = self.enemy_goal

        opponent = self.opponents[0]

        distance_to_ball = distance(self, ball)

        future = 240
        steps = predict(future)
        if len(steps) < 1:
            return self.output

        prl = None
        p_ball = None

        for step in steps:
            l, ground, t = step
            prl = l
            if reachable(self, l, t):
                if ball.location.z > 150:
                    if ground:
                        p_ball = l
                        time_left = t
                        break
                else:
                    if l.z < 120:
                        if (
                            p_ball is None
                            or distance(l, enemy_goal) < distance(p_ball, enemy_goal)
                            and distance(l, enemy_goal) < 1000
                        ):
                            p_ball = l
                            time_left = t

        if p_ball is None:
            step = steps[int(clamp(distance(self, ball) / max(1, self.speed * dt), 0, len(steps) - 1)/ 10)]
            p_ball, prl, time_left = step

        pz = p_ball.z
        p_ball.z = 0

        behind_ball = distance(self, goal) < distance(goal, p_ball)
        dir_egB = direction(self.enemy_goal, p_ball)


        # -----------------------------
        #    STRATEGY
        # -----------------------------

        state = StrategyState.Shooting

        # Kickoff
        if ball.location.x == 0 and ball.location.y == 0:
            state = StrategyState.Kickoff

        # Dribbling
        elif ball.location.z > 120 and distance_to_ball < 400 + ball.location.z * 2:
            state = StrategyState.Dribbling

        # Saving
        elif len(steps) < future:
            if distance(steps[len(steps) - 1][0], goal) < 1000:
                state = StrategyState.Saving

        # Demo if ball is going to their net
        elif (
            len(steps) < future
            and distance(ball, enemy_goal) < 1000
            and ball.velocity.size > 500
        ):
            state = StrategyState.Demolishing

        # Demolishing
        elif (
            self.supersonic
            and angle_to(self, opponent) < 10
            and distance(self, opponent)
            and opponent.speed < 1000
        ):
            state = StrategyState.Demolishing

        # Fallback
        elif distance(self, goal) > distance(goal, ball) + 300:
            state = StrategyState.Fallback
        elif (
            angle_to(self, ball) > 90
            and angle_to(opponent, ball) < 30
            and distance(self, ball) > distance(opponent, ball)
            and distance(self, goal) > 3000
        ):
            state = StrategyState.Fallback

        # Clearing
        elif distance(ball, goal) < 4000:
            state = StrategyState.Clearing

        # Shooting
        elif abs(p_ball.x) < (arena.x / 2):
            state = StrategyState.Shooting

        # Centering
        else:
            state = StrategyState.Centering

        # -----------------------------
        #    TARGET
        # -----------------------------

        # Kickoff
        if state == StrategyState.Kickoff:
            target = p_ball + dir_egB * (distance(self, p_ball) * 0.1)

            if distance_to_ball < 900:
                dodge(self,ball)

        # Fallback
        elif state == StrategyState.Fallback:
            target = arrive_with_angle(self,
                ball.location + direction(ball, goal) * distance(ball, goal) * 0.8,
                direction(ball, goal),
            )

        # Demolishing
        elif state == StrategyState.Demolishing:
            target = opponent.location

            if angle_to(self, opponent) < 1:
                self.output.boost = True

        # Shooting
        elif state == StrategyState.Shooting:
            if distance_to_ball > 1000:
                target = arrive_with_angle(self,p_ball + dir_egB * 70, dir_egB)
            else:
                target = p_ball + dir_egB * (120 + distance_to_ball * 0.5)

        # Centering
        elif state == StrategyState.Centering:
            target = arrive_with_angle(self,p_ball, dir_egB)

        # Saving
        elif state == StrategyState.Saving:
            nearest_cross_point_dist = 9999
            for step in steps:
                l, ground, t = step
                if reachable(self, l, t):
                    if distance(self, l) < nearest_cross_point_dist:
                        target = l
                        nearest_cross_point_dist = distance(self, l)
                        time_left = t
            if target is None:
                target = goal

            if not is_in_goal_cone(self, ball, goal) and distance(self, ball) < 700:
                dodge(self,ball)

        # Clearing
        elif state == StrategyState.Clearing:
            target = arrive_with_angle(self,p_ball, direction(p_ball, goal))

        # Dribbling
        elif state == StrategyState.Dribbling:

            if ball.location.z > 500 or ball.velocity.z > 500:
                vector_size = 10
            else:
                if self.boost > 10:
                    vector_size = 60
                else:
                    vector_size = 50
            if distance(ball, goal) < 2000 or distance(ball, enemy_goal) < 2000:
                vector_size = 90

            vector = dir_egB * vector_size

            if distance(self, enemy_goal) < 3000:
                vector.x *= 2

            target = p_ball + vector
            p_ball = target

            if (
                distance(self, opponent.location) < 1000
                and abs(angle_to(opponent, ball)) < 30
                and distance(opponent, enemy_goal) < distance(self, enemy_goal)
                and ball.location.z < 200
                and distance_to_ball < 200
            ):
                dodge(self,enemy_goal)

            if distance(self, opponent.location) < 500:
                if ball.location.z < 200 and distance_to_ball < 200:
                    dodge(self,enemy_goal)

            if (
                distance(self, enemy_goal) < 2000
                and abs(angle_to(self, enemy_goal)) < 20
                and ball.location.z < 200
                and distance_to_ball < 200
            ):
                dodge(self,enemy_goal)

        # target limits
        target = loc(target)
        if not inside_arena(self):
            target = self.location + direction(self, center) * 2000.0
        target.z = 0.0
        arena_limit_offset = 10
        target.x = clamp(
            target.x, -arena.x + arena_limit_offset, arena.x - arena_limit_offset
        )
        target.y = clamp(
            target.y, -arena.y + arena_limit_offset, arena.y - arena_limit_offset
        )

        # pickup boosts along the way
        boost_target = None
        if (
            self.boost < 70
            and behind_ball
            and abs(angle_to(self, target, dd)) < 30
            and distance(self, target) > 500
            and distance(self, enemy_goal) > 3000
        ):
            dist_to_best_pad = 9999
            for i in range(len(self.boost_pads)):
                bp = self.boost_pads[i]
                bpl = Vector3(self.boost_locations[i].location)
                if distance(self, bpl) < distance(self, target) / 2:
                    if abs(angle_to(self, bpl, dd)) < 10:
                        if bp.is_active or bp.timer < distance(self, bpl) / 1200:
                            if distance(self, bpl) < dist_to_best_pad:
                                boost_target = bpl
                                dist_to_best_pad = distance(self, bpl)

        if state != StrategyState.Dribbling and distance(self, target) < 500:
            target = loc(ball)

        # -----------------------------
        #    HANDLING
        # -----------------------------

        if self.on_ground:
            # forwards or backwards
            if dd > 0 and angle_to(self, target, dd) > 130 and self.speed < 200:
                if distance(self, target) < 500 or distance(self, target) > 3000:
                    dd = -1.0

            if dd < 0 and angle_to(self, target, dd) > 100 and self.speed < 300:
                dd = 1.0

            # speed
            desired_speed = optimal_speed(distance(self,p_ball), time_left, self.speed)

            if state != StrategyState.Dribbling:
                desired_speed *= 1.5

            if self.speed < desired_speed:
                self.output.throttle = 1 * dd
                if (
                    desired_speed > 1450
                    and abs(angle_to(self, target)) < 5
                    and not self.supersonic
                ):
                    if distance(self, target) < self.speed * 2 + 500:
                        self.output.boost = True
            elif self.speed > desired_speed + 70:
                self.output.throttle = -1 * dd

            if boost_target is not None:
                target = boost_target

            # dodge to get to the target faster
            elif (
                abs(angle_to(self, target)) < 1
                and distance(self, target) > self.speed * 2 + 500
                and self.speed > 1200
            ):
                dodge(self,target)

            # dodge into ball
            elif (
                state != StrategyState.Dribbling
                and distance_to_ball < 700
                and is_in_goal_cone(self, ball, enemy_goal)
                and ball.location.z < 150
                and abs(angle_to(self, ball, dd)) < 80
            ):
                dodge(self,ball)

            # jump into ball
            elif (
                state != StrategyState.Dribbling
                and distance_to_ball < 500
                and behind_ball
            ):
                if (
                    ball.location.z > 100
                    and abs(angle_to(self, ball, dd)) < 10
                    and self.speed > 1300
                ):
                    self.output.jump = True

            # drifting
            self.output.handbrake = abs(angle_to(self, target, dd)) > 90

            # steering
            self.output.steer = get_steer_towards(self, target, dd)

            # driving backwards
            if dd < 0:
                self.output.boost = False
                # halfflip
                if (
                    not self.dodging
                    and distance(self, target) > 2000
                    and self.speed > 1000
                    and abs(angle_to(self, target, dd)) < 10
                ):
                    halfflip(self)

            # me dont like walls
            if self.location.z > 400:
                self.output.handbrake = False
                self.output.steer = clamp(self.rotation.roll * 10, -1, 1)
                self.output.throttle = 1

            # kickoff
            if state == StrategyState.Kickoff:
                self.output.boost = True
                self.output.throttle = 1
                self.output.handbrake = False

        else:
            # falling, recovering
            if not self.dodging and not self.halfflipping:
                self.output.roll = -clamp(self.rotation.roll / 2, -1, 1)
                self.output.pitch = -clamp(self.rotation.pitch / 2, -1, 1)
                # self.output.yaw = clamp(angle_to(self,self.location + self.velocity)/5, -1, 1)

                if abs(self.rotation.roll) > 0.9:
                    self.output.jump = int(time.time() * 10) % 2 == 0

        # continue dodging
        if self.dodging:
            dodge(self)

        # continue halfflipping
        elif self.halfflipping:
            halfflip(self)

        return self.output
