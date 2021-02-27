import math

# from copy import deepcopy
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import (
    GameState,
    BallState,
    CarState,
    Physics,
    Vector3 as vector3,
    Rotator,
)
from beard_utilities import *
from beard_states import *
import cProfile, pstats, io
import time
import numpy as np
from threading import Thread
#from playsound import playsound



def profile(fnc):
    """A decorator that uses cProfile to profile a function"""

    def inner(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = fnc(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return retval

    return inner


class Kamael(BaseAgent):
    def initialize_agent(self):
        self.controller_state = None  # SimpleControllerState()
        self.me = physicsObject()
        self.ball = physicsObject()
        self.me.team = self.team
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
        self.goalPred = None
        self.scorePred = None
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
        self.ballGrounded = False
        self.closestEnemyToMe = None
        self.closestEnemyToMeDistance = math.inf
        self.closestEnemyToBall = None
        self.closestEnemyDistances = [0, 0, 0, 0, 0]
        self.enemyAttacking = False
        self.enemyBallInterceptDelay = 0
        self.enemyPredTime = 0
        self.closestEnemyToBallDistance = math.inf
        # self.enemyBallTime = 0
        self.enemyTargetVec = Vector([0, 0, 0])
        self.contestedThreshold = 300
        self.superSonic = False
        self.wallShot = False
        self.openGoal = False
        self.boostConsumptionRate = 33.3
        self.boostAccelerationRate = 991.666
        # if self.team == 0:
        self.allowableJumpDifference = 90
        # else:
        #     self.allowableJumpDifference = 65
        self.singleJumpLimit = (
            233 + self.defaultElevation + self.allowableJumpDifference
        )  # 233 = maximum height gained from single jump
        self.doubleJumpLimit = (
            495 + self.defaultElevation + self.allowableJumpDifference
        )  # 498 = maximum height gained from double jump
        self.wallShotsEnabled = True
        self.DoubleJumpShotsEnabled = True
        self.touch = None
        self.targetDistance = 1500
        self.fpsLimit = 1 / 120
        self.gravity = -650
        self.jumpPhysics = physicsObject()
        self.hits = []
        self.sorted_hits = []
        self.update_time = 0
        self.fakeDeltaTime = 1.0 / 120.0
        self.accelerationTick = self.boostAccelerationRate * self.fakeDeltaTime
        self.aerialAccelerationTick = 1058 * self.fakeDeltaTime
        # print(f"single aerial acceleration tick: {self.aerialAccelerationTick}| 8x aerial acceleration tick: {self.aerialAccelerationTick*8}")
        self.currentHit = None
        self.resetLimit = 5
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
        self.rotationNumber = 3

        self.hyperJumpTimer = 0
        self.reachLength = 120
        self.debugging = True
        self.angleLimit = 60
        self.lastMan = Vector([0, 0, 0])
        self.aerialsEnabled = True
        self.kickoff_timer = 0
        self.blueGoal = Vector([0, -5120, 0])
        self.orangeGoal = Vector([0, 5120, 0])
        self.boostThreshold = 80
        self.test_done = True
        self.available_delta_v = 0
        self._forward, self.left, self.up = (
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
        )
        self.defaultRotation = None
        self.recovery_height = 45
        self.log = []
        self.test_pred = predictionStruct(Vector([0, 0, 0]), -1)
        self.game_active = True
        self.hit_finding_thread = None
        self.goalie = False
        self.boost_counter = 0
        if self.name.lower().find("st. peter") != -1:
            self.goalie = True

        self.default_demo_location = Vector([20000, 0, 0])
        self.double_point_limit = 525
        self.p_tournament_mode = False
        self.cached_jump_sim = []
        self.singleJumpShotTimer = 0
        self.doubleJumpShotTimer = 0
        self.boost_testing = False
        self.lastSpd = 0
        self.grounded_timer = 0
        self.boost_duration_min = 4
        self.enemyGoalLocations = []
        self.boost_gobbling = False
        self.ally_hit_count = 0
        self.ally_hit_info = []
        self.aerial_min = 200
        self.match_ended = False
        self.roof_height = None
        self.ball_size = 93
        self.demo_monster = False
        self.ignore_list_names = self.get_ignore_list() #["adversitybot","st. peter","bribblebot","invisibot","sniper","blind and deaf"]
        self.ignore_list_indexes = None
        self.team_size_limit = 4

    def get_ignore_list(self):
        import pathlib
        ignore_list = []
        with open (str(pathlib.Path(__file__).parent.absolute()) + "\\bot_ignore_list.txt") as specials:
            for name in specials.readlines():
                ignore_list.append(str(name.strip()).lower())
        return ignore_list


    def retire(self):
        self.game_active = False
        if self.hit_finding_thread != None:
            self.hit_finding_thread.close()

        print(f"{self.name} thread has exited")

    def init_match_config(self, match_config: "MatchConfig"):
        self.matchSettings = match_config
        # print(f"Boost type is : {self.matchSettings.mutators.boost_amount}")
        self.boostMonster = self.matchSettings.mutators.boost_amount == "Unlimited"
        # print(self.matchSettings.game_mode)
        self.ignore_kickoffs = self.matchSettings.game_mode == "Heatseeker"
        # print(self.ignore_kickoffs)

    def demoRelocation(self, car):
        # print("running demo relocation")
        if car.team == 0:
            # if distance2D(self.ball.location, self.demoSpawns[0][0]) < distance2D(
            #     self.ball.location, self.demoSpawns[0][1]
            # ):
            #     return self.demoSpawns[0][0]
            # else:
            #     return self.demoSpawns[0][1]
            return self.default_demo_location
        else:
            # if distance2D(self.ball.location, self.demoSpawns[1][0]) < distance2D(
            #     self.ball.location, self.demoSpawns[1][1]
            # ):
            #     return self.demoSpawns[1][0]
            # else:
            #     return self.demoSpawns[1][1]
            return self.default_demo_location

    def do_test(self):

        for i in range(2000):
            target_time = float32(i / 1000.0)
            result = jumpSimulatorNormalizingJit(
                float32(self.gravity),
                float32(self.fakeDeltaTime),
                np.array(self.me.velocity, dtype=np.dtype(float)),
                float32(self.defaultElevation),
                target_time,
                float32(1000),
                True,
            )
            # float32(targetHeight), float32(targetHeightTimer), float32(heightMax), float32(maxHeightTime - fakeDeltaTime)
            self.log.append(f"reached max height of {result[2]} at time {result[3]}")
        self.test_done = True
        self.log.append("done")

    def getActiveState(self):
        if type(self.activeState) == LeapOfFaith:
            return 0
        if type(self.activeState) == PreemptiveStrike:
            return 1
        if type(self.activeState) == GetBoost:
            return 2
        if type(self.activeState) == GroundAssault:
            return 3
        if type(self.activeState) == GroundShot:
            return 4
        if type(self.activeState) == HolyProtector:
            return 5
        if type(self.activeState) == BlessingOfDexterity:
            return 6

    def setHalfFlip(self):
        #_time = self.time
        #if _time - self.flipTimer >= 1.9:
        controls = []
        timers = []

        control_1 = SimpleControllerState()
        control_1.throttle = -1
        control_1.jump = True

        controls.append(control_1)
        timers.append(0.125)

        controls.append(SimpleControllerState())
        timers.append(self.fakeDeltaTime*4)

        control_3 = SimpleControllerState()
        control_3.throttle = -1
        control_3.pitch = 1
        control_3.jump = True
        controls.append(control_3)
        timers.append(self.fakeDeltaTime * 4)

        control_4 = SimpleControllerState()
        control_4.throttle = -1
        control_4.pitch = -1
        control_4.roll = -.1
        #control_4.jump = True

        controls.append(control_4)
        timers.append(0.5)

        self.activeState = Divine_Mandate(self, controls, timers)

        self.flipTimer = self.time

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
        angle = correctAngle(math.degrees(math.atan2(loc[1], loc[0])))

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

    def setJumping(self, targetType, target=None):
        _time = self.time
        if _time - self.flipTimer >= 1.9:
            if targetType == 2:
                self.createJumpChain(2, 400, jumpSim=None, set_state=True)

            elif targetType == 20:
                self.activeState = Special_Delivery(self)
                self.flipTimer = _time

            elif targetType != -1:
                self.activeState = LeapOfFaith(self, targetType, target=target)
                self.flipTimer = _time

            else:
                self.activeState = Divine_Mandate(
                    self, [SimpleControllerState(jump=True)], [0.21]
                )
                self.flipTimer = _time - 1

    def setDashing(self, target):
        _time = self.time
        if _time - self.flipTimer >= 1.9:
            self.activeState = WaveDashing(self, target)
            self.flipTimer = _time

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

    # def copy_game_info(self,game):
    #     game_info_obj = {}
    #     game_info_obj["seconds_elapsed"] = game.game_info.seconds_elapsed
    #     game_info_obj["game_time_remaining"] = game.game_info.game_time_remaining
    #     game_info_obj["is_overtime"] = game.game_info.is_overtime
    #     game_info_obj["is_unlimited_time"] = game.game_info.is_unlimited_time
    #     game_info_obj["is_round_active"] = game.game_info.is_round_active
    #     game_info_obj["is_kickoff_pause"] = game.game_info.is_kickoff_pause
    #     game_info_obj["world_gravity_z"] = game.game_info.world_gravity_z
    #     game_info_obj["game_speed"] = game.game_info.game_speed
    #
    #     print(game_info_obj.seconds_elapsed)
    #
    #     self.gameInfo = game_info_obj

    def preprocess(self, game):
        self.ball_size = game.game_ball.collision_shape.sphere.diameter/2


        self.gameInfo.update(game)
        self.oldPreds = self.ballPred
        self.ballPred = self.get_ball_prediction_struct()
        # self.ballPred = deepcopy(self.get_ball_prediction_struct())
        self.players = [self.index]
        car = game.game_cars[self.index]
        self.timid = False
        ally_count = len(self.allies)
        enemy_count = len(self.enemies)
        self.deltaTime = clamp(
            1, self.fpsLimit, game.game_info.seconds_elapsed - self.time
        )
        self.time = game.game_info.seconds_elapsed
        self.me.demolished = car.is_demolished
        self.me.index = self.index
        updateHits = False
        self.gravity = game.game_info.world_gravity_z

        # print(game.game_info.world_gravity_z)

        if self.defaultRotation == None:
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

        # print(self.me.rotation[0])
        if not self.hitbox_set:
            self.fieldInfo = self.get_field_info()
            self.carLength = car.hitbox.length
            self.carWidth = car.hitbox.width
            self.carHeight = car.hitbox.height

            self.functional_car_height = self.carHeight
            self.groundCutOff = 93 + (self.carHeight + 17) * 0.8
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

            # self.singleJumpLimit = (
            #         233 + self.defaultElevation + self.allowableJumpDifference
            # )  # 233 = maximum height gained from single jump
            # self.doubleJumpLimit = (
            #         495 + self.defaultElevation + self.allowableJumpDifference
            # )  # 498 = maximum height gained from double jump

            single_jump = jumpSimulatorNormalizingJit(
                float32(self.gravity),
                float32(self.fakeDeltaTime),
                np.array(self.me.velocity, dtype=np.dtype(float)),
                float32(self.defaultElevation),
                float32(610),
                float32(10000),
                False,
            )

            double_jump = jumpSimulatorNormalizingJit(
                float32(self.gravity),
                float32(self.fakeDeltaTime),
                np.array(self.me.velocity, dtype=np.dtype(float)),
                float32(self.defaultElevation),
                float32(10),
                float32(10000),
                True,
            )

            self.doubleJumpSim = double_jump
            old_sj = self.singleJumpLimit * 1
            old_dj = self.doubleJumpLimit * 1

            self.singleJumpLimit = self.allowableJumpDifference + single_jump[2]
            self.doubleJumpLimit = self.allowableJumpDifference + double_jump[2]
            # print(f"doublejump limit is: {self.doubleJumpLimit}")
            self.singleJumpShotTimer = single_jump[3]
            self.doubleJumpShotTimer = double_jump[3]

            # print(f"simulated max double jump height is: {double_jump[2]}")
            # print(f"simulated max single jump height is: {single_jump[2]}")
            #
            # print(f"single jump limit: {self.singleJumpLimit} double jump limit: {self.doubleJumpLimit}")
            # print(f"old single jump limit: {old_sj} old double jump limit: {old_dj}")
            # print(f"max single jump time @ {single_jump[3]}")
            # print(f"max double jump time @ {double_jump[3]}")

            # print(f"Kamael {self.index} hitbox (length:{self.carLength} width:{self.carWidth} height:{self.carHeight}) reach: {self.reachLength} grounder limit: {self.groundCutOff}")

            # print(f"single jump limit: {self.singleJumpLimit} double jump limit: {self.doubleJumpLimit}")

            if self.debugging:
                self.log.append(
                    f"Kamael on team {self.team} hitbox (length:{self.carLength} width:{self.carWidth} height:{self.carHeight}) reach: {self.reachLength} grounder limit: {self.groundCutOff}"
                )
                self.log.append(
                    f"single jump limit: {self.singleJumpLimit} double jump limit: {self.doubleJumpLimit}"
                )

            if self.name.lower().find("st. peter") != -1:
                self.goalie = True
                if self.p_tournament_mode:
                    for i in range(game.num_cars):
                        car = game.game_cars[i]
                        if car.team == self.team:
                            if car.name.lower().find("st. peter") != -1:
                                if i < self.index:
                                    self.goalie = False
            self.cached_jump_sim = jumpSimulatorNormalizing(
                self, 3, 1000, doubleJump=True
            )[-1]
            # print(f"info for 1.35 seconds in is: {self.cached_jump_sim[int(1.35/self.fakeDeltaTime)]}")

            if self.gravity > -650 and self.boostMonster:
                self.doubleJumpLimit = self.singleJumpLimit + 100
                self.DoubleJumpShotsEnabled = False

            self.enemyGoalLocations.append(Vector([893 * sign(self.team), 5120 * -sign(self.team), 0]))
            self.enemyGoalLocations.append(Vector([0, 5120 * -sign(self.team), 0]))
            self.enemyGoalLocations.append(Vector([893 * -sign(self.team), 5120 * -sign(self.team), 0]))

            add_car_offset(self,projecting=False)
            # roughly 147 is touching the ball if facing straight on with octane hitbox
            adjusted_roof_height = self.roof_height
            self.reachLength = math.floor(
                math.sqrt(adjusted_roof_height * (self.ball_size * 2 - adjusted_roof_height))) + self.carLength * .5
            print(f"self.reachLength is: {self.reachLength}")

        add_car_offset(self, projecting=self.debugging)

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

        self.allies.clear()
        self.enemies.clear()
        if not self.ignore_list_indexes:
            active_teammates = []
            self.ignore_list_indexes = []
            for i in range(game.num_cars):
                if i != self.index:
                    car = game.game_cars[i]
                    if car.team == self.team:
                        for name in self.ignore_list_names:
                            if str(car.name).lower().find(name) != -1:
                                self.ignore_list_indexes.append(i)
                                print(f"ignoring {car.name}!")
                        if i not in self.ignore_list_indexes:
                            active_teammates.append(i)
                else:
                    active_teammates.append(self.index)
            if active_teammates.index(self.index) > self.team_size_limit-1:
                self.demo_monster = True

            if len(active_teammates) > self.team_size_limit:
                for ally in active_teammates[self.team_size_limit:]:
                    self.ignore_list_indexes.append(ally)


        for i in range(game.num_cars):
            if i != self.index and i not in self.ignore_list_indexes:
                car = game.game_cars[i]
                _obj = physicsObject()
                _obj.index = i
                _obj.team = car.team
                _obj.demolished = car.is_demolished
                _obj.index = i
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
                    if car.team == 0:
                        _dist = distance2D(_obj.location, self.blueGoal)
                    else:
                        _dist = distance2D(_obj.location, self.orangeGoal)
                    if car.team == self.team:
                        _obj.retreating = player_retreat_status(
                            _obj, self.ball.location, car.team, num_allies=ally_count
                        )
                        if _obj.retreating and self.team == 5:
                            if distance2D(_obj.location, self.ball.location) < 300:
                                _obj.retreating = False

                        # _obj.next_hit = find_ally_hit(self,_obj)
                    else:
                        _obj.retreating = player_retreat_status(
                            _obj, self.ball.location, car.team, num_allies=enemy_count
                        )
                else:
                    # print(f"relocated demo'd player {car.name}")
                    _obj.location = self.demoRelocation(car)
                    _obj.velocity = Vector([0, 0, 0])
                    _obj.rotation = Vector([0, 0, 0])
                    _obj.avelocity = Vector([0, 0, 0])
                    _obj.boostLevel = 33
                    _obj.onSurface = True
                    _obj.retreating = True
                    # _obj.next_hit = predictionStruct(convertStructLocationToVector(self.ballPred.slices[-1]), self.time + 7)

                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)
        # self.gameInfo = game.game_info
        self.boosts = []
        self.bigBoosts = []

        for index in range(self.fieldInfo.num_boosts):
            packetBoost = game.game_boosts[index]
            fieldInfoBoost = self.fieldInfo.boost_pads[index]
            boostStatus = False
            if packetBoost.timer <= 0:
                if packetBoost.is_active:
                    boostStatus = True
            boostLocation = [
                fieldInfoBoost.location.x,
                fieldInfoBoost.location.y,
                fieldInfoBoost.location.z,
            ]
            boost_obj = Boost_obj(
                [
                    fieldInfoBoost.location.x,
                    fieldInfoBoost.location.y,
                    fieldInfoBoost.location.z,
                ],
                fieldInfoBoost.is_full_boost,
                boostStatus,
            )
            self.boosts.append(boost_obj)
            if boost_obj.bigBoost:
                self.bigBoosts.append(boost_obj)

        self.onWall = False
        self.wallShot = False
        self.aerialsEnabled = True
        self.aerialsLimited = False
        if len(self.allies) < 1:
            if not self.ignore_kickoffs and not self.goalie and False:
                self.aerialsLimited = True
                self.aerialsEnabled = True
            else:
                self.aerialsEnabled = False

        if (
            self.onSurface
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
        # if self.dribbling:
        #     print(f"we dribbling {self.time}")
        self.findClosestToEnemies()
        self.resetCount += 1
        self.setJumpPhysics()
        self.available_delta_v = 1060 * (self.me.boostLevel / 33.333)
        if self.onSurface and not self.onWall and self.me.boostLevel > 0:
            self.available_delta_v += 500
        if self.boostMonster:
            self.available_delta_v = math.inf

        # recent hit finding update
        # if len(self.allies) > 0: #or self.team == 0:
        if len(self.allies) < 1 and self.team == 3:
            self.update_hits()
        else:

            if len(self.hits) < 1:
                self.update_hits()
            else:
                for h in self.hits:
                    if h != None:
                        h.update(self.time)
                self.sorted_hits = SortHits(self.hits)
                if self.sorted_hits[0].time_difference() > 5:
                    updateHits = True
                # predictions_valid = validateExistingPred(self,predictionStruct(self.sorted_hits[0].pred_vector,self.sorted_hits[0].prediction_time))
                if not updateHits:
                    predictions_valid = validateExistingPred(self, self.test_pred)
                else:
                    predictions_valid = False

                refresh_timer = 0.15
                # if len(self.allies) < 1:
                #     refresh_timer = 0.25

                if (
                    updateHits == True
                    or self.sorted_hits[0].prediction_time < self.time
                    or not predictions_valid
                    or self.time - self.update_time > refresh_timer
                ):
                    self.update_hits()

                elif not self.validate_current_shots():
                    # print(f"had invalid shot, recalculating {self.time}")
                    self.update_hits()
        # else:
        #     self.update_hits()

        if self.resetCount >= self.resetLimit:
            findEnemyHits(self)
            self.resetCount = 0
        else:
            self.enemyBallInterceptDelay = self.enemyPredTime - self.time

        if self.gameInfo.is_kickoff_pause:
            self.kickoff_timer = self.time

        if not self.test_done:
            self.do_test()

    def findClosestToEnemies(self):
        if len(self.enemies) > 0:
            (
                self.closestEnemyToBall,
                self.closestEnemyToBallDistance,
            ) = findEnemyClosestToLocation3D(self, self.ball.location)
            (
                self.closestEnemyToMe,
                self.closestEnemyToMeDistance,
            ) = findEnemyClosestToLocation3D(self, self.me.location)
            self.contested = False
            self.enemyAttacking = False

            # if self.closestEnemyToMeDistance <= self.contestedThreshold:
            #     self.contested = True
            #     self.enemyAttacking = True

            if self.closestEnemyToBallDistance <= self.contestedThreshold:
                self.contested = True
                self.enemyAttacking = True

            elif self.enemyAttackingBall():
                self.enemyAttacking = True

            if self.closestEnemyToBall != None:
                closestEnemyToBallTargetDistance = findDistance(
                    self.enemyTargetVec, self.closestEnemyToBall.location
                )
                # if self.resetCount == 0:
                #     self.closestEnemyDistances = [(closestEnemyToBallTargetDistance+1)-i*.2 for i in range(5)]
                # else:
                self.closestEnemyDistances.append(closestEnemyToBallTargetDistance)
                del self.closestEnemyDistances[0]

        else:
            self.closestEnemyToBall = self.me
            self.closestEnemyToMe = self.me
            self.closestEnemyToBallDistance = 0
            self.closestEnemyToMeDistance = 0
            self.contested = False
            self.enemyAttacking = False
            # self.log.append("in here")

    # def enemyAttackingBall(self):
    #     current = math.inf
    #     for each in self.closestEnemyDistances:
    #         if each < current:
    #             current = each
    #         else:
    #             return False
    #
    #     return True
    def enemyAttackingBall(self):
        if self.closestEnemyToBall.velocity.magnitude() < 25:
            return False

        enemy_to_target_direction = direction(
            self.enemyTargetVec.flatten(), self.closestEnemyToBall.location.flatten()
        )
        if (
            angleBetweenVectors(
                enemy_to_target_direction,
                self.closestEnemyToBall.velocity.flatten().normalize(),
            )
            > 60
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
        target_angle = math.atan2(targetLocal.data[1], targetLocal.data[0])

        _yaw = math.sin(target_angle)

        if _yaw < 0:
            yaw = -clamp(1, 0.5, abs(_yaw))
        else:
            yaw = clamp(1, 0.5, abs(_yaw))

        _pitch = math.cos(target_angle)

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
        timers.append(self.fakeDeltaTime * 3)

        controls.append(SimpleControllerState(jump=False, throttle=throttle))
        timers.append(self.fakeDeltaTime * 2)

        controls.append(
            SimpleControllerState(
                jump=True, pitch=pitch, throttle=throttle, yaw=yaw, handbrake=True
            )
        )
        timers.append(self.fakeDeltaTime * 2)
        # print(f"hyper jumping {self.time}")
        self.activeState = Divine_Mandate(self, controls, timers)

        return True

    # def create_weak_doublejump(self, angle_up=True):
    #     controls = []
    #     timers = []
    #     pitch = 0
    #     if angle_up:
    #         pitch = -1
    #
    #     controls.append(SimpleControllerState(jump=True,pitch=pitch))
    #     timers.append(0.2)
    #     controls.append(SimpleControllerState(pitch=pitch))
    #     timers.append(self.fakeDeltaTime*3)
    #     controls.append(SimpleControllerState(jump=True))
    #     timers.append(self.fakeDeltaTime*3)
    #     controls.append(SimpleControllerState(pitch=pitch))
    #     timers.append(0.2)
    #
    #     self.activeState = Divine_Mandate(self, controls, timers)

    def createJumpChain(
        self, timeAlloted, targetHeight, jumpSim=None, set_state=True, aim=True
    ):
        # targetHeight,targetHeightTimer,heightMax,maxHeightTime,doublejump
        if jumpSim == None:
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
            pitch = clamp(0.75, 0.3, 1 - (clamp(0.75, 0.001, timeRemaining)))
            # print(f"pitch value: {pitch}")
            controls.append(SimpleControllerState(jump=True, pitch=pitch))
            timers.append(timeRemaining - self.fakeDeltaTime * 5)

            controls.append(SimpleControllerState(jump=False, throttle=1))
            timers.append(self.fakeDeltaTime * 4)

            controls.append(0)
            timers.append(0.4)

            self.flipTimer = self.time + clamp(1.45, 0.3, timeAlloted)

            # if set_state and jumpSim[3] > jumpSim[0]:
            #     set_state = False

        else:
            controls.append(SimpleControllerState(jump=True))
            timers.append(firstJumpDuration)
            timeRemaining -= firstJumpDuration

            controls.append(SimpleControllerState(jump=False, throttle=1))
            timers.append(self.fakeDeltaTime * 4)
            timeRemaining -= self.fakeDeltaTime * 4

            controls.append(SimpleControllerState(jump=True))
            timers.append(self.fakeDeltaTime * 6)
            timeRemaining -= self.fakeDeltaTime * 6

            # print(f"Double jump shot target height: {targetHeight}")

            # if targetHeight >= self.double_point_limit:
            if aim:
                controls.append(1)
                timers.append(clamp(10, 0, timeRemaining + self.fakeDeltaTime * 10))
                # print("in here")

        if set_state:
            self.activeState = Divine_Mandate(self, controls, timers)
        else:
            return Divine_Mandate(self, controls, timers)

    def validate_current_shots(self):
        # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot,5 aerial shot
        for h in self.hits:
            if h != None:
                if h.guarenteed_hittable:
                    if h.hit_type == 0:
                        if not validate_ground_shot(self, h, self.groundCutOff):
                            # print(f"ground shots invalidated! {self.time}")
                            return False
                    elif h.hit_type == 1:
                        if not validate_jump_shot(
                            self,
                            h,
                            self.groundCutOff,
                            self.singleJumpLimit,
                            self.doubleJumpLimit,
                        ):
                            # print(f"jumpshot invalidated! {self.time}")
                            return False
                    elif h.hit_type == 2:
                        if not validate_wall_shot(self, h, self.groundCutOff):
                            return False
                    elif h.hit_type == 3:
                        # hit_type 3 currently not in use
                        pass
                    elif h.hit_type == 4:
                        if not validate_double_jump_shot(
                            self, h, self.singleJumpLimit, self.doubleJumpLimit
                        ):
                            # print(f"double jumpshot invalidated! {self.time}")
                            return False
                    elif h.hit_type == 5:
                        if not validate_aerial_shot(
                            self, h, self.aerial_min, self.doubleJumpLimit
                        ):
                            # print(f"aerial shot invalidated! {self.time}")
                            return False
        return True

    def update_hits(self):
        if not self.boost_testing:

            if (
                type(self.activeState) != PreemptiveStrike
                or not self.activeState.active
            ):
                leftPost = Vector([893 * sign(self.team), 5120 * -sign(self.team), 0])
                rightPost = Vector([893 * -sign(self.team), 5120 * -sign(self.team), 0])
                res = len(self.allies) + 1
                if self.demo_monster:
                    res = 60
                self.hits = findHits(
                    self,
                    self.groundCutOff,
                    self.singleJumpLimit,
                    self.doubleJumpLimit,
                    resolution=res,
                )

                self.test_pred = predictionStruct(
                    convertStructLocationToVector(
                        self.ballPred.slices[self.ballPred.num_slices - 1]
                    ),
                    self.ballPred.slices[self.ballPred.num_slices - 1].game_seconds
                    * 1.0,
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
                    )
                    self.sorted_hits = [ground_shot]
                self.update_time = self.time * 1
                # print(f"Updating hits {self.time}")

    #@profile
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        oldTimer = self.time
        self.log.clear()
        self.preprocess(packet)

        if len(self.allies) > 0 and not self.ignore_kickoffs:
            newTeamStateManager(self)

        else:
            soloStateManager_testing(self)

        if self.activeState != None:
            action = self.activeState.update()

        else:
            self.activeState = PreemptiveStrike(self)
            action = self.activeState.update()
        self.controller_state = action

        if self.debugging:
            drawAsterisks(self.enemyTargetVec, self)
            self.renderer.begin_rendering()
            self.renderer.draw_string_3d(
                self.me.location.data,
                2,
                2,
                str(type(self.activeState).__name__),
                self.renderer.white(),
            )
            for each in self.renderCalls:
                each.run()
            # self.renderer.draw_line_3d(self.me.location.data,
            #                            extend_to_sidewall(self, self.ball.location, self.me.location).data,
            #                            self.renderer.yellow())
            self.renderer.end_rendering()
            # if self.debugging:
            #     for msg in self.log:
            #         print(msg)
        self.renderCalls.clear()
        if action.boost and self.me.boostLevel > 0:
            self.boost_counter += 1
        else:
            self.boost_counter = 0
        # print(f"{self.gameInfo.is_round_active} {self.time}")

        # print(self.me.location[2])

        return action
