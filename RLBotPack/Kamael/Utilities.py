import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
#import numpy as np
from numba import jit



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
        self.lastTouch = 0
        self.lastToucher = 0
        self.rot_vector = None
        self.onSurface = False


# class Vector:
#     def __init__(self, content): #accepts list of float/int values
#         self.data = np.array(content)
#         #done
#     def __str__(self):
#         return str(self.data.tolist())
#         #done
#
#     def __repr__(self):
#         return str(self)
#
#     def __len__(self):
#         return self.data.size
#
#     def __getitem__(self, item):
#         return self.data[item]
#
#     def vec3Convert(self):
#         return vec3(self.data[0],self.data[1].self.data[2])
#
#     def raiseLengthError(self,other, operation):
#         raise ValueError(f"Tried to perform {operation} on 2 vectors of differing lengths")
#
#     def raiseCrossError(self):
#         raise ValueError("Both vectors need 3 terms for cross product")
#
#     def __mul__(self, other):
#         if len(self.data) == len(other.data):
#             return Vector(np.multiply(self.data,other.data).tolist())
#             #return Vector([self.data[i] * other[i] for i in range(len(other))])
#         else:
#             self.raiseLengthError(other,"multiplication")
#         #done
#
#     def __add__(self, other):
#         if len(self.data) == len(other.data):
#             #return Vector([self.data[i] + other[i] for i in range(len(other))])
#             return Vector(np.add(self.data,other.data).tolist())
#         else:
#             self.raiseLengthError(other, "addition")
#         #done
#
#     def __sub__(self, other):
#         if len(self.data) == len(other.data):
#             #return Vector([self.data[i] - other[i] for i in range(len(other))])
#             return Vector(np.subtract(self.data, other.data).tolist())
#         else:
#             self.raiseLengthError(other, "subtraction")
#         #done
#
#     def crossProduct(self,other):
#         if len(self.data) == 3 and len(other.data) == 3:
#             return Vector(np.cross(self.data,other.data).tolist())
#
#         else:
#             self.raiseCrossError()
#         #done
#
#
#     def magnitude(self):
#         return np.linalg.norm(self.data)
#
#
#     def normalize(self):
#         magnitude = self.magnitude()
#         if magnitude != 0.0:
#             return Vector((self.data / magnitude).tolist())
#         else:
#             return self
#
#     def dotProduct(self,other):
#         return np.dot(self.data,other.data)
#
#     def scale(self,scalar):
#         return Vector((self.data*scalar).tolist())
#
#
#     def correction_to(self, ideal):
#         current_in_radians = math.atan2(self[1], -self[0])
#         ideal_in_radians = math.atan2(ideal[1], -ideal[0])
#
#         correction = ideal_in_radians - current_in_radians
#         if abs(correction) > math.pi:
#             if correction < 0:
#                 correction += 2 * math.pi
#             else:
#                 correction -= 2 * math.pi
#
#         return correction
#
#
#     def toList(self):
#         return self.data.tolist()
#
#     def lerp(self,otherVector,percent): #percentage indicated 0 - 1
#         percent = clamp(1,0,percent)
#         originPercent = 1-percent
#
#         scaledOriginal = self.scale(originPercent)
#         other = otherVector.scale(percent)
#         return scaledOriginal+other


def newVectorsTest():
    testVec1 = Vector([5,5,5])
    testVec2 = Vector([3,3,3])

    print(f"testing print: {testVec1}")
    print(f"testing len: {len(testVec1)}")
    print(f"testing get item: {testVec1[0]}")
    print(f"testing multiply: {testVec1*testVec2}")
    print(f"testing addition: {testVec1+testVec2}")
    print(f"testing subtraction: {testVec1-testVec2}")
    print(f"testing cross product: {testVec1.crossProduct(testVec2)}")
    print(f"testing magnitude: {testVec1.magnitude()}")
    print(f"testing normalize: {testVec1.normalize()}")
    print(f"testing dotproduct: {testVec1.dotProduct(testVec2)}")
    print(f"testing scale multiplication: {testVec1.scale(2)}")
    print(f"testing lerp: {testVec1.lerp(testVec2,.5)}")
    print("done testing")

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

    __rmul__ = __mul__


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

    def align_to(self, rot):
        v = Vector([self[0], self[1], self[2]])
        v.data = [v[0], math.cos(rot[2]) * v[1] + math.sin(rot[2]) * v[2],
                  math.cos(rot[2]) * v[2] - math.sin(rot[2]) * v[1]]
        v.data = [math.cos(-rot[1]) * v[0] + math.sin(-rot[1]) * v[2], v[1],
                  math.cos(-rot[1]) * v[2] - math.sin(-rot[1]) * v[0]]
        v.data = [math.cos(-rot[0]) * v[0] + math.sin(-rot[0]) * v[1],
                  math.cos(-rot[0]) * v[1] - math.sin(-rot[0]) * v[0],
                  v[2]]

        return v

    def align_from(self, rot):
        v = Vector([self[0], self[1], self[2]])
        v.data = [math.cos(rot[0]) * v[0] + math.sin(rot[0]) * v[1], math.cos(rot[0]) * v[1] - math.sin(rot[0]) * v[0], v[2]]
        v.data = [math.cos(rot[1]) * v[0] + math.sin(rot[1]) * v[2], v[1],
              math.cos(rot[1]) * v[2] - math.sin(rot[1]) * v[0]]
        v.data = [v[0], math.cos(-rot[2]) * v[1] + math.sin(-rot[2]) * v[2],
              math.cos(-rot[2]) * v[2] - math.sin(-rot[2]) * v[1]]

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

class hit:
    def __init__(self,current_time:float,prediction_time:float,hit_type:int,pred_vector:Vector,pred_vel:Vector,hittable:bool,fastestTime:float):
        self.current_time = current_time
        self.prediction_time = prediction_time
        self.hit_type = hit_type  #0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate
        self.pred_vector = pred_vector
        self.pred_vel = pred_vel
        self.guarenteed_hittable = hittable
        self.fastestArrival = fastestTime

    def time_difference(self):
        return self.prediction_time - self.current_time

def constrain_pi(n):
    while n > math.pi:
        n -= math.pi * 2
    while n < -math.pi:
        n += math.pi * 2
    return n

def butterZone(vec):
    if abs(vec[0]) < 893:
        if abs(vec[1]) > 4500:
            return True
    return False

def correct(target, val, mult = 1):
    rad = constrain_pi(target - val)
    return (rad * mult)

class Rotation_Vector(Vector):
    def __init__(self, rot):
        self.data = [rot.yaw,rot.pitch,rot.roll]

    def angle_to_vec(rot, vec): # angle between a vector and rotation
        return math.acos(Vector([1, 0, 0]).align_to(rot).dotProduct(vec.normalize()))


    def angle_between(rot1, rot2): # angle between two rotations
        return Vector([1,0,0]).align_to(rot1).dotProduct(Vector([1,0,0]).align_to(rot2))



def Align_Car_To(agent, vector: Vector, up=Vector([0, 0, 0])):
    car_rot = agent.me.rotation
    car_rot_vel = agent.me.avelocity

    local_euler = car_rot_vel.align_from(agent.me.rotation)
    align_local = vector.align_from(agent.me.rotation)

    local_up = up.align_from(agent.me.rotation)

    # Improving this
    rot_ang_const = 0.25
    stick_correct = 6.0

    a1 = math.atan2(align_local[1], align_local[0])
    a2 = math.atan2(align_local[2], align_local[0])

    if local_up[1] == 0 and local_up[2] == 0:
        a3 = 0.0
    else:
        a3 = math.atan2(local_up[1], local_up[2])

    yaw = correct(0.0, -a1 + local_euler[2] * rot_ang_const, stick_correct)
    pitch = correct(0.0, -a2 - local_euler[1] * rot_ang_const, stick_correct)
    roll = correct(0.0, -a3 - local_euler[0] * rot_ang_const, stick_correct)

    yaw = clamp(1,-1,yaw)
    pitch = clamp(1,-1,pitch)
    roll = clamp(1,-1,roll)
    steer = clamp(1,-1,yaw)

    return steer,yaw,pitch,roll

def pointAtBall(agent):
    controler_state = SimpleControllerState()
    _direction = (agent.ball.location - agent.me.location).normalize()
    controler_state.steer,controler_state.yaw,controler_state.pitch,controler_state.roll = Align_Car_To(agent, _direction,up = Vector([0,0,1]))
    return controler_state




def impulse_velocity(agent, position, time):
    dir_to_ball = position - agent.jumpPhysics.location
    simple_impulse = Vector(dir_to_ball[:2])
    simple_impulse.scale(1/max(0.0001,time))
    vertical_vel = -(0.5 * agent.gravity * time * time - dir_to_ball[2]) / max(0.0001, time)
    return Vector(simple_impulse[0], simple_impulse[1], vertical_vel)

def calc_air(agent, position, time):
    return agent.calcDeltaV(position,time)

class ballTouch():
    def __init__(self, touchInfo):
        self.player_name = touchInfo.player_name
        self.hit_location = touchInfo.hit_location
        self.team = touchInfo.team
        self.player_index = touchInfo.player_index
        self.time_seconds = touchInfo.time_seconds

    def __repr__(self):
        valueString = f"""
        player_name = {self.player_name}
        hit_location = {self.hit_location}
        team = {self.team}
        player_index = {self.player_index}
        time_seconds = {self.time_seconds}
        """
        return valueString

    def __eq__(self,other):
        if type(other) != ballTouch:
            raise ValueError(f"Can not do comparisan operations of balltouch and {type(other)} objects.")

        if self.player_name != other.player_name:
            return False

        if self.hit_location != other.hit_location:
            return False

        if self.team != other.team:
            return False

        if self.player_index != other.player_index:
            return False

        if self.time_seconds != other.time_seconds:
            return False

        return True

def goal_selector(agent, mode = 0): #0 angles only, 1 enemy consideration
    leftPost = Vector([-sign(agent.team) * 500, 5200 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 500, 5200 * -sign(agent.team), 200])
    center = Vector([0, 5600 * -sign(agent.team), 200])
    variance = 5
    maxAngle = 40

    targetVec = agent.currentHit.pred_vector

    shotAngles = [math.degrees(angle2(targetVec, leftPost)),
                  math.degrees(angle2(targetVec, center)),
                  math.degrees(angle2(targetVec, rightPost))]

    correctedAngles = [correctAngle(x + 90 * -sign(agent.team)) for x in shotAngles]

    if distance2D(targetVec,center) >=4000:
        createTriangle(agent, center)
        return center,correctedAngles[1]

    if correctedAngles[1] >=maxAngle:
        createTriangle(agent, leftPost)
        return leftPost,correctedAngles[2]

    if correctedAngles[1] <= -maxAngle:
        createTriangle(agent, rightPost)
        return rightPost,correctedAngles[0]

    if mode == 0 or agent.openGoal:
        createTriangle(agent, center)
        return center,correctedAngles[1]

    if agent.openGoal:
        return center,correctedAngles[1]

    #print(f"aiming happening! {agent.time}")

    if distance2D(agent.closestEnemyToBall.location,center) < 3500:
        simple_projection = agent.closestEnemyToBall.location + agent.closestEnemyToBall.velocity.scale(.5)
        left_distance = distance2D(simple_projection,leftPost)
        right_distance = distance2D(simple_projection,rightPost)
        if left_distance > right_distance:
            return Vector([-sign(agent.team) * 500, 5200 * -sign(agent.team), 200]),correctedAngles[0]
        else:
            return Vector([sign(agent.team) * 500, 5200 * -sign(agent.team), 200]),correctedAngles[2]
    else:
        return center,correctedAngles[1]

def convertStructLocationToVector(struct):
    return Vector([struct.physics.location.x,struct.physics.location.y,struct.physics.location.z])

def convertStructVelocityToVector(struct):
    return Vector([struct.physics.velocity.x, struct.physics.velocity.y, struct.physics.velocity.z])

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
            if vec[1] > 5600:
                vec.data[1] = 5600

    elif vec[1] < -5120:
        if abs(vec[0]) > 850:
            vec.data[1] = -5120

        else:
            if vec[1] < -5600:
                vec.data[1] = -5600


def demoEnemyCar(agent,targetCar):
    currentSpd = clamp(maxPossibleSpeed,100,agent.currentSpd)
    distance = distance2D(agent.me.location,targetCar.location)

    currentTimeToTarget = inaccurateArrivalEstimator(agent,targetCar.location)
    lead = clamp(5,0,currentTimeToTarget)

    enemyspd = targetCar.velocity.magnitude()
    multi = clamp(1500,0,enemyspd*currentTimeToTarget)
    targPos = targetCar.location + (targetCar.velocity.normalize().scale(multi))
    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), targPos.toList(), agent.renderer.purple))
    return testMover(agent,targPos,maxPossibleSpeed)

def demoTarget(agent,targetCar):
    currentSpd = clamp(maxPossibleSpeed, 100, agent.currentSpd)
    distance = distance2D(agent.me.location, targetCar.location)

    currentTimeToTarget = inaccurateArrivalEstimator(agent, targetCar.location)
    lead = clamp(5, 0, currentTimeToTarget)

    enemyspd = targetCar.velocity.magnitude()
    multi = clamp(1500, 0, enemyspd * currentTimeToTarget)
    targPos = targetCar.location + (targetCar.velocity.normalize().scale(multi))
    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), targPos.toList(), agent.renderer.purple))

    return driveController(agent,targPos,currentTimeToTarget,expedite = True)
    #return testMover(agent, targPos, maxPossibleSpeed)


def demoMagic(agent):
    currentSpd = agent.currentSpd
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
            renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), targetPos.toList(), agent.renderer.purple))

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
        if agent.time - flip_status.flipStartedTimer <= 0.10:
            jump = True
        else:
            jump = False
    else:
        jump = True
        flip_status.started = True
        flip_status.flipStartedTimer = agent.time

    if agent.time - flip_status.flipStartedTimer >= 0.15:
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
    #error = f"{str(type(_object))} is not a valid input for 'getLocation' function "
    raise ValueError(f"{str(type(_object))} is not a valid input for 'getLocation' function ")



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

    if abs(math.degrees(angle)) >=90:
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

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), closestBoost.location.toList(),
                                        agent.renderer.yellow))

    return efficientMover(agent, closestBoost.location, agent.maxSpd,boostHunt=False)

def backmanBoostGrabber(agent, stayOnSide = True):
    #minDistance = distance2D(Vector([0, 5100 * sign(agent.team), 200]), agent.ball.location)
    minY = (agent.ball.location[1] +3000*sign(agent.team))*sign(agent.team)
    closestBoost = physicsObject()
    closestBoost.location = Vector([0, 4900 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            if boost.location[1] *sign(agent.team) >= minY:
                if stayOnSide:
                    if len(agent.allies) < 1:
                        if agent.ball.location[0] >= 0:
                            if boost.location[0] < 0:
                                continue

                        else:
                            if agent.ball.location[0] < 0:
                                if boost.location[0] >= 0:
                                    continue

                distance = distance2D(agent.me.location, boost.location)
                localCoords = toLocal(boost.location, agent.me)
                angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
                distance += angle * 5
                if boost.bigBoost:
                    distance = distance *.333
                if distance < bestDistance:
                    bestDistance = distance
                    closestBoost = boost
                    bestAngle = angle

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), closestBoost.location.toList(),
                                        agent.renderer.yellow))


    #return efficientMover(agent, closestBoost.location, agent.maxSpd, boostHunt=False)
    return driveController(agent,closestBoost.location,0.001,expedite=False)

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

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), closestBoost.location.toList(),
                                        agent.renderer.yellow))
    return efficientMover(agent, closestBoost.location, agent.maxSpd,boostHunt=False)

def distance1D(origin,destination,index):
    return abs(getLocation(origin)[index] - getLocation(destination)[index])





def findOppositeSideVector(agent,objVector,antiTarget, desiredBallDistance):
    #angle = math.degrees(angle2(objVector,antiTarget))
    targetDistance = distance2D(objVector, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - objVector).normalize()
    return getLocation(antiTarget) - (oppositeVector.scale(targetDistance + desiredBallDistance))


def findOppositeSide(agent,targetLoc,antiTarget, desiredBallDistance):
    #angle = correctAngle(math.degrees(angle2(targetLoc,antiTarget)))
    targetDistance = distance2D(targetLoc, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - targetLoc).normalize()
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
            agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), center,
                                                agent.renderer.blue))
            if distance2D(agent.me.location,rendevouz) > 500:
                return efficientMover(agent, rendevouz, maxPossibleSpeed,boostHunt=True)
            else:
                return efficientMover(agent,rendevouz,50,boostHunt=True)

    else:
        centerField = Vector([0,agent.ball.location[1] + 3000*sign(agent.team),0])
        if agent.me.boostLevel < 50:
            return saferBoostGrabber(agent)
        else:
            agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), centerField.toList(),
                                                agent.renderer.blue))
            return efficientMover(agent, centerField, maxPossibleSpeed,boostHunt=True)


def secondManSupport(agent):
    defendTarget = Vector([0, 5120 * sign(agent.team), 200])
    if agent.me.boostLevel < 50:
        return saferBoostGrabber(agent)

    destination = findOppositeSide(agent,agent.ball.location,defendTarget,-100)
    destination.data[1] += sign(agent.team)*1200
    destination.data[2] = 75
    placeVecWithinArena(destination)
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), destination.toList(),
                                        agent.renderer.green))

    return efficientMover(agent,destination,maxPossibleSpeed,boostHunt=True)

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

def find_L_distance(groundVector,wallVector):
    groundedWallSpot = Vector([wallVector.data[0],wallVector.data[1],0])
    return distance2D(groundVector,groundedWallSpot)+findDistance(groundedWallSpot,wallVector)

def ShellTime(agent):
    defendTarget = Vector([0, 5500 * sign(agent.team), 200])
    attackTarget = Vector([0, 5200 * -sign(agent.team), 200])
    rush = False

    targetVec = agent.currentHit.pred_vector

    defensiveRange = 300

    maxRange = 1200
    if agent.contested:
        maxRange = 400
        #attackTarget[0] = targetVec[0]

    goalDistance = distance2D(targetVec, defendTarget)
    carDistance = distance2D(agent.me.location, defendTarget)
    ballGoalDistance = distance2D(agent.ball.location,defendTarget)
    targDistance = distance2D(agent.me.location,targetVec)
    dist3D = findDistance(agent.me.location,targetVec)
    expedite = False
    flippant = False
    if ballGoalDistance+defensiveRange < carDistance:
        rightPost = Vector([900, 5000 * sign(agent.team), 200])
        leftPost = Vector([-900, 5000 * sign(agent.team), 200])
        if distance2D(agent.me.location,rightPost) < distance2D(agent.me.location,leftPost):
            post = rightPost
        else:
            post = leftPost

        if distance2D(targetVec,post)+defensiveRange < distance2D(agent.me.location,post):
            return driveController(agent, post, 0.0001, expedite=True)




    if agent.currentHit.hit_type == 1:
        return handleBounceShot(agent, waitForShot=False)

    #print(f"in here! {agent.time}")

    localPos = toLocal(targetVec, agent.me)
    angleDegrees = correctAngle(math.degrees(math.atan2(localPos[1], localPos[0])))
    moddedOffset = False

    if abs(angleDegrees) <= 40:
        carOffset = agent.carLength *.6
    elif abs(angleDegrees) >= 140:
        carOffset = agent.carLength *.25
    else:
        carOffset = agent.carWidth*.4

    #ballOffset = 92.5 + clamp(15, 0, targetVec[2] - 92.5)
    ballOffset = 90
    totalOffset = carOffset + ballOffset
    adjustedOffset = totalOffset*1
    totalOffset*=.9
    positioningOffset = totalOffset
    destination = None
    moddedOffset = False


    # if carDistance < goalDistance:
    #     if agent.contested:
    #         if agent.enemyAttacking:
    #             if agent.ballDelay - agent.enemyBallInterceptDelay < 0:
    #                 if agent.currentHit.pred_vector[2] <= agent.groundCutOff:
    #                     if agent.team == 0:
    #                         #return groundTackler(agent)
    #                         pass


    goalSpot, ballGoalAngle = goal_selector(agent, mode=0)


        #totalOffset = positioningOffset

    if distance2D(attackTarget,targetVec) <5000:
        #positioningOffset = 0
        futurePos = agent.me.location + (agent.me.velocity.scale(agent.ballDelay))
        fpos_pred_distance = distance2D(futurePos, targetVec)
        shotViable = False
        targLocal = toLocal(targetVec,agent.me)
        targAngle = math.degrees(math.atan2(targLocal[1],targLocal[0]))
        targAngle = correctAngle(targAngle)
        if fpos_pred_distance <= adjustedOffset:
            shotViable = True
        shotlimit = 0.85
        if agent.contested:
            shotlimit = 0.65
        if agent.ballDelay <= shotlimit:
            if targDistance < 1500:
                boostHog = False
                if abs(ballGoalAngle) <= 40:
                    if abs(angleDegrees) <= 25:
                        if agent.forward:
                            if agent.currentSpd * agent.ballDelay >= clamp(99999, 0,
                                                                           targDistance - adjustedOffset):
                                if not agent.onWall and agent.onSurface:
                                    if shotViable:
                                        if extendToGoal(agent, targetVec, futurePos):
                                            if fpos_pred_distance >= 75:
                                                destination = attackTarget - direction(attackTarget,targetVec).scale(totalOffset)
                                                positioningOffset = totalOffset
                                                #moddedOffset = False
                                                agent.setPowershot(agent.ballDelay,
                                                                   targetVec)
                                                #destination = targetVec
                                                #print(f"taking a defensive shot at net! {ballGoalAngle}")

    # if not destination:
    #     if (agent.ballDelay  - agent.currentHit.fastestArrival) > 2:
    #         if targDistance > 500:
    #             _direction = direction(attackTarget, targetVec)
    #             positioningOffset = 1000
    #             targetLoc = targetVec - _direction.scale(positioningOffset)
    #             placeVecWithinArena(targetLoc)
    #             print(f"defensive prep shot: {agent.time}")
    #             return prepShot(agent,targetLoc,targetVec)
    if not destination:
        if agent.contested:
            if goalDistance < 5000:
                if not agent.openGoal:
                    _direction = direction(defendTarget, targetVec)
                    positioningOffset = totalOffset * .65
                    destination = targetVec - _direction.scale(positioningOffset)


    if not destination:
        if agent.forward:
            _direction = direction(attackTarget, targetVec)
            positioningOffset = clamp(maxRange, totalOffset*.65, targDistance * .25)
            destination = targetVec - _direction.scale(positioningOffset)
            moddedOffset = True

    if not destination:
        _direction = direction(attackTarget, targetVec)
        positioningOffset = totalOffset * .65
        destination = targetVec - _direction.scale(positioningOffset)
        #moddedOffset = False




    if moddedOffset:
        modifiedDelay = clamp(6, 0, agent.ballDelay - ((positioningOffset) / clamp(maxPossibleSpeed,0.001,agent.currentSpd)))
    else:
        modifiedDelay = agent.ballDelay


    #result = timeDelayedMovement(agent, destination, agent.ballDelay,True)
    result = driveController(agent, destination, agent.time+modifiedDelay,expedite=True,flippant=flippant)

    destination.data[2] = 75
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,
                                        agent.me.location.toList(),
                                        destination.toList(),
                                        agent.renderer.blue))



    return result


def turtleTime(agent):
    goalDistance = distance2D(agent.ball.location,Vector([0, 5100 * sign(agent.team), 200]))
    defendTarget = Vector([0, 5600 * sign(agent.team), 200])
    carToGoalDistance = distance2D(agent.me.location,Vector([0, 5100 * sign(agent.team), 200]))

    if goalDistance - carToGoalDistance > 2000:
        if agent.ballGrounded:
            return lineupShot(agent,1)
        else:
            return handleBounceShot(agent,waitForShot=False)


    targetVec = agent.currentHit.pred_vector

    _enemyInfluenced = True
    if goalDistance < 1300:
        _enemyInfluenced = False

    flipDecider(agent,targetVec,enemyInfluenced= _enemyInfluenced)

    targDistance = distance2D(targetVec,defendTarget)

    if targDistance < 5000:
        if ballHeadedTowardsMyGoal(agent):
            defendTarget, reposition = noOwnGoalDefense(agent,targetVec)
            if reposition:
                agent.renderCalls.append(
                    renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), defendTarget.toList(),
                               agent.renderer.blue))
                placeVecWithinArena(defendTarget)
                return testMover(agent, defendTarget, 2300)
    targ_local = toLocal(targetVec,agent.me)
    goal_local = toLocal(Vector([0, 5100 * sign(agent.team), 200]),agent.me)
    targ_angle = math.degrees(math.atan2(targ_local[1],targ_local[0]))
    goal_angle = math.degrees(math.atan2(goal_local[1],goal_local[0]))

    if abs(targ_angle) > 65 and abs(targ_angle) < 115:
        carOffset = 0
    else:
        carOffset = agent.carLength/2

    distance = distance2D(defendTarget,targetVec)
    oppositeVector = (getLocation(defendTarget) - targetVec).normalize()
    destination =  getLocation(defendTarget) - (oppositeVector.scale(distance - clamp(110,25,25)))
    placeVecWithinArena(destination)
    if goalDistance < carToGoalDistance:
        result = testMover(agent, destination, maxPossibleSpeed)
    else:
        result = timeDelayedMovement(agent, destination, agent.ballDelay,True)

    destination.data[2] = 95
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d,agent.me.location.toList(),destination.toList(),agent.renderer.blue))
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
            if dist <=50 or dist/agent.currentSpd <= jumpTimer :
                if targetVec[2] >200:
                    agent.setJumping(-1)
                elif targetVec[2] > 125:
                    agent.setJumping(0)

    else:
        if pred.game_seconds - agent.gameInfo.seconds_elapsed< jumpTimer :
            if dist <= 50 or dist/agent.currentSpd <= jumpTimer :
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

def ballContested(agent):
    #closestToMe,mDist = findEnemyClosestToLocation(agent,agent.me.location)
    closestToBall, bDist = findEnemyClosestToLocation2D(agent,agent.ball.location)
    if bDist:
        if bDist < agent.contestedThreshold:
            return True
        else:
            return False
    return False

def cornerDetection(_vec):
    #a simple function for determining if a vector is located within the corner of the field
    #if the vector is, will return the corner number, otherwise will return -1
    # 0 = blue right, 1 = blue left, 2 = orange left, 3 = orange right  #perspective from blue goal
    y_value = 3840
    x_value = 2500

    if abs(_vec.data[0]) > x_value and abs(_vec.data[1]) > y_value:
        x = _vec.data[0]
        y = _vec.data[1]

        if x > 0:
            if y > 0:
                return 2
            else:
                return 1
        else:
            if y > 0:
                return 3
            else:
                return 0

    else:
        return -1

def naive_hit_prediction(agent):
    primaryDirection = direction(agent.closestEnemyToBall.location,agent.enemyTargetVec)
    normed = primaryDirection.normalize()
    naivePosition = agent.currentHit.pred_vector + normed.scale(maxPossibleSpeed)
    placeVecWithinArena(naivePosition)
    return naivePosition




def handleBounceShot(agent, waitForShot = True):
    variance = 5
    leftPost = Vector([-sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])
    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector

    if targetVec[2] < agent.groundCutOff:
        return lineupShot(agent,1)

    defensiveTouch = inTheMiddle(targetVec[1], [3500 * sign(agent.team), 5500 * sign(agent.team)])
    ballToGoalDist = distance2D(center,targetVec)
    targDistance = distance2D(agent.me.location,targetVec)
    dist3D = findDistance(agent.me.location,targetVec)

    targetLocal = toLocal(targetVec, agent.me)
    carToTargAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

    ballLocal = agent.ball.local_location
    if abs(carToTargAngle) <=40:
        carOffset = agent.carLength*.66
    elif  abs(carToTargAngle) >=140:
        carOffset = agent.carLength*.33
    else:
        carOffset = agent.carWidth *.5

    totalOffset = (carOffset +93)*.8
    shotViable = False


    futurePos = agent.me.location + (agent.me.velocity.scale(agent.ballDelay))
    fpos_pred_distance = distance2D(futurePos,targetVec)

    if fpos_pred_distance <= totalOffset:
        shotViable = True

    goalSpot,correctedAngle = goal_selector(agent, mode=0)

    if len(agent.allies) < 1:
        if abs(correctedAngle) >= 60:
            if agent.contested or agent.me.boostLevel < 50:
                if not butterZone(targetVec):
                    return playBack(agent)

    rush = False
    ballToGoalDist = distance2D(center,targetVec)
    #waitingShotPosition = None

    _direction = direction(center, targetVec)
    positioningOffset = totalOffset*.9
    waitingShotPosition = targetVec - _direction.scale(totalOffset)
    positioningOffset = totalOffset
    badPosition = targetVec + _direction.scale(totalOffset)

    targetLoc = None
    boostHog = True
    shotlimit = 1
    if agent.contested:
        shotlimit = 0.75



    if agent.ballDelay <= shotlimit:
        if is_in_strike_zone(agent, targetVec):
            go_ahead = False
            if agent.ball.lastToucher == agent.name:
                if agent.ball.lastTouch >= 1:
                    go_ahead = True
            else:
                go_ahead = True
            if go_ahead:
                if targDistance < 1500:
                    boostHog = False
                if abs(carToTargAngle) <= 45:
                    if agent.forward:
                        if agent.currentSpd >= 1500 or ballToGoalDist < 5000:
                            if distance2D(futurePos, waitingShotPosition) < distance2D(futurePos, badPosition):
                                if agent.currentSpd * agent.ballDelay >= clamp(99999,0,targDistance-totalOffset):
                                    if not agent.onWall and agent.onSurface:
                                        if shotViable:
                                            if fpos_pred_distance >= 75:
                                                targetLoc = waitingShotPosition
                                                agent.setPowershot(agent.ballDelay,targetVec)
                                                #print("taking a shot at net!")
                                else:
                                    if not agent.onWall and agent.onSurface:
                                        pass
        if targetLoc == None:
            if agent.contested or agent.goalward:
                if agent.ballDelay < shotlimit:
                    if distance2D(futurePos,waitingShotPosition) < distance2D(futurePos,badPosition):
                        if agent.currentSpd * agent.ballDelay >= clamp(99999, 0, targDistance - totalOffset):
                            if not agent.onWall and agent.onSurface:
                                if shotViable:
                                    targetLoc = waitingShotPosition
                                    agent.setPowershot(agent.ballDelay, targetVec)

    if agent.contested:
        maxRange = 1600
    else:
        maxRange = 800

    modifiedDelay = agent.ballDelay
    if not targetLoc:

        if defensiveTouch:
            myLeftPost = Vector([-sign(agent.team) * 4200, sign(agent.team)*5000, 200])
            myRightPost = Vector([sign(agent.team) * 4200, targetVec[1], 200])
            if distance2D(myLeftPost, targetVec) < distance2D(myRightPost, targetVec):
                defensivePosition = findOppositeSide(agent, targetVec, leftPost, totalOffset)
            else:
                defensivePosition = findOppositeSide(agent, targetVec, rightPost, totalOffset)
            waitingShotPosition = defensivePosition

        targetLoc = waitingShotPosition

        agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), waitingShotPosition.toList(),
                                            agent.renderer.green))
    #return timeDelayedMovement(agent, targetLoc, agent.ballDelay, boostHog)
    return driveController(agent, targetLoc, agent.time+modifiedDelay,expedite=True)



def playDefensive(agent):
    centerGoal = Vector([0, 5200 * sign(agent.team), 200])
    rightPost = Vector([900, 5200 * sign(agent.team), 200])
    leftPost = Vector([-900, 5200 * sign(agent.team), 200])

    return driveController(agent,centerGoal,0.0001,expedite=True)

def playBack(agent):
    centerField = Vector([agent.ball.location[0], agent.ball.location[1] + 4500 * sign(agent.team), 0])


    boostTarget,dist = boostSwipe(agent)
    if boostTarget != None and dist < 2000:
        return driveController(agent,boostTarget,agent.time,expedite=True)

    if agent.me.boostLevel < 80:
        return backmanBoostGrabber(agent)

    else:
        agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), centerField.toList(),
                                            agent.renderer.blue))
        #return efficientMover(agent, centerField, maxPossibleSpeed, boostHunt=True)
        return driveController(agent,centerField,agent.time,expedite=False)



def scaredyCat(agent):
    centerGoal = Vector([0, 5200 * sign(agent.team), 200])
    hitPrediction = naive_hit_prediction(agent)
    predictionDistance = distance2D(hitPrediction,centerGoal)
    playerDistance = distance2D(agent.me.location,centerGoal)
    if playerDistance < predictionDistance:
        if predictionDistance > 3000:
            if agent.me.boostLevel < 85:
                return backmanBoostGrabber(agent)



    # if playerDistance <= 200:
    #     return turnTowardsPosition(agent,agent.ball.location,3)

    #return driveController(agent,centerGoal,agent.time+ agent.ballDelay,expedite=True)

    if distance2D(agent.closestEnemyToBall.location, centerGoal) > predictionDistance:
        return driveController(agent, hitPrediction, agent.time + (agent.enemyBallInterceptDelay + 0.1), expedite=False)
    else:
        return driveController(agent, centerGoal, agent.time + 1, expedite=False)





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

# def bringToCorner(agent):
#     leftCorner = Vector([-4000,sign(agent.team)*4500,0])
#     rightCorner = Vector([4000,sign(agent.team)*4500,0])
#
#     targVec = convertStructLocationToVector(agent.selectedBallPred)
#     if agent.me.location[0] < targVec[0]:
#         target = rightCorner
#     else:
#         target = leftCorner
#
#     direction = target - targVec
#     newPosition = findOppositeSide(agent,targVec,target,120)
#     print(f"bringing to corner {agent.time}")
#     return timeDelayedMovement(agent,newPosition,agent.ballDelay,False)

def bringToCorner(agent):
    targVec = agent.currentHit.pred_vector
    centerGoal = Vector([0, 5300 * sign(agent.team), 200])
    rightCorner = Vector([-4500, targVec[1], 0])
    leftCorner = Vector([4500, targVec[1], 0])

    targetLocal = toLocal(targVec, agent.me)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

    carToBallAngle = correctAngle(carToBallAngle)

    if abs(carToBallAngle) <= 45:
        carOffset = agent.carLength / 2
    elif abs(carToBallAngle) >= 135:
        carOffset = (agent.carLength / 3) * .5
    else:
        carOffset = (agent.carWidth / 2) * .5

    totalOffset = carOffset+90

    positioningOffset = 0
    #targetWord = "center"
    # if agent.me.location[0] < targVec[0]:
    #     target = rightCorner
    # else:
    #     target = leftCorner
    if targVec[0] > 0:
        target = leftCorner
    else:
        target = rightCorner

    distance = distance2D(agent.me.location,targVec)
    targetLoc = None

    if abs(targVec[0]) >2500 or distance < 500:
        _direction = direction(target, targVec)
        targetLoc = targVec - _direction.scale(totalOffset * .8)
        positioningOffset = totalOffset * .8
        modifiedDelay = agent.ballDelay

    if not targetLoc:
        multiCap = clamp(.5, .25, distance / 10000)
        multi = clamp(multiCap, .15, (5000 - abs(agent.me.location[0])) / 10000)
        _direction = direction(target, targVec)
        positioningOffset = clamp(1000, carOffset,distance * multi)
        targetLoc = targVec - _direction.scale(positioningOffset)
        modifiedDelay = clamp(6, 0, agent.ballDelay - (positioningOffset / agent.currentSpd))

    return driveController(agent, targetLoc, agent.time+modifiedDelay, expedite=True,flippant=True)

def defensiveManuevering(agent):
    pass

def shadowDefense(agent):
    myGoal = Vector([0, 5200 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector

    distanceFromGoal = distance2D(targetVec,myGoal)

    _direction = direction(myGoal,targetVec)
    destination = myGoal-_direction.scale(distanceFromGoal*.5)

    return driveController(agent,destination,agent.time+agent.ballDelay,expedite=False)


def prepShot(agent,position,targetPosition):
    distanceFromPosition = distance2D(agent.me.location,position)
    #print(f"setting up shot: {agent.time}")
    #if distanceFromPosition > 100:
    return driveController(agent,position,agent.time,expedite = False,flippant=False)
    #else:
        # return turnTowardsPosition(agent,targetPosition,1)



def groundTackler(agent):
    center = Vector([0, 5500 * sign(agent.team), 200])
    target = agent.currentHit.pred_vector
    targetLocal = toLocal(target, agent.me)
    targDist = distance2D(agent.me.location,target)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))



    if abs(carToBallAngle) <=40:
        carOffset = agent.carLength*.6
    elif abs(carToBallAngle) >= 140:
        carOffset = agent.carLength*.2
    else:
        carOffset = agent.carWidth*.4

    ballOffset = 90
    totalOffset = (carOffset+ballOffset)*.8

    futurePos = agent.me.location + (agent.me.velocity.scale(agent.ballDelay))
    fpos_pred_distance = distance2D(futurePos, target)
    shotViable = False
    if fpos_pred_distance <= totalOffset:
        shotViable = True

    _direction = direction(target,center)

    targetLoc = target - _direction.scale(totalOffset*.5)

    if shotViable:
        if agent.enemyBallInterceptDelay < .3:
            agent.setJumping(6,target = agent.enemyTargetVec)
            print(f"ground tacking! {agent.time}")
    return driveController(agent,targetLoc,agent.time+agent.enemyBallInterceptDelay,expedite = True)





def lineupShot(agent,multi):
    variance = 5

    leftPost = Vector([-sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])

    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector

    if targetVec[2] > agent.groundCutOff:
        return handleBounceShot(agent)

    # if ballHeadedTowardsMyGoal(agent):
    #     return ShellTime(agent)


    distance = distance2D(agent.me.location, targetVec)
    dist3D = findDistance(agent.me.location, targetVec)
    goalDist = distance2D(center, targetVec)
    ballToGoalDist = distance2D(targetVec, center)
    targetLocal = toLocal(targetVec,agent.me)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1],targetLocal[0]))
    carToGoalDistance = distance2D(center,agent.me.location)
    carToBallDistance = distance2D(targetVec,agent.me.location)


    carToBallAngle = correctAngle(carToBallAngle)

    goalSpot,correctedAngle = goal_selector(agent, mode=1)

    if len(agent.allies) < 1 or agent.me.boostLevel < 1:
        if abs(correctedAngle) >= 60:
            if agent.contested:
                if not butterZone(targetVec):
                    return playBack(agent)


    targetLoc = None
    rush = False
    ballOffset = 93


    if abs(carToBallAngle) <=40:
        carOffset = agent.carLength*.666
    elif abs(carToBallAngle) >= 140:
        carOffset = agent.carLength*.3
    else:
        carOffset = agent.carWidth *.45

    positioningOffset = 50
    shotOffset = carOffset+ballOffset
    ballOffset -= clamp(25, 0, targetVec[2] - 92.5)
    totalOffset = carOffset + ballOffset
    #futurePos = agent.me.location + agent.me.velocity.scale(agent.ballDelay)
    futurePos = agent.me.location + agent.me.velocity.scale(agent.ballDelay)
    fpos_pred_distance = distance2D(futurePos, targetVec)
    shotViable = False
    adjustedOffset = carOffset + ballOffset
    if fpos_pred_distance <= adjustedOffset:
        shotViable = True
    shotlimit = .9
    maxRange = 1600
    if agent.contested:
        shotlimit = 0.65
        #if not agent.openGoal:
        maxRange = 800

    if agent.ballDelay <= shotlimit:
        go_ahead = True

        if agent.me.boostLevel > 0:
            go_ahead = False

        if go_ahead:
            if abs(correctedAngle) <= 35:
                if agent.forward and abs(carToBallAngle) <= 25 or not agent.forward and abs(carToBallAngle) >= 155:
                    # if agent.forward:
                    if agent.contested:
                        if agent.currentSpd >= 1500 or ballToGoalDist < 5000:
                            if agent.currentSpd * agent.ballDelay >= clamp(99999, 0, carToBallDistance - shotOffset):
                                if not agent.onWall and agent.onSurface:
                                    if shotViable:
                                        if fpos_pred_distance >= 75:
                                            if extendToGoal(agent,targetVec,futurePos):
                                                agent.setPowershot(agent.ballDelay, targetVec)
                                                _direction = direction(goalSpot, targetVec)
                                                positioningOffset = totalOffset * .8
                                                targetLoc = targetVec - _direction.scale(positioningOffset)

                                                modifiedDelay = agent.ballDelay


    blocking = False

    #if distance < 800:

    # if (agent.ballDelay  - agent.currentHit.fastestArrival) > 1.5:
    #     if distance > 500:
    #         _direction = direction(goalSpot, targetVec)
    #         positioningOffset = 1.5*1000
    #         targetLoc = targetVec - _direction.scale(positioningOffset)
    #         placeVecWithinArena(targetLoc)
    #         return prepShot(agent,targetLoc,targetVec)


    # if not targetLoc:
    #     if is_in_strike_zone(agent,targetVec):
    #         #print(f"rushing ball {agent.time}")
    #         _direction = direction(center,targetVec)
    #         targetLoc = targetVec - _direction.scale(carOffset)
    #         modifiedDelay = agent.ballDelay

    if not targetLoc:
        if agent.contested:
            if not agent.openGoal:
                _direction = direction(center, targetVec)
                positioningOffset = totalOffset*.6
                targetLoc = targetVec - _direction.scale(positioningOffset)
                modifiedDelay = agent.ballDelay

    # if not targetLoc:
    #     if distance < 500:
    #         _direction = direction(goalSpot, targetVec)
    #         positioningOffset = totalOffset*.5
    #         targetLoc = targetVec - _direction.scale(positioningOffset)
    #         modifiedDelay = agent.ballDelay
    #         #print(f"straight shooting {agent.time}")


    if not targetLoc:
        if not agent.contested:
            if ballToGoalDist < 5000:
                if abs(targetVec[0]) < 3000:
                    _direction = direction(goalSpot, targetVec)
                    positioningOffset = clamp(maxRange, totalOffset*.65, distance*.5)
                    targetLoc = targetVec - _direction.scale(positioningOffset)
                    modifiedDelay = clamp(6, 0.0001, agent.ballDelay - (
                            (positioningOffset) / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)))
                    #print("new-old positioning",agent.time)

    if not targetLoc:
        #if abs(targetVec[0]) < 3500:
        multiCap = clamp(.65, .3, distance / 10000)
        multi = clamp(multiCap, .15, (5000 - abs(agent.me.location[0])) / 10000)
        _direction = direction(goalSpot, targetVec)
        positioningOffset = clamp(maxRange, totalOffset*.65, (distance * multi))
        targetLoc = targetVec - _direction.scale(positioningOffset)
        modifiedDelay = clamp(6, 0.0001, agent.ballDelay - (
                    (positioningOffset) / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)))
    if not targetLoc:
        _direction = direction(goalSpot, targetVec)
        positioningOffset = totalOffset*.6 #clamp(maxRange, totalOffset * .5, (distance * multi))
        #positioningOffset = totalOffset * .25
        targetLoc = targetVec - _direction.scale(positioningOffset)
        modifiedDelay = agent.ballDelay
        print("in here")


    result = driveController(agent,targetLoc,agent.time+modifiedDelay,expedite=True)

    targetLoc.data[2] = 95
    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.me.location.toList(), targetLoc.toList(),
                                        agent.renderer.purple))

    agent.renderCalls.append(renderCall(agent.renderer.draw_line_3d, agent.ball.location.toList(), goalSpot,
                                        agent.renderer.red))
    return result



def maxSpeedAdjustment(agent,target):
    tar_local = toLocal(target,agent.me)
    angle = abs(correctAngle(math.degrees(math.atan2(tar_local[1],tar_local[0]))))
    dist = findDistance(agent.me.location,target)
    distCorrection = dist/300

    if dist >=2000:
        return maxPossibleSpeed

    if abs(angle) <=3:
        return maxPossibleSpeed

    if not agent.forward:
        return maxPossibleSpeed



    cost_inc = maxPossibleSpeed/180
    if dist < 1200:
        cost_inc*=2
    #angle = abs(angle) -10
    angle = abs(angle)
    newSpeed = clamp(maxPossibleSpeed,300,maxPossibleSpeed - (angle*cost_inc))
    #print(f"adjusting speed to {newSpeed}")

    return newSpeed




def extendToGoal(agent,ball_vec,startPos):
    leftPost = Vector([-sign(agent.team) * 750, 5120 * -sign(agent.team), 200])
    centerPost = Vector([0, 5120 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 750, 5120 * -sign(agent.team), 200])
    _direction = direction(ball_vec, startPos)

    distance = distance2D(startPos,centerPost)
    newPos = startPos + _direction.scale(distance)

    if abs(newPos[0]) < 800:
        return True
    else:
        return False




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

    if angles[0]+5 < angles[1] < angles[2]-5:
        return True
    return False



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

def ruleOneCheck(agent):
    if agent.closestEnemyToMeDistance < 200:
        if agent.currentSpd < 100:
            if relativeSpeed(agent.me.velocity,agent.closestEnemyToMe.velocity) < 100:
                return True

    return False

def relativeSpeed(vec_a,vec_b):
    #takes in 2 velocity vectors and returns the relative speed difference
    return (vec_a - vec_b).magnitude()

def dirtyCarryCheck(agent):
    maxRange = 150
    ballRadius = 92.5
    #print("being called")
    if agent.onSurface:
        if abs(agent.ball.location[0]) < 3800:
            if not agent.onWall:
                if agent.touch.player_index == agent.index:
                    if agent.time - agent.touch.time_seconds < 1:
                        if distance2D(agent.me.location,agent.ball.location) <=maxRange:
                            if agent.ball.location[2] >= ballRadius+(agent.carHeight/2) and agent.ball.location[2] < 250:
                                if relativeSpeed(agent.ball.velocity,agent.me.velocity) <=500:
                                    #print("dribbling")
                                    return True
    return False


def catch_ball(agent): #should be called from lineupshot()
    center = Vector([0, 5200 * -sign(agent.team), 200])
    maxOffset = 15

    targetVec = agent.currentHit.pred_vector

    ball_velocity = agent.currentHit.pred
    xOff = clamp(maxOffset,-maxOffset,ball_velocity[0]/10)
    yOff = clamp(maxOffset,-maxOffset,ball_velocity[1]/10)

    _direction = direction(center,targetVec)
    targetLoc = targetVec - _direction.scale(maxOffset)
    destination = targetLoc  + Vector([xOff, yOff, 0])
    return driveController(agent, destination, agent.time+agent.ballDelay, expedite=True)

def bad_angle_relocator(agent,angle,target,target_speed):
    pass
    # targetDistance = distance2D(agent.me.location,target)
    # if targetDistance <= 500 and targetDistance >= 200:
    #     if target_speed <=700 and agent.currentSpd < target_speed*1.5:
    #         if agent.forward:
    #             if abs(angle >45) :
    #                 agent.setJumping(6,target = target)
    #                 print(f"jumping at weird angle: {agent.time}")
    #             else:
    #                 if abs(angle) < 135:
    #                     agent.setJumping(6, target=target)
    #                     print(f"jumping at weird angle: {agent.time}")
def newCarry(agent):
    center = Vector([0, 5500 * -sign(agent.team), 200])
    _direction = direction(agent.ball.location,center)
    directionIncrement = _direction.scale(1/60)

    ballVelocity2D = Vector(agent.ball.velocity.data)
    carVelocity2D = Vector(agent.me.velocity.data)
    relativeVelocity = carVelocity2D - ballVelocity2D

    RV_increment = relativeVelocity.scale(1/60)
    hybridIncrement = RV_increment - directionIncrement

    destination = agent.ball.location + hybridIncrement
    cradled = False
    if agent.touch.player_index == agent.index and findDistance(agent.me.location,agent.ball.location) < 160:
        if agent.ball.location[2] <= 140:
            cradled = True

    flick = False
    if (agent.contested) or agent.closestEnemyToBallDistance <= 600:
        flick = True

    elif distance2D(agent.me.location,center) < 1500:
        flick = True

    if flick and cradled:
        #print("flicking!")
        agent.setJumping(0)

    return driveController(agent,destination,agent.time + (1/60))

    #rel


def carry_flick(agent, cradled = False):
    center = Vector([0, 5500 * -sign(agent.team), 200])
    offsetCap = 35
    minOffset = 8
    if agent.me.boostLevel >=5:
        if agent.forward:
            offsetCap = 45
    flick = False

    availableAccel = getNaturalAcceleration2(agent.currentSpd)
    if agent.me.boostLevel > 5:
        if agent.forward:
            availableAccel+= 991.667

    #print(availableAccel/60)
    #offsetCap = clamp(70,8,availableAccel/60)
    #print(offsetCap)


    targetVec = agent.currentHit.pred_vector

    # targetVec = agent.ball.location + agent.ball.velocity.scale(agent.deltaTime)
    # agent.ballDelay = agent.deltaTime
    #targetVec = agent.ball.location + agent.ball.velocity.scale(agent.deltaTime)


    targetLocal = toLocal(targetVec, agent.me)
    carToBallAngle = correctAngle(math.degrees(math.atan2(targetLocal[1], targetLocal[0])))

    goalTarget,angle = goal_selector(agent, mode = 0)

    goalLocal = toLocal(goalTarget,agent.me)
    goalAngle = math.degrees(math.atan2(goalLocal[1], goalLocal[0]))
    goalAngle = correctAngle(goalAngle)

    if agent.touch.player_index == agent.index and findDistance(agent.me.location,agent.ball.location) < 160:
        if agent.ball.location[2] <= 140:
            cradled = True

    #print(f"cradled: {cradled} {agent.time}")
    if agent.enemyBallInterceptDelay <= .5 or agent.closestEnemyToBallDistance <= 600:
        flick = True

    offset = clamp(offsetCap,minOffset,((abs(carToBallAngle)+abs(goalAngle))/2)*16)
    if distance2D(agent.me.location,center) < 1000:
        if not flick:
            offset = 90
            #print("exagerating offset")

    targetLoc = findOppositeSide(agent, targetVec, goalTarget, offset)

    if flick and cradled:
        #print("flicking!")
        agent.setJumping(0)
    #print("we dribbling!")
    #return timeDelayedMovement(agent,targetLoc,agent.ballDelay,False)
    #print(f"in carry {agent.time}")
    return driveController(agent, targetLoc, agent.time+agent.ballDelay,expedite=True)
    #return driveController(agent, targetLoc, agent.time + 1/30, expedite=True)

def inTheMiddle(testNumber,guardNumbersList):
    return min(guardNumbersList) <= testNumber <= max(guardNumbersList)

def handleWallShot(agent):
    enemyGoal = Vector([0,-sign(agent.team)*5200,1500])
    myGoal = enemyGoal = Vector([0,sign(agent.team)*5200,500])
    targetVec = agent.currentHit.pred_vector
    destination = None
    wall = which_wall(targetVec)
    if wall == 0 or wall == 2:
        _direction = (myGoal - targetVec).normalize()
        destination = targetVec + _direction.scale(100)

    if not destination:
        _direction = (enemyGoal - targetVec).normalize()
        destination = targetVec+_direction.scale(100)

    return wallMover(agent,destination,agent.targetDistance/clamp(10,0.0001,agent.ballDelay),agent.ballDelay)

def wallMover(agent,target,targetSpd,arrivalTime):
    target = getLocation(target)
    currentSpd = agent.currentSpd
    controller_state = SimpleControllerState()
    controller_state.throttle = 1
    if targetSpd > maxPossibleSpeed:
        targetSpd = maxPossibleSpeed
    jumpingDown = False

    #print(f"in here {agent.time}")
    intersection,wall = guided_find_wall_intesection(agent, target)
    #intersection,wall = find_wall_intersection(agent.me, target)  #0 = orange backboard, 1 = east wall, 2 = blue backboard, 3 = west wall
    placeVecWithinArena(target)
    if not agent.onWall and agent.wallShot:
        needsIntersection = True
        if wall == 0:
            if agent.me.location[1] < intersection[1]:
                needsIntersection = False
        elif wall == 1:
            if agent.me.location[0] > intersection[0]:
                needsIntersection = False
        elif wall == 2:
            if agent.me.location[1] > intersection[1]:
                needsIntersection = False
        elif wall == 3:
            if agent.me.location[0] < intersection[0]:
                needsIntersection = False


        if needsIntersection:
            #return efficientMover(agent,intersection,targetSpd,boostHunt=False)
            return driveController(agent,intersection,agent.time+(arrivalTime-agent.time)/2, expedite = True)

    elif agent.onWall and not agent.wallShot:
        jumpingDown = True
        target = intersection
        intersection.data[2] = 0

    location = toLocal(target, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    angle_degrees = correctAngle(math.degrees(angle_to_target))
    _distance = agent.targetDistance
    #print(_distance)
    createTriangle(agent, target)
    steering, slide = rockSteer(angle_to_target, _distance)
    if slide:
        if abs(agent.me.avelocity[2]) < 1:
            slide = False

    if abs(steering) >= .95:
        optimalSpd = maxSpeedAdjustment(agent, target)

        if targetSpd > optimalSpd:
            targetSpd = optimalSpd

    targetSpd = clamp(2200, 0, math.ceil(targetSpd))

    if targetSpd > currentSpd:
        if agent.onSurface and not slide:
            if targetSpd > 1050 and (currentSpd < maxPossibleSpeed and clamp(2200,currentSpd,currentSpd+agent.accelerationTick*6) <= targetSpd):
                controller_state.boost = True
    elif targetSpd < currentSpd and (targetSpd < 2200 and currentSpd >2200):
        #if agent.getActiveState() != 3:
        controller_state.throttle = -1
    controller_state.steer = steering
    if jumpingDown:
        if abs(correctAngle(math.degrees(angle_to_target))) < 5:
            if agent.me.location[2] >=250:
                agent.setJumping(2)
                #print("jumping off wall")

    return controller_state

def decelerationSim(agent,timeAlloted):
    increment = 525 * agent.fakeDeltaTime
    currentSpeed = agent.currentSpd
    distance = 0
    while timeAlloted > 0:
        timeAlloted -= agent.fakeDeltaTime
        currentSpeed -= increment
        distance+= currentSpeed*agent.fakeDeltaTime
    return distance

"""
def efficientMover(agent,target_object,target_speed,boostHunt = False):
    if agent.onWall:
        return wallMover(agent, target_object, target_speed)

    controller_state = SimpleControllerState()
    originalTarget = target_object

    createTriangle(agent, target_object)
    placeVecWithinArena(originalTarget)
    placeVecWithinArena(target_object)
    location = toLocal(target_object, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    _distance = distance2D(agent.me, target_object)
    _angle = math.degrees(angle_to_target)


    current_speed = agent.currentSpd
    if not agent.forward:
        controller_state.throttle = -1

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
    if _distance < 350:
        if agent.currentSpd < 600:

            if agent.forward:
                if abs(_angle) >=65:

                    #print(f"turning {agent.time}")
                    return turnTowardsPosition(agent,target_object,2)

    if len(agent.allies) >= 1:
        steerDirection, slideBool = newSteer(angle_to_target)
    else:
        steerDirection, slideBool = rockSteer(angle_to_target,_distance)

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
                            if o_dist > clamp(2300,current_speed,current_speed+500)*2.1:
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
"""


def driveController(agent,target,arrivalTime, expedite = False, flippant = False):
    tta = clamp(6,0.001,arrivalTime - agent.time)
    _distance = distance2D(agent.me.location,target)
    idealSpeed = clamp(2200,0,math.ceil(_distance/tta))
    if agent.onWall:
        return wallMover(agent,target,idealSpeed,arrivalTime)
    placeVecWithinArena(target)

    localTarget = toLocal(target, agent.me)
    angle = math.atan2(localTarget[1], localTarget[0])
    angle_degrees = correctAngle(math.degrees(angle))

    createTriangle(agent, target)
    if ruleOneCheck(agent):
        agent.setJumping(6,target = target)
        #print("breaking rule #1")

    if agent.forward:
        throttle = 1
    else:
        throttle = -1
        oldAngle = angle_degrees
        angle_degrees -= 180
        angle_degrees = correctAngle(angle_degrees)

        angle_to_target = math.radians(angle)
        if agent.onSurface:
            if _distance > 1000:
                if abs(angle_degrees) <= 10:
                    agent.setHalfFlip()

    boost = False
    steer, handbrake = rockSteer(angle, _distance,modifier=700)

    # if _distance < 300 and _distance > 40:
    #     if agent.currentSpd < 600:
    #         if abs(angle_degrees) > 45 and abs(angle_degrees) < 135:
    #             if not agent.dribbling:
    #                 agent.setJumping(6,target = target)

    if abs(steer) > 0.9:
        idealSpeed = maxSpeedAdjustment(agent,target)

    idealSpeed = clamp(2200,0,math.ceil(idealSpeed))

    if agent.currentSpd > idealSpeed and (agent.currentSpd < 2200 and idealSpeed < 2200):

        if _distance > 200:
            if decelerationSim(agent,tta):
                throttle = 0
            else:
                if agent.forward:
                    throttle = -1
                else:
                    throttle = 1

        if agent.forward:
            throttle = -1
        else:
            throttle = 1

    elif agent.currentSpd < idealSpeed:
        if idealSpeed > agent.currentSpd + agent.accelerationTick*6 or idealSpeed >= 2200:
            if agent.onSurface:
                if expedite:
                    if not agent.superSonic:
                        if agent.forward:
                            boost = True

        if agent.currentSpd > 1050:
            if _distance > clamp(maxPossibleSpeed,agent.currentSpd,agent.currentSpd+500)*2.3 or (agent.me.boostLevel <=1 and flippant):
                if abs(angle_degrees) <= clamp(5, 0, _distance / 1000):
                    if agent.onSurface:
                        if agent.forward:
                            agent.setJumping(1)
                        else:
                            agent.setJumping(3)


    if handbrake:
        if abs(agent.me.avelocity[2]) < 1:
            handbrake = False
        boost = False


    controler = SimpleControllerState()
    controler.steer = steer
    controler.throttle = throttle
    controler.handbrake = handbrake
    controler.boost = boost

    return controler

def testMover(agent, target_object,targetSpd):
    if agent.onWall:
        return wallMover(agent,target_object,targetSpd)
    if targetSpd > maxPossibleSpeed:
        targetSpd = maxPossibleSpeed

    #print(f"test mover called {agent.time}")
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

    if _distance < 350:
        if agent.currentSpd < 600:

            if agent.forward:
                if abs(angle_degrees) >=65:
                    pass
                    #print(f"turning {agent.time}")
                    #return turnTowardsPosition(agent,target_object,2)

    createTriangle(agent, target_object)

    if len(agent.allies) >= 1:
        steering, slide = newSteer(angle_to_target)
    else:
        steering, slide = rockSteer(angle_to_target,_distance)

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
            if targetSpd > 1400 and currentSpd < maxPossibleSpeed-50:
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
        if _distance > clamp(2300,1400,currentSpd+500)*2.2:
            if agent.onSurface:
                if not agent.onWall:
                    if currentSpd < targetSpd:
                            maxAngle = 3 + clamp(2,0,_distance/1000)
                            if abs(angle_degrees) < maxAngle:
                                    agent.setJumping(1)

    return controller_state


def timeDelayedMovement(agent,targetVec,delay,boostHungry):
    arrivalEstimate = inaccurateArrivalEstimator(agent, targetVec)

    if arrivalEstimate >= delay:
        return testMover(agent, targetVec, maxPossibleSpeed)

    else:
        distance = clamp(999999,0.00001,distance2D(agent.me.location,targetVec))
        speed = distance/delay

    return efficientMover(agent, targetVec, speed,boostHunt=boostHungry)



def efficientMover(agent,target_object,target_speed,boostHunt = False):
    if agent.onWall:
        return wallMover(agent, target_object, target_speed)

    controller_state = SimpleControllerState()
    originalTarget = target_object

    createTriangle(agent, target_object)
    placeVecWithinArena(originalTarget)
    placeVecWithinArena(target_object)
    location = toLocal(target_object, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    _distance = distance2D(agent.me, target_object)
    _angle = math.degrees(angle_to_target)


    current_speed = agent.currentSpd
    if not agent.forward:
        controller_state.throttle = -1

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
    if _distance < 350:
        if agent.currentSpd < 600:

            if agent.forward:
                if abs(_angle) >=65:
                    pass
                    #print(f"turning {agent.time}")
                    #return turnTowardsPosition(agent,target_object,2)

    if len(agent.allies) >= 1:
        steerDirection, slideBool = newSteer(angle_to_target)
    else:
        steerDirection, slideBool = rockSteer(angle_to_target,_distance)

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
                            if o_dist > clamp(2300,current_speed,current_speed+500)*2.1:
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


def rockSteer(angle,distance,forward = True, modifier = 500):
    turn = Gsteer(angle)
    slide = False
    distanceMod = clamp(10,.3,distance/500)
    if forward:
        _angle = correctAngle(math.degrees(angle))
    else:
        _angle = correctAngle(math.degrees(angle)-180)


    adjustedAngle = _angle/distanceMod
    if abs(turn) >=1:
        if abs(adjustedAngle) > 100:
            slide = True

    return turn,slide


def greedyMover(agent,target_object):
    controller_state = SimpleControllerState()
    controller_state.handbrake = False
    location = toLocal(target_object, agent.me)
    angle = math.atan2(location.data[1], location.data[0])
    controller_state.throttle = 1
    if getVelocity(agent.me.velocity) < maxPossibleSpeed:
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

def isBallNearWall(ballstruct, defaultDistance = 120):
    if ballstruct.physics.location.x > 4096 - defaultDistance:
        return True
    if ballstruct.physics.location.x < -4096 + defaultDistance:
        return True

    if ballstruct.physics.location.y < -5120 + defaultDistance:
        if abs(ballstruct.physics.location.x) > 950:
            return True

    if ballstruct.physics.location.y > 5120 - defaultDistance:
        if abs(ballstruct.physics.location.x) > 950:
            return True
    return False


def isBallHittable(ballStruct,agent,maxHeight):
    #multi = clamp(3, 1, len(agent.allies)+1)
    offset = (agent.carHeight+93)*.9
    if agent.wallShotsEnabled:
        multi = 20
    else:
        multi = 1
    if ballStruct.physics.location.z<= maxHeight:
        return True
    if ballStruct.physics.location.x > 4096 - offset:
        if ballStruct.physics.location.z <= 200*multi:
            return True
    if ballStruct.physics.location.x < -4096 + offset:
        if ballStruct.physics.location.z <= 200*multi:
            return True

    if ballStruct.physics.location.y < -5120 + offset:
        if ballStruct.physics.location.z <= 200*multi:
            if abs(ballStruct.physics.location.x) > 900:
                if len(agent.allies) > 0:
                    return True
    if ballStruct.physics.location.y > 5120 - offset:
        if ballStruct.physics.location.z <= 200*multi:
            if abs(ballStruct.physics.location.x) > 900:
                if len(agent.allies) > 0:
                    return True
    return False

def turnTowardsPosition(agent,targetPosition,threshold):
    localTarg = toLocal(targetPosition,agent.me)
    localAngle = correctAngle(math.degrees(math.atan2(localTarg[1],localTarg[0])))
    controls = SimpleControllerState()
    #print("ttp being called")

    if abs(localAngle) > threshold:
        if agent.forward:
            if localAngle > 0:
                controls.steer = 1
            else:
                controls.steer = -1

            controls.handbrake = True
            if agent.currentSpd <250:
                controls.throttle = 1
            else:
                controls.throttle = -1
        else:
            if localAngle > 0:
                controls.steer = -1
            else:
                controls.steer = 1
            controls.handbrake = True
            if agent.currentSpd <250:
                controls.throttle = -1
            else:
                controls.throttle = 1

    return controls


def findSoonestBallTouchable(agent):
    if agent.ballPred != None:
        bestStruct = agent.ballPred.slices[359]
        quickest = 99999999
        spd = clamp(maxPossibleSpeed, 300, abs(agent.currentSpd))

        if agent.ballPred is not None:
            for i in range(0, agent.ballPred.num_slices):
                if agent.ballPred.slices[i].physics.location.z <= 155:
                    distance = distance2D(agent.me.location, Vector([agent.ballPred.slices[i].physics.location.x,
                                                                     agent.ballPred.slices[i].physics.location.y,
                                                                     agent.ballPred.slices[i].physics.location.z]))
                    adjustedSpd = clamp(maxPossibleSpeed,spd, spd+ distance * .5)
                    timeEstimate = distance / adjustedSpd
                    if timeEstimate < quickest:
                        bestStruct = agent.ballPred.slices[i]
                        quickest = timeEstimate
            return bestStruct

    return None

def isBallGrounded(agent,heightMax,frameMin):
    if agent.ballPred is not None:
        for i in range(0, frameMin):
            if agent.ballPred.slices[i].physics.location.z > heightMax:
                return False
        return True
    return False

def findAerialTargets(agent):
    heightMin = 300
    applicableStructs = []
    aerialTarget = None
    if agent.me.boostLevel >=10:
        for i in range(0, agent.ballPred.num_slices):
            if agent.ballPred.slices[i].physics.location.z >= heightMin:
                #if agent.me.location[2]*sign(agent.team) > agent.ballPred.slices[i].physics.location.z*sign(agent.team):
                applicableStructs.append(agent.ballPred.slices[i])
            else:
                break

    return applicableStructs





# def findSuitableBallPosition2(agent, heightMax, speed, origin):
#     applicableStructs = []
#     spd = clamp(2300,300,speed)
#     ballInGoal = None
#     goalTimer = math.inf
#     if agent.ballPred is not None:
#         for i in range(0, agent.ballPred.num_slices):
#             if isBallHittable(agent.ballPred.slices[i],agent,heightMax):
#                 applicableStructs.append(agent.ballPred.slices[i])
#                 if agent.team == 0:
#                     if agent.ballPred.slices[i].physics.location.y <= -5250:
#                         ballInGoal = agent.ballPred.slices[i]
#                         goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
#                         break
#                 else:
#                     if agent.ballPred.slices[i].physics.location.y >= 5250:
#                         ballInGoal = agent.ballPred.slices[i]
#                         goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
#                         break
#     targets = []
#     for pred in applicableStructs:
#         distance = distance2D(Vector([pred.physics.location.x,pred.physics.location.y]),origin)
#         timeToTarget = inaccurateArrivalEstimator(agent,Vector([pred.physics.location.x,pred.physics.location.y,pred.physics.location.z]))
#         if timeToTarget < (pred.game_seconds - agent.gameInfo.seconds_elapsed):
#             if goalTimer < pred.game_seconds - agent.gameInfo.seconds_elapsed:
#                 agent.goalPred = ballInGoal
#             targets.append(pred)
#
#     if len(targets) < 2 and len(targets) > 0:
#         return targets[0]
#     elif len(targets) >=2:
#         return targets[int(len(targets)/2)]
#
#
#     if goalTimer < math.inf:
#         agent.goalPred = ballInGoal
#     return agent.ballPred.slices[-1]

def find_soonest_hit(agent):
    lowest = math.inf
    best = None

    for hit in agent.hits:
        if hit != None:
            if hit.prediction_time < lowest:
                best = hit

    return best

def find_ball_pred_by_time(agent,time):
    for i in range(0, agent.ballPred.num_slices):
        if agent.ballPred.slices[i].game_seconds == time:
            return agent.ballPred.slices[i]

    #print("didn't find right prediction")
    return agent.ballPred.slices[0]

def findEnemyHits(agent):
    enemyOnWall = False
    enemyInAir = False
    enemyOnGround= True
    enemyTarget = None
    found = False

    if agent.closestEnemyToBall.onSurface:
        if agent.closestEnemyToBall.location[2] > 100:
            enemyOnWall = True
            #enemyOnGround = False
        else:
            enemyOnGround = True
    else:
        if agent.closestEnemyToBall.boostLevel >= 5:
            if agent.closestEnemyToBall.location[2] > 300:
                enemyInAir = True
        else:
            enemyInAir = False
    if enemyInAir:
        enemyOnGround = True
        enemyInAir = False
    for i in range(0, agent.ballPred.num_slices):
        if i % 5 != 0:
            continue
        # if i % fifth == 0:
        #     yield

        pred = agent.ballPred.slices[i]
        location = convertStructLocationToVector(pred)

        if enemyOnWall:
            if isBallNearWall(pred):
                timeToTarget, distance =  enemyWallMovementEstimator(agent.closestEnemyToBall,location, agent)
                if timeToTarget < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                    agent.enemyBallInterceptDelay = pred.game_seconds - agent.gameInfo.seconds_elapsed
                    agent.enemyTargetVec = location
                    found = True
                    agent.enemyPredTime = pred.game_seconds
                    #print(f"enemy on wall {timeToTarget}")
                    break

        if enemyOnGround:
            if location[2] > 300:
                continue
            else:
                timeToTarget = enemyArrivalEstimator(agent, location)
                if timeToTarget <= pred.game_seconds - agent.gameInfo.seconds_elapsed:
                    agent.enemyBallInterceptDelay = pred.game_seconds - agent.gameInfo.seconds_elapsed
                    agent.enemyTargetVec = location
                    found = True
                    agent.enemyPredTime = pred.game_seconds
                    #print(f"enemy Delay: {agent.enemyBallInterceptDelay}, my Delay: {agent.ballDelay} || {agent.contested}  ||  {agent.timid}")
                    break

        if enemyInAir:
            pass #do air stuffs!

    if not found:
        agent.enemyBallInterceptDelay = 10
        agent.enemyTargetVec = location
        agent.enemyPredTime = agent.time+10
    #print("got here")











def findHits(agent, grounder_cutoff, jumpshot_cutoff):
    ground_shot = None
    jumpshot = None
    wall_shot = None
    ballInGoal = None
    catchCanidate = None

    for i in range(0, agent.ballPred.num_slices):
        if i > 60 and i%3 != 0:
            continue
        pred = agent.ballPred.slices[i]
        grounder = False
        if ground_shot == None or wallshot == None:
            if isBallHittable(pred, agent, grounder_cutoff):
                wallshot = isBallNearWall(pred)
                if not wallshot:
                    grounder = True
                    if ground_shot == None:
                        distance = distance2D(Vector([pred.physics.location.x, pred.physics.location.y]), agent.me.location)
                        # timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                        #     [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]),offset = 93)
                        timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                            [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]))
                        if timeToTarget < pred.game_seconds-agent.gameInfo.seconds_elapsed:
                            ground_shot = hit(agent.time,pred.game_seconds ,0,convertStructLocationToVector(pred),convertStructVelocityToVector(pred),True,timeToTarget)
                else:
                    if wall_shot == None:
                        if agent.onWall and wallshot:
                            distance = findDistance(agent.me.location, convertStructLocationToVector(pred))
                            # timeToTarget = inaccurateArrivalEstimator(agent, convertStructLocationToVector(pred),offset = 93)
                            timeToTarget = inaccurateArrivalEstimator(agent, convertStructLocationToVector(pred))

                            if timeToTarget < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                                wall_shot = hit(agent.time, pred.game_seconds, 2,
                                                  convertStructLocationToVector(pred),convertStructVelocityToVector(pred), True,timeToTarget)
                                agent.targetDistance = distance
                                agent.timeEstimate = timeToTarget

                        else:
                            if wallshot:
                                timeToTarget, distance = new_ground_wall_estimator(agent,
                                                                                   convertStructLocationToVector(pred))
                                if timeToTarget < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                                    wall_shot = hit(agent.time, pred.game_seconds, 2,
                                                    convertStructLocationToVector(pred),convertStructVelocityToVector(pred), True,timeToTarget)
                                    agent.targetDistance = distance
                                    agent.timeEstimate = timeToTarget



        if jumpshot == None:
            if not grounder:
                if isBallHittable(agent.ballPred.slices[i], agent, jumpshot_cutoff):
                    distance = distance2D(Vector([pred.physics.location.x, pred.physics.location.y]),
                                          agent.me.location)
                    # timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                    #     [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]),offset = 93)
                    timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                        [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]))
                    tth = pred.game_seconds - agent.gameInfo.seconds_elapsed
                    if timeToTarget < tth and tth > (pred.physics.location.z-agent.groundCutOff)*agent.heightIncrement:
                        jumpshot = hit(agent.time, pred.game_seconds, 1,
                                          convertStructLocationToVector(pred),convertStructVelocityToVector(pred), True,timeToTarget)

        if catchCanidate == None:
            pass

        if abs(pred.physics.location.y) >= 5250:
            timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]))

            if agent.ballPred.slices[i].physics.location.z <= grounder_cutoff:
                if ground_shot == None:
                    ground_shot = hit(agent.time,agent.ballPred.slices[i].game_seconds ,0,convertStructLocationToVector(agent.ballPred.slices[i]),convertStructVelocityToVector(agent.ballPred.slices[i]),False,timeToTarget)

            else:
                if jumpshot == None:
                    jumpshot = hit(agent.time, agent.ballPred.slices[i].game_seconds, 1,
                                      convertStructLocationToVector(agent.ballPred.slices[i]),convertStructVelocityToVector(agent.ballPred.slices[i]),False,timeToTarget)
            ballInGoal = agent.ballPred.slices[i]

            return ground_shot,jumpshot,wall_shot

    if ground_shot != None and jumpshot != None and wall_shot != None:
        return ground_shot,jumpshot,wall_shot

    if ground_shot == None and jumpshot == None and wall_shot == None:
        ground_shot = hit(agent.time, agent.ballPred.slices[-1].game_seconds, 0,
                       convertStructLocationToVector(agent.ballPred.slices[-1]),convertStructVelocityToVector(agent.ballPred.slices[i]), False,6)

        #print("nothing good to go for")
        agent.timid = True

    return ground_shot, jumpshot, wall_shot




def findSuitableBallPosition(agent, heightMax, speed, origin):
    applicableStructs = []
    spd = clamp(2300,300,speed)
    ballInGoal = None
    goalTimer = math.inf
    if agent.ballPred is not None:
        for i in range(0, agent.ballPred.num_slices,3):
            if isBallHittable(agent.ballPred.slices[i],agent,heightMax):
                applicableStructs.append(agent.ballPred.slices[i])
                if agent.team == 0:
                    if agent.ballPred.slices[i].physics.location.y <= -5250:
                        ballInGoal = agent.ballPred.slices[i]
                        goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
                        break
                else:
                    if agent.ballPred.slices[i].physics.location.y >= 5250:
                        ballInGoal = agent.ballPred.slices[i]
                        goalTimer = agent.ballPred.slices[i].game_seconds - agent.gameInfo.seconds_elapsed
                        break
    agent.wallShot = False
    for pred in applicableStructs:
        wallshot = isBallNearWall(pred)
        if not wallshot:
            distance = distance2D(Vector([pred.physics.location.x,pred.physics.location.y]),origin)
            timeToTarget = inaccurateArrivalEstimator(agent,Vector([pred.physics.location.x,pred.physics.location.y,pred.physics.location.z]))
        else:
            if agent.onWall and wallshot:
                distance = findDistance(agent.me.location,convertStructLocationToVector(pred))
                timeToTarget = inaccurateArrivalEstimator(agent, Vector(
                    [pred.physics.location.x, pred.physics.location.y, pred.physics.location.z]))
            else:
                timeToTarget,distance = new_ground_wall_estimator(agent,convertStructLocationToVector(pred))
                #timeToTarget,distance = groundWallArrivalEstimator(agent,convertStructLocationToVector(pred))

        #adjustSpd = clamp(2300,1000,speed+distance*.7)
        if timeToTarget < (pred.game_seconds - agent.gameInfo.seconds_elapsed):
            if goalTimer < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                agent.goalPred = ballInGoal
            agent.wallShot = False
            if wallshot:
                if pred.physics.location.z > agent.jumpLimit:
                    agent.wallShot = True
                    agent.targetDistance = distance
                    agent.timeEstimate = timeToTarget
            if timeToTarget < goalTimer:
                return pred


    if ballInGoal:
        agent.wallShot = False
        if isBallNearWall(ballInGoal):
            if ballInGoal.physics.location.z > agent.jumpLimit:
                agent.wallShot = True
        return ballInGoal

    if len(applicableStructs) > 0:
        agent.wallShot = False
        if isBallNearWall(applicableStructs[0]):
            if applicableStructs[0].physics.location.z > agent.jumpLimit:
                agent.wallShot = True
        return applicableStructs[0]

    agent.wallShot = isBallNearWall(agent.ballPred.slices[-1])
    return agent.ballPred.slices[-1]

def inaccurateArrivalEstimatorRemote(agent,start,destination):
    distance = clamp(math.inf,1,distance2D(start,destination))
    currentSpd = clamp(2300,1,agent.currentSpd)

    if agent.me.boostLevel > 0:
        maxSpd = clamp(2300,currentSpd,currentSpd+ (distance*.3))
    else:
        maxSpd = clamp(maxPossibleSpeed, currentSpd, currentSpd + (distance*.15))

    return distance/maxSpd

def inaccurateArrivalEstimator(agent,destination, offset = 120):
    distance = clamp(math.inf,0.00001,distance2D(agent.me.location,destination)-offset)
    moreAccurateEstimation = timeWithAccelAgentless(agent.currentSpd,agent.me.boostLevel,distance,agent.fakeDeltaTime,agent.boostConsumptionRate) #calcTimeWithAcceleration(agent,distance)

    #print(f"estimate for reaching distance {distance}: {moreAccurateEstimation}")
    return moreAccurateEstimation


def enemyArrivalEstimator(agent,destination):
    distance = clamp(math.inf, 0.00001, distance2D(agent.closestEnemyToBall.location, destination)-140)
    moreAccurateEstimation = calcEnemyTimeWithAcceleration(agent, distance,agent.closestEnemyToBall)
    return moreAccurateEstimation

def calcEnemyTimeWithAcceleration(agent,distance,enemyPhysicsObject):
    estimatedSpd = abs(enemyPhysicsObject.velocity.magnitude())
    estimatedTime = 0
    distanceTally = 0
    boostAmount = enemyPhysicsObject.boostLevel
    boostingCost = 33.3 * agent.deltaTime
    linearChunk = 1600 / 1410
    #print("enemy started")
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < maxPossibleSpeed:
            acceleration =  getNaturalAcceleration2(estimatedSpd)#getNaturalAcceleration(estimatedSpd) #1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration+=991
                boostAmount -= boostingCost
            if acceleration > 0:
                estimatedSpd += acceleration*agent.deltaTime
            distanceTally+= estimatedSpd*agent.deltaTime
            estimatedTime += agent.deltaTime
        else:
            distanceTally += estimatedSpd * agent.deltaTime
            estimatedTime += agent.deltaTime

    #print("enemy ended")
    return estimatedTime


def which_wall(destination):
    #orange = north
    if destination[1] >= 4900:
        #orange backboard
        return 0
    elif destination[1] < -4900:
        #blue backboard
        return 2
    elif destination[0] < -3900:
        #east wall
        return 1
    else:
        #west wall
        return 3
def guided_find_wall_intesection(agent,destination):
    partDist = findDistance(agent.me.location,destination)/3
    y_intercept = destination[1] + sign(agent.team)*partDist
    if destination[0] > 0:
        x_intercept = destination[0] - partDist
    else:
        x_intercept = destination[0] + partDist

    wall = which_wall(destination)
    if wall == 0:
        intersection = Vector([x_intercept, 5200, 0])
    elif wall == 1:
        intersection = Vector([-4100, y_intercept, 0])
    elif wall == 2:
        intersection = Vector([x_intercept, -5200, 0])
    else:
        intersection = Vector([4100, y_intercept, 0])
    return intersection, wall

def find_wall_intersection(phys_obj,destination):
    y_intercept = (destination.data[1] + phys_obj.location[1])/2
    x_intercept = (destination.data[0] + phys_obj.location[0])/2

    wall = which_wall(destination)
    if wall == 0:
        intersection = Vector([x_intercept,5200,0])
    elif wall == 1:
        intersection = Vector([-4100, y_intercept, 0])
    elif wall == 2:
        intersection = Vector([x_intercept,-5200,0])
    else:
        intersection = Vector([4100, y_intercept, 0])
    return intersection,wall

def enemyWallMovementEstimator(phys_obj,destination, agent):
    intersection = find_wall_intersection(phys_obj, destination)[0]
    _distance = clamp(math.inf,0.0001,findDistance(intersection, phys_obj.location)-140)
    _distance += findDistance(intersection, destination)
    return timeWithAccelAgentless(phys_obj.velocity.magnitude(), phys_obj.boostLevel, _distance, agent.fakeDeltaTime,
                                  agent.boostConsumptionRate), _distance


def new_ground_wall_estimator(agent,destination):
    intersection = guided_find_wall_intesection(agent, destination)[0]
    #intersection = find_wall_intersection(agent.me,destination)[0]
    _distance = findDistance(intersection,agent.me.location)
    _distance+= findDistance(intersection,destination)
    return timeWithAccelAgentless(agent.currentSpd,agent.me.boostLevel,_distance,agent.fakeDeltaTime,agent.boostConsumptionRate),_distance

def groundWallArrivalEstimator(agent,destination):
    if agent.me.location[2] > destination[2]:
        wallVec = agent.me.location
        groundVec = destination
    else:
        wallVec = destination
        groundVec = agent.me.location

    totalDistance = find_L_distance(groundVec,wallVec)
    #return calcTimeWithAcceleration(agent,totalDistance),totalDistance
    return timeWithAccelAgentless(agent.currentSpd,agent.me.boostLevel,totalDistance,agent.fakeDeltaTime,agent.boostConsumptionRate),totalDistance

def lerp(v0, v1, t):  # linear interpolation
  return (1 - t) * v0 + t * v1




#@jit
def getNaturalAcceleration2(currentSpd):
    normalIncrement = 1440/1400
    topIncrement = 160/10

    if currentSpd <= 1400:
        return (1440 - (currentSpd*normalIncrement))+160
    elif currentSpd <= 1410:
        return 160 - ((currentSpd-1400)*topIncrement)
    else:
        return 0

#@jit
def timeWithAccelAgentless(currentSpd,currentBoost,distance,fakeDelta,boostingCost):
    estimatedSpd = currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = currentBoost
    boostingCost = boostingCost
    flipped = False
    while distanceTally < distance and estimatedTime < 7:
        if estimatedSpd < 2200:
            acceleration = getNaturalAcceleration2(estimatedSpd)  # 1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            else:
                if not flipped and (distance - distanceTally) > 1500:
                    flipped = True
                    acceleration += 500
            if acceleration > 0:
                estimatedSpd += acceleration * fakeDelta
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta
        else:
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta

    # print("friendly ended")
    return estimatedTime


def calcTimeWithAcceleration(agent,distance):
    estimatedSpd = agent.currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = agent.me.boostLevel
    boostingCost = 33.3*agent.fakeDeltaTime
    flipped = False
    #linearChunk = 1600/1400
    while distanceTally < distance and estimatedTime < 7:
        if estimatedSpd < 2200:
            acceleration = getNaturalAcceleration(estimatedSpd) #1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration+=991
                boostAmount -= boostingCost
            else:
                if not flipped and (distance-distanceTally) > 1500:
                    flipped = True
                    acceleration += 500
            if acceleration > 0:
                estimatedSpd += acceleration * agent.fakeDeltaTime
            distanceTally+= estimatedSpd*agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime
        else:
            #estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime

    #print("friendly ended")
    return estimatedTime

def calcTimeWithAcceleration_OLD(agent,distance):
    estimatedSpd = agent.currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = agent.me.boostLevel
    boostingCost = 33.3*agent.fakeDeltaTime
    linearChunk = 1600/1400
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < 2200:
            acceleration = 1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration+=991
                boostAmount -= boostingCost
            if acceleration > 0:
                estimatedSpd += acceleration * agent.fakeDeltaTime
            distanceTally+= estimatedSpd*agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime
        else:
            #estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime

    #print("friendly ended")
    return estimatedTime




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
    spd = agent.currentSpd
    spd = clamp(maxPossibleSpeed,1500,spd + spd/(dist/1000))

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
def ballHeadedTowardsMyGoal_testing(agent,hit):
    myGoal = Vector([0, 5100 * sign(agent.team), 200])

    fpos = hit.pred_vector + hit.pred_vel.scale(1/20)

    if distance2D(fpos,myGoal) < distance2D(hit.pred_vector,myGoal):
        return True
    return False

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

def steerPD(angle,rate):
    #baby PD loop that takes an angle to turn and the current rate of turn
    final = ((35*(angle+rate))**3)/10
    return clamp(1,-1,final)

def defaultPD(agent, local, direction = 0):
    #turns car to face a given local coordinate.
    #direction can specify left/right only turns w/ -1/1
    c = SimpleControllerState()
    turn = math.atan2(local.data[1],local.data[0])
    turn = (math.pi * direction) + turn if direction != 0 else turn
    up = matrixDot(agent.me.matrix,Vector([0,0,agent.me.location.data[2]]))
    #up =  agent.me.matrix.dot(Vector3(0,0,agent.me.location[2]))
    temp = [math.atan2(up.data[1],up.data[2]), math.atan2(local.data[2],local.data[0]), turn]
    #temp = [math.atan2(up[1],up[2]), math.atan2(local[2],local[0]), turn]
    target = temp#retargetPD(agent.me.rvel, temp)
    c.steer = steerPD(turn, 0)
    c.yaw = steerPD(target[2],-agent.me.avelocity.data[2]/4)
    c.pitch = steerPD(target[1],agent.me.avelocity.data[1]/4)
    c.roll = steerPD(target[0],agent.me.avelocity.data[0]/2.5)
    return temp,c

def matrixDot(_matrix,vector):
    return Vector([_matrix[0].dotProduct(vector),_matrix[1].dotProduct(vector),_matrix[2].dotProduct(vector)])

def backsolve(target,agent,time):
    #determines the delta-v required to reach a target on time
    d = target-agent.me.location

    dx = (2* ((d.data[0]/time)-agent.me.velocity.data[0]))/time
    dy = (2* ((d.data[1]/time)-agent.me.velocity.data[1]))/time
    dz = (2 * ((325*time)+((d.data[2]/time)-agent.me.velocity[2])))/time
    return Vector([dx,dy,dz])

# def aerial(agent, target, time):
#     #takes the agent, an intercept point, and an intercept time.Adjusts the agent's controller
#     #(agent.c) to perform an aerial
#     before = agent.c.jump
#     dv_target = backsolve(target,agent,time)
#     dv_total = dv_target.magnitude()
#     dv_local = matrixDot(agent.me.matrix,dv_target)
#     #dv_local = agent.me.matrix.dot(dv_target)
#     angles = defaultPD(agent,dv_local)
#
#     precision = clamp(0.6,0.05,dv_total/1500)
#     #precision = cap((dv_total/1500),0.05, 0.60)
#
#     if dv_local[2] > 100  or agent.me.airborne == False:
#         if agent.sinceJump < 0.3:
#             agent.c.jump = True
#         elif agent.sinceJump >= 0.32:
#             agent.c.jump = True
#             agent.c.pitch = agent.c.yaw = agent.c.roll = 0
#         else:
#             agent.c.jump = False
#     else:
#         agent.c.jump = False
#
#     if dv_total > 75:
#         if abs(angles[1])+abs(angles[2]) < precision:
#             agent.c.boost = True
#         else:
#             agent.c.boost = False
#     else:
#         fly_target = agent.me.matrix.dot(target - agent.me.location)
#         angles = defaultPD(agent,fly_target)
#         agent.c.boost = False

def drawAsterisks(vec,agent):
    if agent.team == 0:
        color = agent.renderer.red
    else:
        color = agent.renderer.green

    segmentLength = 55

    topVertical = vec + Vector([0,0,segmentLength])
    bottomVertical = vec + Vector([0,0,-segmentLength])
    leftHorizontal = vec + Vector([-segmentLength,0,0])
    rightHorizontal = vec + Vector([segmentLength, 0, 0])
    forwardHorizontal = vec + Vector([0,-segmentLength,0])
    backHorizontal = vec + Vector([0,segmentLength,0])

    topLeftFrontDiagnal = vec + Vector([-segmentLength,segmentLength,segmentLength])
    topRightFrontDiagnal = vec + Vector([segmentLength, segmentLength, segmentLength])
    bottomLeftFrontDiagnal = vec + Vector([-segmentLength, segmentLength, -segmentLength])
    bottomRightFrontDiagnal = vec + Vector([segmentLength, segmentLength, -segmentLength])

    bottomRightBackDiagnal = vec + Vector([segmentLength, -segmentLength, -segmentLength])
    bottomLeftBackDiagnal = vec + Vector([-segmentLength, -segmentLength, -segmentLength])
    topRightBackDiagnal = vec + Vector([segmentLength, -segmentLength, segmentLength])
    topLeftBackDiagnal = vec + Vector([-segmentLength, -segmentLength, segmentLength])

    points = [topVertical,bottomVertical,leftHorizontal,rightHorizontal,forwardHorizontal,backHorizontal,
              topLeftFrontDiagnal,topRightFrontDiagnal,bottomLeftFrontDiagnal,bottomRightFrontDiagnal,
              bottomRightBackDiagnal,bottomLeftBackDiagnal,topRightBackDiagnal,topLeftBackDiagnal]

    for p in points:
        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, p.toList(), vec.toList(), color))



def createBox(agent,_vector):
    if agent.team == 0:
        color = agent.renderer.blue
    else:
        color = agent.renderer.orange
    half = 55
    tbl = _vector + Vector([-half,half,half])
    tbr = _vector + Vector([half,half,half])
    tfl = _vector + Vector([-half,-half,half])
    tfr = _vector + Vector([half,-half,half])

    bbl = _vector + Vector([-half,half,-half])
    bbr = _vector + Vector([half,half,-half])
    bfl = _vector + Vector([-half,-half,-half])
    bfr = _vector + Vector([half,-half,-half])

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, tbl.toList(), tbr.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, tfr.toList(), tbr.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, tfr.toList(), tfl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, tbl.toList(), tfl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bbl.toList(), bbr.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bfr.toList(), bbr.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bfr.toList(), bfl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bfl.toList(), bbl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bbl.toList(), tbl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bbr.toList(), tbr.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bfl.toList(), tfl.toList(), color))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, bfr.toList(), tfr.toList(), color))


def createTriangle(agent,_vector):
    _vector.data[2] = 40
    length = 65
    top = _vector + Vector([0,0,length])
    right = _vector + Vector([length,length,0])
    left = _vector + Vector([-length,length,0])
    back = _vector + Vector([0,-length,0])

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, top.toList(), right.toList(), agent.renderer.purple))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, top.toList(), left.toList(), agent.renderer.purple))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, top.toList(), back.toList(), agent.renderer.purple))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, left.toList(), right.toList(), agent.renderer.purple))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, back.toList(), right.toList(), agent.renderer.purple))

    agent.renderCalls.append(
        renderCall(agent.renderer.draw_line_3d, back.toList(), left.toList(), agent.renderer.purple))

if __name__ == "__main__":
    newVectorsTest()











