import math
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
        self.gameInfo = None
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
        #if self.team == 0:
        self.allowableJumpDifference = 90
        # else:
        #     self.allowableJumpDifference = 65
        self.singleJumpLimit = (
            233 + self.defaultElevation + self.allowableJumpDifference
        )  # 233 = maximum height gained from single jump
        self.doubleJumpLimit = (
            493 + self.defaultElevation + self.allowableJumpDifference
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
        self.fakeDeltaTime = 1 / 120
        self.accelerationTick = self.boostAccelerationRate * (1.0 / 120.0)
        self.aerialAccelerationTick = 1060 * (1.0 / 120.0)
        self.currentHit = None
        self.resetLimit = 5
        self.resetCount = 0
        self.resetTimer = 0
        self.timid = False
        self.dribbling = False
        self.goalward = False
        self.stubbornessTimer = 0
        self.stubbornessMax = 600
        self.stubbornessMin = 5
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
        self.debugging = False
        self.angleLimit = 60
        self.lastMan = Vector([0,0,0])
        self.aerialsEnabled = True
        self.kickoff_timer = 0
        self.blueGoal = Vector([0, -5120, 0])
        self.orangeGoal = Vector([0, 5120, 0])
        self.boostThreshold = 50
        self.test_done = True
        self.available_delta_v = 0
        self._forward, self.left, self.up = (
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
            Vector([0, 0, 0]),
        )
        self.defaultRotation = None
        self.recovery_height = 200
        self.log = []
        self.test_pred = predictionStruct(Vector([0,0,0]),-1)
        self.game_active = True
        self.hit_finding_thread = None
        self.goalie = False
        if self.name.lower().find("st. peter") != -1:
            self.goalie = True



    def retire(self):
        self.game_active = False
        if self.hit_finding_thread != None:
            self.hit_finding_thread.close()
        print("Kamael thread has exited")


    def init_match_config(self, match_config: "MatchConfig"):
        self.matchSettings = match_config
        #print(f"Boost type is : {self.matchSettings.mutators.boost_amount}")
        self.boostMonster = self.matchSettings.mutators.boost_amount == "Unlimited"
        #print(self.matchSettings.game_mode)
        self.ignore_kickoffs = self.matchSettings.game_mode == "Heatseeker"
        #print(self.ignore_kickoffs)

    def demoRelocation(self, car):
        # print("running demo relocation")
        if car.team == 0:
            if distance2D(self.ball.location, self.demoSpawns[0][0]) < distance2D(
                self.ball.location, self.demoSpawns[0][1]
            ):
                return self.demoSpawns[0][0]
            else:
                return self.demoSpawns[0][1]
        else:
            if distance2D(self.ball.location, self.demoSpawns[1][0]) < distance2D(
                self.ball.location, self.demoSpawns[1][1]
            ):
                return self.demoSpawns[1][0]
            else:
                return self.demoSpawns[1][1]

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
        self.activeState = BlessingOfDexterity(self)

    def aerialGetter(self, pred, target, time):
        return Wings_Of_Justice(self, pred, target, time)

    # def aerialGetter(self, pred, aim_loc, tth):
    #     return Wings_Of_Justice(self, pred, aim_loc, tth)

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

            if targetType != -1:
                self.activeState = LeapOfFaith(self, targetType, target=target)
                self.flipTimer = _time
            else:
                self.activeState = Divine_Mandate(
                    self, [SimpleControllerState(jump=True)], [0.15]
                )
                self.flipTimer = _time

    def setDashing(self, target):
        self.activeState = WaveDashing(self, target)

    def setGuidance(self, target: Vector):
        self.activeState = DivineGuidance(self, target)
        #print(f"guidance called! {self.time}")

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
        self.oldPreds = self.ballPred
        self.ballPred = self.get_ball_prediction_struct()
        self.players = [self.index]
        car = game.game_cars[self.index]
        self.timid = False
        self.deltaTime = clamp(
            1, self.fpsLimit, game.game_info.seconds_elapsed - self.time
        )
        self.time = game.game_info.seconds_elapsed
        self.me.demolished = car.is_demolished
        self.me.index = self.index
        updateHits = False

        if self.defaultRotation == None:
            self.defaultRotation = Vector3(car.physics.rotation.pitch,
                    car.physics.rotation.yaw,
                    car.physics.rotation.roll)

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
            self.currentSpd = clamp(2300, 1, self.getCurrentSpd())
            self.me.matrix = rotator_to_matrix(self.me)
            self._forward, self.left, self.up = self.me.matrix
            self.me.rotational_velocity = matrixDot(self.me.matrix, self.me.avelocity)
            self.me.retreating = player_retreat_status(self.me, self.ball.location,self.team)
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

            # if self.team == 0:
            #     self.functional_car_height = self.carHeight +17
            #     self.groundCutOff = 93 + (self.carHeight + 17) * .75  # ((self.carHeight+17) * 0.75)
            # else:
            self.functional_car_height = self.carHeight
            self.groundCutOff = 93 + (self.carHeight +17) * .8
            self.hitbox_set = True
            # roughly 147 is touching the ball if facing straight on with octane hitbox
            self.reachLength = (
                93 + self.carLength * 0.5
            )*0.95 # (92 + (car.hitbox.length * 0.665)) * 0.9
            self.defaultOffset = Vector(
                [
                    car.hitbox_offset.x * 1,
                    car.hitbox_offset.y * 1,
                    car.hitbox_offset.z * 1,
                ]
            )
            if self.debugging:
                self.log.append(
                    f"Kamael on team {self.team} hitbox (length:{self.carLength} width:{self.carWidth} height:{self.carHeight}) reach: {self.reachLength} grounder limit: {self.groundCutOff}"
                )
                self.log.append(
                    f"single jump limit: {self.singleJumpLimit} double jump limit: {self.doubleJumpLimit}"
                )
            #threading testing
            # self.update_hits()
            # self.hit_finding_thread = Thread(target=hit_generator, args=(self, self.groundCutOff, self.singleJumpLimit, self.doubleJumpLimit))

        # print(f"{Vector([car.hitbox_offset.x,car.hitbox_offset.y,car.hitbox_offset.z])} {self.time}")
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
        for i in range(game.num_cars):
            if i != self.index:
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

                    _obj.retreating = player_retreat_status(_obj, self.ball.location,car.team)
                else:
                    # print(f"relocated demo'd player {car.name}")
                    _obj.location = self.demoRelocation(car)
                    _obj.velocity = Vector([0, 0, 0])
                    _obj.rotation = Vector([0, 0, 0])
                    _obj.avelocity = Vector([0, 0, 0])
                    _obj.boostLevel = 33
                    _obj.onSurface = True
                    _obj.retreating = True

                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)
        self.gameInfo = game.game_info
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
        if len(self.allies) < 1 and not self.boostMonster or self.ignore_kickoffs or self.goalie:
            self.aerialsEnabled = False
        if self.onSurface:
            if self.me.location[2] > 25:
                self.onWall = self.up[2] < 0.98
        if len(self.allies) > 0:
            self.lastMan = lastManFinder(self).location
        else:
            self.lastMan = self.me.location

        self.determineFacing()
        self.gravity = game.game_info.world_gravity_z
        self.dribbling = dirtyCarryCheck(self)
        self.findClosestToEnemies()
        self.resetCount += 1
        self.setJumpPhysics()
        self.available_delta_v = 1060 * (self.me.boostLevel / 33.333)
        if self.onSurface and not self.onWall and self.me.boostLevel > 0:
            self.available_delta_v += 500

        #recent hit finding update
        if len(self.allies) > 0:

            if len(self.hits) < 1:
                self.update_hits()
            else:
                for h in self.hits:
                    if h != None:
                        h.update(self.time)
                self.sorted_hits = SortHits(self.hits)
                #predictions_valid = validateExistingPred(self,predictionStruct(self.sorted_hits[0].pred_vector,self.sorted_hits[0].prediction_time))
                predictions_valid = validateExistingPred(self, self.test_pred)

                if updateHits == True or self.sorted_hits[0].prediction_time < self.time or not predictions_valid or self.time - self.update_time > 1:
                    self.update_hits()

                elif not self.validate_current_shots():
                    #print(f"had invalid shot, recalculating {self.time}")
                    self.update_hits()
        else:
            self.update_hits()



        if self.resetCount >= self.resetLimit:
            findEnemyHits(self)
            self.resetCount = 0
        else:
            self.enemyBallInterceptDelay = self.enemyPredTime - self.time

        if self.gameInfo.is_kickoff_pause:
            self.kickoff_timer = self.time

        if self.time < self.kickoff_timer > 10:
            self.boostThreshold = 50
        else:
            self.boostThreshold = 50

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
                closestEnemyToBallTargetDistance = distance2D(
                    self.enemyTargetVec, self.closestEnemyToBall.location
                )
                # self.closestEnemyDistances.append(self.closestEnemyToBallDistance)
                self.closestEnemyDistances.append(closestEnemyToBallTargetDistance)
                del self.closestEnemyDistances[0]

        else:
            self.closestEnemyToBall = self.me
            self.closestEnemyToMe = self.me
            self.closestEnemyToBallDistance = 0
            self.closestEnemyToMeDistance = 0
            self.contested = False
            self.enemyAttacking = False
            #self.log.append("in here")

    def enemyAttackingBall(self):
        current = math.inf
        for each in self.closestEnemyDistances:
            if each < current:
                current = each
            else:
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

    def createJumpChain(self, timeAlloted, targetHeight, jumpSim = None,set_state = True):
        # targetHeight,targetHeightTimer,heightMax,maxHeightTime,doublejump
        if jumpSim == None:
            jumpSim = [450,1.6,400,1.55,True]

        controls = []
        timers = []
        pitch = 0
        firstJumpDuration = 0.2 + self.fakeDeltaTime

        targetTime = timeAlloted
        timeRemaining = targetTime * 1

        # controls.append(SimpleControllerState(jump=True,pitch = 1))
        # timers.append(self.fakeDeltaTime*2)

        if jumpSim[-1] == False:
            pitch = clamp(0.75, 0.2, 0.75 - (timeRemaining - self.fakeDeltaTime * 3))
            # print(f"pitch value: {pitch}")
            controls.append(SimpleControllerState(jump=True, pitch=pitch))
            timers.append(timeRemaining - self.fakeDeltaTime * 5)

            controls.append(SimpleControllerState(jump=False))
            timers.append(self.fakeDeltaTime * 1)

            controls.append(0)
            timers.append(self.fakeDeltaTime * 20)

        else:
            controls.append(SimpleControllerState(jump=True))
            timers.append(firstJumpDuration)
            timeRemaining -= firstJumpDuration

            controls.append(SimpleControllerState(jump=False))
            timers.append(self.fakeDeltaTime * 3)
            timeRemaining -= self.fakeDeltaTime * 3

            controls.append(SimpleControllerState(jump=True))
            timers.append(self.fakeDeltaTime * 3)
            timeRemaining -= self.fakeDeltaTime * 3

            #print(f"Double jump shot target height: {targetHeight}")

            if targetHeight >= 525:
                controls.append(1)
                timers.append(clamp(2,0,timeRemaining))
                #print("in here")

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
                        if not validate_ground_shot(self,h,self.groundCutOff):
                            #print(f"ground shots invalidated! {self.time}")
                            return False
                        else:
                            pass
                            #print(f"ground shots validated! {self.time}")
                    elif h.hit_type == 1:
                        if not validate_jump_shot(self,h,self.groundCutOff,self.singleJumpLimit,self.doubleJumpLimit):
                            #print(f"jumpshot invalidated! {self.time}")
                            return False
                        else:
                            pass
                    elif h.hit_type == 2:
                        if not validate_wall_shot(self,h,self.groundCutOff):
                            return False
                    elif h.hit_type == 3:
                        #hit_type 3 currently not in use
                        pass
                    elif h.hit_type == 4:
                        if not validate_double_jump_shot(self,h,self.singleJumpLimit,self.doubleJumpLimit):
                            #print(f"double jumpshot invalidated! {self.time}")
                            return False
                        else:
                            pass
                    elif h.hit_type == 5:
                        if not validate_aerial_shot(self,h,self.singleJumpLimit,self.doubleJumpLimit):
                            #print(f"aerial shot invalidated! {self.time}")
                            return False
                        else:
                            pass
        return True

    def update_hits(self):
        self.hits = findHits(
            self, self.groundCutOff, self.singleJumpLimit, self.doubleJumpLimit)

        self.test_pred = predictionStruct(convertStructLocationToVector(self.ballPred.slices[-1]),self.ballPred.slices[-1].game_seconds*1.0)
        self.sorted_hits = SortHits(self.hits)
        self.update_time = self.time*1
        #print(f"Updating hits {self.time}")

    # @profile
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # if self.index == 0:
        #     return self.get_output_copy(packet)
        oldTimer = self.time
        self.log.clear()
        self.preprocess(packet)

        if len(self.allies) > 0 and not self.ignore_kickoffs:
            # if self.team == 0:
            #     team_synergy(self)
            # else:
            newTeamStateManager(self)
            #dummyState(self)
        else:
            soloStateManager_testing(self)
            #dribbleTesting(self)
            # guidanceTesting(self)
            #aerialTesting(self)


        if not packet.game_info.is_round_active:
            self.activeState = None

        if self.activeState != None:
            action = self.activeState.update()

        else:
            action = SimpleControllerState()
            self.log.append(f"active state was None {self.time}")
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
            # numbers = [f"{x.time_difference():.2f}" if x != None else None for x in self.hits]
            # # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot
            # textOutput = f"ground shot:{numbers[0]} jumpshot:{numbers[1]} wallshot:{numbers[2]} highJump:{numbers[3]}"
            # self.renderer.draw_string_2d(20, 200, 3, 3, textOutput, self.renderer.white())
            for each in self.renderCalls:
                each.run()
            self.renderer.end_rendering()
            if self.debugging:
                for msg in self.log:
                    print(msg)
        self.renderCalls.clear()

        # if self.team == 1:
        #     print(self.activeState)

        return action
