from Utilities import *
from States import *
import time
import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3 as vector3, Rotator

from rlutilities.linear_algebra import *
from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash
from rlutilities.simulation import Game, Ball, Car

class diabloBot(BaseAgent):
    def __init__(self, name, team, index):
        Game.set_mode("soccar")
        self.game = Game(index, team)
        self.index = index
        self.name = name
        self.team = team

    def initialize_agent(self):
        self.controller_state = SimpleControllerState()
        self.me = physicsObject()
        self.ball = physicsObject()
        self.me.team = self.team
        self.allies = []
        self.enemies = []
        self.start = 5
        self.flipStart = 0
        self.flipping = False
        self.controller = None
        self.flipTimer = time.time()
        #self.activeState = Chase(self)
        self.activeState = Kickoff(self)
        self.gameInfo = None
        self.onSurface = False
        self.boosts = []
        self.fieldInfo = []
        self.positions = []
        self.time = 0
        self.deltaTime = 0
        self.maxSpd = 2200
        self.ballPred = []
        self.selectedBallPred = None
        self.ballDelay = 0
        self.renderCalls = []
        self.ballPredObj = None
        self.carHeight = 84
        self.forward = True
        self.velAngle = 0
        self.onWall = False
        self.stateTimer = time.time()

    def getActiveState(self):
        if type(self.activeState) == JumpingState:
            return 0
        if type(self.activeState) == Kickoff:
            return 1
        if type(self.activeState) == GetBoost:
            return 2
        if type(self.activeState) == Dribble:
            return 3
        if type(self.activeState) == GroundShot:
            return 4
        if type(self.activeState) == GroundDefend:
            return 5
        if type(self.activeState) == halfFlip:
            return 6

    def setHalfFlip(self):
        self.activeState = halfFlip(self)

    def determineFacing(self):
        offset = self.me.location + self.me.velocity
        #direction = self.me.location + offset
        loc = toLocal(offset,self.me)
        angle = math.degrees(math.atan2(loc[1],loc[0]))
        if angle < -180:
            angle += 360
        if angle > 180:
            angle -= 360

        if abs(angle) >150 and self.getCurrentSpd() > 200:
            self.forward = False
        else:
            self.forward = True

        self.velAngle = angle
        #print(self.forward, angle)



    def setJumping(self,targetType):
        self.activeState = JumpingState(self,targetType)


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
        self.ballPred = self.get_ball_prediction_struct()
        self.players = [self.index]
        self.game.read_game_information(game,
                                        self.get_rigid_body_tick(),
                                        self.get_field_info())
        car = game.game_cars[self.index]
        self.me.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
        self.me.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
        self.me.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
        #self.me.rotation = Rotation_Vector(car.physics.rotation)
        self.me.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
        self.me.boostLevel = car.boost
        self.onSurface = car.has_wheel_contact
        self.positions.insert(0,self.me.location)
        if len(self.positions) > 200:
            self.positions = self.positions[:200]
        # t = time.time()
        # self.deltaTime = t-self.time
        # self.time = t
        self.deltaTime = clamp(1/60,1/300,self.game.time_delta)
        # self.deltaList.insert(0,self.deltaTime)
        # if len(self.deltaList) > 200:
        #     self.deltaList = self.deltaList[:200]


        ball = game.game_ball.physics
        self.ball.location = Vector([ball.location.x, ball.location.y, ball.location.z])
        self.ball.velocity = Vector([ball.velocity.x, ball.velocity.y, ball.velocity.z])
        self.ball.rotation = Vector([ball.rotation.pitch, ball.rotation.yaw, ball.rotation.roll])
        self.ball.avelocity = Vector([ball.angular_velocity.x, ball.angular_velocity.y, ball.angular_velocity.z])
        self.me.matrix = rotator_to_matrix(self.me)
        self.ball.local_location = localizeVector(self.ball.location,self.me)
        self.determineFacing()
        self.onWall = False
        if self.onSurface:
            if self.me.location[2] > 70:
                self.onWall = True


        # collects info for all other cars in match, updates objects in self.players accordingly
        self.allies.clear()
        self.enemies.clear()
        for i in range(game.num_cars):
            if i != self.index:
                car = game.game_cars[i]
                _obj = physicsObject()
                _obj.index = i
                _obj.team = car.team
                _obj.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
                _obj.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
                _obj.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
                _obj.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
                _obj.boostLevel = car.boost
                _obj.local_location = localizeVector(_obj,self.me)

                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)
        self.gameInfo = game.game_info
        #print(self.Game.time_delta)


        #boost info
        self.boosts.clear()
        self.fieldInfo = self.get_field_info()
        for index in range(len(self.fieldInfo.boost_pads)):
            packetBoost = game.game_boosts[index]
            fieldInfoBoost = self.fieldInfo.boost_pads[index]
            self.boosts.append(Boost_obj([fieldInfoBoost.location.x,fieldInfoBoost.location.y,fieldInfoBoost.location.z],fieldInfoBoost.is_full_boost, packetBoost.is_active))




    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.preprocess(packet)
        #testFlight(self)
        #launchStateManager(self)
        if len(self.allies) >=1:
            teamStateManager(self)
        else:
            soloStateManager(self)
        #soloStateAerialManager(self)
        action = self.activeState.update()

        self.renderer.begin_rendering()
        self.renderer.draw_string_2d(100, 100, 1, 1, str(type(self.activeState)), self.renderer.white())

        for each in self.renderCalls:
            each.run()
        self.renderer.end_rendering()
        self.renderCalls.clear()

        return action


