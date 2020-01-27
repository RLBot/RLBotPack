from Utilities import *
import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

"""
Right corner	loc: (-2048, -2560), yaw: 0.25 pi	loc: (2048, 2560), yaw: -0.75 pi
Left corner	loc: (2048, -2560), yaw: 0.75 pi	loc: (-2048, 2560), yaw: -0.25 pi
Back right	loc: (-256.0, -3840), yaw: 0.5 pi	loc: (256.0, 3840), yaw: -0.5 pi
Back left	loc: (256.0, -3840), yaw: 0.5 pi	loc: (-256.0, 3840), yaw: -0.5 pi
Far back center	loc: (0.0, -4608), yaw: 0.5 pi	loc: (0.0, 4608), yaw: -0.5 pi
"""


def getKickoffPosition(vec):
    kickoff_locations = [[2048, 2560], [256, 3848], [0, 4608]]
    if abs(vec[0]) >= 350:
        return 0
    elif abs(vec[0]) > 5:
        return 1
    else:
        return 2

class baseState:
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def __repr__(self):
        return f"{type(self).__name__}"

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
        self.initiated = agent.time
        self.jumpTimer = agent.time
        self.firstJump = False
        self.secondJump = False
        self.firstJumpHold = 0.5
        self.secondJumpHold = 0.4
        self.active = True


    def update(self):
        stateController = SimpleControllerState()

        if not self.firstJump:
            self.firstJump = True
            stateController.jump = True
            self.jumpTimer = self.agent.time

        elif self.firstJump and not self.secondJump:
            if self.agent.time - self.jumpTimer < self.firstJumpHold:
                stateController.jump = True

            elif self.agent.time - self.jumpTimer > self.firstJumpHold and self.agent.time - self.jumpTimer < self.firstJumpHold +.05:
                stateController.boost = True
                stateController.jump = False

            else:
                self.secondJump = True
                stateController.boost = True
                self.jumpTimer = self.agent.time

        else:
            if self.agent.time - self.jumpTimer < self.secondJumpHold:
                stateController.jump = True
                stateController.boost = True

            else:
                self.active = False
                self.jump = False
                self.agent.activeState = DivineGrace(self.agent)

        if self.agent.time - self.jumpTimer > 0.15 and self.agent.time - self.jumpTimer < 0.35:
            stateController.pitch = 1
        return stateController




class Aerial():
    def __init__(self,agent,target,time):
        self.active = False
        self.agent = agent
        self.target = target
        self.time = clamp(10,0.00001,time)
        self.jumping = False
        self.jumpTimer = 0
        self.airborne = False
        self.launcher = None
        self.setup()

    def setup(self):
        dv_target = backsolve(self.target, self.agent, self.time)
        if self.agent.deltaV >= dv_target.magnitude():
            self.dv_target = dv_target
            self.active = True
            self.launcher = airLaunch(self.agent)




    def update(self):
        # takes the agent, an intercept point, and an intercept time.Adjusts the agent's controller
        # (agent.c) to perform an aerial
        self.time = self.time = clamp(10,0.00001,self.time - self.agent.deltaTime)
        before = self.jumping
        dv_target = backsolve(self.target, self.agent, self.time)
        dv_total = dv_target.magnitude()
        dv_local = matrixDot(self.agent.me.matrix, dv_target)
        # dv_local = agent.me.matrix.dot(dv_target)
        angles,self.controller = defaultPD(self.agent, dv_local)

        print(self.controller.yaw,self.controller.pitch,self.controller.roll)

        precision = clamp(0.6, 0.05, dv_total / 1500)
        # precision = cap((dv_total/1500),0.05, 0.60)

        # if dv_local[2] > 100 or not self.airborne and self.agent.onSurface: #agent.me.airborne == False:
        #     #if agent.sinceJump < 0.3:
        #     if self.jumpTimer < 0.3:
        #         self.jumping = True
        #         if before != True:
        #             self.controller.pitch = self.controller.yaw = self.controller.roll = 0
        #
        #     elif self.jumpTimer >= 0.32:
        #         self.jumping = True
        #         self.airborne = True
        #         if before != True:
        #             self.controller.pitch = self.controller.yaw = self.controller.roll = 0
        #         #agent.c.pitch = agent.c.yaw = agent.c.roll = 0
        #     else:
        #         self.jumping = False
        #         #agent.c.jump = False
        # else:
        #     self.jumping = False
        #     #agent.c.jump = False

        if self.launcher.active:
            return self.launcher.update()
        else:

            if dv_total > 50:
                if abs(angles[1]) + abs(angles[2]) < precision:
                    self.controller.boost = True
                    #agent.c.boost = True
                else:
                    self.controller.boost = False
                    #print(dv_total)
                    #agent.c.boost = False
            else:
                fly_target = self.agent.me.matrix.dot(self.target - self.agent.me.location)
                angles = defaultPD(self.agent, fly_target)
                self.controller.boost = False

            #self.controller.jump = self.jumping

            if self.time <= 0.0001:
                self.active = False
                print("timed out?")
            return self.controller

class Celestial_Arrest(baseState):
    def __init__(self,agent):
        self.active = True
        self.agent = agent

    def update(self):
        pass


class LeapOfFaith(baseState):
    def __init__(self,agent, targetCode,target = None):
        self.agent = agent
        self.active = True
        self.targetCode = targetCode #0 flip at ball , 1 flip forward, 2 double jump, 3 flip backwards, 4 flip left, 5 flip right, 6 flip at target ,7 left forward diagnal flip, 8 right forward diagnal flip
        self.flip_obj = FlipStatus(agent.time)
        self.target = target
        self.cancelTimerCap = .3
        self.cancelStartTime = None
        self.jumped = False

    def update(self):
        controller_state = SimpleControllerState()
        jump = flipHandler(self.agent, self.flip_obj)
        if jump:
            if self.targetCode == 1:
                controller_state.pitch = -1
                controller_state.steer = 0
                controller_state.throttle = 1

            elif self.targetCode == 0:
                ball_local = toLocal(self.agent.ball.location, self.agent.me)
                ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
                controller_state.jump = True
                controller_state.yaw = math.sin(ball_angle)
                pitch = -math.cos(ball_angle)
                controller_state.pitch = pitch
                if pitch > 0:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1


            elif self.targetCode == 2:
                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.yaw = 0
            elif self.targetCode == 3:
                controller_state.pitch = 1
                controller_state.steer = 0
                controller_state.throttle = -1

            elif self.targetCode == -1:
                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.throttle = 0

            elif self.targetCode == 4:
                controller_state.pitch = 0
                controller_state.yaw = -1
                controller_state.steer = -1
                controller_state.throttle = -0

            elif self.targetCode == 5:
                controller_state.pitch = 0
                controller_state.yaw = 1
                controller_state.steer = 1
                controller_state.throttle = -0

            elif self.targetCode == 6:
                target_local = toLocal(self.target, self.agent.me)
                target_angle = math.atan2(target_local.data[1], target_local.data[0])
                controller_state.jump = True
                controller_state.yaw = math.sin(target_angle)
                pitch = -math.cos(target_angle)
                controller_state.pitch = pitch
                if pitch > 0:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1

            elif self.targetCode == 7:
                controller_state.pitch = -1
                controller_state.yaw = -1
                controller_state.steer = -1
                controller_state.throttle = 1

            elif self.targetCode == 8:
                controller_state.pitch = -1
                controller_state.yaw = 1
                controller_state.steer = 1
                controller_state.throttle = 1

            elif self.targetCode == 9:
                #diagnal flip cancel
                controller_state.pitch = -1
                controller_state.roll = -1
                #controller_state.steer = -1
                controller_state.throttle = 1

            elif self.targetCode == 10:
                #diagnal flip cancel
                controller_state.pitch = -1
                controller_state.roll = 1
                #controller_state.steer = -1
                controller_state.throttle = 1


            elif self.targetCode == -1:

                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.throttle = 0

        controller_state.jump = jump
        controller_state.boost = False
        if self.targetCode == 7 or self.targetCode == 8:
            controller_state.boost = True
        if self.flip_obj.flipDone:
            if self.targetCode != 9 or self.targetCode != 10:
                self.active = False
            else:
                if not self.cancelStartTime:
                    self.cancelStartTime = self.agent.time
                    return controller_state
                if self.targetCode == 9:
                    controller_state.pitch = 1
                    controller_state.roll = 1
                    controller_state.throttle = 1
                else:
                    controller_state.pitch = 1
                    controller_state.roll = -1
                    controller_state.throttle = 1
                if self.agent.time - self.cancelStartTime >= self.cancelTimerCap:
                    self.active = False

        # if self.agent.forward:
        #     controller_state.throttle = 1
        # else:
        #     controller_state.throttle = -1

        return controller_state

class RighteousVolley(baseState):
    def __init__(self,agent,delay,target):
        baseState.__init__(self,agent)
        self.smartAngle = False
        self.target = target
        height = target[2]
        # if agent.team == 0:
        #     delay = clamp(1.25,.3,delay+0.05)
        # else:
        delay = clamp(1.25, .3, delay+0.05)
        if delay >= .3:
            if height <= 200:
                #print("tiny powershot")
                self.jumpTimerMax = .1
                self.angleTimer = clamp(.15,.05,self.jumpTimerMax/2)
            else:
                #print("normal powershot")
                self.jumpTimerMax = delay-.2
                self.angleTimer = clamp(.15, .1, self.jumpTimerMax / 2)
        self.delay = delay
        if self.delay >= .5:
            self.smartAngle = True
        self.jumped = False
        self.jumpTimer = 0
        #print("setting action to powershot")

    def update(self):
        controller_state = SimpleControllerState()
        controller_state.throttle = 0
        controller_state.boost = False
        ball_local = toLocal(self.agent.ball.location, self.agent.me)
        #ball_local = toLocal(self.target, self.agent.me)
        ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
        angle_degrees = correctAngle(math.degrees(ball_angle))
        if not self.jumped:
            self.jumped = True
            controller_state.jump = True
            return controller_state
        else:
            self.jumpTimer += self.agent.deltaTime


            if self.jumpTimer < self.angleTimer:
                controller_state.pitch = 1

            if self.jumpTimer < self.jumpTimerMax:
                controller_state.jump = True

            else:
                controller_state.jump = False


                if self.jumpTimer > self.jumpTimerMax:
                    if self.jumpTimer >= self.delay-.2 and self.jumpTimer < self.delay-.15:
                        controller_state.jump = False
                    elif self.jumpTimer >= self.delay-.15 and self.jumpTimer < self.delay:
                        controller_state.yaw = math.sin(ball_angle)
                        controller_state.throttle = 1
                        if abs(angle_degrees) > 90:
                            controller_state.pitch = 1
                        else:
                            controller_state.pitch = -1
                        controller_state.jump = True
                    elif self.jumpTimer < self.delay+.1:
                        controller_state.jump = False
                    else:
                        self.active = False
                        controller_state.jump = False
            return controller_state



class DivineRetribution():
    def __init__(self,agent,targetCar):
        self.agent = agent
        self.targetCar = targetCar
        self.active = True
    def update(self,):
        action = demoTarget(self.agent,self.targetCar)
        return action

class DemolitionBot():
    def __init__(self,agent):
        self.agent = agent
        self.active = True

    def update(self):
        target = self.agent.closestEnemyToBall
        valid = False
        if target.location[2] <= 90:
            if ((target.location[1] > self.agent.ball.location[1] and target.location[1] < self.agent.me.location[1]) or
                (target.location[1] < self.agent.ball.location[1] and target.location[1] > self.agent.me.location[1])):
                valid = True

        if valid:
            return demoEnemyCar(self.agent,target)

        else:
            self.active = False
            return ShellTime(self.agent)




class GroundShot(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return lineupShot(self.agent,3)

class GroundAssault(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return lineupShot(self.agent,1)

class HolyGrenade(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return handleBounceShot(self.agent)

class HolyProtector(baseState):
    def update(self):
        return ShellTime(self.agent)


class AerialDefend(baseState):
    pass


class TurnTowardsPosition(baseState):
    def __init__(self,agent,target,targetCode): #0 = ball.location
        baseState.__init__(self,agent)
        self.target = target
        self.threshold = 1
        self.targetCode = targetCode

    def update(self):
        if self.targetCode == 0:
            self.target = self.agent.ball.location
        localTarg = toLocal(self.target,self.agent.me)
        localAngle = correctAngle(math.degrees(math.atan2(localTarg[1],localTarg[0])))
        controls = SimpleControllerState()

        if abs(localAngle) > self.threshold:
            if self.agent.forward:
                if localAngle > 0:
                    controls.steer = 1
                else:
                    controls.steer = -1

                controls.handbrake = True
                if self.agent.currentSpd <300:
                    controls.throttle = .5
            else:
                if localAngle > 0:
                    controls.steer = -.5
                else:
                    controls.steer = 1
                controls.handbrake = True
                if self.agent.currentSpd <300:
                    controls.throttle = -.5
        else:
            self.active = False
        return controls

class Obstruct(baseState):
    def update(self):
        if not kickOffTest(self.agent):
            return turtleTime(self.agent)

        else:
            self.active = False
            self.agent.activeState = PreemptiveStrike(self.agent)
            return self.agent.activeState.update()
"""        
def getKickoffPosition(vec):
    kickoff_locations = [[2048, 2560], [256, 3848], [0, 4608]]
    for i in range(len(kickoff_locations)):
        if kickoff_locations[i] == [abs(vec[0]),abs(vec[1])]:
            return i
    return -1
"""
class Kickoff(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.started = False
        self.firstFlip = False
        self.secondFlip = False
        self.finalFlipDistance = 750
        self.active = True
        self.startTime = agent.time
        self.flipState = None

    def fakeKickOffChecker(self):
        closestToBall, bDist = findEnemyClosestToLocation(self.agent, self.agent.ball.location)
        myDist = findDistance(self.agent.me.location,self.agent.ball.location)

        if bDist:
            if bDist <= myDist*.75:
                return True
            else:
                return False
        return False

    def retire(self):
        self.active = False
        self.agent.activeState = None
        self.flipState = None

    def update(self):
        spd = self.agent.currentSpd
        if self.flipState != None:
            if self.flipState.active:
                controller = self.flipState.update()
                if self.agent.time - self.flipState.flip_obj.flipStartedTimer <= 0.15:
                    if spd < 2200:
                        controller.boost = True
                return controller
            if self.secondFlip:
                self.retire()

        jumping = False
        ballDistance = distance2D(self.agent.me.location, self.agent.ball.location)

        if not self.started:
            if not kickOffTest(self.agent):
                self.started = True
                self.startTime = self.agent.time

        if self.started and self.agent.time - self.startTime > 2.5:
            self.retire()

        if not self.firstFlip:
            if spd > 1100:
                self.flipState = LeapOfFaith(self.agent,0,target = self.agent.ball.location)
                self.firstFlip = True
                return self.flipState.update()

        if ballDistance > self.finalFlipDistance:
            destination = self.agent.ball.location
            if not self.firstFlip:
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    destination.data[0] -= 200
                else:
                    destination.data[0] += 200
            else:
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    destination.data[0] -= 5
                else:
                    destination.data[0] += 5
            return greedyMover(self.agent, destination)

        else:
            self.flipState = LeapOfFaith(self.agent,0,self.agent.ball.location)
            self.secondFlip = True
            return self.flipState.update()

class PreemptiveStrike(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.started = False
        self.firstFlip = False
        self.secondFlip = False
        self.finalFlipDistance = 850
        #self.finalFlipDistance = 1400
        self.active = True
        self.startTime = agent.time
        self.flipState = None
        self.kickoff_type = getKickoffPosition(agent.me.location)
        self.method = 0
        self.setup()
        agent.stubbornessTimer = 5
        agent.stubborness= agent.stubbornessMax

    def setup(self):
        if abs(self.agent.me.location[0]) < 257:
            self.method = 1
            self.replacement = Kickoff(self.agent)


    def rightSelf(self):
        controller_state = SimpleControllerState()

        if self.agent.me.rotation[2] > 0:
            controller_state.roll = -1

        elif self.agent.me.rotation[2] < 0:
            controller_state.roll = 1

        if self.agent.me.rotation[0] > self.agent.velAngle:
            controller_state.yaw = -1

        elif self.agent.me.rotation[0] < self.agent.velAngle:
            controller_state.yaw = 1

        if self.agent.me.rotation[0] > 0:
            controller_state.pitch = -1

        elif self.agent.me.rotation[0] < 0:
            controller_state.pitch = 1

        controller_state.throttle = 1

        return controller_state

    def fakeKickOffChecker(self):
        closestToBall, bDist = findEnemyClosestToLocation(self.agent, self.agent.ball.location)
        myDist = findDistance(self.agent.me.location,self.agent.ball.location)

        if bDist:
            if bDist <= myDist*.75:
                return True
            else:
                return False
        return False

    def retire(self):
        self.active = False
        self.agent.activeState = None
        self.flipState = None

    def update(self):
        if self.method == 1:
            action = self.replacement.update()
            if not self.replacement.active:
                self.retire()
            return action


        else:
            spd = self.agent.currentSpd

            if self.flipState != None:
                if self.flipState.active:
                    controller = self.flipState.update()
                    controller.boost = True
                    return controller
                if self.secondFlip:
                    self.retire()

            jumping = False
            ballDistance = distance2D(self.agent.me.location, self.agent.ball.location)
            if ballDistance < 200:
                self.retire()

            if not self.started:
                if not kickOffTest(self.agent):
                    self.started = True
                    self.startTime = self.agent.time

            if self.started and self.agent.time - self.startTime > 2.5:
                self.retire()

            if not self.firstFlip:
                if spd > 1050:
                    localBall = self.agent.ball.local_location
                    angle = correctAngle(math.degrees(math.atan2(localBall[1],localBall[0])))
                    #if self.agent.team == 0:
                    if angle < 0:
                        self.flipState = LeapOfFaith(self.agent, 9)
                    else:
                        self.flipState = LeapOfFaith(self.agent, 10)
                    # else:
                    #     if angle > 0:
                    #         self.flipState = LeapOfFaith(self.agent, 9)
                    #     else:
                    #         self.flipState = LeapOfFaith(self.agent, 10)
                    self.firstFlip = True
                    controller = self.flipState.update()
                    controller.boost = True
                    return controller

            destination = self.agent.ball.location
            if ballDistance > self.finalFlipDistance:

                #destination.data[1] += -sign(self.agent.team)*100
                if not self.firstFlip:
                    #print(self.kickoff_type)
                    if self.agent.team == 1:
                        if self.kickoff_type == 0:
                            if destination[0] > self.agent.me.location[0]:
                                #print("greater than 0")
                                destination.data[0] += 1100#1000
                            else:
                                destination.data[0] -= 1100#1000
                                #print("less than 0")
                        elif self.kickoff_type == 1:
                            if destination[0] > self.agent.me.location[0]:
                                #print("greater than 0")
                                destination.data[0] += 900
                            else:
                                destination.data[0] -= 900
                                #print("less than 0")
                        elif self.kickoff_type == 2:
                            destination.data[0] -= 750

                        else:

                            if destination[0] > self.agent.me.location[0] or self.kickoff_type == -1:
                                destination.data[0] += 1100
                            else:
                                destination.data[0] -= 1100
                    else:
                        if self.kickoff_type == 0:
                            if destination[0] > self.agent.me.location[0]:
                                #print("greater than 0")
                                destination.data[0] += 1100#1000
                            else:
                                destination.data[0] -= 1100#1000
                                #print("less than 0")
                        elif self.kickoff_type == 1:
                            if destination[0] > self.agent.me.location[0]:
                                #print("greater than 0")
                                destination.data[0] += 900
                            else:
                                destination.data[0] -= 900
                                #print("less than 0")
                        elif self.kickoff_type == 2:
                            destination.data[0] += 750

                        else:

                            if destination[0] > self.agent.me.location[0] or self.kickoff_type == -1:
                                destination.data[0] -= 1100
                            else:
                                destination.data[0] += 1100
                else:
                    if destination[0] > self.agent.me.location[0]:
                        destination.data[0] -=25
                    else:
                        destination.data[0] += 25

                controls = greedyMover(self.agent, destination)
                if self.firstFlip and not self.secondFlip:
                    if self.flipState:
                        if not self.flipState.active:
                            if not self.agent.onSurface:
                                controls = self.rightSelf()

                if spd < 2195:
                    controls.boost = True
                else:
                    controls.boost = False
                return controls

            else:
                if self.agent.onSurface:
                    self.flipState = LeapOfFaith(self.agent, 0)
                    self.secondFlip = True
                    return self.flipState.update()
                else:
                    controls = self.rightSelf()
                    if spd < 2200:
                        controls.boost = True
                    if ballDistance < 150:
                        self.retire()
                    return controls

class DivineGrace(baseState):
    def update(self):
        if self.agent.onSurface or self.agent.me.location[2] < 60:
            self.active = False
        controller_state = SimpleControllerState()

        if self.agent.me.rotation[2] > 0:
            #controller_state.roll = clamp(1,-1,-1-self.agent.me.avelocity[2])
            controller_state.roll = -1

        elif self.agent.me.rotation[2] < 0:
            #controller_state.roll = clamp(1,-1,1-self.agent.me.avelocity[2])
            controller_state.roll = 1

        if self.agent.me.rotation[0] > self.agent.velAngle:
            #controller_state.yaw = controller_state.roll = clamp(1,-1,-1-self.agent.me.avelocity[0])
            controller_state.yaw = -1

        elif self.agent.me.rotation[0] < self.agent.velAngle:
            #controller_state.yaw = controller_state.roll = clamp(1,-1,1-self.agent.me.avelocity[0])
            controller_state.yaw = 1

        controller_state.throttle = 1

        return controller_state

class WardAgainstEvil(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.active = True
        self.timeCreated = self.agent.time
    def update(self):
        #print(f"We're too scared! {self.agent.time}")
        return scaredyCat(self.agent)

class BlessingOfDexterity(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.active = True
        self.firstJump= False
        self.secondJump = False
        self.jumpStart = 0
        self.timeCreated = self.agent.time


    def update(self):
        controller_state = SimpleControllerState()
        controller_state.throttle = -1
        if not self.firstJump:
            controller_state.jump = True
            controller_state.pitch = 1
            self.firstJump = True
            self.jumpStart = self.agent.time
            return controller_state

        elif self.firstJump and not self.secondJump:
            jumpTimer = self.agent.time - self.jumpStart
            controller_state.pitch = 1
            controller_state.jump = False
            if jumpTimer < 0.12:
                controller_state.jump = True
            if jumpTimer > 0.15:
                controller_state.jump = True
                self.jumpStart = self.agent.time
                self.secondJump = True
            return controller_state

        elif self.firstJump and self.secondJump:
            timer = self.agent.time - self.jumpStart
            if timer < 0.15:
                controller_state.pitch = 1

            else:
                controller_state.pitch = -1
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
            self.agent.activeState = PreemptiveStrike(self.agent)
            return self.agent.activeState.update()

class BlessingOfSafety(baseState):
    def update(self):
        distMin = 2000
        # if len(self.agent.allies) ==1:
        #     distMin = 1500
        # elif len(self.agent.allies) > 1:
        #     distMin = 1200

        if distance2D(Vector([0, 5200 * sign(self.agent.team), 200]),
                      self.agent.currentHit.pred_vector) < distMin:
            return ShellTime(self.agent)
        else:
            if self.agent.rotationNumber == 2:
                if len(self.agent.allies) >=2:
                    return playBack(self.agent,buffer = 2500)
                else:
                    return playBack(self.agent)
            if self.agent.rotationNumber >=3:
                return playBack(self.agent,buffer = 6500)

            #print("returning default value")
            return playBack(self.agent)


class DivineAssistance(baseState):
    def update(self):
        return secondManSupport(self.agent)




def halfFlipStateManager(agent):
    if agent.activeState.active == False:
        agent.activeState = BlessingOfDexterity(agent)

    else:
        if type(agent.activeState) != BlessingOfDexterity:
            agent.activeState = BlessingOfDexterity(agent)

class soloDefense(baseState):
    def update(self):
        if distance2D(Vector([0, 5200 * sign(self.agent.team), 200]),convertStructLocationToVector(self.agent.selectedBallPred))<1500:
            return ShellTime(self.agent)
        else:
            return playBack(self.agent)

class ScaleTheWalls(baseState):
    def update(self):
        return handleWallShot(self.agent)

class AngelicEmbrace(baseState):
    def update(self):
        return carry_flick(self.agent,cradled = True)
        #return newCarry(self.agent)


class emergencyDefend(baseState):
    def update(self):
        penetrationPosition = convertStructLocationToVector(self.agent.goalPred)
        penetrationPosition.data[1] = 5350 * sign(self.agent.team)
        if self.agent.goalPred.game_seconds - self.agent.gameInfo.seconds_elapsed > .1:
            if distance2D(self.agent.me.location,penetrationPosition) > 100:
                return testMover(self.agent,penetrationPosition,2300)
        else:
            if penetrationPosition[2] > 300:
                self.activeState = LeapOfFaith(self.agent, -1)
                return self.activeState.update()

            else:
                self.activeState = LeapOfFaith(self.agent, 0)
                return self.activeState.update()

def parseCarInfo(carList, index, _max = False):
    val = 0
    best = None
    for each in carList:
        if _max:
            if each[index] > val:
                best = each
                val = each[index]
        else:
            if each[index] < val:
                best = each
                val = each[index]

    return best

def teamStateManager(agent):
    if len(agent.allies) < 1:
        soloStateManager(agent)
        return

    agentType = type(agent.activeState)
    groundHeighCutOff = 120

    if agentType != PreemptiveStrike:
        if not kickOffTest(agent):
            myGoalLoc = center = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = center = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)
            carDistanceFromEnemyGoal = distance2D(enemyGoalLoc, agent.me)

            if ballDistanceFromGoal <= 2000:
                agent.contested = True

            timeTillBallReady = 6

            if agent.contested:
                ballStruct = agent.selectedBallPred
                timeTillBallReady = agent.ballDelay
            else:
                if is_in_strike_zone(agent, convertStructLocationToVector(agent.selectedBallPred)):
                    agent.contested = True
                    ballStruct = agent.selectedBallPred
                    timeTillBallReady = agent.ballDelay
                else:
                    agent.selectedBallPred = findSuitableBallPosition(agent, 110, agent.getCurrentSpd(), agent.me.location)

            ballStruct = agent.selectedBallPred
            goalward = ballHeadedTowardsMyGoal(agent)
            agent.openGoal = openGoalOpportunity(agent)

            aerialStructs = findAerialTargets(agent)




            createBox(agent, hit.pred_vector)
            # print(groundHeighCutOff,structHeight)


            if agentType == LeapOfFaith:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == BlessingOfDexterity:
                if agent.activeState.active != False:
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if agentType == RighteousVolley:
                if agent.activeState.active != False:
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if agentType == Aerial:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 165:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            # carDistancesFromGoal = []
            # cardistancesFromBall = []
            # carInfo = []
            # for c in agent.allies:
            #     cdfg = distance2D(myGoalLoc, c.location)
            #     cdfb = distance2D(agent.ball.location, c.location)
            #     carDistancesFromGoal.append(cdfg)
            #     cardistancesFromBall.append(cdfb)
            #     carInfo.append([cdfg, cdfb, c])

            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)
            carDistanceFromBall = distance2D(agent.me.location, agent.ball.location)

            predLocation = convertStructLocationToVector(agent.selectedBallPred)


            if len(agent.allies) == 1: #print 2vX
                if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] *sign(agent.team): #bp = -3000  ball = -4000/ 3000,4000 // op = 3000 ball = 4000 /3000,4000
                    #beyond the ball - demo and retreat if there's a last man, otherwise evac asap
                    if agent.allies[0].location[1] * sign(agent.team) < agent.ball.location[1] *sign(agent.team):
                        #get back asap!
                        if agentType != BlessingOfSafety:
                            agent.activeState = BlessingOfSafety(agent)
                        return
                    else:
                        #there's a back man, cause some havic
                        #print("it's clobbering time!")
                        if agentType != DemolitionBot:
                            agent.activeState = DemolitionBot(agent)
                        return

                else:
                    #bot not over extended, check to see if teammate is
                    if agent.allies[0].location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team):
                        #both bots are in defensive positions
                        if distance2D(agent.me.location,agent.ball.location) <= distance2D(agent.allies[0].location,agent.ball.location):
                            #print("this bot is closest to ball, go on offensive")
                            if goalward:
                                if agentType != HolyProtector:
                                    agent.activeState = HolyProtector(agent)
                                return

                            if structHeight <= groundHeighCutOff:
                                if agentType != GroundAssault:
                                    agent.activeState = GroundAssault(agent)
                                return
                            else:
                                if agentType != HolyGrenade:
                                    agent.activeState = HolyGrenade(agent)
                                return
                        else:
                            if agentType != BlessingOfSafety:
                                agent.activeState = BlessingOfSafety(agent)
                            return
                    else:
                        #teammate is closer, play the back man
                        if agentType != BlessingOfSafety:
                            agent.activeState = BlessingOfSafety(agent)
                        return




            else: #3vX+
                print("why am I in 3v3?")
                if goalward:
                    if agent.activeState != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                else:
                    if predLocation[2] > groundHeighCutOff:
                        if agentType != HolyGrenade:
                            agent.activeState = HolyGrenade(agent)
                        return
                    else:
                        if agentType != GroundAssault:
                            agent.activeState = GroundAssault(agent)
                        return

            #     pass
            #
            # if carDistanceFromGoal > ballDistanceFromGoal + 100:
            #     if agentType != GroundDefend:
            #         agent.activeState = GroundDefend(agent)
            #     return
            #
            # elif goalward:
            #     if agentType != GroundDefend:
            #         agent.activeState = GroundDefend(agent)
            #     return
            #
            #
            # else:
            #
            #     if structHeight <= groundHeighCutOff:
            #         if agentType != Dribble:
            #             agent.activeState = Dribble(agent)
            #         return
            #     else:
            #         if agentType != bounceShot:
            #             agent.activeState = bounceShot(agent)
            #         return

        else:
            if agent.activeState != PreemptiveStrike:
                agent.activeState = PreemptiveStrike(agent)
            return


def launchStateManager(agent):
    if agent.activeState:
        if agent.activeState.active:
            return
        else:
            if type(agent.activeState) == airLaunch:
                agent.activeState = DivineGrace(agent)

            else:
                if agent.onSurface:
                    if agent.getCurrentSpd() < 50:
                        agent.activeState = airLaunch(agent)

    else:
        agent.activeState = airLaunch(agent)


def facePositionManager(agent):
    agentType = type(agent.activeState)
    if agentType != TurnTowardsPosition or not agent.activeState.active:
        agent.activeState = TurnTowardsPosition(agent,agent.ball.location,0)

def demoTest(agent):
    targ = findEnemyClosestToLocation(agent,agent.ball.location)[0]
    return demoEnemyCar(agent,targ)


def newTeamStateManager(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            if agentType == LeapOfFaith:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == BlessingOfDexterity:
                if agent.activeState.active != False:
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if agentType == RighteousVolley:
                if agent.activeState.active != False:
                    return
            fastesthit = find_soonest_hit(agent)
            hit = fastesthit
            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if tempDelay >= agent.enemyBallInterceptDelay - .25:
                if agent.enemyAttacking:
                    agent.contested = True


            if tempDelay >= agent.enemyBallInterceptDelay + 1:
                if not butterZone(hit.pred_vector):
                    if ballDistanceFromGoal <= 5000:
                        agent.timid = True
                    else:
                        scared = True
                    #print(tempDelay,agent.enemyBallInterceptDelay)
                    #pass

            if distance2D(hit.pred_vector,myGoalLoc) <= 2000 or distance2D(agent.enemyTargetVec,myGoalLoc) <= 2000:
                agent.contested = True
                agent.timid = False
                scared = False



            if not agent.contested:
                if agent.hits[0] != None:
                    if hit.hit_type != 2:
                        temptime = agent.hits[0].prediction_time - agent.time
                        # if temptime >=1:

                        if temptime < agent.enemyBallInterceptDelay - .25:
                            if not ballHeadedTowardsMyGoal_testing(agent, agent.hits[0]):
                                hit = agent.hits[0]

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed
            agent.ballGrounded = False

            #print(agent.ballDelay, agent.enemyBallInterceptDelay,agent.contested,agent.timid)

            if hit.hit_type == 2:
                agent.wallShot = True
                agent.ballGrounded = False
            else:
                agent.wallShot = False
                if hit.hit_type == 1:
                    if hit.pred_vector[2] <=agent.groundCutOff:
                        agent.ballGrounded = True
                    else:
                        agent.ballGrounded = False



            createBox(agent, hit.pred_vector)

            if agentType == Aerial:
                if agent.activeState.active != False:
                    return



            if not agent.onSurface:
                if agent.me.location[2] > 170:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return


            if agent.dribbling:
                if not goalward:
                    if agentType != AngelicEmbrace:
                        agent.activeState = AngelicEmbrace(agent)
                    return

            #determine which man in rotation I am #1, #2, #3, forward
            man = 1
            if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] *sign(agent.team):
                if agent.me.location[1] * sign(agent.team) < agent.currentHit.pred_vector[1] * sign(agent.team):
                    man = 4
            else:

                myDist = distance2D(agent.me.location, agent.ball.location)
                for ally in agent.allies:
                    if not ally.demolished:
                        if ally.location[1] * sign(agent.team) > agent.ball.location[1] *sign(agent.team):
                            if distance2D(ally.location, agent.ball.location) < myDist:
                                man += 1
                man = clamp(3, 0, man)

            agent.rotationNumber = man

            if man == 1:
                hit = fastesthit
                agent.currentHit = hit
                agent.ballDelay = hit.prediction_time - agent.time

                #print(f"{hit.hit_type} in {agent.ballDelay} seconds")

                
                if agent.me.boostLevel <=0:
                    if len(agent.allies) >1:
                        if distance2D(agent.me.location,hit.pred_vector) > 7000:
                            if not is_in_strike_zone(agent,hit.pred_vector):
                                if agentType != BlessingOfSafety:
                                    agent.activeState = BlessingOfSafety(agent)
                                return

                if carDistanceFromGoal > ballDistanceFromGoal:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                if goalward:
                    if hit.hit_type != 2:
                        if agentType != HolyProtector:
                            agent.activeState = HolyProtector(agent)
                        return
                    else:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return


                else:
                    if hit.hit_type == 0:  # hit.pred_vector[2] <= agent.groundCutOff:
                        if agentType != GroundAssault:
                            agent.activeState = GroundAssault(agent)
                        return

                    elif hit.hit_type == 1:
                        if agentType != HolyGrenade:
                            agent.activeState = HolyGrenade(agent)
                        return

                    else:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return



            elif man == 2:
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

            elif man == 3:
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

            elif man == 4:
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

        else:
            agent.activeState = PreemptiveStrike(agent)



def soloStateManager(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            #agent.resetTimer += agent.deltaTime

            if agentType == LeapOfFaith:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == BlessingOfDexterity:
                if agent.activeState.active != False:
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if agentType == RighteousVolley:
                if agent.activeState.active != False:
                    return

            hit = find_soonest_hit(agent)
            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.time
            #print(tempDelay)

            if tempDelay >= agent.enemyBallInterceptDelay - .5:
                if agent.enemyAttacking:
                    agent.contested = True


            if tempDelay >= agent.enemyBallInterceptDelay + 1:
                if not butterZone(hit.pred_vector):
                    if ballDistanceFromGoal <= 5000:
                        agent.timid = True
                    else:
                        scared = True
                    #print(tempDelay,agent.enemyBallInterceptDelay)
                    #pass

            if distance2D(hit.pred_vector,myGoalLoc) <= 2000 or distance2D(agent.enemyTargetVec,myGoalLoc) <= 2000:
                agent.contested = True
                agent.timid = False
                scared = False





            if not agent.contested:
                if agent.hits[0] != None:
                    temptime = agent.hits[0].prediction_time - agent.gameInfo.seconds_elapsed
                    #if temptime >=1:
                    if hit.hit_type != 2:
                        if temptime < agent.enemyBallInterceptDelay - .5:
                            hit = agent.hits[0]

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.time
            agent.ballGrounded = False

            #print(agent.ballDelay, agent.enemyBallInterceptDelay,agent.contested,agent.timid)

            if hit.hit_type == 2:
                agent.wallShot = True
                agent.ballGrounded = False
            else:
                agent.wallShot = False
                if hit.hit_type == 1:
                    if hit.pred_vector[2] <=agent.groundCutOff:
                        agent.ballGrounded = True
                    else:
                        agent.ballGrounded = False



            createBox(agent, hit.pred_vector)

            if agentType == Aerial:
                if agent.activeState.active != False:
                    return



            if not agent.onSurface:
                if agent.me.location[2] > 170:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return


            if agent.dribbling:
                if not goalward:
                    if agentType != AngelicEmbrace:
                        agent.activeState = AngelicEmbrace(agent)
                    return
            #else:
                # agent.resetTimer += agent.deltaTime
                # if agent.resetTimer >= 5:
                #     agent.resetTimer = 0
                #     print("setting up dribble training")
                #     #game_state = GameState()
                #     #self.set_game_state(game_state)
                #     ball_state = BallState(Physics(location=Vector3(agent.me.location[0], agent.me.location[1], agent.me.location[2]+160),velocity=Vector3(agent.me.velocity[0],agent.me.velocity[1],agent.me.velocity[2])))
                #     game_state = GameState(ball=ball_state)
                #     agent.set_game_state(game_state)
                #     if agentType != AngelicEmbrace:
                #         agent.activeState = AngelicEmbrace(agent)
                #     return


            # if agent.timid or scared:
            #     #print(f"being timid {agent.time}")
            #     if agentType != WardAgainstEvil:
            #         agent.activeState = WardAgainstEvil(agent)
            #     return

            # if scared or agent.timid:
            #     if agentType != BlessingOfSafety:
            #         agent.activeState = BlessingOfSafety(agent)
            #     return


            if carDistanceFromGoal > ballDistanceFromGoal:
                if agentType != HolyProtector:
                    agent.activeState = HolyProtector(agent)
                return

            elif goalward:
                if hit.hit_type !=2:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return
                else:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                        #print("scaling walls")
                    #print(f"scale the walls defensive {agent.time}")
                    return


            else:

                if hit.hit_type == 0:
                    if agentType != GroundAssault:
                        agent.activeState = GroundAssault(agent)
                    return

                elif hit.hit_type == 1:
                    if agentType != HolyGrenade:
                        agent.activeState = HolyGrenade(agent)
                    return

                elif hit.hit_type == 2:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                    return

                else:
                    print("we got an eroneous hit_type somehow")
            print("rawr")

        else:
            agent.activeState = PreemptiveStrike(agent)

def soloStateManager_testing(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            #agent.resetTimer += agent.deltaTime

            if agentType == LeapOfFaith:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == BlessingOfDexterity:
                if agent.activeState.active != False:
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if agentType == RighteousVolley:
                if agent.activeState.active != False:
                    return

            hit = find_soonest_hit(agent)


            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed
            #print(tempDelay)

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                if agent.enemyAttacking:
                    agent.contested = True


            # if tempDelay >= agent.enemyBallInterceptDelay + .5:
            #     if not butterZone(hit.pred_vector):
            #         if ballDistanceFromGoal <= 5000:
            #             agent.timid = True
            #         else:
            #             scared = True

            if distance2D(hit.pred_vector,myGoalLoc) <= 2000 or distance2D(agent.enemyTargetVec,myGoalLoc) <= 2000:
                agent.contested = True
                agent.timid = False
                scared = False

            # if not agent.contested:
            #     if agent.hits[0] != None:
            #         if hit.hit_type != 2:
            #             temptime = agent.hits[0].prediction_time - agent.time
            #             # if temptime >=1:
            #
            #             if temptime < agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
            #                 if not ballHeadedTowardsMyGoal_testing(agent, agent.hits[0]):
            #                     hit = agent.hits[0]

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.time
            agent.ballGrounded = False


            if hit.hit_type == 2:
                agent.wallShot = True
            else:
                agent.wallShot = False



            createBox(agent, hit.pred_vector)

            if agentType == Aerial:
                if agent.activeState.active != False:
                    return



            if not agent.onSurface:
                if agent.me.location[2] > 170:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return


            if agent.dribbling:
                #if not goalward:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            if scared or agent.timid:
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

            if carDistanceFromGoal > ballDistanceFromGoal:
                if agentType != HolyProtector:
                    agent.activeState = HolyProtector(agent)
                return

            if goalward:
                if hit.hit_type !=2:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return
                else:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                    return


            else:
                if hit.hit_type == 0:  #hit.pred_vector[2] <= agent.groundCutOff:
                    if agentType != GroundAssault:
                        agent.activeState = GroundAssault(agent)
                    return

                elif hit.hit_type == 1:
                    if agentType != HolyGrenade:
                        agent.activeState = HolyGrenade(agent)
                    return

                else:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                    return

        else:
            agent.activeState = PreemptiveStrike(agent)


