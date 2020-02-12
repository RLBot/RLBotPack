import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3 as vector3, Rotator
from Utilities import *
from States import *
import cProfile, pstats, io
import time
import numpy as np



def profile(fnc):
    """A decorator that uses cProfile to profile a function"""

    def inner(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = fnc(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return retval

    return inner



class Kamael(BaseAgent):

    def initialize_agent(self):
        self.controller_state = None #SimpleControllerState()
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
        self.currentSpd = 1
        #octane hitbox
        self.hitbox_set = False
        self.carLength = 118.007
        self.carWidth = 84.2
        self.carHeight = 36.159
        self.groundCutOff = 120#93+(self.carHeight*.8)
        self.ballGrounded = False
        self.closestEnemyToMe = None
        self.closestEnemyToMeDistance = math.inf
        self.closestEnemyToBall = None
        self.closestEnemyDistances = [0,0,0,0,0]
        self.enemyAttacking = False
        self.enemyBallInterceptDelay = 0
        self.enemyPredTime = 0
        self.closestEnemyToBallDistance = math.inf
        #self.enemyBallTime = 0
        self.enemyTargetVec = Vector([0,0,0])
        self.contestedThreshold = 650
        self.superSonic = False
        self.wallShot = False
        self.openGoal = False
        self.boostConsumptionRate = 33.3
        self.boostAccelerationRate = 991.666
        self.jumpLimit = 280
        self.wallShotsEnabled = True
        self.touch = None
        self.targetDistance = 1500
        self.fpsLimit = 1/120
        self.gravity = -650
        self.jumpPhysics = physicsObject()
        self.hits = []
        self.fakeDeltaTime = 1/60
        self.heightIncrement = .75/self.jumpLimit
        self.accelerationTick = self.boostAccelerationRate*(1/60)
        self.currentHit = None
        self.resetLimit = 5
        self.resetCount = 0
        self.resetTimer = 0
        self.timid = False
        self.dribbling = False
        self.goalward = False
        self.stubbornessTimer = 0
        self.stubbornessMax = 600
        self.stubbornessMin = 300
        self.stubborness = self.stubbornessMin
        self.activeState = PreemptiveStrike(self)
        self.contestedTimeLimit = .5
        self.demoSpawns = [[Vector([-2304, -4608,0]),Vector([2304, -4608,0])],[Vector([2304, 4608,0]),Vector([-2304, 4608,0])]]
        self.rotationNumber = 1
        self.dtype = [('physics', [('location', '<f4', 3), ('rotation', [('pitch', '<f4'), ('yaw', '<f4'), ('roll', '<f4')]), ('velocity', '<f4', 3), ('angular_velocity', '<f4', 3)]), ('game_seconds', '<f4')]
        self.Dtype = np.dtype([('physics', [('location', '<f4', 3),
                               ('rotation', [('pitch', '<f4'), ('yaw', '<f4'), ('roll', '<f4')]),
                               ('velocity', '<f4', 3),
                               ('angular_velocity', '<f4', 3)]),
                  ('game_seconds', '<f4')])

        self.reachLength = 93+50
        self.debugging = False

    def demoRelocation(self,car):
        if car.team == 0:
            if distance2D(self.ball.location,self.demoSpawns[0][0]) < distance2D(self.ball.location,self.demoSpawns[0][1]):
                return self.demoSpawns[0][0]
            else:
                return self.demoSpawns[0][1]
        else:
            if distance2D(self.ball.location, self.demoSpawns[1][0]) < distance2D(self.ball.location,
                                                                                  self.demoSpawns[1][1]):
                return self.demoSpawns[1][0]
            else:
                return self.demoSpawns[1][1]

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

    def setJumpPhysics(self):
        car_up = Vector([0, 0, 1]).align_to(self.me.rotation)
        self.jumpPhysics.location = self.me.location
        self.jumpPhysics.velocity = self.me.velocity + car_up.scale(300)
        self.jumpPhysics.avelocity = self.me.avelocity

    def calcDeltaV(self, position, time):
        carPos = self.me.location
        carVel = self.jumpPhysics.velocity
        return Vector([
            (position[0] - carVel[0] * time - carPos[0]) / (0.5 * time * time),
            (position[1] - carVel[1] * time - carPos[1]) / (0.5 * time * time),
            (position[2] - carVel[2] * time - carPos[2]) / (0.5 * time * time) - self.gravity,
        ])

    def determineFacing(self):
        offset = self.me.location + self.me.velocity.normalize().scale(500)
        loc = toLocal(offset,self.me)
        angle = correctAngle(math.degrees(math.atan2(loc[1],loc[0])))

        if abs(angle) > 90:
            if self.currentSpd <= self.stubborness:
                self.forward = True
            else:
                self.forward = False
            #self.forward = False
        else:
            self.forward = True
        #self.forward = False

        self.velAngle = angle

    def setPowershot(self,delay,target):
        self.activeState = RighteousVolley(self,delay,target)



    def setJumping(self,targetType,target = None):
        _time = self.time
        if _time - self.flipTimer >= 1.9:
            self.activeState = LeapOfFaith(self, targetType,target = target)
            self.flipTimer = _time

    def setDashing(self,target):
        self.activeState = WaveDashing(self,target)


    def getCurrentSpd(self):
        return Vector(self.me.velocity[:2]).magnitude()

    def updateSelectedBallPrediction(self,ballStruct):
        x = physicsObject()
        x.location = Vector([ballStruct.physics.location.x, ballStruct.physics.location.y, ballStruct.physics.location.z])
        x.velocity = Vector([ballStruct.physics.velocity.x, ballStruct.physics.velocity.y, ballStruct.physics.velocity.z])
        x.rotation = Vector([ballStruct.physics.rotation.pitch, ballStruct.physics.rotation.yaw, ballStruct.physics.rotation.roll])
        x.avelocity = Vector([ballStruct.physics.angular_velocity.x, ballStruct.physics.angular_velocity.y, ballStruct.physics.angular_velocity.z])
        x.local_location = localizeVector(x.location, self.me)
        self.ballPredObj = x




    def preprocess(self, game):
        self.oldPreds = self.ballPred
        self.ballPred = self.get_ball_prediction_struct()
        self.players = [self.index]
        car = game.game_cars[self.index]
        self.timid = False
        self.deltaTime = clamp(1, self.fpsLimit, game.game_info.seconds_elapsed - self.time)
        self.time = game.game_info.seconds_elapsed
        self.me.demolished = car.is_demolished
        if not car.is_demolished:
            self.me.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
            self.me.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
            self.me.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
            self.me.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
            self.me.boostLevel = car.boost
            self.onSurface = car.has_wheel_contact
            self.superSonic = car.is_super_sonic
            self.currentSpd = clamp(2300, 1, self.getCurrentSpd())
        else:
            self.me.location = self.demoRelocation(car)
            self.me.velocity = Vector([0,0,0])
            self.me.rotation = Vector([0,0,0])
            self.me.avelocity = Vector([0,0,0])
            self.me.boostLevel = 34
            self.onSurface = True
            self.superSonic = False
            self.currentSpd = 0.0001

        #print(self.me.rotation[0])
        if not self.hitbox_set:
            self.fieldInfo = self.get_field_info()
            self.carLength = car.hitbox.length
            self.carWidth = car.hitbox.width
            self.carHeight = car.hitbox.height
            self.groundCutOff = 93+(self.carHeight*.72)
            self.hitbox_set = True
            self.reachLength = 75+(car.hitbox.length*.665)
            print(f"Kamael on team {self.team} hitbox (length:{self.carLength} width:{self.carWidth} height:{self.carHeight}) ")

        if self.stubbornessTimer > 0:
            self.stubbornessTimer -= self.deltaTime
            if self.stubbornessTimer <=0:
                self.stubborness = self.stubbornessMin

        ball = game.game_ball.physics
        self.ball.location = Vector([ball.location.x, ball.location.y, ball.location.z])
        self.ball.velocity = Vector([ball.velocity.x, ball.velocity.y, ball.velocity.z])
        self.ball.rotation = Vector([ball.rotation.pitch, ball.rotation.yaw, ball.rotation.roll])
        self.ball.avelocity = Vector([ball.angular_velocity.x, ball.angular_velocity.y, ball.angular_velocity.z])
        self.me.matrix = rotator_to_matrix(self.me)
        self.ball.local_location = localizeVector(self.ball.location,self.me)
        ball.lastTouch = game.game_ball.latest_touch.time_seconds
        ball.lastToucher = game.game_ball.latest_touch.player_name
        touch = ballTouch(game.game_ball.latest_touch)
        if not self.touch:
            self.touch = touch

        if self.touch != touch:
            self.touch = touch

        self.allies.clear()
        self.enemies.clear()
        for i in range(game.num_cars):
            if i != self.index:
                car = game.game_cars[i]
                _obj = physicsObject()
                _obj.index = i
                _obj.team = car.team
                _obj.demolished = car.is_demolished
                if not car.is_demolished:
                    _obj.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
                    _obj.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
                    _obj.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
                    _obj.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
                    _obj.boostLevel = car.boost
                    _obj.local_location = localizeVector(_obj,self.me)
                    _obj.onSurface = car.has_wheel_contact
                else:
                    #print(f"relocated demo'd player {car.name}")
                    _obj.location = self.demoRelocation(car)
                    _obj.velocity = Vector([0, 0, 0])
                    _obj.rotation = Vector([0, 0, 0])
                    _obj.avelocity = Vector([0, 0, 0])
                    _obj.boostLevel = 33
                    _obj.onSurface = True

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
            if packetBoost.timer <=0:
                if packetBoost.is_active:
                    boostStatus = True
            boostLocation = [fieldInfoBoost.location.x,fieldInfoBoost.location.y,fieldInfoBoost.location.z]
            boost_obj = Boost_obj([fieldInfoBoost.location.x,fieldInfoBoost.location.y,fieldInfoBoost.location.z],fieldInfoBoost.is_full_boost, boostStatus)
            self.boosts.append(boost_obj)
            if boost_obj.bigBoost:
                self.bigBoosts.append(boost_obj)

        self.onWall = False
        self.wallShot = False
        if self.onSurface:
            if self.me.location[2] >= self.wallLimit:
                self.onWall = True
        #if type(self.activeState) != PreemptiveStrike:
        self.hits =  findHits(self, self.groundCutOff, self.jumpLimit)
        # for i in range(1000):
        #     convertToArray(self)
        # for i in range(1000):
        #     newConvertToArray(self)
        #self.ballPred = newConvertToArray(self)
        #self.hits = findHits_testing(self, self.groundCutOff, self.jumpLimit)

        # print("==========")
        # for each in self.hits:
        #     if each != None:
        #         print(each)


        self.determineFacing()
        self.goalPred = None
        self.gravity = game.game_info.world_gravity_z
        self.dribbling = dirtyCarryCheck(self)
        self.findClosestToEnemies()
        self.resetCount +=1
        if self.resetCount >= self.resetLimit:
            findEnemyHits(self)
            self.resetCount = 0
        else:
            self.enemyBallInterceptDelay = self.enemyPredTime - self.time
        drawAsterisks(self.enemyTargetVec,self)




    def findClosestToEnemies(self):
        if len(self.enemies) > 0:
            self.closestEnemyToBall, self.closestEnemyToBallDistance = findEnemyClosestToLocation2D(self,self.ball.location)
            self.closestEnemyToMe, self.closestEnemyToMeDistance = findEnemyClosestToLocation2D(self, self.me.location)
            self.contested = False
            self.enemyAttacking = False

            if self.closestEnemyToBallDistance <=self.contestedThreshold:
                self.contested = True
                self.enemyAttacking = True

            elif self.enemyAttackingBall():
                self.enemyAttacking = True

            closestEnemyToBallTargetDistance = distance2D(self.enemyTargetVec,self.closestEnemyToBall.location)
            #self.closestEnemyDistances.append(self.closestEnemyToBallDistance)
            self.closestEnemyDistances.append(closestEnemyToBallTargetDistance)
            del self.closestEnemyDistances[0]
        else:
            self.closestEnemyToBall = self.me
            self.closestEnemyToMe = self.me
            self.closestEnemyToBallDistance = 0
            self.closestEnemyToMeDistance = 0
            self.contested = False
            self.enemyAttacking = False
        # if self.enemyBallInterceptDelay != 0:
        #     print(f"{self.enemyBallInterceptDelay}")


    def enemyAttackingBall(self):
        current = math.inf
        for each in self.closestEnemyDistances:
            if each < current:
                current = each
            else:
                return False

        return True

    #@profile
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        oldTimer = self.time
        self.preprocess(packet)
        if len(self.allies) > 0:
            newTeamStateManager(self)
        else:
            #soloStateManager(self)
            # if self.team == 0:
            #     soloStateManager(self)
            # else:
            soloStateManager_testing(self)

        #action = SimpleControllerState()
        action = self.activeState.update()
        self.controller_state = action
        if self.debugging:
            self.renderer.begin_rendering()
            self.renderer.draw_string_3d(self.me.location.data, 2, 2, str(type(self.activeState).__name__),
                                         self.renderer.white())

            for each in self.renderCalls:
                each.run()
            self.renderer.end_rendering()
            self.renderCalls.clear()

        # if self.currentSpd < 300:
        #     print(self.activeState)
        # if not self.onSurface:
        #     action.handbrake = True

        return action




