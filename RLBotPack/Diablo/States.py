from Utilities import *
import time
import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

from rlutilities.linear_algebra import *
from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash, Drive #,FollowPath,
from rlutilities.simulation import Game, Ball, Car

class baseState:
    def __init__(self, agent):
        #generic useful objects
        self.agent = agent
        self.active = True

class State:
    RESET = 0
    WAIT = 1
    INITIALIZE = 2
    RUNNING = 3



class GetBoost(baseState):
    def update(self):
        return saferBoostGrabber(self.agent)


class airLaunch(baseState):
    def __init__(self,agent):
        baseState.__init__(self,agent)
        self.initiated = time.time()
        self.jumpTimer = time.time()
        self.firstJump = False
        self.secondJump = False
        self.firstJumpHold = 0.5
        self.secondJumpHold = 0.4


    def update(self):
        stateController = SimpleControllerState()

        if not self.firstJump:
            self.firstJump = True
            stateController.jump = True
            self.jumpTimer = time.time()

        elif self.firstJump and not self.secondJump:
            if time.time() - self.jumpTimer < self.firstJumpHold:
                stateController.jump = True

            elif time.time() - self.jumpTimer > self.firstJumpHold and time.time() - self.jumpTimer < self.firstJumpHold +.05:
                stateController.boost = True
                stateController.jump = False

            else:
                self.secondJump = True
                stateController.boost = True
                self.jumpTimer = time.time()

        else:
            if time.time() - self.jumpTimer < self.secondJumpHold:
                stateController.jump = True
                stateController.boost = True

            else:
                self.active = False
                self.jump = False
                #self.agent.activeState = flightSystems(self.agent)

        if time.time() - self.jumpTimer > 0.15:

            pitchAngle = math.degrees(self.agent.me.rotation[1])
            y_vel = self.agent.me.avelocity[1]
            pitch = 0
            if pitchAngle > 50:
                if y_vel > -.4:
                    pitch = clamp(1,-1,-1 + abs(y_vel))
            elif pitchAngle < 50:
                if y_vel < .4:
                    pitch = clamp(1,-1,1 - abs(y_vel))

            #print(pitchAngle)

            if y_vel > 1:
                pitch = -1
            elif y_vel < -1:
                pitch = 1

            stateController.pitch = pitch
        #print(math.degrees(self.agent.me.rotation[1]))
        return stateController


class AerialHandler():
    def __init__(self,agent):
        self.agent = agent
        self.active = False
        self.setup()

    def setup(self):
        self.aerial = Aerial(self.agent.game.my_car)
        self.turn = AerialTurn(self.agent.game.my_car)
        myGoal = center = Vector([0, 5200 * sign(self.agent.team), 200])
        enemyGoal = center = Vector([0, 5200 * -sign(self.agent.team), 200])
        if self.agent.me.boostLevel > 0:
            for i in range(0, self.agent.ballPred.num_slices):
                targetVec = Vector([self.agent.ballPred.slices[i].physics.location.x,
                                    self.agent.ballPred.slices[i].physics.location.y,
                                    self.agent.ballPred.slices[i].physics.location.z])
                # interferenceTimer += self.agent.deltaTime
                # if interferenceTimer < 1:
                #     if findEnemyClosestToLocation(self.agent,targetVec)[1] < 150:
                #         break
                if self.agent.ballPred.slices[i].physics.location.z >= 300:
                    goalDist = distance2D(center, targetVec)
                    #if distance2D(myGoal, targetVec) > distance2D(myGoal, self.agent.me.location):
                    if self.agent.me.location[1] * sign(self.agent.team) > self.agent.ballPred.slices[i].physics.location.y * sign(self.agent.team):
                        zOffset = 0
                        if goalDist < 1500:
                            if targetVec[2] > 600:
                                zOffset = 70
                        shotAngle = correctAngle(math.degrees(angle2(targetVec, enemyGoal)) + 90 * -sign(self.agent.team))


                        if abs(shotAngle) <=80:
                            xOffset = clamp(80,-80,(shotAngle*2)*-sign(self.agent.team))
                            self.aerial.target = vec3(self.agent.ballPred.slices[i].physics.location.x+xOffset,
                                                      self.agent.ballPred.slices[i].physics.location.y,
                                                      self.agent.ballPred.slices[i].physics.location.z+zOffset)

                            self.aerial.arrival_time = self.agent.ballPred.slices[i].game_seconds

                            simulation = self.aerial.simulate()

                            # # check if we can reach it by an aerial
                            if norm(simulation.location - self.aerial.target) < 100:
                                self.target_ball = self.agent.ballPred.slices[i]
                                self.xOffset = xOffset
                                self.zOffset = zOffset
                                self.active = True
                                break

    def stillValid(self):
        for i in range(0, self.agent.ballPred.num_slices):
            if self.agent.ballPred.slices[i].physics.location.z >= 300:
                if abs(self.target_ball.game_seconds - self.agent.ballPred.slices[i].game_seconds) < self.agent.deltaTime*3:
                    difference = 0
                    difference+= abs((self.agent.ballPred.slices[i].physics.location.x+self.xOffset) - (self.target_ball.physics.location.x+self.zOffset))
                    difference += abs(self.agent.ballPred.slices[i].physics.location.y - self.target_ball.physics.location.y)
                    difference += abs((self.agent.ballPred.slices[i].physics.location.z+self.zOffset) - (self.target_ball.physics.location.z+self.zOffset))
                    if difference < 10:
                        self.aerial.target = vec3(self.agent.ballPred.slices[i].physics.location.x + self.xOffset,
                                                  self.agent.ballPred.slices[i].physics.location.y,
                                                  self.agent.ballPred.slices[i].physics.location.z + self.zOffset)

                        self.aerial.arrival_time = self.agent.ballPred.slices[i].game_seconds
                        self.target_ball = self.agent.ballPred.slices[i]

                        simulation = self.aerial.simulate()
                        return

        self.active = False
        self.setup()

    def update(self):
        if self.agent.me.boostLevel > 0:
            self.setup()
            self.aerial.step(self.agent.deltaTime)
            self.controls = self.aerial.controls
            self.controls.jump = True
            if self.aerial.finished:
                self.active = False
        else:
            self.active = False
        return self.controls


class JumpingState(baseState):
    def __init__(self,agent, targetCode): #0 for ball, 1 for forward...
        self.agent = agent
        self.active = True
        self.targetCode = targetCode
        self.flip_obj = FlipStatus()

    def update(self):
        controller_state = SimpleControllerState()
        jump = flipHandler(self.agent, self.flip_obj)
        if jump:
            if self.targetCode == 1:
                controller_state.pitch = -1
                controller_state.steer = 0
                controller_state.throttle = 1

            elif self.targetCode == 0:
                #print("How can I flip towards a ball when you don't tell me where it is?!?!?!")
                ball_local = toLocal(self.agent.ball.location, self.agent.me)
                ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
                #print(ball_angle,math.cos(ball_angle))
                controller_state.jump = True
                controller_state.yaw = math.sin(ball_angle)
                pitch = -math.cos(ball_angle) #-abs(math.cos(ball_angle))
                controller_state.pitch = pitch
                if pitch > 0:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1

            elif self.targetCode == 2:
                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.yaw = 0
            if self.targetCode == 3:
                controller_state.pitch = 1
                controller_state.steer = 0
                controller_state.throttle = -1

        controller_state.jump = jump
        controller_state.boost = False
        #controller_state.throttle = 1
        if self.flip_obj.flipDone:
            self.active = False

        return controller_state


class gettingPhysical(baseState):
    def update(self):
        action = demoMagic(self.agent)
        if action != None:
            return action
        else:
            return saferBoostGrabber(self.agent)


class GroundShot(baseState):
    #shoot while ball grounded
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return lineupShot(self.agent,3)

class Dribble(baseState):
    #shoot while ball grounded
    def __init__(self, agent):
        #generic useful objects
        self.agent = agent
        self.active = True

    def update(self):
        # if not kickOffTest(self.agent):
        #     #return boostHungry(self.agent)
        return lineupShot(self.agent,1)
        # else:
        #     self.active = False
        #     #print("Retiring groundshot")
        #     self.agent.activeState = Kickoff(self.agent)
        #     return self.agent.activeState.update()


class GroundDefend(baseState):
    def update(self):
        # if not kickOffTest(self.agent):
        return defendGoal(self.agent)
        # else:
        #     self.active = False
        #     #print("Retiring groundshot")
        #     self.agent.activeState = Kickoff(self.agent)
        #     return self.agent.activeState.update()


class AerialDefend(baseState):
    #defend while ball is in air
    pass




class Obstruct(baseState):
    #stay on the direct opposite side of the ball from the opposition
    def update(self):
        if not kickOffTest(self.agent):
            return turtleTime(self.agent)

        else:
            self.active = False
            #print("Retiring turtleMode")
            self.agent.activeState = Kickoff(self.agent)
            return self.agent.activeState.update()

class Kickoff(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.started = False
        self.firstFlip = False
        self.secondFlip = False
        self.finalFlipDistance = 900
        self.active = True
        self.startTime = time.time()
        self.flipState = None

    def retire(self):
        self.active = False
        self.agent.activeState = None
        self.flipState = None
        #stateManager(self.agent)

    def update(self):
        spd = self.agent.getCurrentSpd()
        if self.flipState != None:
            if self.flipState.active:
                controller = self.flipState.update()
                if time.time() - self.flipState.flip_obj.flipStartedTimer <= 0.15:
                    if spd < 2200:
                        controller.boost = True
                return controller
            if self.secondFlip:
                self.retire()

        jumping = False
        ballDistance = findDistance(self.agent.me.location, self.agent.ball.location)

        if not self.started:
            if not kickOffTest(self.agent):
                self.started = True
                self.startTime = time.time()

        if self.started and time.time() - self.startTime > 2.5:
            self.retire()

        if not self.firstFlip:
            if spd > 1100:
                self.flipState = JumpingState(self.agent,1)
                self.firstFlip = True
                return self.flipState.update()

        if ballDistance > self.finalFlipDistance:
            return greedyMover(self.agent, self.agent.ball)

        else:
            self.flipState = JumpingState(self.agent,1)
            self.secondFlip = True
            return self.flipState.update()

class aerialRecovery(baseState):
    def update(self):
        if self.agent.onSurface or self.agent.me.location[2] < 100:
            self.active = False
        controller_state = SimpleControllerState()
        # if self.agent.me.rotation[1] > 0:
        #     controller_state.pitch = 1
        #
        # elif self.agent.me.rotation[1] < 0:
        #     controller_state.pitch = -1

        if self.agent.me.rotation[2] > 0:
            controller_state.roll = -1

        elif self.agent.me.rotation[2] < 0:
            controller_state.roll = 1

        if self.agent.me.rotation[0] > self.agent.velAngle:
            controller_state.yaw = -1

        elif self.agent.me.rotation[0] < self.agent.velAngle:
            controller_state.yaw = 1

        # if self.agent.me.avelocity[0] > 2:
        #     controller_state.yaw = -1
        # elif self.agent.me.avelocity[0] < 2:
        #     controller_state.yaw = 1
        #
        # if self.agent.me.avelocity[1] > 2:
        #     controller_state.pitch= 1
        # elif self.agent.me.avelocity[1] < 2:
        #     controller_state.pitch = -1
        #
        # if self.agent.me.avelocity[2] > 2:
        #     controller_state.roll = -1
        # elif self.agent.me.avelocity[2] < 2:
        #     controller_state.roll = 1

        if self.active:
            controller_state.throttle = 1
        else:
            controller_state.throttle = 0

        return controller_state



class halfFlip(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.active = True
        self.firstJump= False
        self.secondJump = False
        self.jumpStart = 0
        self.timeCreated = time.time()
        #print("half flipping!!!")


    def update(self):
        controller_state = SimpleControllerState()
        if not self.firstJump:
            controller_state.throttle = -1
            controller_state.jump = True
            controller_state.pitch = 1
            self.firstJump = True
            self.jumpStart = time.time()
            return controller_state

        elif self.firstJump and not self.secondJump:
            jumpTimer = time.time() - self.jumpStart
            controller_state.throttle = -1
            controller_state.pitch = 1
            controller_state.jump = False
            if jumpTimer < 0.12:
                controller_state.jump = True
            if jumpTimer > 0.15:
                controller_state.jump = True
                self.jumpStart = time.time()
                self.secondJump = True
            return controller_state

        elif self.firstJump and self.secondJump:
            timer = time.time() - self.jumpStart
            if timer < 0.15:
                controller_state.throttle = -1
                controller_state.pitch = 1

            else:
                controller_state.pitch = -1
                controller_state.throttle = 1
                controller_state.roll = 1

            if timer > .8:
                controller_state.roll = 0
            if timer > 1.15:
                self.active = False
            return controller_state

        else:
            print("halfFlip else conditional called in update. This should not be happening")



class Chase(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        if not kickOffTest(self.agent):
            return efficientMover(self.agent,self.agent.ball,self.agent.maxSpd)
        else:
            self.active = False
            self.agent.activeState = Kickoff(self.agent)
            #print("switchign to kickoff")
            return self.agent.activeState.update()

class backMan(baseState):
    def update(self):
        return backmanDefense(self.agent)


class secondMan(baseState):
    def update(self):
        return secondManSupport(self.agent)




def alteredStateManager(agent):
    agentType = type(agent.activeState)
    if agentType == JumpingState:
        if agent.activeState.active != False:
            return
    if agentType != gettingPhysical:
        agent.activeState = gettingPhysical(agent)

def halfFlipStateManager(agent):
    if agent.activeState.active == False:
        agent.activeState = halfFlip(agent)

    else:
        if type(agent.activeState) != halfFlip:
            agent.activeState = halfFlip(agent)


def simpleStateManager(agent):
    agentType = type(agent.activeState)

    if agentType != Kickoff:
        if not kickOffTest(agent):
            myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc,agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc,agent.me)

            timeTillBallReady = 9999
            agent.ballDelay = 6

            #ballStruct = findSuitableBallPosition(agent, 125)
            #ballStruct = findSoonestBallTouchable(agent)
            ballStruct =  findSuitableBallPosition2(agent, 150,agent.getCurrentSpd(),agent.me.location)
            agent.selectedBallPred = ballStruct
            goalward = ballHeadedTowardsMyGoal(agent)
            openNet = openGoalOpportunity(agent)

            if ballStruct != None:
                if ballStruct == agent.ballPred.slices[0]:
                    timeTillBallReady = 0
                else:
                    timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
                #print(timeTillBallReady)
            else:
                timeTillBallReady = 0
            agent.ballDelay = timeTillBallReady


            if agentType == JumpingState:
                if agent.activeState.active != False:
                    return

            if agentType == halfFlip:
                if agent.activeState.active != False:
                    return

            if agentType == aerialRecovery:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 150:
                    if agentType != aerialRecovery:
                        agent.activeState = aerialRecovery(agent)
                    return

            if ballDistanceFromGoal < 2500:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)

            elif carDistanceFromGoal > ballDistanceFromGoal+50:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)

            elif goalward:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)


            else:
                if openNet:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return

                elif challengeDecider(agent):
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return

                # elif timeTillBallReady > 2.5:
                #     if agent.me.boostLevel <= 25:
                #         if agentType != GetBoost:
                #             agent.activeState = GetBoost(agent)
                #         return

                if agentType != Dribble:
                    agent.activeState = Dribble(agent)


        else:
            agent.activeState = Kickoff(agent)

def teamStateManager(agent):
    agentType = type(agent.activeState)

    if agentType != Kickoff:
        if not kickOffTest(agent):
            myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)

            carDistancesFromGoal = []
            for c in agent.allies:
                carDistancesFromGoal.append(distance2D(myGoalLoc, c.location))

            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            cardistancesFromBall = []
            for c in agent.allies:
                cardistancesFromBall.append(distance2D(agent.ball.location, c.location))

            carDistanceFromBall = distance2D(agent.me.location,agent.ball.location)



            timeTillBallReady = 9999
            agent.ballDelay = 6
            ballStruct = findSuitableBallPosition2(agent, 150, agent.getCurrentSpd(), agent.me.location)
            agent.selectedBallPred = ballStruct
            goalward = ballHeadedTowardsMyGoal(agent)

            if ballStruct != None:
                if ballStruct == agent.ballPred.slices[0]:
                    timeTillBallReady = 0
                else:
                    timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
            else:
                timeTillBallReady = 0
            agent.ballDelay = timeTillBallReady

            if agentType == JumpingState:
                if agent.activeState.active != False:
                    return

            if agentType == halfFlip:
                if agent.activeState.active != False:
                    return

            if agentType == aerialRecovery:
                if agent.activeState.active != False:
                    _test = AerialHandler(agent)
                    if _test.active:
                        if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady:
                            agent.activeState = _test
                    return
            if agentType == AerialHandler:
                if agent.activeState.active != False:
                    return

            _test = AerialHandler(agent)
            if _test.active:
                if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady :
                    agent.activeState = _test
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 150:
                    if agentType != aerialRecovery:
                        agent.activeState = aerialRecovery(agent)
                        return

            if len(agent.allies) < 1:
                soloStateManager(agent)
                return



            if len(agent.allies) == 1:
                if carDistanceFromBall< cardistancesFromBall[0]:
                    if carDistanceFromGoal < ballDistanceFromGoal:
                        if not goalward:
                            if agentType != Dribble:
                                agent.activeState = Dribble(agent)
                            return
                        else:
                            if agentType != GroundDefend:
                                agent.activeState = GroundDefend(agent)
                            return
                    else:
                        if ballDistanceFromGoal <= 3500:
                            if agent.activeState != backMan:
                                agent.activeState = backMan(agent)
                            return
                        else:
                            agent.activeState = secondMan(agent)

                else:
                    if ballDistanceFromGoal >=3500:
                        if agentType != secondMan:
                            agent.activeState = secondMan(agent)
                        return
                    else:
                        if agentType != backMan:
                            agent.activeState = backMan(agent)
                        return

            else:
                if carDistanceFromBall < min(cardistancesFromBall):
                    if carDistanceFromGoal < ballDistanceFromGoal:
                        if agentType != Dribble:
                            agent.activeState = Dribble(agent)
                        return
                    else:
                        if agent.activeState != backMan:
                            agent.activeState = backMan(agent)
                        return

                if ballDistanceFromGoal >= 6500:
                    if carDistanceFromGoal > min(carDistancesFromGoal):
                        if agentType != gettingPhysical:
                            agent.activeState = gettingPhysical(agent)
                        return
                    else:
                        if agent.activeState != secondMan:
                            agent.activeState = secondMan(agent)
                        return

                else:
                    if carDistanceFromGoal <= min(carDistancesFromGoal):
                        if agentType != backMan:
                            agent.activeState = backMan(agent)
                        return
                    else:
                        if ballDistanceFromGoal >= 5000:
                            if agentType != gettingPhysical:
                                agent.activeState = gettingPhysical(agent)
                            return
                        else:
                            if agentType != Dribble:
                                agent.activeState = Dribble(agent)
                            return

        else:
            agent.activeState = Kickoff(agent)

def launchStateManager(agent):
    if agent.activeState:
        if agent.activeState.active:
            return
        else:
            if type(agent.activeState) == airLaunch:
                agent.activeState = aerialRecovery(agent)

            # elif type(agent.activeState) == flightSystems:
            #     agent.activeState = aerialRecovery(agent)

            else:
                if agent.onSurface:
                    if agent.getCurrentSpd() < 50:
                        agent.activeState = airLaunch(agent)

    else:
        agent.activeState = airLaunch(agent)



def soloStateManager(agent):
    agentType = type(agent.activeState)

    if agentType != Kickoff:
        if not kickOffTest(agent):
            myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            timeTillBallReady = 9999
            agent.ballDelay = 6

            # ballStruct = findSuitableBallPosition(agent, 125)
            # ballStruct = findSoonestBallTouchable(agent)
            ballStruct = findSuitableBallPosition2(agent, 150, agent.getCurrentSpd(), agent.me.location)
            agent.selectedBallPred = ballStruct
            goalward = ballHeadedTowardsMyGoal(agent)
            openNet = openGoalOpportunity(agent)

            if ballStruct != None:
                if ballStruct == agent.ballPred.slices[0]:
                    timeTillBallReady = 0
                else:
                    timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
                # print(timeTillBallReady)
            else:
                timeTillBallReady = 0
            agent.ballDelay = timeTillBallReady

            if agentType == JumpingState:
                if agent.activeState.active != False:
                    return

            if agentType == halfFlip:
                if agent.activeState.active != False:
                    return

            if agentType == aerialRecovery:
                if agent.activeState.active != False:
                    return

            if agentType == AerialHandler:
                if agent.activeState.active != False:
                    return

            _test = AerialHandler(agent)
            if _test.active:
                if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady:
                    agent.activeState = _test
                    #print("going for aerial!")
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 150:
                    if agentType != aerialRecovery:
                        agent.activeState = aerialRecovery(agent)
                        return

            if ballDistanceFromGoal < 2500:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)


            elif carDistanceFromGoal > ballDistanceFromGoal + 50:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)

            elif goalward:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)


            else:
                # if timeTillBallReady < 2:
                if openNet:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return

                elif challengeDecider(agent):
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return


                elif agent.me.boostLevel >= 25:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)

                else:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)

                # else:
                #     if agentType != GetBoost:
                #         agent.activeState = GetBoost(agent)

        else:
            agent.activeState = Kickoff(agent)

# def soloStateAerialManager(agent):
#     agentType = type(agent.activeState)
#
#     if agentType != Kickoff:
#         if not kickOffTest(agent):
#             myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])
#
#             ballDistanceFromGoal = distance2D(myGoalLoc,agent.ball)
#             carDistanceFromGoal = distance2D(myGoalLoc,agent.me)
#
#             timeTillBallReady = 9999
#             agent.ballDelay = 6
#
#             #ballStruct = findSuitableBallPosition(agent, 125)
#             #ballStruct = findSoonestBallTouchable(agent)
#             ballStruct =  findSuitableBallPosition2(agent, 150,agent.getCurrentSpd(),agent.me.location)
#             agent.selectedBallPred = ballStruct
#             goalward = ballHeadedTowardsMyGoal(agent)
#             openNet = openGoalOpportunity(agent)
#
#             if ballStruct != None:
#                 if ballStruct == agent.ballPred.slices[0]:
#                     timeTillBallReady = 0
#                 else:
#                     timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
#                 #print(timeTillBallReady)
#             else:
#                 timeTillBallReady = 0
#             agent.ballDelay = timeTillBallReady
#
#
#             if agentType == JumpingState:
#                 if agent.activeState.active != False:
#                     return
#
#             if agentType == halfFlip:
#                 if agent.activeState.active != False:
#                     return
#
#             if agentType == aerialRecovery:
#                 if agent.activeState.active != False:
#                     return
#
#             if agentType == AerialHandler:
#                 if agent.activeState.active != False:
#                     return
#
#             _test = AerialHandler(agent)
#             if _test.active:
#                 if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady :
#                     agent.activeState = _test
#                     return
#
#             if not agent.onSurface:
#                 if agent.me.location[2] > 150:
#                     if agentType != aerialRecovery:
#                         agent.activeState = aerialRecovery(agent)
#                         return
#
#
#             if ballDistanceFromGoal < 2500:
#                 if agentType != GroundDefend:
#                     agent.activeState = GroundDefend(agent)
#
#
#             elif carDistanceFromGoal > ballDistanceFromGoal+50:
#                 if agentType != GroundDefend:
#                     agent.activeState = GroundDefend(agent)
#
#             elif goalward:
#                 if agentType != GroundDefend:
#                     agent.activeState = GroundDefend(agent)
#
#
#             else:
#                 #if timeTillBallReady < 2:
#                 if openNet:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#                     return
#
#                 elif challengeDecider(agent):
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#                     return
#
#
#                 elif agent.me.boostLevel >= 25:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#
#                 else:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#
#
#                 # else:
#                 #     if agentType != GetBoost:
#                 #         agent.activeState = GetBoost(agent)
#
#         else:
#             agent.activeState = Kickoff(agent)



# def soloStateManager(agent):
#     agentType = type(agent.activeState)
#
#     if agentType != Kickoff:
#         if not kickOffTest(agent):
#             myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])
#
#             ballDistanceFromGoal = distance2D(myGoalLoc,agent.ball)
#             carDistanceFromGoal = distance2D(myGoalLoc,agent.me)
#
#             timeTillBallReady = 9999
#             agent.ballDelay = 6
#
#             #ballStruct = findSuitableBallPosition(agent, 125)
#             #ballStruct = findSoonestBallTouchable(agent)
#             ballStruct =  findSuitableBallPosition2(agent, 150,agent.getCurrentSpd(),agent.me.location)
#             agent.selectedBallPred = ballStruct
#             goalward = ballHeadedTowardsMyGoal(agent)
#             openNet = openGoalOpportunity(agent)
#
#             if ballStruct != None:
#                 if ballStruct == agent.ballPred.slices[0]:
#                     timeTillBallReady = 0
#                 else:
#                     timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
#                 #print(timeTillBallReady)
#             else:
#                 timeTillBallReady = 0
#             agent.ballDelay = timeTillBallReady
#
#
#             if agentType == JumpingState:
#                 if agent.activeState.active != False:
#                     return
#
#             if agentType == halfFlip:
#                 if agent.activeState.active != False:
#                     return
#
#             if agentType == aerialRecovery:
#                 if agent.activeState.active != False:
#                     return
#
#             if not agent.onSurface:
#                 if agent.me.location[2] > 150:
#                     if agentType != aerialRecovery:
#                         agent.activeState = aerialRecovery(agent)
#                         return
#
#
#             if ballDistanceFromGoal < 2500:
#                 if agentType != GroundDefend:
#                     agent.activeState = GroundDefend(agent)
#
#
#             elif carDistanceFromGoal > ballDistanceFromGoal+50:
#                 if agentType != GroundDefend:
#                     agent.activeState = GroundDefend(agent)
#
#             # elif goalward:
#             #     if agentType != GroundDefend:
#             #         agent.activeState = GroundDefend(agent)
#
#
#             else:
#                 #if timeTillBallReady < 2:
#                 if openNet:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#                     return
#
#                 elif challengeDecider(agent):
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#                     return
#
#
#                 elif agent.me.boostLevel >= 25:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#
#                 else:
#                     if agentType != Dribble:
#                         agent.activeState = Dribble(agent)
#
#
#                 # else:
#                 #     if agentType != GetBoost:
#                 #         agent.activeState = GetBoost(agent)
#
#         else:
#             agent.activeState = Kickoff(agent)
