import math
import time
#import States
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlutilities.linear_algebra import *
from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash
from rlutilities.simulation import Game, Ball, Car
import cProfile, pstats, io



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



GOAL_WIDTH = 1900
FIELD_LENGTH = 10280
FIELD_WIDTH = 8240
maxPossibleSpeed = 2300

boosts = [
    [3584, 0,0],
    [-3584, 0,0],
    [3072, 4096,0],
    [3072, -4096,0],
    [-3072, 4096,0],
    [-3072, -4096,0]
    ]

class predictionStruct:
    def __init__(self,location,_time):
        self.location = location
        self.time = _time


class renderCall:
    def __init__(self,_function,*args):
        self.function = _function
        self.args = args

    def run(self):
        self.function(self.args[0],self.args[1],self.args[2]())



# class FlipStatus:
#     def __init__(self):
#         self.started = False
#         self.flipStartedTimer = None
#         self.flipDone = False

class FlipStatus:
    def __init__(self,_time):
        self.started = False
        self.flipStartedTimer = _time
        self.flipDone = False

class Boost_obj:
    def __init__(self,location,bigBoost, spawned):
        self.location = Vector(location) #list of 3 coordinates
        self.bigBoost = bigBoost # bool indicating if it's a cannister or just a pad
        self.spawned = spawned  # bool indicating whether it's currently spawned


class physicsObject:
    def __init__(self):
        self.location = Vector([0, 0, 0])
        self.velocity = Vector([0, 0, 0])
        self.rotation = Vector([0, 0, 0])
        self.avelocity = Vector([0, 0, 0])
        self.local_location = Vector([0, 0, 0])
        self.boostLevel = 0
        self.team = -1
        self.matrix = []

class Vector:
    def __init__(self, content): #accepts list of float/int values
        self.data = content

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]

    def vec3Convert(self):
        return vec3(self.data[0],self.data[1].self.data[2])

    def raiseLengthError(self,other, operation):
        raise ValueError(f"Tried to perform {operation} on 2 vectors of differing lengths")

    def raiseCrossError(self):
        raise ValueError("Both vectors need 3 terms for cross product")

    def __mul__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] * other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other,"multiplication")

    def __add__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] + other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other, "addition")

    def __sub__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] - other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other, "subtraction")

    def alignTo(self, rot):
        v = Vector([self.data[0], self.data[1], self.data[2]])
        v = Vector([v[0],math.cos(rot[0]) * v[1] + math.sin(rot[0]) * v[2],math.cos(rot[0]) * v[2] - math.sin(rot[0]) * v[1]])
        v = Vector([math.cos(-rot[1]) * v[0] + math.sin(-rot[1]) * v[2], v[1], math.cos(-rot[1]) * v[2] - math.sin(-rot[1]) * v[0]])
        v = Vector([math.cos(-rot[2]) * v[0] + math.sin(-rot[2]) * v[1], math.cos(-rot[2]) * v[1] - math.sin(-rot[2]) * v[0], v[2]])

        return v

    def crossProduct(self,other):
        if len(self.data) == 3 and len(other.data) == 3:
            newVec = [0,0,0]
            newVec[0] = self[1]*other[2] - self[2]*other[1]
            newVec[1] = self[2]*other[0] - self[0]*other[2]
            newVec[2] = self[0] * other[1] - self[1] * other[0]

            return Vector(newVec)


        else:
            self.raiseCrossError()

    def flatten(self):
        return Vector(self.data[:2]+[0])


    def magnitude(self):
        return math.sqrt(sum([x*x for x in self]))

    def normalize(self):
        mag = self.magnitude()
        if mag != 0:
            return Vector([x/mag for x in self])
        else:
            return Vector([0 for _ in range(len(self.data))])

    def dotProduct(self,other):
        product = 0
        for i,j in zip(self,other):
            product += i*j
        return product

    def scale(self,scalar):
        return Vector([x*scalar for x in self.data])


    def correction_to(self, ideal):
        current_in_radians = math.atan2(self[1], -self[0])
        ideal_in_radians = math.atan2(ideal[1], -ideal[0])

        correction = ideal_in_radians - current_in_radians
        if abs(correction) > math.pi:
            if correction < 0:
                correction += 2 * math.pi
            else:
                correction -= 2 * math.pi

        return correction


    def toList(self):
        return self.data

    def lerp(self,otherVector,percent): #percentage indicated 0 - 1
        percent = clamp(1,0,percent)
        originPercent = 1-percent

        scaledOriginal = self.scale(originPercent)
        other = otherVector.scale(percent)
        return scaledOriginal+other

def convertStructLocationToVector(struct):
    return Vector([struct.physics.location.x,struct.physics.location.y,struct.physics.location.z])

def Rotation_Vector(rot):
    pitch = float(rot.pitch)
    yaw = float(rot.yaw)
    facing_x = math.cos(pitch) * math.cos(yaw)
    facing_y = math.cos(pitch) * math.sin(yaw)
    facing_z = math.sin(pitch)
    return Vector([facing_x, facing_y, facing_z])


def alternativeAngle(x):
    if x > 0:
        return x-360
    if x <= 0:
        return x + 360


def placeVecWithinArena(vec):
    if vec[0] > 4096:
        vec.data[0] = 4096

    elif vec[0] < -4096:
        vec.data[0] = -4096

    if vec[1] > 5120:
        if abs(vec[0]) > 850:
            vec.data[1] = 5120

        else:
            if vec[1] > 5300:
                vec.data[1] = 5300

    elif vec[1] < -5120:
        if abs(vec[0]) > 850:
            vec.data[1] = -5120

        else:
            if vec[1] < -5300:
                vec.data[1] = -5300




def demoMagic(agent):
    currentSpd = agent.getCurrentSpd()
    if currentSpd <1900:
        if agent.me.boostLevel <=0:
            agent.activeState.active = False
    e_goal = Vector([0, 5100 * -sign(agent.team), 200])
    best = None
    distance = math.inf
    for e in agent.enemies:
        if e.location[2] <= 120:
            _distance = distance2D(e_goal,e.location)
            if _distance < distance:
                distance = _distance
                best = e

    if best != None:
        if currentSpd <=100:
            currentSpd = 100

        currentTimeToTarget = distance / currentSpd
        lead = clamp(agent.deltaTime*60,agent.deltaTime*5,agent.deltaTime*distance/500)
        difference = best.velocity.scale(lead)
        targetPos = e.location + difference
        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, agent.me.location.data, targetPos.data, agent.renderer.purple))

        if currentTimeToTarget <= agent.deltaTime*30:
            targetLocal = toLocal(targetPos,agent.me)
            angle = math.degrees(math.atan2(targetLocal[1],targetLocal[0]))
            if abs(angle) <= 40:
                agent.setJumping(0)

        return testMover(agent,targetPos,2300)



    else:
        return None



def kickOffTest(agent):
    if agent.gameInfo.is_kickoff_pause:
        if len(agent.allies) > 0:
            myDist = distance2D(agent.me.location,agent.ball.location)
            for ally in agent.allies:
                if distance2D(ally.location,agent.ball.location) < myDist:
                    return False
        return True
    return False

def flipHandler(agent,flip_status):
    if flip_status.started:
        jump = False
    else:
        jump = True
        flip_status.started = True
        flip_status.flipStartedTimer = time.time()

    if time.time() - flip_status.flipStartedTimer >= 0.15:
        jump = True
        flip_status.flipDone = True

    return jump


def quad(a,b,c):
    inside = (b**2) - (4*a*c)
    if inside < 0 or a == 0:
        return 0.1
    else:
        n = ((-b - math.sqrt(inside))/(2*a))
        p = ((-b + math.sqrt(inside))/(2*a))
        if p > n:
            return p
        return n



def get_car_facing_vector(car):
    pitch = float(car.rotation[0])
    yaw = float(car.rotation[1])
    facing_x = math.cos(pitch) * math.cos(yaw)
    facing_y = math.cos(pitch) * math.sin(yaw)

    return Vector([facing_x, facing_y])






def rotator_to_matrix(our_object):
    r = our_object.rotation
    CR = math.cos(r[2])
    SR = math.sin(r[2])
    CP = math.cos(r[0])
    SP = math.sin(r[0])
    CY = math.cos(r[1])
    SY = math.sin(r[1])

    matrix = []
    matrix.append(Vector([CP*CY, CP*SY, SP]))
    matrix.append(Vector([CY*SP*SR-CR*SY, SY*SP*SR+CR*CY, -CP * SR]))
    matrix.append(Vector([-CR*CY*SP-SR*SY, -CR*SY*SP+SR*CY, CP*CR]))
    return matrix

def getLocation(_object):
    if type(_object) == Vector:
        return _object
    if type(_object) == physicsObject:
        return _object.location
    raise ValueError(f"{type(_object)} is not a valid input for 'getLocation' function ")



def clamp(_max,_min,value):
    if value > _max:
        return _max
    if value < _min:
        return _min
    return value

def sign(x):
    if x <= 0:
        return -1
    else:
        return 1

def steer(angle):
    final = ((35 * angle) ** 3) / 20
    return clamp(1,-1,final)

def newSteer(angle):
    turn = Gsteer(angle)
    slide = False

    if abs(math.degrees(angle)) >=85:
        slide = True

    return (turn,slide)

def slideSteer(angle,distance):
    sliding = False
    degrees = math.degrees(angle)

    if distance < 1000:
        if abs(degrees) > 70 and abs(degrees) < 180:
            sliding = True
        """
        if abs(degrees) < 3:
            return(0,False)
        """

        return (clamp(1, -1, (degrees/360)*8),sliding)
    else:
        if abs(degrees) < 3:
            return(0,False)

        return (clamp(1, -1, (degrees/360)*8), sliding)


def saferBoostGrabber(agent):
    minDistance = distance2D(Vector([0, 5100 * sign(agent.team), 200]),agent.ball.location)
    closestBoost = physicsObject()
    closestBoost.location = Vector([0, 5100 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            goalDistance = distance2D(boost.location, Vector([0, 5100 * sign(agent.team), 200]))
            if goalDistance < minDistance*.7:
                distance = distance2D(agent.me.location,boost.location)
                localCoords = toLocal(boost.location, agent.me)
                angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
                if boost.bigBoost:
                    distance = distance*.5
                distance += angle * 5
                if distance < bestDistance:
                    bestDistance = distance
                    closestBoost = boost
                    bestAngle = angle

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, closestBoost.location.data,
                                        agent.renderer.yellow))

    return efficientMover(agent, closestBoost.location, agent.maxSpd,boostHunt=False)

def boostHungry(agent):
    closestBoost = agent.me
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            distance = distance2D(boost.location, agent.me)
            localCoords = toLocal(closestBoost.location, agent.me)
            angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
            distance +=  angle*5
            distance += distance2D(agent.me.location,agent.ball.location)
            if boost.bigBoost:
                distance *= .5
            if distance < bestDistance:
                bestDistance = distance
                closestBoost = boost
                bestAngle = angle

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, closestBoost.location.data,
                                        agent.renderer.yellow))
    return efficientMover(agent, closestBoost.location, agent.maxSpd,boostHunt=False)

def distance1D(origin,destination,index):
    return abs(getLocation(origin)[index] - getLocation(destination)[index])


def defendGoal(agent):
    return ShellTime(agent)



def findOppositeSideVector(agent,objVector,antiTarget, desiredBallDistance):
    angle = math.degrees(angle2(objVector,antiTarget))
    targetDistance = distance2D(objVector, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - objVector).normalize()
    totalOffset = desiredBallDistance
    return getLocation(antiTarget) - (oppositeVector.scale(targetDistance + desiredBallDistance))


def findOppositeSide(agent,targetLoc,antiTarget, desiredBallDistance):
    angle = correctAngle(math.degrees(angle2(targetLoc,antiTarget)))
    targetDistance = distance2D(targetLoc, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - targetLoc).normalize()
    totalOffset = desiredBallDistance
    return getLocation(antiTarget) - (oppositeVector.scale(targetDistance + desiredBallDistance))

def findGoalAngle(agent):
    center = Vector([0, 5150 * -sign(agent.team), 200])
    return math.degrees(angle2(agent.ball, center)) * sign(agent.team)

def determineVelocityToGoal(agent):
    myGoal = Vector([0, 5150 * -sign(agent.team), 200])
    startingDistance = distance2D(myGoal,agent.ball.location)
    if startingDistance < distance2D(myGoal,agent.ball.location + agent.ball.velocity):
        return True
    else:
        return False

def backmanDefense(agent):
    center = Vector([0, 5120 * sign(agent.team), 200])
    rendevouz = Vector([0, 4900 * sign(agent.team), 200])
    ballToGoaldistance = distance2D(center,agent.ball.location)
    distance = distance2D(agent.me.location,agent.ball.location)

    if distance < 5000:
        if distance < 1500:
            return ShellTime(agent)

        defenderFound = False
        for ally in agent.allies:
            a_dist= distance2D(ally.location,agent.ball.location)
            if a_dist < distance:
                if distance2D(center,ally.location) < ballToGoaldistance:
                    defenderFound = True
        if not defenderFound:
            return ShellTime(agent)

        else:
            agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, center,
                                                agent.renderer.blue))
            if distance2D(agent.me.location,rendevouz) > 500:
                return efficientMover(agent, rendevouz, 2200,boostHunt=True)
            else:
                return efficientMover(agent,rendevouz,50,boostHunt=True)

    else:
        centerField = Vector([0,agent.ball.location[1] + 3000*sign(agent.team),0])
        if agent.me.boostLevel < 50:
            return saferBoostGrabber(agent)
        else:
            agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, centerField.data,
                                                agent.renderer.blue))
            return efficientMover(agent, centerField, 2200,boostHunt=True)


def secondManSupport(agent):
    defendTarget = Vector([0, 5120 * sign(agent.team), 200])
    if agent.me.boostLevel < 50:
        return saferBoostGrabber(agent)

    destination = findOppositeSide(agent,agent.ball.location,defendTarget,-100)
    destination.data[1] += sign(agent.team)*2200
    destination.data[2] = 75
    placeVecWithinArena(destination)
    destination.data[0] = clamp(3500,-3500,destination.data[0])

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, destination.data,
                                        agent.renderer.green))

    return efficientMover(agent,destination,2200,boostHunt=True)

def ownGoalCheck(agent,targetVec):
    leftPost = Vector([sign(agent.team) * 800, 5100 * sign(agent.team), 200])
    rightPost = Vector([-sign(agent.team) * 800, 5100 * sign(agent.team), 200])
    center = Vector([0, 5100 * sign(agent.team), 200])

    if distance2D(agent.ball.location,center) < distance2D(agent.me.location,center):
        localTarget = toLocal(targetVec,agent.me)
        targetAngle = correctAngle(math.degrees(math.atan2(localTarget[1],localTarget[0])))

        localRP = toLocal(rightPost, agent.me)
        rightPostAngle = correctAngle(math.degrees(math.atan2(localRP[1], localRP[0])))

        localLP = toLocal(leftPost, agent.me)
        leftPostAngle = correctAngle(math.degrees(math.atan2(localLP[1], localLP[0])))

        if leftPostAngle < targetAngle < rightPostAngle:
            if leftPostAngle - targetAngle > rightPostAngle -targetAngle:
                return True,leftPost
            else:
                return True,rightPost

    return False,None

def noOwnGoalDefense(agent,targetVec):
    leftCorner = Vector([-sign(agent.team) * 4096, 5200 * sign(agent.team), 50])
    rightCorner = Vector([sign(agent.team) * 4096, 5200 * sign(agent.team), 50])
    leftPost = Vector([-sign(agent.team) * 760, 4100 * sign(agent.team), 50])
    rightPost = Vector([sign(agent.team) * 760, 4100 * sign(agent.team), 50])
    center = Vector([0, 5400 * sign(agent.team), 200])

    ballGoalDist = distance2D(targetVec, center)
    carGoalDist = distance2D(agent.me.location, center)

    if ballGoalDist > 6000:
        if (agent.me.location[1] * sign(agent.team)) + (sign(agent.team) * 120) < agent.ball.location[1] * sign(agent.team):
            return (center, False)

    elif (agent.me.location[1] * sign(agent.team)) + (sign(agent.team) * 20) > agent.ball.location[1] * sign(agent.team):
        return (center, False)

    if ballGoalDist < 1000:
        return (center, False)

    ballToLeft = distance1D(leftCorner,targetVec,0)
    ballToRight = distance1D(rightCorner,targetVec,0)

    carToLeft = distance1D(leftCorner,agent.me.location,0)
    carToRight = distance1D(rightCorner,agent.me.location,0)
    if carToLeft < ballToLeft:
        return (rightPost, True)

    if carToRight < ballToRight:
        return (leftPost, True)


    return (rightPost, True)


# def ShellTime(agent):
#     defendTarget = Vector([0, 5350 * sign(agent.team), 200])
#     rush = False
#     if agent.selectedBallPred:
#         targetVec = Vector([agent.selectedBallPred.physics.location.x,
#                              agent.selectedBallPred.physics.location.y,
#                              agent.selectedBallPred.physics.location.z])
#     else:
#         targetVec = agent.ball.location
#
#     defensiveRange = 250
#     if agent.contested:
#         defensiveRange = 10
#
#     goalDistance = distance2D(targetVec, defendTarget)
#     carDistance = distance2D(agent.me.location, defendTarget)
#     ballGoalDistance = distance2D(agent.ball.location,defendTarget)
#
#
#     _enemyInfluenced = True
#
#
#     if goalDistance < 1300:
#         _enemyInfluenced = False
#
#     if len(agent.allies) < 1:
#         flipDecider(agent, targetVec,enemyInfluenced= _enemyInfluenced)
#     else:
#         flipDecider2(agent)
#
#     if carDistance < goalDistance:
#         #if not agent.contested or openGoalOpportunity(agent):
#         localPos = toLocal(targetVec,agent.me)
#         angleDegrees = math.degrees(math.atan2(localPos[1],localPos[0]))
#         if abs(angleDegrees) <=35 or abs(angleDegrees) >= 145:
#             carOffset = agent.carLength/2
#         else:
#             carOffset = agent.carWidth/2
#
#         ballOffset = 75
#
#         totalOffset = carOffset + ballOffset
#         destination = findOppositeSide(agent,targetVec,Vector([0, 5300 * -sign(agent.team), 0]),totalOffset)
#         if abs(angleDegrees) <= 35:
#             if agent.ballGrounded:
#                 rush = True
#         # else:
#         #     _direction = direction(defendTarget, targetVec)
#         #     destination = targetVec - _direction.scale(120)
#
#     else:
#         if agent.ballGrounded:
#             rush = True
#         if agent.me.location[0] > targetVec[0]:
#             xOff = 25
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff += clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#
#         else:
#             xOff = -25
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff -= clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#         yOff = 25
#         yOff += clamp(30,0,abs(targetVec[0] - agent.me.location[0]))
#
#         destination = Vector([targetVec[0]+xOff,targetVec[1]+sign(agent.team)*yOff,targetVec[2]])
#
#     placeVecWithinArena(destination)
#     if rush:
#         result = testMover(agent,destination,maxPossibleSpeed)
#     else:
#
#         result = timeDelayedMovement(agent, destination, agent.ballDelay,True)
#
#     destination.data[2] = 75
#     agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,
#                                         agent.me.location.data,
#                                         destination.data,
#                                         agent.renderer.blue))
#
#     return result

def turnTowardsPosition(agent,targetPosition,threshold):
    localTarg = toLocal(targetPosition,agent.me)
    localAngle = correctAngle(math.degrees(math.atan2(localTarg[1],localTarg[0])))
    controls = SimpleControllerState()

    if abs(localAngle) > threshold:
        if agent.forward:
            if localAngle > 0:
                controls.steer = 1
            else:
                controls.steer = -1

            controls.handbrake = True
            if agent.currentSpd <300:
                controls.throttle = .5
        else:
            if localAngle > 0:
                controls.steer = -1
            else:
                controls.steer = 1
            controls.handbrake = True
            if agent.currentSpd <300:
                controls.throttle = -.5

    return controls

def playDefensive(agent):
    centerGoal = Vector([0, 5200 * sign(agent.team), 200])
    dist = distance2D(agent.me.location,centerGoal)

    # if agent.contested:
    #     return bringToCorner(agent)

    if dist > 1000:
        return testMover(agent, centerGoal, maxPossibleSpeed)
    elif dist > 200:
        return efficientMover(agent, centerGoal, maxPossibleSpeed, True)
    # elif dist > 100:
    #     return efficientMover(agent, centerGoal, 500, True)
    else:
        print("turning")
        return turnTowardsPosition(agent, agent.ball.location, 2)

def playBack(agent):
    centerField = Vector([agent.ball.location[0], agent.ball.location[1] + 4500 * sign(agent.team), 0])


    boostTarget,dist = boostSwipe(agent)
    if boostTarget != None and dist < 2000:
        #print("swiper no swiping!")
        return testMover(agent,boostTarget,maxPossibleSpeed)
    if agent.me.boostLevel < 50:
        return backmanBoostGrabber(agent)

    else:
        agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, centerField.data,
                                            agent.renderer.blue))
        return efficientMover(agent, centerField, maxPossibleSpeed, boostHunt=True)

def boostSwipe(agent):
    enemyBackBoostLocations = [Vector([3072,-sign(agent.team)*4096,73]),Vector([-3072,-sign(agent.team)*4096,73])]

    backBoosts = []
    minDist = math.inf
    bestBoost = None
    for b in agent.boosts:
        if b.bigBoost:
            if b.spawned:
                for eb in enemyBackBoostLocations:
                    if distance2D(eb,b.location) < 300:
                        backBoosts.append(eb)
                        dist = distance2D(eb,agent.me.location)
                        if dist < minDist:
                            bestBoost = eb
                            minDist = dist
                        #return b.location

    return bestBoost,minDist

def findEnemyClosestToLocation2D(agent,location):
    if len(agent.enemies) > 0:
        closest = agent.enemies[0]
        cDist = math.inf
        for e in agent.enemies:
            x = distance2D(e.location, location)
            if x < cDist:
                cDist = x
                closest = e
        return closest,cDist
    else:
        return None,None

# def ShellTime(agent):
#     defendTarget = Vector([0, 5120 * sign(agent.team), 200])
#     if agent.selectedBallPred:
#         targetVec = Vector([agent.selectedBallPred.physics.location.x,
#                              agent.selectedBallPred.physics.location.y,
#                              agent.selectedBallPred.physics.location.z])
#     else:
#         targetVec = agent.ball.location
#
#     goalDistance = distance2D(targetVec, defendTarget)
#     carDistance = distance2D(agent.me.location, defendTarget)
#     _enemyInfluenced = True
#
#     if goalDistance < 1300:
#         _enemyInfluenced = False
#
#     if len(agent.allies) < 1:
#         flipDecider(agent, targetVec,enemyInfluenced= _enemyInfluenced)
#     else:
#         flipDecider2(agent)
#
#     if carDistance < goalDistance:
#         destination = Vector([targetVec[0],targetVec[1]+sign(agent.team)*85,targetVec[2]])
#
#     else:
#         if agent.me.location[0] > targetVec[0]:
#             xOff = 80
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff += clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#
#         else:
#             xOff = -80
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff -= clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#         yOff = 55
#
#         yOff += clamp(30,0,abs(targetVec[0] - agent.me.location[0]))
#
#         destination = Vector([targetVec[0]+xOff,targetVec[1]+sign(agent.team)*yOff,targetVec[2]])
#
#     placeVecWithinArena(destination)
#     result = timeDelayedMovement(agent, destination, agent.ballDelay,True)
#
#     destination.data[2] = 75
#     agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,
#                                         agent.me.location.data,
#                                         destination.data,
#                                         agent.renderer.blue))
#
#     return result
def backmanBoostGrabber(agent):
    #minDistance = distance2D(Vector([0, 5100 * sign(agent.team), 200]), agent.ball.location)
    minY = (agent.ball.location[1] +3000*sign(agent.team))*sign(agent.team)
    closestBoost = physicsObject()
    closestBoost.location = Vector([0, 5100 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            if boost.location[1] *sign(agent.team) >= minY:
                #print(minY,boost.location[1] *sign(agent.team),sign(agent.team))
                #goalDistance = distance2D(boost.location, Vector([0, 5100 * sign(agent.team), 200]))
                distance = distance2D(agent.me.location, boost.location)
                localCoords = toLocal(boost.location, agent.me)
                angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
                distance += angle * 5
                if boost.bigBoost:
                    distance = distance * .75
                if distance < bestDistance:
                    bestDistance = distance
                    closestBoost = boost
                    bestAngle = angle

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, closestBoost.location.data,
                                        agent.renderer.yellow))

    return efficientMover(agent, closestBoost.location, agent.maxSpd, boostHunt=False)

# def ShellTime(agent):
#     defendTarget = Vector([0, 5350 * sign(agent.team), 200])
#     rush = False
#     if agent.selectedBallPred:
#         targetVec = Vector([agent.selectedBallPred.physics.location.x,
#                              agent.selectedBallPred.physics.location.y,
#                              agent.selectedBallPred.physics.location.z])
#     else:
#         targetVec = agent.ball.location
#
#     defensiveRange = 250
#     if agent.contested:
#         defensiveRange = 10
#
#     goalDistance = distance2D(targetVec, defendTarget)
#     carDistance = distance2D(agent.me.location, defendTarget)
#     ballGoalDistance = distance2D(agent.ball.location,defendTarget)
#     if ballGoalDistance+defensiveRange < carDistance:
#         return playDefensive(agent)
#
#     # ballCorner = cornerDetection(agent.ball.location)
#     #
#     # if agent.team == 0:
#     #     if ballCorner == 0 or ballCorner == 1:
#     #         if agent.contested:
#     #             return playDefensive(agent)
#     # else:
#     #     if ballCorner == 2 or ballCorner == 3:
#     #         if agent.contested:
#     #             return playDefensive(agent)
#
#     _enemyInfluenced = True
#
#     # if not agent.ballGrounded:
#     #     if not rush:
#     #         if targetVec.data[2] >= 120:
#     #             return handleBounceShot(agent,waitForShot=False)
#
#     if goalDistance < 1300:
#         _enemyInfluenced = False
#
#     if len(agent.allies) < 1:
#         flipDecider(agent, targetVec,enemyInfluenced= _enemyInfluenced)
#     else:
#         flipDecider2(agent)
#
#     if carDistance < goalDistance:
#         #if not agent.contested or openGoalOpportunity(agent):
#         localPos = toLocal(targetVec,agent.me)
#         angleDegrees = math.degrees(math.atan2(localPos[1],localPos[0]))
#         if abs(angleDegrees) <=35 or abs(angleDegrees) >= 145:
#             carOffset = agent.carLength/2
#         else:
#             carOffset = agent.carWidth/2
#
#         ballOffset = 75
#
#         totalOffset = carOffset + ballOffset
#         destination = findOppositeSide(agent,targetVec,Vector([0, 5300 * -sign(agent.team), 0]),carOffset)
#         # if abs(angleDegrees) <= 35:
#         #     rush = True
#         # else:
#         #     _direction = direction(defendTarget, targetVec)
#         #     destination = targetVec - _direction.scale(120)
#
#     else:
#         if agent.me.location[0] > targetVec[0]:
#             xOff = 25
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff += clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#
#         else:
#             xOff = -25
#             if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
#                 xOff -= clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
#
#         yOff = 25
#         yOff += clamp(30,0,abs(targetVec[0] - agent.me.location[0]))
#
#         destination = Vector([targetVec[0]+xOff,targetVec[1]+sign(agent.team)*yOff,targetVec[2]])
#
#     placeVecWithinArena(destination)
#     if rush:
#         result = testMover(agent,destination,maxPossibleSpeed)
#     else:
#
#         result = timeDelayedMovement(agent, destination, agent.ballDelay,True)
#
#     destination.data[2] = 75
#     agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,
#                                         agent.me.location.data,
#                                         destination.data,
#                                         agent.renderer.blue))
#
#     return result

def ShellTime(agent):
    defendTarget = Vector([0, 5800 * sign(agent.team), 200])
    rush = False
    heightCutoff = 120
    if agent.selectedBallPred:
        targetVec = Vector([agent.selectedBallPred.physics.location.x,
                             agent.selectedBallPred.physics.location.y,
                             agent.selectedBallPred.physics.location.z])
    else:
        targetVec = agent.ball.location

    defensiveRange = 50
    # if agent.contested:
    #     defensiveRange = 10

    goalDistance = distance2D(targetVec, defendTarget)
    carDistance = distance2D(agent.me.location, defendTarget)
    ballGoalDistance = distance2D(agent.ball.location,defendTarget)
    if ballGoalDistance+defensiveRange < carDistance:
        return playDefensive(agent)


    localPos = toLocal(targetVec, agent.me)
    angleDegrees = math.degrees(math.atan2(localPos[1], localPos[0]))

    if abs(angleDegrees) <= 45 or abs(angleDegrees) >= 135:
        carOffset = agent.carLength / 2
        ballOffset = 75
    else:
        carOffset = agent.carWidth/ 2
        ballOffset = 45

    totalOffset = carOffset + ballOffset

    if carDistance < goalDistance:
         destination = findOppositeSide(agent,targetVec,Vector([0, 5300 * -sign(agent.team), 0]),totalOffset)

    else:
        # if agent.me.location[0] > targetVec[0]:
        #     xOff = 25
        #     if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
        #         xOff += clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
        #
        #
        # else:
        #     xOff = -25
        #     if agent.me.location[1] * -sign(agent.team) > -sign(agent.team) * targetVec[1]:
        #         xOff -= clamp(30,1,abs(targetVec[1]-agent.me.location[1])/15)
        #
        # yOff = carOffset * .85
        # yOff += clamp(90,0,abs(targetVec[0] - agent.me.location[0]))
        # #print("yoff matters?", agent.time)

        #destination = Vector([targetVec[0]+xOff,targetVec[1]+sign(agent.team)*yOff,targetVec[2]])
        destination = findOppositeSide(agent, targetVec, defendTarget, -totalOffset)
        #print("here",agent.time)

    #placeVecWithinArena(destination)


    if agent.ballGrounded:
        modifiedDelay = clamp(6, 0, agent.ballDelay - (totalOffset / agent.currentSpd))
    else:
        modifiedDelay = agent.ballDelay
    result = timeDelayedMovement(agent, destination, agent.ballDelay,True)

    # if len(agent.allies) <1:
    #     flipDecider(agent,targetVec,True)
    # else:
    #     flipDecider2(agent)
    flipDecider(agent, targetVec, True)
    destination.data[2] = 75
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,
                                        agent.me.location.data,
                                        destination.data,
                                        agent.renderer.blue))

    return result


def turtleTime(agent):
    goalDistance = distance2D(agent.ball.location,Vector([0, 5100 * sign(agent.team), 200]))
    defendTarget = Vector([0, 5250 * sign(agent.team), 200])


    if agent.selectedBallPred:
        targetVec = Vector([agent.selectedBallPred.physics.location.x, agent.selectedBallPred.physics.location.y,
                            agent.selectedBallPred.physics.location.z])
        agent.ballDelay = agent.selectedBallPred.game_seconds - agent.gameInfo.seconds_elapsed

    else:
        targetVec = agent.ball.location
        agent.ballDelay = 0

    _enemyInfluenced = True
    if goalDistance < 1300:
        _enemyInfluenced = False

    flipDecider(agent,targetVec,enemyInfluenced= _enemyInfluenced)

    if distance2D(targetVec,defendTarget) < 5000:
        if ballHeadedTowardsMyGoal(agent):
            defendTarget, reposition = noOwnGoalDefense(agent,targetVec)
            if reposition:
                agent.renderCalls.append(
                    renderCall(agent.renderer.draw_line_3d, agent.me.location.data, defendTarget.data,
                               agent.renderer.blue))
                placeVecWithinArena(defendTarget)
                return testMover(agent, defendTarget, 2300)
    targ_local = toLocal(targetVec,agent.me)
    goal_local = toLocal(Vector([0, 5100 * sign(agent.team), 200]),agent.me)
    targ_angle = math.degrees(math.atan2(targ_local[1],targ_local[0]))
    goal_angle = math.degrees(math.atan2(goal_local[1],goal_local[0]))

    distance = distance2D(defendTarget,targetVec)
    oppositeVector = (getLocation(defendTarget) - targetVec).normalize()
    destination =  getLocation(defendTarget) - (oppositeVector.scale(distance - clamp(110,50,50)))
    placeVecWithinArena(destination)
    result = timeDelayedMovement(agent, destination, agent.ballDelay,True)

    destination.data[2] = 95
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,agent.me.location.data,destination.data,agent.renderer.blue))
    return result

def prepareShot(agent):
    leftPost = Vector([-sign(agent.team) * 700, 5100 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 700, 5100 * -sign(agent.team), 200])
    center = Vector([0, 5150 * -sign(agent.team), 200])

def goalWallFixer(agent):
    myGoal = Vector([0, 5120 * sign(agent.team), 0])
    jump = False
    if abs(agent.me.location[0]) < 893:
        if abs(agent.me.location[1]) > 5120:
            if agent.onWall:
                jump = True
    return jump

def flipDecider2(agent):
    if agent.selectedBallPred == None:
        pred = agent.ballPred.slices[0]
    else:
        pred = agent.selectedBallPred

    targetVec = convertStructLocationToVector(pred)
    dist = distance2D(agent.me.location,targetVec)

    jumpTimer = .5

    if agent.contested:
        timeUntilshot = pred.game_seconds - agent.gameInfo.seconds_elapsed
        if pred.game_seconds - agent.gameInfo.seconds_elapsed< jumpTimer :
            if dist <=50 or dist/agent.getCurrentSpd() <= jumpTimer :
                if targetVec[2] >200:
                    agent.setJumping(-1)
                elif targetVec[2] > 125:
                    agent.setJumping(0)

    else:
        if pred.game_seconds - agent.gameInfo.seconds_elapsed< jumpTimer :
            if dist <= 50 or dist/agent.getCurrentSpd() <= jumpTimer :
                if targetVec[2] > 200:
                    agent.setJumping(-1)
                elif targetVec[2] > 125:
                    agent.setJumping(0)


def flipDecider(agent,targetVec,enemyInfluenced=False):
    if not enemyInfluenced:
        targetVec = agent.ball.location
        if distance2D(agent.me.location, agent.ball.location) <= 200:
            if targetVec[2] <= 160:
                agent.setJumping(0)

    else:
        if distance2D(agent.me.location,targetVec) <= 200:
            if targetVec[2] <= 160:
                if len(agent.enemies) > 0:
                    closest = agent.enemies[0]
                    cDist = math.inf
                    for e in agent.enemies:
                        x = findDistance(e.location,agent.ball.location)
                        if x < cDist:
                            cDist = x
                            closest = e
                    if cDist < 350:
                        agent.setJumping(0)

def findEnemyClosestToLocation(agent,location):
    if len(agent.enemies) > 0:
        closest = agent.enemies[0]
        cDist = math.inf
        for e in agent.enemies:
            x = findDistance(e.location, location)
            if x < cDist:
                cDist = x
                closest = e
        return closest,cDist
    else:
        return None,None

def ballContested(agent):
    closestToMe,mDist = findEnemyClosestToLocation(agent,agent.me.location)
    closestToBall, bDist = findEnemyClosestToLocation(agent,agent.ball.location)

    if mDist:
        if mDist > 800 and bDist > 800:
            agent.contested = False
        else:
            agent.contested = True
    else:
        agent.contested = False


def lineupShot(agent,multi):
    variance = 5

    leftPost = Vector([-sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])

    myGoal = Vector([0, 5300 * sign(agent.team), 200])


    # if agent.me.location.data[1] *-sign(agent.team) > agent.ball.location.data[1] *-sign(agent.team):
    #     print("am I ahead of the ball?")

    if ballHeadedTowardsMyGoal(agent):
        return ShellTime(agent)

    if agent.selectedBallPred:
        targetVec = Vector([agent.selectedBallPred.physics.location.x, agent.selectedBallPred.physics.location.y,
                            agent.selectedBallPred.physics.location.z])
        agent.ballDelay = agent.selectedBallPred.game_seconds - agent.gameInfo.seconds_elapsed

    else:
        targetVec = agent.ball.location
        agent.ballDelay = 0

    #ballCorner = cornerDetection(agent.ball.location)

    distance = distance2D(agent.me.location, targetVec)
    dist2D = distance2D(agent.me.location, targetVec)
    goalDist = distance2D(center, targetVec)
    ballToGoalDist = distance2D(targetVec, center)
    targetLocal = toLocal(targetVec,agent.me)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1],targetLocal[0]))
    carToGoalDistance = distance2D(center,agent.me.location)
    carToBallDistance = distance2D(targetVec,agent.me.location)

    carToBallAngle = correctAngle(carToBallAngle)


    shotAngles = [math.degrees(angle2(targetVec, leftPost)),
                  math.degrees(angle2(targetVec, center)),
                  math.degrees(angle2(targetVec, rightPost))]

    correctedAngles=[correctAngle(x + 90 * -sign(agent.team)) for x in shotAngles]

    # if len(agent.allies) < 1:
    #     flipDecider(agent,targetVec,True)
    #     # if abs(correctedAngles[1]) >= 60:
    #     #     if agent.contested:
    #     #         return playBack(agent)
    # else:
    #     flipDecider2(agent)
    flipDecider(agent, targetVec, True)

    if distance2D(center,targetVec) < 2000:
        goalAngle = correctedAngles[1]
        goalSpot = center

    else:
        if correctedAngles[1] < -variance:
            goalAngle = correctedAngles[0]
            goalSpot = leftPost

        elif correctedAngles[1] > variance:
            goalAngle = correctedAngles[2]
            goalSpot = rightPost

        else:
            goalAngle = correctedAngles[1]
            goalSpot = center
    #goalSpot = center

    targetLoc = None
    rush = False
    ballOffset = 70

    if abs(carToBallAngle) <=45 or abs(carToBallAngle) >= 135:
        carOffset = agent.carLength/2
    else:
        carOffset = agent.carWidth/2
        #carOffset = 5

    positioningOffset = 0
    ballOffset = 70
    totalOffset = carOffset + ballOffset

    # if agent.contested and not agent.openGoal:
    #     _direction = direction(center, targetVec)
    #     targetLoc = targetVec - _direction.scale(carOffset+50)
    #     positioningOffset = carOffset+50

    if abs(carToBallAngle) < 30:
        if is_in_strike_zone(agent, targetVec):
            targetLoc = targetVec
            positioningOffset = totalOffset
            targetLoc.data[1] += sign(agent.team)*10
            if abs(carToBallAngle) <=4:
                if distance2D(agent.me.location, agent.ball.location) < 400:
                    if agent.ballGrounded:
                        if openGoalOpportunity(agent):
                            if agent.me.boostLevel < 1:
                                if (agent.me.location[1] * -sign(agent.team))+ -sign(agent.team)*100 < agent.ball.location[1] * -sign(agent.team):
                                    agent.setJumping(0)



    if not targetLoc:
        # if not agent.contested:
        #if agent.closestEnemyToBallDistance >500:
        if abs(targetVec[0]) < 2200:
            if ballToGoalDist < 5800 and ballToGoalDist > 1300:
                if agent.ballGrounded:
                    if abs(agent.me.location[1] - abs(targetVec[1]))> 600:
                        _direction = direction(goalSpot, targetVec)

                        targetLoc = targetVec - _direction.scale(clamp(1000,totalOffset,120 + distance * 0.5))
                        positioningOffset = clamp(1000,totalOffset,120 + distance * 0.5)



    if not targetLoc:
        targetLoc = findOppositeSide(agent, targetVec, goalSpot, clamp(400, totalOffset, distance * .35))
        positioningOffset =  clamp(400, totalOffset, distance * .35)
        #targetLoc = findOppositeSide(agent,targetVec,goalSpot,clamp(125,20,(dist/1.5)-abs(carToBallAngle)))

    # if agent.contested:
    #     defensivePosition = findOppositeSide(agent, targetVec, myGoal, -120)
    #     y = targetLoc.data[1]
    #     percent = 1
    #     if agent.team == 0:
    #         if y < 0:
    #             percent = clamp(1, 0, abs(y / 5120))
    #
    #     else:
    #         if y > 0:
    #             percent = clamp(1, 0, abs(y / 5120))
    #
    #     if percent < 0.75:
    #         targetLoc = targetLoc.lerp(defensivePosition, percent)
    #         # print(f"lerping {y}  {percent}")
    #placeVecWithinArena(targetLoc)


        #modifiedDelay = clamp(6,0,agent.ballDelay-((positioningOffset+carOffset)/agent.currentSpd))
    if agent.ballGrounded:
        modifiedDelay = clamp(6, 0, agent.ballDelay - ((positioningOffset) / clamp(maxPossibleSpeed,0.001,agent.currentSpd)))
    else:
        modifiedDelay = agent.ballDelay #clamp(6, 0, agent.ballDelay - (carOffset / agent.currentSpd))
    result = timeDelayedMovement(agent, targetLoc, modifiedDelay,True)

    targetLoc.data[2] = 95
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, targetLoc.data,
                                        agent.renderer.purple))

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.ball.location.data, goalSpot,
                                        agent.renderer.red))
    return result


# def lineupShot(agent,multi):
#     variance = 5
#
#     leftPost = Vector([-sign(agent.team) * 700, 5200 * -sign(agent.team), 200])
#     rightPost = Vector([sign(agent.team) * 700, 5200 * -sign(agent.team), 200])
#     center = Vector([0, 5200 * -sign(agent.team), 200])
#
#     if ballHeadedTowardsMyGoal(agent):
#         return ShellTime(agent)
#
#     if agent.selectedBallPred:
#         targetVec = Vector([agent.selectedBallPred.physics.location.x, agent.selectedBallPred.physics.location.y,
#                             agent.selectedBallPred.physics.location.z])
#         agent.ballDelay = agent.selectedBallPred.game_seconds - agent.gameInfo.seconds_elapsed
#
#     else:
#         targetVec = agent.ball.location
#         agent.ballDelay = 0
#
#     dist = distance2D(agent.me.location, targetVec)
#     goalDist = distance2D(center, targetVec)
#     ballToGoalDist = distance2D(targetVec, center)
#     targetLocal = toLocal(targetVec,agent.me)
#     carToBallAngle = math.degrees(math.atan2(targetLocal[1],targetLocal[0]))
#     carToGoalDistance = distance2D(center,agent.me.location)
#
#     carToBallAngle = correctAngle(carToBallAngle)
#
#
#     shotAngles = [math.degrees(angle2(targetVec, leftPost)),
#                   math.degrees(angle2(targetVec, center)),
#                   math.degrees(angle2(targetVec, rightPost))]
#
#     correctedAngles=[x + 90 * -sign(agent.team) for x in shotAngles]
#
#     if len(agent.allies) < 1:
#         flipDecider(agent, targetVec,enemyInfluenced= True)
#     else:
#         flipDecider2(agent)
#
#     if distance2D(center,targetVec) < 1500:
#         goalAngle = correctedAngles[1]
#         goalSpot = center
#
#     else:
#         if correctedAngles[1] < -variance:
#             goalAngle = correctedAngles[0]
#             goalSpot = leftPost
#
#         elif correctedAngles[1] > variance:
#             goalAngle = correctedAngles[2]
#             goalSpot = rightPost
#
#         else:
#             goalAngle = correctedAngles[1]
#             goalSpot = center
#
#
#     targetLoc = None
#     rush = False
#     if agent.ball.location[2] <= 140:
#         if dist > 40:
#             rush = True
#
#     if abs(carToBallAngle) < 30:
#         if is_in_strike_zone(agent, targetVec):
#             targetLoc = targetVec
#             targetLoc.data[1] += sign(agent.team)*10
#             if abs(carToBallAngle) <=6:
#                 if distance2D(agent.me.location, agent.ball.location) < 400:
#                         if targetVec[2] <= 150:
#                             if openGoalOpportunity(agent):
#                                 if (agent.me.location[1] * -sign(agent.team))+ -sign(agent.team)*100 < agent.ball.location[1] * -sign(agent.team):
#                                     agent.setJumping(0)
#
#
#
#     if not targetLoc:
#         if abs(targetVec[0]) < 2200:
#             if ballToGoalDist < 5800 and ballToGoalDist > 1300:
#                 if targetVec[2] < 120:
#                     if abs(agent.me.location[1] < abs(targetVec[1])):
#                         _direction = direction(center, targetVec)
#                         targetLoc = targetVec - _direction.scale(120 + dist * 0.5)
#         if not targetLoc:
#             targetLoc = findOppositeSide(agent,targetVec,goalSpot,clamp(125,60,(dist/1.5)-abs(carToBallAngle)))
#
#
#     placeVecWithinArena(targetLoc)
#
#     if rush:
#         result = testMover(agent,targetLoc,maxPossibleSpeed)
#     else:
#         result = timeDelayedMovement(agent, targetLoc, agent.ballDelay,True)
#
#     targetLoc.data[2] = 95
#     agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.data, targetLoc.data,
#                                         agent.renderer.purple))
#
#     agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.ball.location.data, goalSpot,
#                                         agent.renderer.red))
#     return result



def maxSpeedAdjustment(agent,target):
    tar_local = toLocal(target,agent.me)
    angle = abs(correctAngle(math.degrees(math.atan2(tar_local[1],tar_local[0]))))
    dist = distance2D(agent.me.location,target)
    distCorrection = dist/300

    if dist >=2000:
        return maxPossibleSpeed

    if abs(angle) <=3:
        return maxPossibleSpeed



    cost_inc = maxPossibleSpeed/180
    if dist < 1000:
        cost_inc*=2.5
    #angle = abs(angle) -10
    angle = abs(angle)
    newSpeed = clamp(maxPossibleSpeed,400,maxPossibleSpeed - (angle*cost_inc))
    #print(f"adjusting speed to {newSpeed}")

    return newSpeed



def is_in_strike_zone(agent, ball_vec):
    leftPost = Vector([-sign(agent.team) * 700, 5100 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 700, 5100 * -sign(agent.team), 200])
    localLeft = toLocal(leftPost,agent.me)
    localRight = toLocal(rightPost,agent.me)
    localBall = toLocal(ball_vec,agent.me)

    angles = [math.degrees(math.atan2(localLeft[1],localLeft[0])),
              math.degrees(math.atan2(localBall[1],localBall[0])),
              math.degrees(math.atan2(localRight[1],localRight[0]))]

    if not agent.forward:
        for i in range(len(angles)):
            angles[i] = angles[i]-180

    if angles[0]+2.5 < angles[1] < angles[2]-2.5:
        return True
    return False

def calcTimeWithAcceleration(agent,distance):
    estimatedSpd = agent.currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = agent.me.boostLevel
    boostingCost = 33.3*agent.deltaTime
    linearChunk = 1600/1410
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = 1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration+=991
                boostAmount -= boostingCost
            if acceleration > 0:
                estimatedSpd += acceleration * agent.deltaTime
            distanceTally+= estimatedSpd*agent.deltaTime
            estimatedTime += agent.deltaTime
        else:
            #estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.deltaTime
            estimatedTime += agent.deltaTime

    #print("friendly ended")
    return estimatedTime

# def inaccurateArrivalEstimator(agent,destination):
#     distance = clamp(math.inf,1,distance2D(agent.me.location,destination))
#     currentSpd = clamp(2300,1,agent.getCurrentSpd())
#     localTarg = toLocal(destination,agent.me)
#     if agent.forward:
#         angle = math.degrees(math.atan2(localTarg[1],localTarg[0]))
#     else:
#         angle = correctAngle(math.degrees(math.atan2(localTarg[1],localTarg[0]))-180)
#     if distance < 2000:
#         if abs(angle) > 40:
#             distance+= abs(angle)
#
#     if agent.me.boostLevel > 0:
#         maxSpd = clamp(2300,currentSpd,currentSpd+ (distance*.3))
#     else:
#         maxSpd = clamp(2200, currentSpd, currentSpd + (distance*.15))
#
#     return distance/maxSpd

def inaccurateArrivalEstimator(agent,destination):
    distance = clamp(math.inf,0.00001,distance2D(agent.me.location,destination)-(91+agent.carLength/2))
    moreAccurateEstimation = calcTimeWithAcceleration(agent,distance)

    #print(f"estimate for reaching distance {distance}: {moreAccurateEstimation}")
    return moreAccurateEstimation

def direction(source, target) -> Vector:
    return (getLocation(source) - getLocation(target)).normalize()

def angle2(target_location,object_location):
    difference = getLocation(target_location) - getLocation(object_location)
    return math.atan2(difference[1], difference[0])

def getVelocity(_obj):
    return math.sqrt(sum([x*x for x in _obj]))

def getVelocity2D(_obj):
    return math.sqrt(sum[_obj.velocity[0]**2,_obj.velocity[0]**2])

def findDistance(origin,destination):
    difference = getLocation(origin) - getLocation(destination)
    return abs(math.sqrt(sum([x * x for x in difference])))

def distance2D(origin,destination):
    _origin = getLocation(origin)
    _destination = getLocation(destination)
    _origin = Vector([_origin[0],_origin[1]])
    _destination = Vector([_destination[0],_destination[1]])
    difference = _origin - _destination
    return abs(math.sqrt(sum([x * x for x in difference])))

def correctAngle(x):

    while x > 360:
        x-=360
    while x < -360:
        x+=360

    if x > 180:
        x-=360
    elif x < -180:
        x+=360

    return x

def localizeVector(target_object,our_object):
    x = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(our_object.matrix[0])
    y = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(our_object.matrix[1])
    z = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(our_object.matrix[2])
    return Vector([x, y, z])

def toLocal(target,our_object):
    if isinstance(target,physicsObject):
        return target.local_location
    else:
        return localizeVector(target,our_object)

# def testMover(agent, target_object,targetSpd):
#     if targetSpd > 2200:
#         targetSpd = 2200
#
#     if agent.me.boostLevel <= 88:
#         newTarget = convenientBoost(agent,getLocation(target_object))
#         if newTarget != None:
#             target_object = newTarget
#             targetSpd = 2200
#             agent.renderCalls.append(
#                 renderCall(agent.renderer.draw_line_3d, agent.me.location.data, target_object.data,
#                            agent.renderer.yellow))
#             return efficientMover(agent,target_object,targetSpd,boostHunt=False)
#     currentSpd = agent.getCurrentSpd()
#     _distance = distance2D(agent.me, target_object)
#
#     if targetSpd < currentSpd+150 or agent.me.boostLevel <=0 or targetSpd < 900 or (getLocation(target_object)[2]>120 and _distance < 300):
#         return efficientMover(agent,target_object,targetSpd,boostHunt=False)
#
#     location = toLocal(target_object, agent.me)
#     controller_state = SimpleControllerState()
#     angle_to_target = math.atan2(location.data[1], location.data[0])
#     angle_degrees = correctAngle(math.degrees(angle_to_target))
#     if angle_degrees >=120:
#         if currentSpd <= 500:
#             agent.forward = False
#
#     if not agent.forward:
#         return efficientMover(agent, target_object, targetSpd,boostHunt=False)
#
#     if len(agent.allies) >= 1:
#         steering, slide = newSteer(angle_to_target)
#     else:
#         steering, slide = rockSteer(angle_to_target,_distance)
#
#     if abs(steering) >=.95:
#         optimalSpd = maxSpeedAdjustment(agent, target_object)
#
#         if targetSpd > optimalSpd:
#             targetSpd = optimalSpd
#
#     controller_state.steer = steering
#     controller_state.handbrake = slide
#     if agent.forward:
#         controller_state.throttle = 1.0
#     else:
#         controller_state.throttle = -1.0
#
#     if targetSpd > currentSpd:
#         if agent.onSurface and not slide:
#             if targetSpd > 1400 and currentSpd < 2200:
#                 if agent.forward:
#                     controller_state.boost = True
#     elif targetSpd < currentSpd:
#         if agent.getActiveState() != 3:
#             if agent.forward:
#                 controller_state.throttle = -1
#             else:
#                 controller_state.throttle = 1
#         else:
#             if currentSpd - targetSpd < 25:
#                 controller_state.throttle = 0
#             else:
#                 if agent.forward:
#                     controller_state.throttle = -1
#                 else:
#                     controller_state.throttle = 1
#
#     if currentSpd > 1400:
#         if _distance > clamp(2300,1400,currentSpd+500)*1.6:
#             if agent.onSurface:
#                 if not agent.onWall:
#                     if currentSpd < targetSpd:
#                             maxAngle = 3 + clamp(2,0,_distance/1000)
#                             if abs(angle_degrees) < maxAngle:
#                                     agent.setJumping(1)
#
#     return controller_state

# def testMover(agent, target_object,targetSpd):
#     if targetSpd > maxPossibleSpeed:
#         targetSpd = maxPossibleSpeed
#     placeVecWithinArena(target_object)
#     currentSpd = agent.currentSpd
#     _distance = distance2D(agent.me, target_object)
#
#     # if targetSpd < currentSpd+150 or agent.me.boostLevel <=0 or targetSpd < 900 or (getLocation(target_object)[2]>120 and _distance < 300):
#     #     return efficientMover(agent,target_object,targetSpd,boostHunt=False)
#
#     location = toLocal(target_object, agent.me)
#     controller_state = SimpleControllerState()
#     angle_to_target = math.atan2(location.data[1], location.data[0])
#     angle_degrees = correctAngle(math.degrees(angle_to_target))
#     if angle_degrees >=120:
#         if currentSpd <= 500:
#             agent.forward = False
#
#     if not agent.forward:
#         return efficientMover(agent, target_object, targetSpd,boostHunt=False)
#
#     if agent.me.boostLevel <=0:
#         return efficientMover(agent, target_object, targetSpd, boostHunt=False)
#
#     if len(agent.allies) >= 1:
#         steering, slide = newSteer(angle_to_target)
#     else:
#         steering, slide = rockSteer(angle_to_target,_distance)
#
#     #steering, slide = newSteer(angle_to_target)
#
#     if abs(steering) >=.95:
#         optimalSpd = maxSpeedAdjustment(agent, target_object)
#
#         if targetSpd > optimalSpd:
#             targetSpd = optimalSpd
#
#     controller_state.steer = steering
#     controller_state.handbrake = slide
#     if agent.forward:
#         controller_state.throttle = 1.0
#     else:
#         controller_state.throttle = -1.0
#
#     if targetSpd > currentSpd:
#         if agent.onSurface and not slide:
#             if targetSpd > 1400 and currentSpd < maxPossibleSpeed-100:
#                 if agent.forward:
#                     controller_state.boost = True
#     elif targetSpd < currentSpd:
#         if agent.getActiveState() != 3:
#             if agent.forward:
#                 controller_state.throttle = -1
#             else:
#                 controller_state.throttle = 1
#         else:
#             if currentSpd - targetSpd < 25:
#                 controller_state.throttle = 0
#             else:
#                 if agent.forward:
#                     controller_state.throttle = -1
#                 else:
#                     controller_state.throttle = 1
#
#     if currentSpd > 1400:
#         if _distance > clamp(2300,1400,currentSpd+500)*1.6:
#             if agent.onSurface:
#                 if not agent.onWall:
#                     if currentSpd < targetSpd:
#                             maxAngle = 3 + clamp(2,0,_distance/1000)
#                             if abs(angle_degrees) < maxAngle:
#                                     agent.setJumping(1)
#
#     return controller_state

def testMover(agent, target_object,targetSpd):
    if targetSpd > maxPossibleSpeed:
        targetSpd = maxPossibleSpeed
    placeVecWithinArena(target_object)
    currentSpd = agent.currentSpd
    _distance = distance2D(agent.me, target_object)

    # if targetSpd < currentSpd+150 or agent.me.boostLevel <=0 or targetSpd < 900 or (getLocation(target_object)[2]>120 and _distance < 300):
    #     return efficientMover(agent,target_object,targetSpd,boostHunt=False)

    location = toLocal(target_object, agent.me)
    controller_state = SimpleControllerState()
    angle_to_target = math.atan2(location.data[1], location.data[0])
    angle_degrees = correctAngle(math.degrees(angle_to_target))
    if angle_degrees >=120:
        if currentSpd <= 500:
            agent.forward = False

    if not agent.forward:
        return efficientMover(agent, target_object, targetSpd,boostHunt=False)

    if agent.me.boostLevel <=0:
        return efficientMover(agent, target_object, targetSpd, boostHunt=False)

    # if len(agent.allies) >= 1:
    #     steering, slide = newSteer(angle_to_target)
    # else:
    #     steering, slide = rockSteer(angle_to_target,_distance)
    steering, slide = newSteer(angle_to_target)
    if slide:
        if abs(agent.me.avelocity[2]) < 1:
            slide = False

    #steering, slide = newSteer(angle_to_target)

    if abs(steering) >=.95:
        optimalSpd = maxSpeedAdjustment(agent, target_object)

        if targetSpd > optimalSpd:
            targetSpd = optimalSpd

    controller_state.steer = steering
    controller_state.handbrake = slide
    if agent.forward:
        controller_state.throttle = 1.0
    else:
        controller_state.throttle = -1.0

    if targetSpd > currentSpd:
        if agent.onSurface and not slide:
            if targetSpd > 1400 and currentSpd < maxPossibleSpeed-100:
                if agent.forward:
                    controller_state.boost = True
    elif targetSpd < currentSpd:
        if agent.getActiveState() != 3:
            if agent.forward:
                controller_state.throttle = -1
            else:
                controller_state.throttle = 1
        else:
            if currentSpd - targetSpd < 25:
                controller_state.throttle = 0
            else:
                if agent.forward:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1

    if currentSpd > 1400:
        if _distance > clamp(2300,1400,currentSpd+500)*1.6:
            if agent.onSurface:
                if not agent.onWall:
                    if currentSpd < targetSpd:
                            maxAngle = 3 + clamp(2,0,_distance/1000)
                            if abs(angle_degrees) < maxAngle:
                                    agent.setJumping(1)

    return controller_state


# def timeDelayedMovement(agent,targetVec,delay):
#     arrivalEstimate = inaccurateArrivalEstimator(agent, targetVec)
#
#     if arrivalEstimate >= delay:
#         return testMover(agent, targetVec, 2200)
#
#     else:
#         dist = distance2D(agent.me.location, targetVec)
#         adjustedSpd = 0
#         if dist > 150:
#             adjustedSpd = dist/10
#         return efficientMover(agent, targetVec, (dist/delay)+adjustedSpd,boostHunt=True)

def timeDelayedMovement(agent,targetVec,delay,boostHungry):
    arrivalEstimate = inaccurateArrivalEstimator(agent, targetVec)

    if arrivalEstimate >= delay:
        return testMover(agent, targetVec, maxPossibleSpeed)

    else:
        distance = clamp(999999,0.00001,distance2D(agent.me.location,targetVec))
        speed = distance/delay

    return efficientMover(agent, targetVec, speed,boostHunt=boostHungry)



# def efficientMover(agent,target_object,target_speed,boostHunt = False):
#     controller_state = SimpleControllerState()
#     originalTarget = target_object
#
#     if boostHunt:
#         if agent.me.boostLevel < 88:
#             newTarget = convenientBoost(agent,getLocation(target_object))
#             if newTarget != None:
#                 target_speed = maxPossibleSpeed
#                 target_object = newTarget
#                 agent.renderCalls.append(
#                     renderCall(agent.renderer.draw_line_3d, agent.me.location.data, newTarget.data,
#                                agent.renderer.yellow))
#     placeVecWithinArena(originalTarget)
#     placeVecWithinArena(target_object)
#     location = toLocal(target_object, agent.me)
#     angle_to_target = math.atan2(location.data[1], location.data[0])
#     _distance = distance2D(agent.me, target_object)
#     current_speed = agent.currentSpd
#     if not agent.forward:
#         controller_state.throttle = -1
#         _angle = math.degrees(angle_to_target)
#         _angle -= 180
#         if _angle < -180:
#             _angle += 360
#         if _angle > 180:
#             _angle -= 360
#
#         angle_to_target = math.radians(_angle)
#         if agent.onSurface:
#             if _distance > 1200:
#                 if abs(_angle) <= 50 :
#                     agent.setHalfFlip()
#
#     if len(agent.allies) >= 1:
#         steerDirection, slideBool = newSteer(angle_to_target)
#     else:
#         steerDirection, slideBool = rockSteer(angle_to_target,_distance)
#     #steerDirection, slideBool = newSteer(angle_to_target)
#     if not agent.forward:
#         steerDirection = -steerDirection
#     controller_state.steer = steerDirection
#     controller_state.handbrake = slideBool
#
#     if abs(steerDirection) >=.9:
#         optimalSpd = maxSpeedAdjustment(agent, target_object)
#
#         if target_speed > optimalSpd:
#             target_speed = optimalSpd
#
#     if current_speed < target_speed:
#         if agent.forward:
#             controller_state.throttle = 1
#         else:
#             controller_state.throttle = -1
#
#         if agent.getActiveState() == 3 or agent.getActiveState() == 4 or agent.getActiveState() == 5:
#             if abs(math.degrees(angle_to_target)) <= clamp(3,0,_distance/1000):
#                 if agent.onSurface:
#                     if current_speed >= 1050:
#                         o_dist = distance2D(agent.me.location,originalTarget)
#                         if o_dist >= 1000:
#                             if o_dist > clamp(2300,current_speed,current_speed+500)*1.7:
#                                 if agent.forward:
#                                     agent.setJumping(1)
#                                 else:
#                                     agent.setJumping(3)
#
#     else:
#         if current_speed > target_speed:
#             if agent.getActiveState() != 3:
#                 if agent.forward:
#                     controller_state.throttle = -1
#                 else:
#                     controller_state.throttle = 1
#             else:
#                 if current_speed - target_speed < 35:
#                     controller_state.throttle = 0
#                 else:
#                     if agent.forward:
#                         controller_state.throttle = -1
#                     else:
#                         controller_state.throttle = 1
#
#     if slideBool:
#         if agent.currentSpd < 500:
#             controller_state.handbrake = False
#
#     return controller_state

def efficientMover(agent,target_object,target_speed,boostHunt = False):
    controller_state = SimpleControllerState()
    originalTarget = target_object

    if boostHunt:
        if agent.me.boostLevel < 88:
            newTarget = convenientBoost(agent,getLocation(target_object))
            if newTarget != None:
                target_speed = maxPossibleSpeed
                target_object = newTarget
                agent.renderCalls.append(
                    renderCall(agent.renderer.draw_line_3d, agent.me.location.data, newTarget.data,
                               agent.renderer.yellow))
    placeVecWithinArena(originalTarget)
    placeVecWithinArena(target_object)
    location = toLocal(target_object, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    _distance = distance2D(agent.me, target_object)
    current_speed = agent.currentSpd
    if not agent.forward:
        controller_state.throttle = -1
        _angle = math.degrees(angle_to_target)
        _angle -= 180
        if _angle < -180:
            _angle += 360
        if _angle > 180:
            _angle -= 360

        angle_to_target = math.radians(_angle)
        if agent.onSurface:
            if _distance > 1200:
                if abs(_angle) <= 50 :
                    agent.setHalfFlip()

    # if len(agent.allies) >= 1:
    #     steerDirection, slideBool = newSteer(angle_to_target)
    # else:
    #     steerDirection, slideBool = rockSteer(angle_to_target,_distance)
    steerDirection, slideBool = newSteer(angle_to_target)
    if slideBool:
        if abs(agent.me.avelocity[2]) < 1:
            slideBool = False
    #steerDirection, slideBool = newSteer(angle_to_target)
    if not agent.forward:
        steerDirection = -steerDirection
    controller_state.steer = steerDirection
    controller_state.handbrake = slideBool

    if abs(steerDirection) >=.9:
        optimalSpd = maxSpeedAdjustment(agent, target_object)

        if target_speed > optimalSpd:
            target_speed = optimalSpd

    if current_speed < target_speed:
        if agent.forward:
            controller_state.throttle = 1
        else:
            controller_state.throttle = -1

        if agent.getActiveState() == 3 or agent.getActiveState() == 4 or agent.getActiveState() == 5:
            if abs(math.degrees(angle_to_target)) <= clamp(3,0,_distance/1000):
                if agent.onSurface:
                    if current_speed >= 1050:
                        o_dist = distance2D(agent.me.location,originalTarget)
                        if o_dist >= 1500:
                            if o_dist > clamp(2300,current_speed,current_speed+500)*1.9:
                                if agent.forward:
                                    agent.setJumping(1)
                                else:
                                    agent.setJumping(3)

    else:
        if current_speed > target_speed:
            if agent.getActiveState() != 3:
                if agent.forward:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1
            else:
                if current_speed - target_speed < 35:
                    controller_state.throttle = 0
                else:
                    if agent.forward:
                        controller_state.throttle = -1
                    else:
                        controller_state.throttle = 1

    if slideBool:
        if agent.currentSpd < 500:
            controller_state.handbrake = False

    return controller_state


def Gsteer(angle):
    final = ((10 * angle+sign(angle))**3) / 20
    return clamp(1,-1,final)


def rockSteer(angle,distance):
    turn = Gsteer(angle)
    slide = False
    distanceMod = clamp(10,.3,distance/500)
    _angle = correctAngle(math.degrees(angle))


    adjustedAngle = _angle/distanceMod
    if abs(turn) >=1:
        if abs(adjustedAngle) > 100:
            slide = True

    return turn,slide

def isBallGrounded(agent,heightMax,frameMin):
    if agent.ballPred is not None:
        for i in range(0, frameMin):
            if agent.ballPred.slices[i].physics.location.z > heightMax:
                return False
        return True
    return False

def greedyMover(agent,target_object):
    controller_state = SimpleControllerState()
    controller_state.handbrake = False
    location = toLocal(target_object, agent.me)
    angle = math.atan2(location.data[1], location.data[0])
    controller_state.throttle = 1
    if getVelocity(agent.me.velocity) < 2200:
        if agent.onSurface:
            controller_state.boost = True
    controller_state.jump = False

    controller_state.steer = Gsteer(angle)

    return controller_state




def exampleController(agent, target_object,target_speed):
    distance = distance2D(agent.me.location,target_object.location)
    if distance > 400:
        agent.state = efficientMover
        return efficientMover(agent,target_object,target_speed,boostHunt=True)

    controller_state = SimpleControllerState()
    controller_state.handbrake = False

    car_direction = get_car_facing_vector(agent.me)
    car_to_ball =  agent.me.location - target_object.location

    steer_correction_radians = steer(car_direction.correction_to(car_to_ball))

    current_speed = getVelocity(agent.me.velocity)
    controller_state.steer = steer(steer_correction_radians)
    if target_speed > current_speed:
        controller_state.throttle = 1.0
        if target_speed > 1400 and current_speed < 2250:
            controller_state.boost = True
    elif target_speed < current_speed:
        controller_state.throttle = 0

    return controller_state

def isBallNearWall(ballstruct):
    if ballstruct.physics.location.x > 4096 - 120:
        return True
    if ballstruct.physics.location.x < -4096 + 120:
        return True

    if ballstruct.physics.location.y < -5120 + 120:
        return True

    if ballstruct.physics.location.y > 5120 - 120:
        return True



def isBallHittable(ballStruct,agent,maxHeight):
    multi = clamp(3, 1, len(agent.allies)+1)
    if ballStruct.physics.location.z<= maxHeight:
        return True
    if ballStruct.physics.location.x > 4096 - 130:
        if ballStruct.physics.location.z <= 200*multi:
            return True
    if ballStruct.physics.location.x < -4096 + 130:
        if ballStruct.physics.location.z <= 200*multi:
            return True

    if ballStruct.physics.location.y < -5120 + 130:
        if ballStruct.physics.location.z <= 200*multi:
            if abs(ballStruct.physics.location.x) > 893:
                return True
    if ballStruct.physics.location.y > 5120 - 130:
        if ballStruct.physics.location.z <= 200*multi:
            if abs(ballStruct.physics.location.x) > 900:
                return True
    return False


def findSoonestBallTouchable(agent):
    if agent.ballPred != None:
        bestStruct = agent.ballPred.slices[359]
        quickest = 99999999
        spd = clamp(2200, 300, abs(agent.getCurrentSpd()))

        if agent.ballPred is not None:
            for i in range(0, agent.ballPred.num_slices):
                if agent.ballPred.slices[i].physics.location.z <= 155:
                    distance = distance2D(agent.me.location, Vector([agent.ballPred.slices[i].physics.location.x,
                                                                     agent.ballPred.slices[i].physics.location.y,
                                                                     agent.ballPred.slices[i].physics.location.z]))
                    adjustedSpd = clamp(2200,spd, spd+ distance * .5)
                    timeEstimate = distance / adjustedSpd
                    if timeEstimate < quickest:
                        bestStruct = agent.ballPred.slices[i]
                        quickest = timeEstimate
            return bestStruct

    return None


def aerialWorkHorse(agent,struct):
    myGoal = center = Vector([0, 5120 * sign(agent.team), 200])
    enemyGoal = center = Vector([0, 5120 * -sign(agent.team), 200])


    aerial = agent.aerial
    a_turn = agent.a_turn

    targetVec = Vector([aerial.target[0],aerial.target[1],aerial.target[2]])
    #print(aerial.target.x)

    if agent.onSurface and not agent.onWall:
        targetLocal = toLocal(targetVec, agent.me)

        carToBallAngle = correctAngle(
            math.degrees(math.atan2(targetLocal[1], targetLocal[0])))

        maxAngle = clamp(45,2,distance2D(agent.me.location,targetVec)/100)
        if abs(carToBallAngle) > maxAngle:
            print("driving to target")
            agent.forward = True
            return efficientMover(agent,targetVec,1000,boostHunt = False)
        # else:
        #     print("launching")
        #     agent.setLaunch()
        #     return agent.activeState.update()

    print("returning aerial controls")
    aerial.step(agent.deltaTime)
    controls = aerial.controls
    if agent.onSurface:
        controls.jump = True
    return controls



#@profile
def aerialSelection(agent, struct):

    myGoal = Vector([0, 5120 * sign(agent.team), 200])
    enemyGoal = Vector([0, 5120 * -sign(agent.team), 200])

    if agent.aerial == None:
        agent.aerial = Aerial(agent.game.my_car)
    if agent.a_turn == None:
        agent.a_turn = AerialTurn(agent.game.my_car)

    aerial = agent.aerial
    a_turn = agent.a_turn


    targetVec = Vector([struct.physics.location.x,struct.physics.location.y,struct.physics.location.z])


    acceptable = False
    if agent.team == 0:
        if agent.me.location[1] < targetVec[1]:
            acceptable = True
    else:
        if agent.me.location[1] > targetVec[1]:
            acceptable = True

    if acceptable:

        if agent.team == 0:

            targetLocal = toLocal(targetVec, agent.me)

            totalAngle = math.degrees(math.atan2(targetLocal[1],targetLocal[0]))

            if abs(totalAngle) > 60:
                return False

        elif agent.team == 1:

            targetLocal = toLocal(targetVec, agent.me)
            totalAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

            if abs(totalAngle) > 60:
                return False


        ballAngle = correctAngle(math.degrees(angle2(targetVec, enemyGoal)+ 90 * -sign(agent.team)))
        if abs(ballAngle) > 55:
            return False


        aerial.arrival_time = struct.game_seconds
        direction = (enemyGoal.flatten() - targetVec.flatten()).normalize()
        beneathAmount = -35
        if distance2D(targetVec, enemyGoal) >= 2000:
            beneathAmount = 0
        offset = direction.scale(100+beneathAmount)
        targetVec = targetVec - offset

        targetVec.data[2]-=beneathAmount

        aerial.target = vec3(targetVec[0], targetVec[1], targetVec[2])

        simulation = aerial.simulate()
        if norm(simulation.location - aerial.target) < 100:
            return True

    return False


def findPredictionByTime(agent,_time): #agent and updated prediction.game_seconds
    req_time = _time - agent.gameInfo.seconds_elapsed
    index = int((1/60) * req_time)
    if index <=0 or index >= 360:
        return -1

    return agent.ballPred[index]



def findSuitableBallPosition(agent, heightMax, speed, origin):
    applicableStructs = []
    spd = clamp(2300,300,speed)
    ballInGoal = None
    goalTimer = math.inf

    aerialStruct = None
    aboveThreshold = False
    valid = True

    for i in range(0, agent.ballPred.num_slices,3):
        # if i > 60 and i%3 == 0:
        #     continue
        pred = agent.ballPred.slices[i]
        _distance = distance2D(Vector([pred.physics.location.x, pred.physics.location.y]), origin)
        if isBallHittable(agent.ballPred.slices[i],agent,heightMax):
            if agent.team == 0:
                if pred.physics.location.y <= -5250:
                    ballInGoal = pred
                    goalTimer = pred.game_seconds - agent.gameInfo.seconds_elapsed
                    agent.goalPred = pred
                    agent.wallShot = isBallNearWall(pred)
                    return ballInGoal,aerialStruct
            else:
                if pred.physics.location.y >= 5250:
                    ballInGoal = pred
                    goalTimer = pred.game_seconds - agent.gameInfo.seconds_elapsed
                    agent.goalPred = pred
                    agent.wallShot = isBallNearWall(pred)
                    return ballInGoal, aerialStruct

            #ground ball selection here


            timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]))
            if timeToTarget < (pred.game_seconds - agent.gameInfo.seconds_elapsed):
                agent.wallShot = isBallNearWall(pred)
                return pred, aerialStruct



        else:
            if aerialStruct == None:
                if pred.physics.location.z >= clamp(700,200,_distance/3):
                    aboveThreshold = True
                    if valid:
                        if agent.me.boostLevel > 0:
                            if aerialSelection(agent, pred):
                                aerialStruct = pred
                # else:
                #     if aboveThreshold:
                #         valid = False


    return pred,aerialStruct



def findSuitableBallPosition2(agent, heightMax, speed, origin):
    applicableStructs = []
    spd = clamp(2300,300,speed)
    ballInGoal = None
    goalTimer = math.inf
    if agent.ballPred is not None:
        for i in range(0, agent.ballPred.num_slices):
            if isBallHittable(agent.ballPred.slices[i],agent,heightMax):
                applicableStructs.append(agent.ballPred.slices[i])
                if agent.team == 0:
                    if agent.ballPred.slices[i].physics.location.y <= -5050:
                        ballInGoal = agent.ballPred.slices[i]
                        goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
                        break
                else:
                    if agent.ballPred.slices[i].physics.location.y >= 5050:
                        ballInGoal = agent.ballPred.slices[i]
                        goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
                        break
                applicableStructs.append(agent.ballPred.slices[i])

    for pred in applicableStructs:
        distance = distance2D(Vector([pred.physics.location.x,pred.physics.location.y]),origin)
        adjustSpd = clamp(2300,1000,speed+distance*.7)
        if distance/adjustSpd < (pred.game_seconds - agent.gameInfo.seconds_elapsed):
            if goalTimer < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                agent.goalPred = ballInGoal
            return pred

    if goalTimer < math.inf:
        agent.goalPred = ballInGoal
    return agent.ballPred.slices[-1]

def inaccurateArrivalEstimatorRemote(agent,start,destination):
    distance = clamp(math.inf,1,distance2D(start,destination))
    currentSpd = clamp(2300,1,agent.getCurrentSpd())

    if agent.me.boostLevel > 0:
        maxSpd = clamp(2300,currentSpd,currentSpd+ (distance*.3))
    else:
        maxSpd = clamp(2200, currentSpd, currentSpd + (distance*.15))

    return distance/maxSpd

def CB_Reworked(agent,targetVec):
    dist = clamp(25000, 1, distance2D(agent.me.location, targetVec))
    ballDist = clamp(25000, 1, distance2D(agent.me.location, agent.ball.location))
    destinationEstimate = inaccurateArrivalEstimator(agent,targetVec)
    locTarget = toLocal(targetVec, agent.me)
    targetAngle = correctAngle(math.degrees(math.atan2(locTarget[1], locTarget[0])))

    bestBoost = None
    bestAngle = 0
    angleDisparity = 1000
    bestDist = math.inf
    bestEstimate = math.inf
    goodBoosts = []
    for b in agent.boosts:
        _dist = distance2D(b.location, agent.me.location)
        if _dist < dist*.6:
            localCoords = toLocal(b.location, agent.me)
            angle = correctAngle(math.degrees(math.atan2(localCoords[1], localCoords[0])))
            _angleDisparity = targetAngle - angle

            if _angleDisparity > targetAngle-30 and _angleDisparity < targetAngle+30:
                goodBoosts.append(b)

    for b in goodBoosts:
        pathEstimate = inaccurateArrivalEstimator(agent,b.location) + inaccurateArrivalEstimatorRemote(agent,b.location,targetVec)
        if agent.me.boostLevel < 50:
            if b.bigBoost:
                pathEstimate*=.8
        if pathEstimate < bestEstimate:
            bestBoost = b
            bestEstimate = pathEstimate

    if bestEstimate < destinationEstimate*1.15 or bestEstimate < agent.ballDelay:
        return bestBoost.location
    else:
        return None

def convenientBoost(agent,targetVec):
    dist = clamp(25000,1,distance2D(agent.me.location,targetVec))
    ballDist = clamp(25000,1,distance2D(agent.me.location,agent.ball.location))
    spd = agent.getCurrentSpd()
    spd = clamp(2200,1500,spd + spd/(dist/1000))

    locTarget = toLocal(targetVec,agent.me)
    targetAngle = correctAngle(math.degrees(math.atan2(locTarget[1],locTarget[0])))


    bestBoost = None
    bestAngle = 0
    angleDisparity = 1000
    bestDist = math.inf
    goodBoosts = []
    for b in agent.boosts:
        _dist = distance2D(b.location,agent.me.location)
        if _dist < dist-500:
            localCoords = toLocal(b.location,agent.me)
            angle = correctAngle(math.degrees(math.atan2(localCoords[1],localCoords[0])))
            _angleDisparity = targetAngle - angle
            _angleDisparity = (_angleDisparity + 180) % 360 - 180
            if b.bigBoost:
                if _angleDisparity > 5:
                    _angleDisparity-=5
                elif _angleDisparity < -5:
                    _angleDisparity +=5

            if abs(_angleDisparity) < clamp(35,0,30*_dist/2000):
                goodBoosts.append(b)


    for each in goodBoosts:
        d = distance2D(each.location,agent.me.location)
        if each.bigBoost:
            d *=.7
        if d < bestDist:
            bestBoost = each
            bestDist = d


    if bestBoost != None and abs(angleDisparity) and (bestDist/spd + distance2D(bestBoost.location,targetVec)/spd < agent.ballDelay):
        if (bestDist/spd) + (distance2D(bestBoost.location,targetVec)/spd) <= agent.ballDelay or ballDist >= 3000:
            return bestBoost.location

    return None


def ballHeadedTowardsMyGoal(agent):
    myGoal = Vector([0, 5100 * sign(agent.team), 200])
    if (distance1D(myGoal, agent.ball.location, 1)  - distance1D(myGoal, agent.ball.location + agent.ball.velocity, 1)) > 0:
        if agent.ball.velocity.magnitude() > 5:
            return True

    return False

def openGoalOpportunity(agent):
    enemyGoal = Vector([0, 5100 * -sign(agent.team), 200])
    ballDistance = distance2D(agent.ball.location,enemyGoal)+200

    for e in agent.enemies:
        if distance2D(e.location,enemyGoal,) < ballDistance:
            return False

    return True

def challengeDecider(agent):
    myDistance = distance2D(agent.me.location,agent.ball.location)
    for e in agent.enemies:
        if distance2D(e.location,agent.ball.location) < myDistance-200:
            return False
    return True


def dpp(target_loc,target_vel,our_loc,our_vel):
    target_loc = getLocation(target_loc)
    our_loc = getLocation(our_loc)
    our_vel = getLocation(our_vel)
    d = distance2D(target_loc,our_loc)
    if d != 0:
        return (((target_loc.data[0] - our_loc.data[0]) * (target_vel.data[0] - our_vel.data[0])) + ((target_loc.data[1] - our_loc.data[1]) * (target_vel.data[1] - our_vel.data[1])))/d
    else:
        return 0

def timeZ(ball):
    rate = 0.97
    return quad(-325, ball.velocity.data[2] * rate, ball.location.data[2]-92.75)


def radius(v):
    return 139.059 + (0.1539 * v) + (0.0001267716565 * v * v)

def ballLowEnough(agent):
    if agent.ball.location[2] < 140:
        return True
    return False

def ballReady(agent):
    ball = agent.ball
    if abs(ball.velocity.data[2]) < 140 and timeZ(agent.ball) < 1:
        return True
    return False

def ballProject(agent):
    goal = Vector([0,-sign(agent.team)*FIELD_LENGTH/2,100])
    goal_to_ball = (agent.ball.location - goal).normalize()
    difference = agent.me.location - agent.ball.location
    return difference * goal_to_ball














