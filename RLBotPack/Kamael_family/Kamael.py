from math import sqrt, floor, atan2, sin, cos, inf, degrees
from random import randint
from queue import Empty
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
# from rlbot.utils.game_state_util import (
#     GameState,
#     BallState,
#     CarState,
#     Physics,
#     Vector3 as vector3,
#     Rotator,
# )

# from rlbot.matchcomms.common_uses.set_attributes_message import handle_set_attributes_message,make_set_attributes_message
#from impossibum_utilities import *
from impossibum_states import *

# import cProfile, pstats, io
import numpy as np
from pathlib import Path
import time
from collections import deque


# def profile(fnc):
#     """A decorator that uses cProfile to profile a function"""
#
#     def inner(*args, **kwargs):
#         pr = cProfile.Profile()
#         pr.enable()
#         retval = fnc(*args, **kwargs)
#         pr.disable()
#         s = io.StringIO()
#         sortby = "cumulative"
#         ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
#         ps.print_stats()
#         print(s.getvalue())
#         return retval
#
#     return inner


class Kamael(BaseAgent):
    def initialize_agent(self):
        self.controller_state = None  # SimpleControllerState()
        self.me = physicsObject()
        self.ball = physicsObject()
        self.me.team = self.team
        self.me.index = self.index
        self.allies = []
        self.enemies = []
        self.start = 5
        self.flipStart = 0
        self.flipping = False
        self.controller = None
        self.gameInfo = GameInfo()
        self.onSurface = False
        self.boosts = []
        self.bigBoosts = []
        self.fieldInfo = []
        self.positions = []
        self.time = 0
        self.deltaTime = 0
        self.maxSpd = 2300
        self.l_cap = 350
        self.ballPred = []
        self.oldPreds = []
        self.selectedBallPred = None
        self.ballDelay = 0.00001
        self.renderCalls = []
        self.ballPredObj = None
        self.forward = True
        self.velAngle = 0
        self.onWall = False
        self.wallLimit = 90
        self.stateTimer = 0
        self.contested = True
        self.flipTimer = 0
        self.goalPred = None #prediction of ball going into player's net
        self.scorePred = None #prediction of ball going into opponant's net
        self.currentSpd = 1
        # octane hitbox
        self.hitbox_set = False
        self.carLength = 118.007
        self.carWidth = 84.2
        self.carHeight = 36.159
        self.functional_car_height = 120
        self.defaultElevation = 17.01
        self.defaultOffset = Vector([13.88, 0.0, 20.75])
        self.groundCutOff = 120  # 93+(self.carHeight*.8)
        self.wallCutOff = 120
        self.ballGrounded = False
        self.closestEnemyToMe = None
        self.closestEnemyToMeDistance = inf
        self.closestEnemyToBall = None
        self.closestEnemyDistances = [0, 0, 0, 0, 0]
        self.enemyAttacking = False
        self.enemyBallInterceptDelay = 0
        self.enemyPredTime = 0
        self.closestEnemyToBallDistance = inf
        self.enemyTargetVec = Vector([0, 0, 0])
        self.enemyTargetVel = Vector([0, 0, 0])
        self.contestedThreshold = 300
        self.superSonic = False
        self.wallShot = False
        self.openGoal = False
        self.boostConsumptionRate = 33.334
        self.allowableJumpDifference = 110
        self.singleJumpLimit = (
            225 + self.defaultElevation + self.allowableJumpDifference
        )  # 233 = maximum height gained from single jump
        self.doubleJumpLimit = (
            500 + self.defaultElevation + self.allowableJumpDifference
        )  # 498 = maximum height gained from double jump
        self.wallShotsEnabled = True
        self.DoubleJumpShotsEnabled = True
        self.touch = None
        self.targetDistance = 1500
        self.fpsLimit = 1 / 120
        self.gravity = -650
        self.jumpPhysics = physicsObject()
        self.hits = [None, None, None, None, None]
        self.sorted_hits = []
        self.first_hit = None
        self.update_time = 0
        self.dribbler = False
        self.goalie = False
        self.last_tick = 0
        self.tick_timers = deque(maxlen=20)
        self.fakeDeltaTime = 1.0 / 120.0
        self.physics_tick = 1.0 / 120
        self.multiplier = 1
        if self.name.lower().find("st. peter") != -1:
            self.goalie = True

        if self.name.lower().find("wyrm") != -1:
            self.dribbler = True
            self.multiplier = 2

        self.accelerationTick = self.boostAccelerationRate * self.fakeDeltaTime
        self.aerialAccelerationTick = (self.boostAccelerationRate+66.666667) * self.fakeDeltaTime
        self.currentHit = hit(
            0, 6, 0, Vector([0, 0, 92.75]), Vector([0, 0, 0]), False, 6, self.team
        )
        self.resetLimit = 2
        self.resetCount = 0
        self.resetTimer = 0
        self.timid = False
        self.dribbling = False
        self.goalward = False
        self.stubbornessTimer = 0
        self.stubbornessMax = 600
        self.stubbornessMin = 25
        if self.ignore_kickoffs:
            self.stubbornessMin = 100
        self.stubborness = self.stubbornessMin
        self.activeState = PreemptiveStrike(self)
        self.contestedTimeLimit = 0.5
        self.demoSpawns = [
            [Vector([-2304, -4608, 0]), Vector([2304, -4608, 0])],
            [Vector([2304, 4608, 0]), Vector([-2304, 4608, 0])],
        ]
        self.rotationNumber = 1
        self.hyperJumpTimer = 0
        self.reachLength = 120
        self.groundReachLength = 120
        self.debugging = False
        self.angleLimit = 60
        self.lastMan = Vector([0, 0, 0])
        self.aerialsEnabled = True
        self.aerialsLimited = False
        self.aerial_timer_limit = 0
        self.kickoff_timer = 0
        self.blueGoal = Vector([0, -5120, 0])
        self.orangeGoal = Vector([0, 5120, 0])
        self.boostThreshold = 65
        self.test_done = True
        self.available_delta_v = 0
        self._forward, self.left, self.up = (
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
        )
        self.defaultRotation = None
        self.recovery_height = 60
        self.log = []
        self.test_pred = predictionStruct(Vector([0, 0, 0]), -1)
        self.game_active = True
        self.hit_finding_thread = None
        self.boost_counter = 0
        self.default_demo_location = Vector([20000, 0, 0])
        self.double_point_limit = 500
        self.p_tournament_mode = False
        self.cached_jump_sim = []
        self.singleJumpShotTimer = 0
        self.doubleJumpShotTimer = 0
        self.boost_testing = False
        self.lastSpd = 0
        self.grounded_timer = 0
        self.boost_duration_min = 2
        self.enemyGoalLocations = []
        self.goal_locations = []
        self.boost_gobbling = False
        self.ally_hit_count = 0
        self.ally_hit_info = []
        self.aerial_min = 200
        self.match_ended = False
        self.roof_height = None
        self.ball_size = 93
        self.demo_monster = self.demo_determiner()
        self.aerial_hog = False
        self.ignore_list_names = self.get_ignore_list()
        self.ignore_list_indexes = []
        self.ignore_checked = False
        self.team_size_limit = 3
        self.takeoff_speed = 0.35
        self.demo_rotations = True
        self.boost_req = (1/120) * 6.5 * self.boostAccelerationRate
        self.seekerbot = False
        self.aerial_reach = 145
        self.min_time = self.fakeDeltaTime * 2
        self.cannister_greed = 1500
        self.fake_single_sim = [90, 0.2, 120, 0.2, [0, 0, 0], 0, False]
        self.aerial_slope = 4950 / 5120
        self.aim_range = 3000
        self.coms_timer = time.perf_counter()
        self.send_rate = 1 / 10
        self.coms_key = "tmcp_version"
        self.allowed_keys = [self.coms_key, "team", "index", "action"]
        self.action_obj = Action({"type": "READY", "time": -1})
        self.cached_action = Action({"type": "READY", "time": -1})
        self.ally_actions = {}
        self.ignored_boosts = []
        self.my_corners = [0, 1]
        self.linep_info = None
        if self.team == 1:
            self.my_corners = [2, 3]
        if self.dribbler:
            self.DoubleJumpShotsEnabled = False
            self.aerialsEnabled = False

        self.winning = False
        ########################
        "floating sim stuff"
        self.collision_location = Vector([0, 0, 0])
        self.simulated_velocity = Vector([0, 0, 0])
        self.sim_frames = []
        self.collision_timer = 5
        self.aim_direction = Vector([0, 0, -1])
        self.roll_type = 1
        self.squash_index = 2
        self.last_float_sim_time = 0
        self.on_ground_estimate = 0
        self.wall_landing = False
        self.aerial_accel_limit = self.boostAccelerationRate
        self.scared = False
        self.min_aerial_buffer = 100
        self.jumped = False
        self.ally_back_count = 0
        self.coast_decel = -525 * self.fakeDeltaTime
        self.active_decel = -3500 * self.fakeDeltaTime
        self.on_correct_side = False
        self.offensive = False
        self.speed_maximums = [
            [0,0.0069],
            [500,0.00398],
            [1000,0.00235],
            [1500,0.001375],
            [1750,0.0011],
            [2300,0.00088]
        ]
        self.scores = [0,0]
        self.personality_switch()
        self.last_controller = SimpleControllerState()

    def find_sim_frame(self, game_time):
        for frame in self.sim_frames:
            if frame[2] >= game_time:
                return frame
        return None

    def set_boost_grabbing(self, index):
        pass

    def find_first_aerial_contact(self, start_time: float, stop_time: float):
        max_dist = self.aerial_reach * 0.95
        started = False
        for i in range(0, self.ballPred.num_slices):
            if not started:
                if i % 10 != 0:
                    continue
                if self.ballPred.slices[i].game_seconds > start_time:
                    started = True

            sim_frame = self.find_sim_frame(self.ballPred.slices[i].game_seconds)
            if sim_frame is not None:
                pred_loc = convertStructLocationToVector(self.ballPred.slices[i])
                if findDistance(pred_loc,sim_frame[0]) < max_dist:
                    return sim_frame[0].scale(1), pred_loc, self.ballPred.slices[i].game_seconds
            if self.ballPred.slices[i].game_seconds > stop_time:
                break

        return None

    def personality_switch(self):
        if self.name.lower().find("nebulous") != -1:
            self.dribbler = False
            self.goalie = False
            self.demo_monster = False
            self.aerial_hog = False

            self.DoubleJumpShotsEnabled = True
            self.aerialsEnabled = True
            self.aerialsLimited = False
            self.min_aerial_buffer = 100
            self.aerial_min = 200
            self.demo_rotations = True

            roll = randint(0, 4)
            if roll == 0:
                print(f"{self.name} is now kamael")
                pass

            elif roll == 1:
                self.goalie = True
                self.demo_rotations = False
                print(f"{self.name} is now st peter")

            elif roll == 2:
                self.dribbler = True
                self.DoubleJumpShotsEnabled = False
                self.aerialsEnabled = False
                print(f"{self.name} is now wyrm")

            elif roll == 3:
                self.aerial_hog = True
                self.min_aerial_buffer = -250
                self.aerial_min = 0
                self.demo_rotations = False
                print(f"{self.name} is now rapha")

            elif roll == 4:
                self.demo_monster = True
                self.demo_rotations = True
                print(f"{self.name} is now aries")

    def update_action(self, action):
        self.cached_action = self.action_obj
        self.action_obj = Action(action)

    def recieve_coms(self):
        for i in range(10):  # limit the amount of messages processed per tick.
            try:
                msg = (
                    self.matchcomms.incoming_broadcast.get_nowait()
                )  # grab a message from the queue
            except Empty:
                break

            if TMCP_verifier(msg) and msg["team"] == self.team:
                if msg["action"]["type"] == "BALL":
                    msg["action"]["vector"] = None

                elif msg["action"]["type"] == "READY":
                    msg["action"]["vector"] = None

                self.ally_actions[msg["index"]] = msg

    def tmcp_teammates(self)->bool:
        for tm in self.allies:
            if tm.index not in self.ally_actions:
                return False
        return True


    def send_coms(self):

        outgoing_msg = {
            "tmcp_version": [1, 0],
            "team": self.team,
            "index": self.index,
            "action": self.action_obj.action,
        }
        self.ally_actions[self.index] = outgoing_msg
        self.matchcomms.outgoing_broadcast.put_nowait(outgoing_msg)

    def manage_transmissions(self):
        if self.rotationNumber == 1:
            self.update_action(
                {
                    "type": "BALL",
                    "time": float(self.currentHit.prediction_time),
                    "direction": direction(
                        self.me.location.flatten(),
                        self.currentHit.pred_vector.flatten(),
                    ).data,
                }
            )

        _time = time.perf_counter()
        # if self.action_obj != self.cached_action or _time - self.coms_timer > self.send_rate:
        if _time - self.coms_timer > self.send_rate:
            self.cached_action = self.action_obj
            self.send_coms()
            self.coms_timer = _time

    def delta_handler(self):
        if False:
            #calculates a rolling avg for delta time
            time_diff = self.time - self.last_tick
            self.last_tick = self.time

            #should filter out occasional outliers such as resets, pausing, etc
            if time_diff < 0.0666667: #15 fps
                self.tick_timers.appendleft(max(time_diff, 0.00833333)) #120 fps
                self.fakeDeltaTime = sum(self.tick_timers)/max(1, len(self.tick_timers))

            self.accelerationTick = (self.boostAccelerationRate + 66.666667) * self.fakeDeltaTime
            self.aerialAccelerationTick = (self.boostAccelerationRate + 66.666667) * self.fakeDeltaTime

    def get_ignore_list(self):
        ignore_list = []
        with open(
            str(Path(__file__).parent.absolute()) + "/bot_ignore_list.txt"
        ) as specials:
            for name in specials.readlines():
                ignore_list.append(str(name.strip()).lower())
        return ignore_list

    def is_hot_reload_enabled(self):
        return False

    def retire(self):
        self.game_active = False
        if self.hit_finding_thread is not None:
            self.hit_finding_thread.close()

    def init_match_config(self, match_config: "MatchConfig"):
        self.matchSettings = match_config
        self.boostMonster = self.matchSettings.mutators.boost_amount == "Unlimited"
        self.ignore_kickoffs = self.matchSettings.game_mode == "Heatseeker"
        base_boost_accel = 991 + (2 / 3)
        boost_multi = float(self.matchSettings.mutators.boost_strength[:-1])
        self.boostAccelerationRate = base_boost_accel * boost_multi
        #print(boost_multi, self.boostAccelerationRate)

    def demoRelocation(self, car):
        return self.default_demo_location

    def lineup_check(self):
        if self.linep_info is None:
            self.linep_info = verify_alignment(self, self.currentHit.pred_vector, self.carLength*0.5)
        return self.linep_info


    def getActiveState(self):
        if type(self.activeState) == LeapOfFaith:
            return 0
        if type(self.activeState) == PreemptiveStrike:
            return 1
        if type(self.activeState) == GroundAssault:
            return 2
        if type(self.activeState) == GroundShot:
            return 3
        if type(self.activeState) == HolyProtector:
            return 4
        if type(self.activeState) == BlessingOfDexterity:
            return 5
        if type(self.activeState) == Wings_Of_Justice:
            return 6

        return -1

    def setHalfFlip(self):
        _time = self.time
        if _time - self.flipTimer >= 1.9:
            controls = []
            timers = []

            control_1 = SimpleControllerState()
            control_1.throttle = -1
            control_1.jump = True

            controls.append(control_1)
            timers.append(0.125)

            controls.append(SimpleControllerState())
            timers.append(self.fakeDeltaTime * 2)

            control_3 = SimpleControllerState()
            control_3.throttle = -1
            control_3.pitch = 1
            control_3.jump = True
            controls.append(control_3)
            timers.append(self.fakeDeltaTime * 2)

            control_4 = SimpleControllerState()
            control_4.throttle = -1
            control_4.pitch = -1
            control_4.roll = -0.1
            # control_4.jump = True

            controls.append(control_4)
            timers.append(0.5)

            controls.append(SimpleControllerState(throttle=1))
            timers.append(0.6)

            self.activeState = Divine_Mandate(self, controls, timers)

            self.flipTimer = self.time
            self.stubbornessTimer = 2
            self.stubborness = self.stubbornessMax

    def aerialGetter(self, pred, target, time):
        return Wings_Of_Justice(self, pred, target, time)

    def setJumpPhysics(self):
        self.jumpPhysics.location = self.me.location
        self.jumpPhysics.velocity = self.me.velocity + self.up.scale(500)
        self.jumpPhysics.velocity.cap(2300)

        self.jumpPhysics.avelocity = self.me.avelocity

    def determineFacing(self):
        offset = self.me.location + self.me.velocity.normalize().scale(500)
        loc = toLocal(offset, self.me)
        angle = correctAngle(degrees(atan2(loc[1], loc[0])))

        if abs(angle) > 90:
            if self.currentSpd <= self.stubborness:
                self.forward = True
            else:
                self.forward = False
        else:
            self.forward = True

        self.velAngle = angle

    def setPowershot(self, delay, target):
        self.activeState = RighteousVolley(self, delay, target)

    def get_jump_sim(self, z):
        return jumpSimulatorNormalizingJit(
            float32(self.gravity),
            float32(self.fakeDeltaTime),
            np.array(self.me.velocity.data, dtype=np.dtype(float),),
            np.array(self.up.data, dtype=np.dtype(float),),
            np.array(self.me.location.data, dtype=np.dtype(float),),
            float32(self.defaultElevation),
            float32(self.takeoff_speed),
            float32(z),
            True,
        )

    def setJumping(self, targetType, target=None):
        _time = self.time
        if _time - self.flipTimer >= 1.85:
            if self.onSurface and not self.jumped:
                if targetType == 2:
                    self.createJumpChain(2, 400, jumpSim=None, set_state=True)
                    self.flipTimer = _time

                elif targetType == 20:
                    self.activeState = Deliverance(
                        self, big_jump=True if target is None else False
                    )
                    # self.createJumpChain(2, 400, jumpSim=None, set_state=True)
                    # self.flipTimer = _time

                elif targetType == 0:
                    self.createJumpChain(
                        0.15, 90, jumpSim=self.fake_single_sim, aim=False
                    )
                    self.flipTimer = _time

                elif targetType != -1:
                    self.activeState = LeapOfFaith(self, targetType, target=target)
                    self.flipTimer = _time

                else:
                    self.activeState = Divine_Mandate(
                        self, [SimpleControllerState(jump=True)], [0.21]
                    )
                    self.flipTimer = _time - 1

    def setGuidance(self, target: Vector):
        if self.gravity <= -650:
            self.activeState = DivineGuidance(self, target)

    def getCurrentSpd(self):
        return self.me.velocity.magnitude()

    def updateSelectedBallPrediction(self, ballStruct):
        x = physicsObject()
        x.location = Vector(
            [
                ballStruct.physics.location.x,
                ballStruct.physics.location.y,
                ballStruct.physics.location.z,
            ]
        )
        x.velocity = Vector(
            [
                ballStruct.physics.velocity.x,
                ballStruct.physics.velocity.y,
                ballStruct.physics.velocity.z,
            ]
        )
        x.rotation = Vector(
            [
                ballStruct.physics.rotation.pitch,
                ballStruct.physics.rotation.yaw,
                ballStruct.physics.rotation.roll,
            ]
        )
        x.avelocity = Vector(
            [
                ballStruct.physics.angular_velocity.x,
                ballStruct.physics.angular_velocity.y,
                ballStruct.physics.angular_velocity.z,
            ]
        )
        x.local_location = localizeVector(x.location, self.me)
        self.ballPredObj = x

    def preprocess(self, game):
        self.ball_size = game.game_ball.collision_shape.sphere.diameter / 2
        self.gameInfo.update(game)
        self.oldPreds = self.ballPred
        self.ballPred = self.get_ball_prediction_struct()
        blue_score = game.teams[0].score
        orange_score = game.teams[1].score
        self.winning = (
            True
            if (self.team == 0 and blue_score > orange_score)
            or (self.team == 1 and blue_score < orange_score)
            else False
        )
        if blue_score != self.scores[0] or orange_score != self.scores[1]:
            self.personality_switch()

        self.linep_info = None

        self.scores[0], self.scores[1] = blue_score, orange_score
        self.players = [self.index]
        car = game.game_cars[self.index]
        ally_count = len(self.allies)
        enemy_count = len(self.enemies)
        self.deltaTime = clamp(
            1, self.fpsLimit, game.game_info.seconds_elapsed - self.time
        )
        self.time = game.game_info.seconds_elapsed
        self.delta_handler()

        self.me.demolished = car.is_demolished

        updateHits = False
        self.gravity = game.game_info.world_gravity_z
        if not self.defaultRotation:
            self.defaultRotation = Vector3(
                car.physics.rotation.pitch,
                car.physics.rotation.yaw,
                car.physics.rotation.roll,
            )

        if not car.is_demolished:
            self.me.location = Vector(
                [car.physics.location.x, car.physics.location.y, car.physics.location.z]
            )
            self.me.velocity = Vector(
                [car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z]
            )
            self.me.rotation = Vector(
                [
                    car.physics.rotation.pitch,
                    car.physics.rotation.yaw,
                    car.physics.rotation.roll,
                ]
            )
            self.me.avelocity = Vector(
                [
                    car.physics.angular_velocity.x,
                    car.physics.angular_velocity.y,
                    car.physics.angular_velocity.z,
                ]
            )
            self.me.boostLevel = car.boost
            self.onSurface = car.has_wheel_contact
            self.superSonic = car.is_super_sonic
            self.lastSpd = self.currentSpd * 1
            self.currentSpd = clamp(2300, 1, self.getCurrentSpd())
            self.me.matrix = rotator_to_matrix(self.me)
            self._forward, self.left, self.up = self.me.matrix
            self.me.rotational_velocity = matrixDot(self.me.matrix, self.me.avelocity)
            self.me.retreating = player_retreat_status(
                self.me, self.ball.location, self.team, num_allies=ally_count
            )
            if self.me.retreating and self.team == 5:
                if distance2D(self.me.location, self.ball.location) < 300:
                    self.me.retreating = False
        else:
            self.me.location = self.demoRelocation(car)
            self.me.velocity = Vector([0, 0, 0])
            self.me.rotation = Vector([0, 0, 0])
            self.me.avelocity = Vector([0, 0, 0])
            self.me.boostLevel = 34
            self.onSurface = True
            self.superSonic = False
            self.currentSpd = 0.0001
            self.me.matrix = rotator_to_matrix(self.me)
            self._forward, self.left, self.up = self.me.matrix
            self.me.rotational_velocity = matrixDot(self.me.matrix, self.me.avelocity)

            self.me.retreating = True

        if not self.hitbox_set:
            self.fieldInfo = self.get_field_info()
            self.carLength = car.hitbox.length
            self.carWidth = car.hitbox.width
            self.carHeight = car.hitbox.height

            self.functional_car_height = self.carHeight
            self.groundCutOff = (self.ball_size + self.carHeight + 17) * 0.9
            self.wallCutOff = (self.ball_size + self.carHeight + 17) * 0.9
            self.hitbox_set = True

            self.defaultOffset = Vector(
                [
                    car.hitbox_offset.x * 1,
                    car.hitbox_offset.y * 1,
                    car.hitbox_offset.z * 1,
                ]
            )
            if int(self.carLength) == 118 or int(self.carLength == 127):
                self.defaultElevation = 17 + self.defaultOffset[2]
            else:
                self.defaultElevation = 18 + self.defaultOffset[2]

            self.recovery_height = self.defaultElevation + 15

            single_jump = jumpSimulatorNormalizingJit(
                float32(self.gravity),
                float32(self.fakeDeltaTime),
                np.array([0, 0, 0], dtype=np.dtype(float)),
                np.array([0, 0, 1], dtype=np.dtype(float)),
                np.array([0, 0, self.defaultElevation], dtype=np.dtype(float)),
                float32(self.defaultElevation),
                float32(10),
                float32(10000),
                False,
            )

            double_jump = jumpSimulatorNormalizingJit(
                float32(self.gravity),
                float32(self.fakeDeltaTime),
                np.array([0, 0, 0], dtype=np.dtype(float)),
                np.array([0, 0, 1], dtype=np.dtype(float)),
                np.array([0, 0, self.defaultElevation], dtype=np.dtype(float)),
                float32(self.defaultElevation),
                float32(10),
                float32(10000),
                True,
            )

            self.doubleJumpSim = double_jump
            self.singleJumpLimit = (self.allowableJumpDifference*0.8) + single_jump[2]
            self.doubleJumpLimit = self.allowableJumpDifference + double_jump[2]
            self.singleJumpShotTimer = single_jump[3]
            self.doubleJumpShotTimer = double_jump[3] - 0.04167

            if self.debugging:
                self.log.append(
                    f"Kamael on team {self.team} hitbox (length:{self.carLength} width:{self.carWidth} height:{self.carHeight}) reach: {self.reachLength} grounder limit: {self.groundCutOff}"
                )
                self.log.append(
                    f"single jump limit: {self.singleJumpLimit} double jump limit: {self.doubleJumpLimit}"
                )

            if self.name.lower().find("peter") != -1:
                self.goalie = True
                self.demo_rotations = False
                if self.p_tournament_mode:
                    for i in range(game.num_cars):
                        car = game.game_cars[i]
                        if car.team == self.team:
                            if car.name.lower().find("st. peter") != -1:
                                if i < self.index:
                                    self.goalie = False

            elif self.name.lower().find("aries") != -1:
                self.demo_monster = True

            elif self.name.lower().find("rapha") != -1:
                self.aerial_hog = True
                self.min_aerial_buffer = -250
                self.aerial_min = 0
                self.demo_rotations = False

            # self.cached_jump_sim = jumpSimulatorNormalizing(
            #     self, 3, 1000, doubleJump=True
            # )[-1]


            if self.gravity > -650 and self.boostMonster:
                self.doubleJumpLimit = self.singleJumpLimit + 100
                self.DoubleJumpShotsEnabled = False

            self.enemyGoalLocations.append(
                Vector([893 * -sign(self.team), 5120 * -sign(self.team), 0])
            )
            self.enemyGoalLocations.append(Vector([0, 5120 * -sign(self.team), 0]))
            self.enemyGoalLocations.append(
                Vector([893 * sign(self.team), 5120 * -sign(self.team), 0])
            )

            self.goal_locations.append(
                Vector([893 * -sign(self.team), 5120 * sign(self.team), 0])
            )
            self.goal_locations.append(Vector([0, 5120 * sign(self.team), 0]))
            self.goal_locations.append(
                Vector([893 * sign(self.team), 5120 * sign(self.team), 0])
            )

            add_car_offset(self, projecting=False)
            adjusted_roof_height = self.roof_height
            self.groundReachLength = (
                floor(
                    sqrt(
                        adjusted_roof_height
                        * (self.ball_size * 2 - adjusted_roof_height)
                    )
                )
                + self.carLength * 0.5
            )
            self.reachLength = self.carLength * 0.5 + self.ball_size
            self.aerial_reach = self.carLength * 0.5 + self.ball_size

            if (
                not self.ignore_checked
                and not self.goalie
                and not self.demo_monster
                and not self.aerial_hog
            ):
                active_teammates = []
                self.ignore_list_indexes = []
                self.ignore_checked = True
                for i in range(game.num_cars):
                    if i != self.index:
                        car = game.game_cars[i]
                        if car.team == self.team:
                            for name in self.ignore_list_names:
                                if str(car.name).lower().find(name.lower()) != -1:
                                    if i not in self.ignore_list_indexes:
                                        self.ignore_list_indexes.append(i)
                                        print(
                                            f"{self.name} will ignore {car.name} in rotation logic"
                                        )

                            if i not in self.ignore_list_indexes:
                                active_teammates.append(i)
                    else:
                        active_teammates.append(self.index)

                kam_list = []
                for i in range(game.num_cars):
                    car = game.game_cars[i]
                    if car.team == self.team:
                        if str(car.name).lower().find("kamael") != -1:
                            kam_list.append(i)

                if len(kam_list) > self.team_size_limit:
                    if self.index == kam_list[self.team_size_limit]:
                        self.goalie = True
                        self.demo_rotations = False
                    elif self.index in kam_list[self.team_size_limit:]:
                        self.demo_monster = True
                    else:
                        for ally in kam_list[self.team_size_limit+1:]:
                            self.ignore_list_indexes.append(ally)

        add_car_offset(self, projecting=self.debugging)
        self.jumped = car.jumped

        if self.stubbornessTimer > 0:
            self.stubbornessTimer -= self.deltaTime
            if self.stubbornessTimer <= 0:
                self.stubborness = self.stubbornessMin

        ball = game.game_ball.physics
        self.ball.location = Vector([ball.location.x, ball.location.y, ball.location.z])
        self.ball.velocity = Vector([ball.velocity.x, ball.velocity.y, ball.velocity.z])
        self.ball.rotation = Vector(
            [ball.rotation.pitch, ball.rotation.yaw, ball.rotation.roll]
        )
        self.ball.avelocity = Vector(
            [ball.angular_velocity.x, ball.angular_velocity.y, ball.angular_velocity.z]
        )
        self.ball.local_location = localizeVector(self.ball.location, self.me)
        ball.lastTouch = game.game_ball.latest_touch.time_seconds
        ball.lastToucher = game.game_ball.latest_touch.player_name
        touch = ballTouch(game.game_ball.latest_touch)
        if not self.touch:
            self.touch = touch

        if self.touch != touch:
            self.touch = touch
            updateHits = True

        self.on_correct_side = self.me.location[1] * sign(
            self.team
        ) >= self.ball.location[1] * sign(self.team)
        self.offensive = self.ball.location[1] * sign(self.team) < 0

        self.allies.clear()
        self.enemies.clear()

        for i in range(game.num_cars):
            if i != self.index and i not in self.ignore_list_indexes:
                car = game.game_cars[i]
                _obj = physicsObject()
                _obj.index = i
                _obj.team = car.team
                _obj.demolished = car.is_demolished
                if not car.is_demolished:
                    _obj.location = Vector(
                        [
                            car.physics.location.x,
                            car.physics.location.y,
                            car.physics.location.z,
                        ]
                    )
                    _obj.velocity = Vector(
                        [
                            car.physics.velocity.x,
                            car.physics.velocity.y,
                            car.physics.velocity.z,
                        ]
                    )
                    _obj.rotation = Vector(
                        [
                            car.physics.rotation.pitch,
                            car.physics.rotation.yaw,
                            car.physics.rotation.roll,
                        ]
                    )
                    _obj.avelocity = Vector(
                        [
                            car.physics.angular_velocity.x,
                            car.physics.angular_velocity.y,
                            car.physics.angular_velocity.z,
                        ]
                    )
                    _obj.boostLevel = car.boost
                    _obj.local_location = localizeVector(_obj, self.me)
                    _obj.onSurface = car.has_wheel_contact
                    if car.team == self.team:
                        _obj.retreating = player_retreat_status(
                            _obj, self.ball.location, car.team, num_allies=ally_count
                        )
                    else:
                        _obj.retreating = player_retreat_status(
                            _obj, self.ball.location, car.team, num_allies=enemy_count
                        )
                else:
                    _obj.location = self.demoRelocation(_obj)
                    _obj.velocity = Vector([0, 0, 0])
                    _obj.rotation = Vector([0, 0, 0])
                    _obj.avelocity = Vector([0, 0, 0])
                    _obj.boostLevel = 33
                    _obj.onSurface = True
                    _obj.retreating = True
                    _obj.man = 3

                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)
        self.boosts = []
        self.bigBoosts = []

        for index in range(self.fieldInfo.num_boosts):
            packetBoost = game.game_boosts[index]
            fieldInfoBoost = self.fieldInfo.boost_pads[index]
            boostStatus = False
            if packetBoost.timer <= 0:
                if packetBoost.is_active:
                    boostStatus = True
            boost_obj = Boost_obj(
                [
                    fieldInfoBoost.location.x,
                    fieldInfoBoost.location.y,
                    fieldInfoBoost.location.z,
                ],
                fieldInfoBoost.is_full_boost,
                boostStatus,
                index,
            )
            self.boosts.append(boost_obj)
            if boost_obj.bigBoost:
                self.bigBoosts.append(boost_obj)

        self.onWall = False
        self.wallShot = False
        self.aerialsEnabled = True #len(self.allies) > 0
        self.aerialsLimited = False
        self.aerial_timer_limit = clamp(6, 2, len(self.allies) * 3)
        # if len(self.allies) < 1 or self.dribbler:
        if self.dribbler or self.goalie:
            self.aerialsEnabled = False
            self.aerialsLimited = True

        if (
            self.onSurface
            and (abs(self.me.location[0]) > 3900 or abs(self.me.location[1]) > 4900)
            and self.me.location[2] > 50
            and abs(self.me.location[1]) < 5120
        ):
            self.onWall = self.up[2] < 0.98
        if len(self.allies) > 0:
            self.lastMan = lastManFinder(self).location
        else:
            self.lastMan = self.me.location

        self.determineFacing()
        self.dribbling = dirtyCarryCheck(self)
        self.boost_gobbling = False
        self.findClosestToEnemies()
        self.resetCount += 1
        self.setJumpPhysics()

        if (
            not self.onSurface
            and (self.time - self.last_float_sim_time) > self.fakeDeltaTime * 5 or self.last_controller.boost
        ):
            run_float_simulation(self)

        if len(self.hits) < 1:
            self.update_hits()
        else:
            if validateExistingPred(self, self.test_pred):
                for h in self.hits:
                    if h is not None:
                        h.update(self.time)
                self.sorted_hits = SortHits(self.hits)
                if (
                    len(self.sorted_hits) < 1
                    or self.sorted_hits[0].time_difference() > 5
                ):
                    updateHits = True

                refresh_timer = 0.15
            else:
                self.hits = [None, None, None, None, None]
                self.sorted_hits = self.hits
                updateHits = True

            if (
                updateHits
                or self.sorted_hits[0].prediction_time < self.time
                or self.time - self.update_time > refresh_timer
            ):
                self.update_hits()

            elif not self.validate_current_shots():
                self.update_hits()

        if self.resetCount >= self.resetLimit:
            findEnemyHits(self)
            self.resetCount = 0
        else:
            self.enemyBallInterceptDelay = self.enemyPredTime - self.time

        if self.gameInfo.is_kickoff_pause:
            self.kickoff_timer = self.time
            self.currentHit = hit(
                self.time,
                self.time,
                0,
                Vector([0, 0, 95]),
                Vector([0, 0, 0]),
                False,
                0,
                self.team,
            )

        self.ignored_boosts.clear()
        self.recieve_coms()

        for index in self.ally_actions:
            if (
                index != self.index
                and self.ally_actions[index]["action"]["type"] == "BOOST"
            ):
                self.ignored_boosts.append(self.ally_actions[index]["action"]["target"])



    def calculate_delta_velocity(self, time_alloted, add_bonus=False):
        boost_duration = self.me.boostLevel / 33.333
        bonus_vel = 0
        if self.onSurface and not self.onWall and self.me.boostLevel > 0 and add_bonus:
            bonus_vel = 500

        if boost_duration >= time_alloted or self.boostMonster:
            return (1057 * time_alloted) + bonus_vel

        else:
            return (
                (1057 * boost_duration)
                + bonus_vel
                + (66 * (time_alloted - boost_duration))
            )

    def findClosestToEnemies(self):
        if len(self.enemies) > 0:
            (
                self.closestEnemyToBall,
                self.closestEnemyToBallDistance,
            ) = findEnemyClosestToLocation(self, self.ball.location, demo_bias=True)
            (
                self.closestEnemyToMe,
                self.closestEnemyToMeDistance,
            ) = findEnemyClosestToLocation(self, self.me.location, demo_bias=True)
            self.contested = False
            self.enemyAttacking = False

            if self.closestEnemyToBallDistance <= self.contestedThreshold:
                self.contested = True
                self.enemyAttacking = True

            elif self.enemyAttackingBall():
                self.enemyAttacking = True


            if self.closestEnemyToBall is not None:
                if self.enemyTargetVec is not None:
                    etv = self.enemyTargetVec
                else:
                    etv = self.ball.location

                closestEnemyToBallTargetDistance = findDistance(
                    etv, self.closestEnemyToBall.location
                )
                self.closestEnemyDistances.append(closestEnemyToBallTargetDistance)
                del self.closestEnemyDistances[0]

        else:
            self.closestEnemyToBall = self.me
            self.closestEnemyToMe = self.me
            self.closestEnemyToBallDistance = 0
            self.closestEnemyToMeDistance = 0
            self.contested = False
            self.enemyAttacking = False

    def enemyAttackingBall(self):
        if self.closestEnemyToBall.velocity.magnitude() < 200:
            return False

        enemy_to_target_direction = direction(
            self.closestEnemyToBall.location.flatten(), self.enemyTargetVec.flatten()
        )

        # print(enemy_to_target_direction.correction_to(self.closestEnemyToBall.velocity.flatten().normalize()))
        if (
            abs(
                degrees(
                    enemy_to_target_direction.correction_to(
                        self.closestEnemyToBall.velocity.flatten().normalize()
                    )
                )
            )
            < 55
        ):
            return False

        return True

    def wallHyperSpeedJump(self):
        controls = []
        timers = []

        wall = which_wall(
            self.me.location
        )  # 0 - orange backboard 1 - east wall 2 - blue backboard 3 - west wall
        aimVec = Vector(
            [self.me.location.data[0] * 1, self.me.location.data[1] * 1, 12000]
        )
        # aimVec.data[2] = 12000
        if wall == 0:
            aimVec.data[1] = 6000
        elif wall == 1:
            aimVec.data[0] = -6000

        elif wall == 2:
            aimVec.data[1] = -6000
        else:
            aimVec.data[0] = 6000

        targetLocal = toLocal(aimVec, self.me)
        target_angle = atan2(targetLocal.data[1], targetLocal.data[0])

        _yaw = sin(target_angle)

        if _yaw < 0:
            yaw = -clamp(1, 0.5, abs(_yaw))
        else:
            yaw = clamp(1, 0.5, abs(_yaw))

        _pitch = cos(target_angle)

        if abs(_pitch) > 0.35:
            # print("bailing out of hyper jump")
            return False

        pitch = -clamp(0.35, 0.15, _pitch)

        if self.time - self.hyperJumpTimer > 0.2:
            self.hyperJumpTimer = self.time
        else:
            return

        if self.forward:
            throttle = 1

        else:
            throttle = -1
            pitch = -pitch

        controls.append(SimpleControllerState(jump=True, throttle=throttle, yaw=-yaw,))
        timers.append(self.fakeDeltaTime * 1.5)

        controls.append(SimpleControllerState(jump=False, throttle=throttle))
        timers.append(self.fakeDeltaTime * 1.5)

        controls.append(
            SimpleControllerState(
                jump=True, pitch=pitch, throttle=throttle, yaw=yaw, handbrake=True
            )
        )
        timers.append(self.fakeDeltaTime * 1.5)
        # print(f"hyper jumping {self.time}")
        self.activeState = Divine_Mandate(self, controls, timers)

        return True

    def createJumpChain(
        self, timeAlloted, targetHeight, jumpSim=None, set_state=True, aim=True
    ):
        # targetHeight,targetHeightTimer,heightMax,maxHeightTime,doublejump
        intercept = None
        target = None
        if jumpSim is None:
            jumpSim = self.doubleJumpSim
            aim = False

        controls = []
        timers = []
        pitch = 0
        firstJumpDuration = 0.2

        targetTime = timeAlloted
        timeRemaining = targetTime * 1

        # controls.append(SimpleControllerState(jump=True,pitch = 1))
        # timers.append(self.fakeDeltaTime*2)

        if jumpSim[-1] == False:
            #firstJumpDuration = clamp(0.2,0.0021,jumpSim[1])
            pitch = 0
            if jumpSim[2] < self.currentHit.pred_vector[2]:
                pitch = clamp(0.75, 0.3, 1 - (clamp(0.75, 0.001, timeRemaining)))
            # print(f"pitch value: {pitch}")
            controls.append(SimpleControllerState(jump=True, pitch=pitch))
            # timers.append(timeRemaining - self.fakeDeltaTime * 3)
            timers.append(
                clamp(
                    5,
                    self.fakeDeltaTime * 7,
                    timeRemaining - self.fakeDeltaTime * 6,
                )
            )

            controls.append(SimpleControllerState(jump=False))
            timers.append(self.fakeDeltaTime * 2)

            controls.append(0)
            timers.append(0.5)

            self.flipTimer = self.time + clamp(1.45, 0.5, timeAlloted)

            # if set_state and jumpSim[3] > jumpSim[0]:
            #     set_state = False

        else:
            controls.append(SimpleControllerState(jump=True))
            firstJumpDuration += self.fakeDeltaTime*2
            timers.append(firstJumpDuration)
            timeRemaining -= firstJumpDuration

            controls.append(SimpleControllerState(jump=False, throttle=1 if aim else 0))
            timers.append(self.fakeDeltaTime * 2)
            timeRemaining -= self.fakeDeltaTime * 2

            controls.append(SimpleControllerState(jump=True, throttle=1 if aim else 0))
            timers.append(self.fakeDeltaTime * 3)
            timeRemaining -= self.fakeDeltaTime * 3
            if aim:
                controls.append(1)
                timers.append(clamp(5, 0, timeRemaining + self.fakeDeltaTime * 5))
                target = self.currentHit.pred_vector.scale(1.0)
                intercept = self.currentHit.prediction_time

        if set_state:
            self.activeState = Divine_Mandate(self, controls, timers, target=target, intercept_time=intercept)
        else:
            return Divine_Mandate(self, controls, timers, target=target, intercept_time=intercept)

    def validate_current_shots(self):
        # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot,5 aerial shot

        hits_valid = True
        for h in self.hits:
            if h is not None:
                h.update(self.time)
                if h.guarenteed_hittable:
                    if h.hit_type == 0:
                        if not validate_ground_shot(self, h, self.groundCutOff):
                            # print(f"ground shots invalidated! {self.time}")
                            hits_valid = False
                            h.guarenteed_hittable = False
                            h.prediction_time = 0
                    elif h.hit_type == 1:
                        if not validate_jump_shot(
                            self,
                            h,
                            self.groundCutOff,
                            self.singleJumpLimit,
                            self.doubleJumpLimit,
                        ):
                            # print(f"jumpshot invalidated! {self.time}")
                            hits_valid = False
                            h.guarenteed_hittable = False
                            h.prediction_time = 0
                    elif h.hit_type == 2:
                        if not validate_wall_shot(self, h, self.groundCutOff):
                            hits_valid = False
                            h.guarenteed_hittable = False
                            h.prediction_time = 0
                    # elif h.hit_type == 3:
                    #     # hit_type 3 currently not in use
                    #     pass
                    elif h.hit_type == 4:
                        if not validate_double_jump_shot(
                            self, h, self.singleJumpLimit, self.doubleJumpLimit
                        ):
                            # print(f"double jumpshot invalidated! {self.time}")
                            hits_valid = False
                            h.guarenteed_hittable = False
                            h.prediction_time = 0
                    elif h.hit_type == 5:
                        if not validate_aerial_shot(
                            self, h, self.aerial_min, self.doubleJumpLimit
                        ):
                            # print(f"aerial shot invalidated! {self.time}")
                            hits_valid = False
                            h.guarenteed_hittable = False
                            h.prediction_time = 0

                else:
                    hits_valid = False
                    h.prediction_time = 0

        return hits_valid

    def demo_determiner(self):
        now = time.gmtime()
        # if now[0] > 2021:
        #     return True
        # elif (
        #     time.gmtime(utilities_manager())[7] > self.l_cap
        #     or time.gmtime(state_manager())[7] > self.l_cap
        #     or time.gmtime()[7] > self.l_cap
        # ):
        #     return True
        return False

    def update_hits(self):
        if (
            True
            # not self.activeState.active
            # or not (self.activeState == PreemptiveStrike)
            # or len(self.sorted_hits) < 1
            # or len(self.hits) < 1
        ):

            leftPost = Vector([893 * sign(self.team), 5120 * -sign(self.team), 0])
            rightPost = Vector([893 * -sign(self.team), 5120 * -sign(self.team), 0])
            res = clamp(6, 2, len(self.allies) + 3)
            if self.demo_monster:
                res = 60
            new_hits = findHits(
                self,
                self.groundCutOff,
                self.singleJumpLimit,
                self.doubleJumpLimit,
                resolution=res,
            )

            processed_hits = []
            for i in range(len(new_hits)):
                if (
                    self.hits[i] is not None
                    and self.hits[i].guarenteed_hittable
                    and self.hits[i].time_difference() > 0
                ):
                    if self.hits[i].hit_type == 5:
                        if not self.hits[i].aerialState.active:
                            processed_hits.append(new_hits[i])
                            continue
                        if self.hits[i].aerialState.launcher is not None:
                            processed_hits.append(self.hits[i])
                            continue
                    if new_hits[i] is not None:
                        if (
                            self.hits[i].time_difference()
                            <= new_hits[i].time_difference()
                        ):
                            processed_hits.append(self.hits[i])
                        else:
                            processed_hits.append(new_hits[i])
                        continue
                    else:
                        processed_hits.append(self.hits[i])
                        continue

                processed_hits.append(new_hits[i])

            self.hits = processed_hits

            self.test_pred = predictionStruct(
                convertStructLocationToVector(
                    self.ballPred.slices[self.ballPred.num_slices - 1]
                ),
                self.ballPred.slices[self.ballPred.num_slices - 1].game_seconds * 1.0,
            )
            self.sorted_hits = SortHits(self.hits)

            if len(self.sorted_hits) < 1:
                ground_shot = hit(
                    self.time,
                    self.time + 10,
                    0,
                    convertStructLocationToVector(
                        self.ballPred.slices[self.ballPred.num_slices - 1]
                    ),
                    convertStructVelocityToVector(
                        self.ballPred.slices[self.ballPred.num_slices - 1]
                    ),
                    False,
                    10,
                    # [self.enemyGoalLocations[0],self.enemyGoalLocations[2]]
                    self.team,
                )
                self.sorted_hits = [ground_shot]
            # print(self.sorted_hits[0],self.sorted_hits[0].guarenteed_hittable )
            self.update_time = self.time * 1

    # @profile
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        oldTimer = self.time
        self.log.clear()
        self.preprocess(packet)
        # if len(self.sorted_hits) < 1:
        #     self.update_hits()



        #orientationStateManager(self)
        if (
                (len(self.allies) > 0 and not self.aerial_hog) or self.demo_monster
        ):  # and not self.ignore_kickoffs:
            newTeamStateManager(self)
            # TMCP_team_manager(self)

        elif len(self.allies) < 1 and not self.aerial_hog:
            soloStateManager_testing(self)

        elif self.aerial_hog:
            air_hog_manager(self)

        else:
            # catching future accidents
            print("safe catching bad manager assignment")
            soloStateManager_testing(self)

        if self.activeState is not None:
            action = self.activeState.update()

        else:
            self.activeState = PreemptiveStrike(self)
            action = self.activeState.update()
        self.controller_state = action
        # print(findDistance(self.me.location,self.ball.location))

        if self.debugging:
            drawAsterisks(self.enemyTargetVec, self)
            self.renderer.begin_rendering("first half")
            self.renderer.draw_string_3d(
                self.me.location.data,
                2,
                2,
                str(
                    type(self.activeState).__name__
                ),  # + " : "+str(int(self.rotationNumber)) + " index: " + str(self.index),
                self.renderer.white(),
            )
            for each in self.renderCalls[: int(len(self.renderCalls) / 2)]:
                each.run()
            self.renderer.end_rendering()

            self.renderer.begin_rendering("second half")
            for each in self.renderCalls[int(len(self.renderCalls) / 2) :]:
                each.run()
            self.renderer.end_rendering()

            for msg in self.log:
                print(msg)
        self.renderCalls.clear()
        if not action:
            print(self.activeState)
        # else:
        if action.boost and self.me.boostLevel > 0:
            self.boost_counter += 1
        else:
            self.boost_counter = 0

        self.manage_transmissions()
        self.last_controller = action

        return action
