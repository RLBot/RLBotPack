import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
import numpy as np
import ctypes
from numba import jit, float32, typeof, boolean
from functools import lru_cache

GOAL_WIDTH = 1900
FIELD_LENGTH = 10280
FIELD_WIDTH = 8240

maxPossibleSpeed = 2300

boosts = [
    [3584, 0, 0],
    [-3584, 0, 0],
    [3072, 4096, 0],
    [3072, -4096, 0],
    [-3072, 4096, 0],
    [-3072, -4096, 0],
]


class predictionStruct:
    def __init__(self, location, _time):
        self.location = location
        self.time = _time


class renderCall:
    def __init__(self, _function, *args):
        self.function = _function
        self.args = args

    def run(self):
        self.function(self.args[0], self.args[1], self.args[2]())


class FlipStatus:
    def __init__(self, _time):
        self.started = False
        self.flipStartedTimer = _time
        self.flipDone = False


class Boost_obj:
    def __init__(self, location, bigBoost, spawned):
        self.location = Vector(location)  # list of 3 coordinates
        self.bigBoost = bigBoost  # bool indicating if it's a cannister or just a pad
        self.spawned = spawned  # bool indicating whether it's currently spawned


class GameInfo:
    def __init__(self):
        self.seconds_elapsed = 0
        self.game_time_remaining = 300
        self.is_overtime = False
        self.is_unlimited_time = False
        self.is_round_active = False
        self.is_kickoff_pause = False
        self.world_gravity_z = -1000
        self.game_speed = 1

    def update(self, gamePacket):
        self.seconds_elapsed = gamePacket.game_info.seconds_elapsed
        self.game_time_remaining = gamePacket.game_info.game_time_remaining
        self.is_overtime = gamePacket.game_info.is_overtime
        self.is_unlimited_time = gamePacket.game_info.is_unlimited_time
        self.is_round_active = gamePacket.game_info.is_round_active
        self.is_kickoff_pause = gamePacket.game_info.is_kickoff_pause
        self.world_gravity_z = gamePacket.game_info.world_gravity_z
        self.game_speed = gamePacket.game_info.game_speed


class physicsObject:
    def __init__(self):
        self.location = Vector([0, 0, 0])
        self.velocity = Vector([0, 0, 0])
        self.rotation = Vector([0, 0, 0])
        self.avelocity = Vector([0, 0, 0])
        self.rotational_velocity = Vector([0, 0, 0])
        self.local_location = Vector([0, 0, 0])
        self.boostLevel = 0
        self.team = -1
        self.matrix = []
        self.lastTouch = 0
        self.lastToucher = 0
        self.rot_vector = None
        self.onSurface = False
        self.demolished = False
        self.retreating = False
        self.index = 0
        self.next_hit = None


def zeroEliminator(value):
    if value == 0:
        return -0.0001
    else:
        return value


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


def validateExistingPred(agent, pred_struct):
    if pred_struct.time <= agent.time:
        return False

    updatedPredAtTime = find_pred_at_time(agent, pred_struct.time)
    if updatedPredAtTime == None:
        return False

    if (
        findDistance(
            convertStructLocationToVector(updatedPredAtTime), pred_struct.location
        )
        > 10
    ):
        return False
    return True


def refuel(agent, boostLocation):
    _direction = (boostLocation - agent.ball.location).flatten().normalize()
    offset = 100
    _direction.scale(offset)
    target = boostLocation + _direction
    # print("going for corner boost")
    return driveController(agent, target, agent.time, expedite=True)


def inCornerWithBoost(agent):
    agentVal = cornerDetection(agent.me.location)
    ballVal = cornerDetection(agent.ball.location)
    cannister = getClosestBoostCannister(agent)
    if cannister != None:
        cannVal = cornerDetection(cannister.location)
    else:
        return False

    if agentVal == ballVal and agentVal == cannVal:
        if agentVal != -1:
            return cannister.location, cannVal
    return False


def getClosestBoostCannister(agent):
    closest = None
    bestDistance = math.inf

    for b in agent.bigBoosts:
        if b.spawned:
            d = distance2D(agent.me.location, b.location)
            if d < bestDistance:
                closest = b
                bestDistance = d
    return closest


def newVectorsTest():
    testVec1 = Vector([5, 5, 5])
    testVec2 = Vector([3, 3, 3])

    print(f"testing print: {testVec1}")
    print(f"testing len: {len(testVec1)}")
    print(f"testing get item: {testVec1[0]}")
    print(f"testing multiply: {testVec1 * testVec2}")
    print(f"testing addition: {testVec1 + testVec2}")
    print(f"testing subtraction: {testVec1 - testVec2}")
    print(f"testing cross product: {testVec1.crossProduct(testVec2)}")
    print(f"testing magnitude: {testVec1.magnitude()}")
    print(f"testing normalize: {testVec1.normalize()}")
    print(f"testing dotproduct: {testVec1.dotProduct(testVec2)}")
    print(f"testing scale multiplication: {testVec1.scale(2)}")
    print(f"testing lerp: {testVec1.lerp(testVec2, .5)}")
    print("done testing")


class Vector:
    def __init__(self, content):  # accepts list of float/int values
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
        return vec3(self.data[0], self.data[1].self.data[2])

    def raiseLengthError(self, other, operation):
        raise ValueError(
            f"Tried to perform {operation} on 2 vectors of differing lengths"
        )

    def raiseCrossError(self):
        raise ValueError("Both vectors need 3 terms for cross product")

    def __mul__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] * other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other, "multiplication")

    __rmul__ = __mul__

    def __eq__(self, other):
        try:
            return self.data == other.data
        except:
            return False

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
        v.data = [
            v[0],
            math.cos(rot[2]) * v[1] + math.sin(rot[2]) * v[2],
            math.cos(rot[2]) * v[2] - math.sin(rot[2]) * v[1],
        ]
        v.data = [
            math.cos(-rot[1]) * v[0] + math.sin(-rot[1]) * v[2],
            v[1],
            math.cos(-rot[1]) * v[2] - math.sin(-rot[1]) * v[0],
        ]
        v.data = [
            math.cos(-rot[0]) * v[0] + math.sin(-rot[0]) * v[1],
            math.cos(-rot[0]) * v[1] - math.sin(-rot[0]) * v[0],
            v[2],
        ]

        return v

    def align_from(self, rot):
        v = Vector([self[0], self[1], self[2]])
        v.data = [
            math.cos(rot[0]) * v[0] + math.sin(rot[0]) * v[1],
            math.cos(rot[0]) * v[1] - math.sin(rot[0]) * v[0],
            v[2],
        ]
        v.data = [
            math.cos(rot[1]) * v[0] + math.sin(rot[1]) * v[2],
            v[1],
            math.cos(rot[1]) * v[2] - math.sin(rot[1]) * v[0],
        ]
        v.data = [
            v[0],
            math.cos(-rot[2]) * v[1] + math.sin(-rot[2]) * v[2],
            math.cos(-rot[2]) * v[2] - math.sin(-rot[2]) * v[1],
        ]

        return v

    def crossProduct(self, other):
        if len(self.data) == 3 and len(other.data) == 3:
            newVec = [0, 0, 0]
            newVec[0] = self[1] * other[2] - self[2] * other[1]
            newVec[1] = self[2] * other[0] - self[0] * other[2]
            newVec[2] = self[0] * other[1] - self[1] * other[0]

            return Vector(newVec)

        else:
            self.raiseCrossError()

    def magnitude(self):
        return abs(math.sqrt(sum([x * x for x in self])))

    def normalize(self):
        mag = self.magnitude()
        if mag != 0:
            return Vector([x / mag for x in self])
        else:
            return Vector([0 for _ in range(len(self.data))])

    def dotProduct(self, other):
        product = 0
        for i, j in zip(self, other):
            product += i * j
        return product

    def scale(self, scalar):
        return Vector([x * scalar for x in self.data])

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

    def flatten(self):
        return Vector(self.data[:2] + [0])

    def toList(self):
        return self.data

    def lerp(self, otherVector, percent):  # percentage indicated 0 - 1
        percent = clamp(1, 0, percent)
        originPercent = 1 - percent

        scaledOriginal = self.scale(originPercent)
        other = otherVector.scale(percent)
        return scaledOriginal + other

    def cap(self, limit):
        if self.magnitude() > limit:
            self.data = self.normalize().scale(limit).data


# ccw and intersect pilfured from https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/ and altered to fit my data structures
def ccw(A: Vector, B: Vector, C: Vector):
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def intersect(A: Vector, B: Vector, C: Vector, D: Vector):
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def cars_intersecting(car_1: physicsObject, car_2: physicsObject):
    car_1_projection = car_1.local_location + car_1.velocity.scale(0.5)
    car_2_projection = car_2.local_location + car_2.velocity.scale(0.5)
    return intersect(car_1.location, car_1_projection, car_2.location, car_2_projection)


def check_for_team_collisions(agent):
    for ally in agent.allies:
        if ally.location[0] < 100:
            if cars_intersecting(agent.me, ally):
                return True, ally
    return False, None


def aerialHasJumpRoom(structLocation, agent):
    futurePosition = agent.me.location + agent.me.velocity  # 1 second into future
    _direction = direction(structLocation, agent.me.location)
    goodPos = structLocation + _direction.scale(90)
    badPos = structLocation - _direction.scale(90)

    if distance2D(futurePosition, goodPos) < distance2D(futurePosition, badPos):
        return True
    return False


def acceptableAerialRisk(agent, targetVec):
    if agent.lastMan != agent.me.location:
        return True

    if targetVec[1] * sign(agent.team) > 0:
        return True

    if butterZone(targetVec):
        return True

    return False


def retreating_tally(teamPlayerList):
    count = 0
    for player in teamPlayerList:
        if player.retreating:
            count += 1
    return count


def new_player_retreat_status(ally: physicsObject, ball_location: Vector, team: int):
    retreating_threshold = 300
    if distance2D(ally.location, ball_location) < 1000:
        if team == 0:
            if ally.velocity[1] < -retreating_threshold:
                return True
        else:
            if ally.velocity[1] > retreating_threshold:
                return True
    return False


def player_retreat_status(ally: physicsObject, ball: Vector, team: int, num_allies=2):
    retreat_threshold = 500 # 900 / (num_allies + 1)
    retreat_distance = 5000

    dist = distance2D(ally.location, ball)
    if dist < retreat_distance:

        if team == 0:
            if ally.velocity[1] < -retreat_threshold:
                return True

        else:
            if ally.velocity[1] > retreat_threshold:
                return True

    return False


class hit:
    def __init__(
        self,
        current_time: float,
        prediction_time: float,
        hit_type: int,
        pred_vector: Vector,
        pred_vel: Vector,
        hittable: bool,
        fastestTime: float,
        jumpSim=None,
        aerialState=None,
    ):
        self.current_time = current_time
        self.prediction_time = prediction_time
        self.hit_type = hit_type  # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot,5 aerial shot
        self.pred_vector = pred_vector
        self.pred_vel = pred_vel
        self.guarenteed_hittable = hittable
        self.fastestArrival = fastestTime
        self.jumpSim = jumpSim
        self.aerialState = aerialState

    def __str__(self):
        return f"hit type: {self.hit_type} delay: {self.time_difference()}"

    def update(self, current_time):
        self.current_time = current_time

    def time_difference(self):
        return self.prediction_time - self.current_time





def butterZone(vec):
    return abs(vec.data[0]) < 800 and abs(vec.data[1]) > 4400


def steer_handler(angle, rate):
    final = ((35 * (angle + rate)) ** 3) / 20
    return clamp(1, -1, final)


def sitting_duck_finder(agent, closerToGoal=True):
    enemyGoal = Vector([0, -sign(agent.team) * 5300, 0])
    for e in agent.enemies:
        if e.onSurface:
            if not e.demolished:
                if e.location[2] < 30:
                    if e.velocity.magnitude() < 1000:
                        return e
    return None


def orientTowardsVector(agent, target):
    localTarg = toLocal(target, agent.me)
    e1 = math.atan2(localTarg[1], localTarg[0])
    steer = steer_handler(e1, 0)
    yaw = steer_handler(e1, -agent.me.avelocity[2] / 6)
    e2 = math.atan2(localTarg[2], localTarg[0])
    pitch = steer_handler(e2, agent.me.avelocity[1] / 6)
    roll = steer_handler(-agent.me.rotation[2], agent.me.avelocity[0] / 6)

    return steer, yaw, pitch, roll


def add_car_offset(agent, projecting=False):

    up = agent.up.scale(agent.defaultOffset[2])
    forward = agent._forward.scale(agent.defaultOffset[0])
    left = agent.left.scale(agent.defaultOffset[1])
    agent.me.location = agent.me.location + up + forward + left
    if not agent.roof_height:
        agent.roof_height = math.floor((agent.me.location+agent.up.scale(agent.carHeight * 0.5))[2])
        #print(f"roof height is: {agent.roof_height}")

    if projecting:
        projection = agent.me.location + agent.me.velocity.scale(agent.fakeDeltaTime)
        # else:
        #     projection = agent.me.location

        forward_middle = projection + agent._forward.scale(
            agent.carLength * 0.5
        )  # +Vector([0,0,50])
        backward_middle = projection - agent._forward.scale(agent.carLength * 0.5)
        right_middle = projection - agent.left.scale(agent.carWidth * 0.5)
        left_middle = projection + agent.left.scale(agent.carWidth * 0.5)

        forward_right = forward_middle + agent.left.scale(agent.carWidth * 0.5)
        forward_left = forward_middle - agent.left.scale(agent.carWidth * 0.5)

        back_right = backward_middle + agent.left.scale(agent.carWidth * 0.5)
        back_left = backward_middle - agent.left.scale(agent.carWidth * 0.5)

        up_offset = agent.up.scale(agent.carHeight * 0.5)
        down_offset = agent.up.scale(-agent.carHeight * 0.5)

        FTL = forward_left + up_offset
        FBL = forward_left + down_offset
        # print(FTL[2])

        FTR = forward_right + up_offset
        FBR = forward_right + down_offset

        BTL = back_left + up_offset
        BBL = back_left + down_offset

        BTR = back_right + up_offset
        BBR = back_right + down_offset

        # vertical lines

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FTL.toList(),
                FBL.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FTR.toList(),
                FBR.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BTL.toList(),
                BBL.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BTR.toList(),
                BBR.toList(),
                agent.renderer.pink,
            )
        )

        # top square

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FTL.toList(),
                FTR.toList(),
                agent.renderer.pink,
            )
        )
        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FTR.toList(),
                BTR.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BTR.toList(),
                BTL.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BTL.toList(),
                FTL.toList(),
                agent.renderer.pink,
            )
        )

        # bottom square

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FBL.toList(),
                FBR.toList(),
                agent.renderer.pink,
            )
        )
        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                FBR.toList(),
                BBR.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BBR.toList(),
                BBL.toList(),
                agent.renderer.pink,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                BBL.toList(),
                FBL.toList(),
                agent.renderer.pink,
            )
        )


def is_shot_scorable(
    target_location, left_post_location, right_post_location
):  # borrowed from Goosefairy
    # this function returns target locations that are corrected to account for the ball's radius
    # If the left and right post swap sides, a goal cannot be scored
    ball_radius = 135  # We purposly make this a bit larger so that our shots have a higher chance of success
    goal_line_perp = (right_post_location - left_post_location).crossProduct(
        Vector([0, 0, 1])
    )
    left = left_post_location + (
        (left_post_location - target_location)
        .normalize()
        .crossProduct(Vector([0, 0, -1]))
        .scale(ball_radius)
    )
    right = right_post_location + (
        (right_post_location - target_location)
        .normalize()
        .crossProduct(Vector([0, 0, 1]))
        .scale(ball_radius)
    )
    left = (
        left_post_location
        if (left - left_post_location).dotProduct(goal_line_perp) > 0.0
        else left
    )
    right = (
        right_post_location
        if (right - right_post_location).dotProduct(goal_line_perp) > 0.0
        else right
    )
    swapped = (
        True
        if (left - target_location)
        .normalize()
        .crossProduct(Vector([0, 0, 1]))
        .dotProduct((right - target_location).normalize())
        > -0.1
        else False
    )
    return left, right, swapped


class ballTouch:
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

    def __eq__(self, other):
        if type(other) != ballTouch:
            raise ValueError(
                f"Can not do comparisan operations of balltouch and {type(other)} objects."
            )

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


def closest_enemy_to_goal(agent):
    e_goal = Vector([0, 5600 * -sign(agent.team), 200])
    closest_distance = math.inf
    closest = None

    for e in agent.enemies:
        c_dist = distance2D(e.location, e_goal)
        if c_dist < closest_distance:
            closest_distance = c_dist
            closest = e

    return closest, closest_distance


def goal_selector(agent, mode=0):  # 0 angles only, 1 enemy consideration
    leftPost = Vector([500 * -sign(agent.team), 5300 * -sign(agent.team), 200])
    rightPost = Vector([500 * sign(agent.team), 5300 * -sign(agent.team), 200])
    center = Vector([0, 5600 * -sign(agent.team), 200])
    real_center = center = Vector([0, 5300 * -sign(agent.team), 200])
    variance = 5
    maxAngle = 40

    targetVec = agent.currentHit.pred_vector

    shotAngles = [
        math.degrees(angle2(targetVec, leftPost)),
        math.degrees(angle2(targetVec, center)),
        math.degrees(angle2(targetVec, rightPost)),
    ]

    correctedAngles = [correctAngle(x + 90 * -sign(agent.team)) for x in shotAngles]
    dist = distance2D(targetVec, center)

    if dist >= 4000 or dist < 1200:
        createTriangle(agent, center)
        return real_center, correctedAngles[1]

    if correctedAngles[1] >= maxAngle:
        createTriangle(agent, leftPost)
        return leftPost, correctedAngles[1]

    if correctedAngles[1] <= -maxAngle:
        createTriangle(agent, rightPost)
        return rightPost, correctedAngles[1]

    if mode == 0 or agent.openGoal:
        createTriangle(agent, center)
        return real_center, correctedAngles[1]

    # if agent.openGoal:
    #     return center,correctedAngles[1]

    # print(f"aiming happening! {agent.time}")

    if distance2D(agent.closestEnemyToBall.location, center) < 3500:
        simple_projection = (
            agent.closestEnemyToBall.location
            + agent.closestEnemyToBall.velocity.scale(0.5)
        )
        left_distance = distance2D(simple_projection, leftPost)
        right_distance = distance2D(simple_projection, rightPost)
        if left_distance > right_distance:
            return leftPost, correctedAngles[1]
        else:
            return rightPost, correctedAngles[1]
    else:
        return center, correctedAngles[1]


def goal_selector_revised(
    agent, mode=0
):  # 0 angles only, closest corner #1 enemy consideration

    leftPost = Vector([650 * sign(agent.team), 5320 * -sign(agent.team), 0])
    rightPost = Vector([650 * -sign(agent.team), 5320 * -sign(agent.team), 0])
    center = Vector([0, 5600 * -sign(agent.team), 0])
    real_center = center = Vector([0, 5320 * -sign(agent.team), 0])
    variance = 5
    maxAngle = 35
    if mode == 1:
        maxAngle = 20

    targetVec = agent.currentHit.pred_vector

    shotAngles = [
        math.degrees(angle2(targetVec, leftPost)),
        math.degrees(angle2(targetVec, center)),
        math.degrees(angle2(targetVec, rightPost)),
    ]

    correctedAngles = [correctAngle(x + 90 * -sign(agent.team)) for x in shotAngles]
    dist = distance2D(targetVec, center)

    if dist >= 5000 or dist < 1500:
        aim = Vector([0, 5250 * -sign(agent.team), 0])
        createBox(agent, aim)
        return aim, correctedAngles[1]

    if correctedAngles[1] <= -maxAngle:
        createBox(agent, leftPost)
        return rightPost, correctedAngles[1]

    if correctedAngles[1] >= maxAngle:
        createBox(agent, rightPost)
        return leftPost, correctedAngles[1]

    if mode == 0 or agent.openGoal:
        createBox(agent, center)
        return real_center, correctedAngles[1]

    distances = [
        distance2D(agent.me.location, leftPost),
        distance2D(agent.me.location, real_center),
        distance2D(agent.me.location, rightPost),
    ]
    index = distances.index(min(distances))
    if index == 0:
        createBox(agent, leftPost)
        return leftPost, correctedAngles[1]
    elif index == 1:
        createBox(agent, Vector([0, 5120 * -sign(agent.team), 200]))
        return center, correctedAngles[1]
    else:
        createBox(agent, rightPost)
        return rightPost, correctedAngles[1]

    if distance2D(agent.closestEnemyToBall.location, center) < 3500:
        simple_projection = (
            agent.closestEnemyToBall.location
            + agent.closestEnemyToBall.velocity.scale(agent.fakeDeltaTime * 10)
        )
        left_distance = distance2D(simple_projection, leftPost)
        right_distance = distance2D(simple_projection, rightPost)
        if left_distance > right_distance:
            return leftPost, correctedAngles[1]
        else:
            return rightPost, correctedAngles[1]
    else:
        return center, correctedAngles[1]


def convertStructLocationToVector(struct):
    return Vector(
        [
            struct.physics.location.x * 1.0,
            struct.physics.location.y * 1.0,
            struct.physics.location.z * 1.0,
        ]
    )


def convertStructVelocityToVector(struct):
    return Vector(
        [
            struct.physics.velocity.x * 1.0,
            struct.physics.velocity.y * 1.0,
            struct.physics.velocity.z * 1.0,
        ]
    )


def placeTargetVecWithinArena(vec, agent):
    if vec[0] > 4096 - agent.defaultElevation:
        vec.data[0] = 4096 - agent.defaultElevation

    elif vec[0] < -4096 + agent.defaultElevation:
        vec.data[0] = -4096 + agent.defaultElevation

    if vec[1] > 5120 - agent.defaultElevation:
        if abs(vec[0]) > 893:
            vec.data[1] = 5120 - agent.defaultElevation

        else:
            if vec[1] > 6000:
                vec.data[1] = 6000

    elif vec[1] < -5120 + agent.defaultElevation:
        if abs(vec[0]) > 893:
            vec.data[1] = -5120 + agent.defaultElevation

        else:
            if vec[1] < -6000:
                vec.data[1] = -6000


def placeVecWithinArena(vec, offset=17.01):
    if vec[0] > 4096 - offset:
        vec.data[0] = 4096 - offset

    elif vec[0] < -4096 + offset:
        vec.data[0] = -4096 + offset

    if vec[1] > 5120:
        if abs(vec[0]) > 893:
            vec.data[1] = 5120 - offset

        else:
            if vec[1] > 6000:
                vec.data[1] = 6000

    elif vec[1] < -5120:
        if abs(vec[0]) > 893:
            vec.data[1] = -5120 + offset

        else:
            if vec[1] < -6000:
                vec.data[1] = -6000

def unpicky_demo_picker(agent):
    best_target = None
    best_distance = math.inf

    for enemy in agent.enemies:
        if (enemy.onSurface or enemy.location[2] < 140) and not enemy.demolished:
            _distance = findDistance(agent.me.location,enemy.location)
            if _distance < best_distance:
                best_target = enemy
                best_distance = _distance

    return best_target


def demoTarget(agent, targetCar):
    currentSpd = clamp(maxPossibleSpeed, 100, agent.currentSpd)
    distance = distance2D(agent.me.location, targetCar.location)

    currentTimeToTarget = inaccurateArrivalEstimator(agent, targetCar.location)
    lead = clamp(2, 0, currentTimeToTarget)

    enemyspd = targetCar.velocity.magnitude()
    multi = clamp(1000, 0, enemyspd * currentTimeToTarget)
    targPos = targetCar.location + (targetCar.velocity.normalize().scale(multi))

    if not targetCar.onSurface:
        if currentTimeToTarget < 0.1:
            local_target = localizeVector(targPos,agent.me)
            angle = math.atan2(local_target[1], local_target[0])
            angle_degrees = correctAngle(math.degrees(angle))
            if abs(angle_degrees) < 30:
                agent.setJumping(1)


    return driveController(
        agent,
        targPos,
        agent.time + currentTimeToTarget,
        expedite=True,
        maintainSpeed=True
    )


def findDemoTarget(agent):
    # find closest enemy between me and my goal
    potentialTargets = [
        e
        for e in agent.enemies
        if inTheMiddle(e.location[1], [agent.me.location[1], sign(agent.team) * 5120])
        and not e.demolished
        and e.onSurface
        and e.location[2] < 30
    ]
    if len(potentialTargets) < 1:
        return None
    elif len(potentialTargets) == 1:
        return potentialTargets[0]

    else:
        closestEnemy = potentialTargets[0]
        closestDistance = math.inf

        for e in potentialTargets:
            dist = distance2D(agent.me.location, e.location)
            if dist < closestDistance:
                closestDistance = dist
                closestEnemy = e
        return closestEnemy


def advancing_demo_handler(agent, max_distance=2000):
    if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
        agent.team
    ):  # if on enemy side of ball
        if agent.me.velocity[1] * sign(agent.team) < 0:
            ideal_target = sitting_duck_finder(agent)
            if ideal_target == None:
                ideal_target = findDemoTarget(agent)

            if (
                ideal_target != None
                and distance2D(agent.me.location, ideal_target.location) <= max_distance
            ):
                return demoTarget(agent, ideal_target)
    return None


def naive_retreating_demo_handler(agent):
    # return None
    if agent.me.location[1] * sign(agent.team) < 4000:
        ideal_target = sitting_duck_finder(agent)
        if ideal_target == None:
            ideal_target = findDemoTarget(agent)

        if ideal_target != None:
            if inTheMiddle(
                ideal_target.location[1], [agent.ball.location[1], agent.me.location[1]]
            ):
                return demoTarget(agent, ideal_target)
    return None


def kickOffTest(agent):
    # print(f"Kickoff pause: {agent.gameInfo.is_kickoff_pause}")
    # print(f"is round active: {agent.gameInfo.is_round_active}")
    # print("========================")
    if agent.ignore_kickoffs or agent.ball.location.flatten() != Vector([0, 0, 0]):
        return False

    if agent.gameInfo.is_kickoff_pause or not agent.gameInfo.is_round_active:
        if len(agent.allies) > 0:
            myDist = distance2D(agent.me.location, agent.ball.location)
            equalAlly = None
            for ally in agent.allies:
                ally_dist = distance2D(ally.location, agent.ball.location)
                if abs(ally_dist - myDist) < 50:
                    equalAlly = ally
                elif ally_dist < myDist:
                    return False
            if equalAlly != None:
                if agent.team == 0:
                    if agent.me.location[0] > 0:
                        return True
                    else:
                        return False
                else:
                    if agent.me.location[0] < 0:
                        return True
                    else:
                        return False

        return True
    return False


def flipHandler(agent, flip_status):
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

    if agent.time - flip_status.flipStartedTimer >= 0.45:
        flip_status.flipDone = True

    return jump


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

    matrix = [
        Vector([CP * CY, CP * SY, SP]),
        Vector([CY * SP * SR - CR * SY, SY * SP * SR + CR * CY, -CP * SR]),
        Vector([-CR * CY * SP - SR * SY, -CR * SY * SP + SR * CY, CP * CR]),
    ]

    return matrix


def getLocation(_object):
    if type(_object) == Vector:
        return _object
    if type(_object) == physicsObject:
        return _object.location
    # error = f"{str(type(_object))} is not a valid input for 'getLocation' function "
    raise ValueError(
        f"{str(type(_object))} is not a valid input for 'getLocation' function "
    )


@jit(float32(float32, float32, float32))
def clamp(_max, _min, value):
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


def newSteer(angle):
    turn = Gsteer(angle)
    slide = False

    if abs(math.degrees(angle)) >= 85:
        slide = True

    return (turn, slide)


def slideSteer(angle, distance):
    sliding = False
    degrees = math.degrees(angle)

    if distance < 1000:
        if abs(degrees) > 70 and abs(degrees) < 180:
            sliding = True
        """
        if abs(degrees) < 3:
            return(0,False)
        """

        return (clamp(1, -1, (degrees / 360) * 8), sliding)
    else:
        if abs(degrees) < 3:
            return (0, False)

        return (clamp(1, -1, (degrees / 360) * 8), sliding)


def partialBackmanGrabber(agent, stayPositive=True, buffer=3000):
    # minDistance = distance2D(Vector([0, 5100 * sign(agent.team), 200]), agent.ball.location)
    minY = (agent.ball.location[1] + buffer * sign(agent.team)) * sign(agent.team)
    closestBoost = physicsObject()
    closestBoost.location = Vector([0, 4900 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            if boost.location[1] * sign(agent.team) >= minY:
                if stayPositive:
                    if boost.location[0] < 0:
                        continue

                else:
                    if boost.location[0] >= 0:
                        continue

                distance = distance2D(agent.me.location, boost.location)
                localCoords = toLocal(boost.location, agent.me)
                angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
                if not agent.forward:
                    angle -= 180
                    angle = correctAngle(angle)

                distance += angle * 5
                if boost.bigBoost:
                    distance = distance * 0.333
                if distance < bestDistance:
                    bestDistance = distance
                    closestBoost = boost
                    bestAngle = angle

    if closestBoost.location != Vector([0, 4900 * sign(agent.team), 200]):
        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                agent.me.location.toList(),
                closestBoost.location.toList(),
                agent.renderer.yellow,
            )
        )
        # expi = agent.me.boostLevel <1
        return driveController(agent, closestBoost.location, agent.time)

    else:
        return gate(agent)


def boost_suggester(
    agent, mode=1, buffer=3000
):  # mode 0: any side, mode:1 stay on side, mode:2 stay on opposite side
    minY = agent.ball.location[1] + (buffer * sign(agent.team))
    # closestBoost = physicsObject()
    closestBoost = None
    # closestBoost.location = Vector([0, 4900 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            if (
                boost.location[1] > minY
                and agent.team == 1
                or boost.location[1] < minY
                and agent.team == 0
            ):
                valid = True
                if mode == 1:
                    if agent.ball.location[0] >= 0:
                        if boost.location[0] < 0:
                            valid = False
                            continue

                    else:
                        if agent.ball.location[0] < 0:
                            if boost.location[0] > 0:
                                valid = False
                                continue

                elif mode == 2:
                    if agent.ball.location[0] >= 0:
                        if boost.location[0] > 0:
                            valid = False
                            continue

                    else:
                        if agent.ball.location[0] < 0:
                            if boost.location[0] < 0:
                                valid = False
                                continue
                if valid:
                    distance = distance2D(agent.me.location, boost.location)
                    localCoords = toLocal(boost.location, agent.me)
                    angle = abs(
                        math.degrees(math.atan2(localCoords[1], localCoords[0]))
                    )
                    if not agent.forward:
                        angle -= 180
                        angle = correctAngle(angle)

                    distance += angle * 5
                    if boost.bigBoost and agent.me.boostLevel < 50:
                        distance = distance * 0.333
                    if distance < bestDistance:
                        bestDistance = distance
                        closestBoost = boost
                        bestAngle = angle

    if closestBoost != None:
        agent.boost_gobbling = True

    return closestBoost


def kickoff_boost_grabber(agent):
    left_boost = Vector([3072, 4096 * sign(agent.team), 0])
    right_boost = Vector([3072, 4096 * sign(agent.team), 0])

    left_dist = distance2D(agent.me.location, left_boost)
    right_dist = distance2D(agent.me.location, right_boost)

    for ally in agent.allies:
        if distance2D(ally.location, left_boost) < left_dist:
            return driveController(agent, right_boost, 0, expedite=right_dist > 1000)

    return driveController(agent, left_boost, 0, expedite=left_dist > 1000)


def backmanBoostGrabber(
    agent, mode=1, buffer=3000
):  # mode 0: any side, mode:1 stay on side, mode:2 stay on opposite side
    minY = agent.ball.location[1] + (buffer * sign(agent.team))
    closestBoost = physicsObject()
    closestBoost.location = Vector([0, 4900 * sign(agent.team), 200])
    bestDistance = math.inf
    bestAngle = 0

    for boost in agent.boosts:
        if boost.spawned:
            if (
                boost.location[1] > minY
                and agent.team == 1
                or boost.location[1] < minY
                and agent.team == 0
            ):
                if mode == 1:
                    if agent.ball.location[0] >= 0:
                        if boost.location[0] < 0:
                            continue

                    else:
                        if agent.ball.location[0] < 0:
                            if boost.location[0] >= 0:
                                continue

                elif mode == 2:
                    if agent.ball.location[0] >= 0:
                        if boost.location[0] > 0:
                            continue

                    else:
                        if agent.ball.location[0] < 0:
                            if boost.location[0] <= 0:
                                continue

                distance = distance2D(agent.me.location, boost.location)
                localCoords = toLocal(boost.location, agent.me)
                angle = abs(math.degrees(math.atan2(localCoords[1], localCoords[0])))
                if not agent.forward:
                    angle -= 180
                    angle = correctAngle(angle)

                distance += angle * 5
                if boost.bigBoost:
                    distance = distance * 0.333
                if distance < bestDistance:
                    bestDistance = distance
                    closestBoost = boost
                    bestAngle = angle

    if bestDistance < math.inf:
        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                agent.me.location.toList(),
                closestBoost.location.toList(),
                agent.renderer.yellow,
            )
        )
        # expi = agent.me.boostLevel <1
        return driveController(agent, closestBoost.location.flatten(), agent.time)

    else:
        # return gate(agent)
        return smart_retreat(agent)


def distance1D(origin, destination, index):
    return abs(getLocation(origin)[index] - getLocation(destination)[index])


def findOppositeSideVector(agent, objVector, antiTarget, desiredBallDistance):
    # angle = math.degrees(angle2(objVector,antiTarget))
    targetDistance = distance2D(objVector, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - objVector).normalize()
    return getLocation(antiTarget) - (
        oppositeVector.scale(targetDistance + desiredBallDistance)
    )


def findOppositeSide(agent, targetLoc, antiTarget, desiredBallDistance):
    # angle = correctAngle(math.degrees(angle2(targetLoc,antiTarget)))
    targetDistance = distance2D(targetLoc, getLocation(antiTarget))
    oppositeVector = (getLocation(antiTarget) - targetLoc).normalize()
    return getLocation(antiTarget) - (
        oppositeVector.scale(targetDistance + desiredBallDistance)
    )


def findGoalAngle(agent):
    center = Vector([0, 5150 * -sign(agent.team), 200])
    return math.degrees(angle2(agent.ball, center)) * sign(agent.team)


def determineVelocityToGoal(agent):
    myGoal = Vector([0, 5150 * sign(agent.team), 200])
    startingDistance = distance2D(myGoal, agent.ball.location)
    if startingDistance < distance2D(myGoal, agent.ball.location + agent.ball.velocity):
        return True
    else:
        return False


def find_L_distance(groundVector, wallVector):
    groundedWallSpot = Vector([wallVector.data[0], wallVector.data[1], 0])
    return distance2D(groundVector, groundedWallSpot) + findDistance(
        groundedWallSpot, wallVector
    )


def goFarPost(agent):
    rightPost = Vector([900, 4800 * sign(agent.team), 0])
    leftPost = Vector([-900, 4800 * sign(agent.team), 0])
    rightDist = distance2D(agent.ball.location, rightPost)
    leftDist = distance2D(agent.ball.location, leftPost)
    selectedDist = 99999
    if rightDist > leftDist:
        post = rightPost
        selectedDist = rightDist
        pointDir = leftPost + Vector([0, -sign(agent.team) * 400, 0])

    else:
        post = leftPost
        selectedDist = leftDist
        pointDir = rightPost + Vector([0, -sign(agent.team) * 400, 0])

    area_info = teammate_nearby(agent, post, 300)

    if distance2D(post, agent.me.location) < 250 and not agent.onWall:
        if agent.currentSpd < 100:
            localTarget = toLocal(pointDir, agent.me)
            angle = math.degrees(math.atan2(localTarget[1], localTarget[0]))
            if abs(angle) > 45:
                agent.setGuidance(pointDir)
        return arrest_movement(agent)

    return driveController(agent, post, agent.time + 0.6, expedite=False)


def gate(agent, hurry=True):
    # print(f"{agent.index} in gate")
    rightPost = Vector([900, 4600 * sign(agent.team), 0])
    leftPost = Vector([-900, 4600 * sign(agent.team), 0])
    center = Vector([0, 5350 * sign(agent.team), 0])
    enemy_goal = Vector([0, 5000 * -sign(agent.team), 0])
    rightDist = distance2D(agent.me.location, rightPost)
    leftDist = distance2D(agent.me.location, leftPost)
    selectedDist = 99999
    # own_goal_info = own_goal_check(agent, agent.ball.location.flatten(), agent.me.location.flatten(), send_back=True)

    if (
        agent.goalie
        and agent.lastMan != agent.me.location
        and abs(agent.me.location[0]) < 800
    ):
        center = Vector([0, 6500 * sign(agent.team), 200])
        # updated peter is blue

    if rightDist < leftDist:
        post = rightPost
        selectedDist = rightDist
    else:
        post = leftPost
        selectedDist = leftDist
    inPlace = False
    centerDist = distance2D(agent.me.location, center)
    if centerDist <= 250:
        inPlace = True

    if teammate_nearby(agent, post, 500)[0]:
        post = center

    if not inPlace:
        if selectedDist >= 1200:
            return driveController(agent, post, agent.time, expedite=hurry)

        elif centerDist > 250:
            return driveController(agent, center, agent.time + 0.2, expedite=False)

    agent.renderCalls.append(
        renderCall(
            agent.renderer.draw_line_3d,
            agent.me.location.toList(),
            agent.enemyTargetVec.toList(),
            agent.renderer.red,
        )
    )
    if inPlace:
        if agent.currentSpd < 50:
            localTarget = toLocal(enemy_goal, agent.me)
            angle = math.degrees(math.atan2(localTarget[1], localTarget[0]))
            if abs(angle) > 35:
                agent.setGuidance(enemy_goal)
        # return SimpleControllerState()
        return arrest_movement(agent)

    return driveController(agent, center, agent.time + 0.6, expedite=False)


def replacementAvailable(
    agent,
):  # is there a teammate able to become a suitable back man
    for ally in agent.allies:
        if (
            abs(
                ally.location[1] * sign(agent.team)
                - agent.me.location[1] * sign(agent.team)
            )
            < 500
        ):
            return True
    return False


def all_allies_back(agent):
    for ally in agent.allies:
        if ally.location[1] * sign(agent.team) < 3120 * sign(agent.team):
            return False
    # print(f"saving myself from sitting back {agent.time}")
    return True


def interceptGuidance(agent, e_goaldist, distLimit=900):
    center = Vector([0, 5200 * sign(agent.team), 200])
    defensiveDistance = distance2D(agent.currentHit.pred_vector, center)
    if False:
        # if len(agent.allies) > 1:
        if agent.lastMan == agent.me.location:
            if defensiveDistance > 2000:
                if not replacementAvailable(agent):
                    if not agent.goalPred:
                        if (
                            agent.enemyBallInterceptDelay + agent.contestedTimeLimit
                            < agent.currentHit.time_difference()
                        ):
                            if e_goaldist > distLimit:
                                if not all_allies_back(agent):
                                    if (
                                        distance2D(
                                            agent.me.location, agent.ball.location
                                        )
                                        > 250
                                    ):
                                        if not goalie_shot(agent, agent.currentHit):
                                            return True, smart_retreat(agent)

    return False, None


def arrest_movement(agent):
    controls = SimpleControllerState()
    if agent.currentSpd > 20:
        if agent.forward:
            controls.throttle = -1

        else:
            controls.throttle = 1

    return controls


def buyTime(agent, attackTarget, defendTarget):
    if agent.currentHit.time_difference() < agent.enemyBallInterceptDelay + 0.25:
        if abs(agent.currentHit.pred_vector[0]) < 2600:
            if distance2D(agent.currentHit.pred_vector, attackTarget) > 2000:
                if distance2D(agent.currentHit.pred_vector, defendTarget) > 2000:
                    predVec = agent.currentHit.pred_vector
                    proceed = False
                    if (
                        agent.me.location[0] > 500
                        and predVec[0] > 500
                        and agent.me.location[0] > predVec[0]
                    ):
                        proceed = True

                    elif (
                        agent.me.location[0] < -500
                        and predVec[0] < -500
                        and agent.me.location[0] < predVec[0]
                    ):
                        proceed = True
                    if proceed:
                        agent.log.append(f"proceeding {agent.time}")
                        myGoal = Vector([0, 5250 * sign(agent.team), 200])

                        targDist = distance2D(agent.me.location, predVec)

                        if agent.me.location[0] > predVec[0]:
                            attackTarget = Vector([5000, predVec[1], predVec[2]])
                        else:
                            attackTarget = Vector([-5000, predVec[1], predVec[2]])

                        localPos = toLocal(predVec, agent.me)
                        angleDegrees = correctAngle(
                            math.degrees(math.atan2(localPos[1], localPos[0]))
                        )

                        if abs(angleDegrees) <= 40:
                            carOffset = agent.carLength * 0.6
                        elif abs(angleDegrees) >= 140:
                            carOffset = agent.carLength * 0.25
                        else:
                            carOffset = agent.carWidth * 0.4

                        totalOffset = (90 + carOffset) * 0.8

                        _direction = direction(attackTarget, predVec)
                        destination = predVec + _direction.scale(totalOffset)

                        badDirection = direction(myGoal, predVec)
                        badPosition = predVec + badDirection.scale(totalOffset)

                        shotViable = False
                        futurePos = agent.me.location + (
                            agent.me.velocity.scale(agent.currentHit.time_difference())
                        )
                        fpos_pred_distance = distance2D(futurePos, predVec)

                        if fpos_pred_distance <= totalOffset:
                            shotViable = True

                        shotlimit = 1
                        if agent.contested:
                            shotlimit = 0.7

                        if agent.currentHit.time_difference() < shotlimit:
                            if distance2D(futurePos, destination) * 1.5 < distance2D(
                                futurePos, badPosition
                            ):
                                if agent.currentSpd * agent.ballDelay >= clamp(
                                    99999, 0, targDist - totalOffset
                                ):
                                    if not agent.onWall and agent.onSurface:
                                        if shotViable:
                                            destination = predVec
                                            agent.setPowershot(
                                                agent.currentHit.time_difference(),
                                                predVec,
                                            )
                                            agent.log.append("stall tactics")
                        # print(f"buying time {agent.time}")

                        return (
                            True,
                            driveController(
                                agent,
                                destination,
                                agent.time + agent.currentHit.time_difference(),
                                expedite=True,
                            ),
                        )

    return False, None


def findFirstAllyOnTeamSideOfBall(agent):
    best = None
    bestDist = math.inf

    for ally in agent.allies:
        if ally.location[1] * sign(agent.team) > agent.ball.location[1] * sign(
            agent.team
        ):
            dist = distance2D(ally.location, agent.ball.location)
            if dist < bestDist:
                best = ally
                bestDist = dist

    if agent.me.location[1] * sign(agent.team) > agent.ball.location[1] * sign(
        agent.team
    ):
        dist = distance2D(agent.me.location, agent.ball.location)
        if dist < bestDist:
            best = agent.me
            bestDist = dist

    return best

def get_ball_offset(agent, hit):
    if hit.pred_vector[2] > agent.groundCutOff:
        return 65
    adjusted_roof_height = agent.roof_height - (hit.pred_vector[2]-agent.ball_size)
    return math.floor(math.sqrt(adjusted_roof_height * (agent.ball_size * 2 - adjusted_roof_height)))


def ShellTime(agent, retreat_enabled=True):
    defendTarget = Vector([0, 5500 * sign(agent.team), 200])
    attackTarget = Vector([0, 5200 * -sign(agent.team), 200])
    # rush = False
    # print("in shell")

    targetVec = agent.currentHit.pred_vector

    defensiveRange = 200

    maxRange = 1200
    if agent.contested:
        maxRange = 800

    goalDistance = distance2D(targetVec, defendTarget)
    carDistance = distance2D(agent.me.location, defendTarget)
    ballGoalDistance = distance2D(agent.ball.location, defendTarget)
    targDistance = distance2D(agent.me.location, targetVec)
    dist3D = findDistance(agent.me.location, targetVec)
    targToGoalDistance = distance2D(targetVec, attackTarget)
    carToGoalDistance = distance2D(agent.me.location, attackTarget)
    expedite = True
    flippant = False
    offensive = agent.ball.location[1] * sign(agent.team) < 0
    # (agent,ball_vec, startPos,buffer=90, send_back=False)
    # own_goal_info = own_goal_check(agent,agent.ball.location.flatten(),agent.me.location.flatten(),send_back=True)

    if agent.currentHit.hit_type == 5:
        # print("why is there an aerial hit in shelltime?")
        agent.activeState = agent.currentHit.aerialState
        return agent.activeState.update()

    if (
        ballGoalDistance + defensiveRange < carDistance
    ):  # and determine_if_shot_goalward(agent.currentHit.pred_vel,agent.team):
        cornerShot = cornerDetection(targetVec) != -1
        # if (not own_goal_info[0] or agent.ball.location[2] > 140) and (not agent.goalPred or agent.lastMan != agent.me.location):
        if not agent.goalPred or agent.lastMan != agent.me.location:
            if retreat_enabled or cornerShot:
                rightPost = Vector([900, 5000 * sign(agent.team), 200])
                leftPost = Vector([-900, 5000 * sign(agent.team), 200])
                if distance2D(agent.me.location, rightPost) < distance2D(
                    agent.me.location, leftPost
                ):
                    post = rightPost
                else:
                    post = leftPost

                if distance2D(targetVec, post) + defensiveRange < distance2D(
                    agent.me.location, post
                ):
                    return driveController(
                        agent, post.flatten(), agent.time, expedite=True
                    )
            else:
                # if offensive:
                #     return handleBounceShot(agent, waitForShot=True, forceDefense=True)
                # else:
                return smart_retreat(agent)

    goalSpot, ballGoalAngle = goal_selector_revised(agent, mode=0)

    if len(agent.allies) < 2:
        if abs(ballGoalAngle) >= agent.angleLimit:
            expedite = False
            if retreat_enabled:
                if (
                    agent.contested
                    or agent.enemyBallInterceptDelay
                    < agent.currentHit.time_difference()
                    or agent.me.boostLevel < agent.boostThreshold
                ):
                    return playBack(agent)
                # return thirdManPositioning(agent)

    corner = cornerDetection(targetVec)
    if len(agent.allies) < 1:
        if agent.team == 0:
            if corner == 0 or corner == 1:
                expedite = False
        else:
            if corner == 2 or corner == 3:
                expedite = False

    if (
        agent.goalPred == None
        and len(agent.allies) < 1
        and agent.currentHit.time_difference() - agent.enemyBallInterceptDelay >= 1
        and offensive
    ):
        expedite = False

    if retreat_enabled:
        challenge = interceptGuidance(agent, ballGoalDistance)
        if challenge[0]:
            return challenge[1]

    localPos = toLocal(targetVec, agent.me)
    angleDegrees = correctAngle(math.degrees(math.atan2(localPos[1], localPos[0])))
    moddedOffset = False

    if abs(angleDegrees) <= 40:
        carOffset = agent.carLength * 0.5
    elif abs(angleDegrees) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5

    ballOffset = get_ball_offset(agent, agent.currentHit)
    totalOffset = (carOffset + ballOffset) * 0.75
    adjustedOffset = totalOffset * 1
    offset_min = totalOffset * 0.65
    positioningOffset = offset_min
    destination = None
    moddedOffset = False

    if agent.currentHit.hit_type == 1 or agent.currentHit.hit_type == 4:
        return handleBounceShot(agent, waitForShot=False)

    if agent.currentHit.hit_type == 2:
        agent.wallShot = True
        agent.ballGrounded = False
        return handleWallShot(agent)

    challenge_flip(agent, targetVec)

    if targetVec[2] >= agent.groundCutOff * 0.9 and agent.ballDelay < 0.6:
        # print(agent.currentHit.hit_type)
        return handleBounceShot(agent, waitForShot=False)

    relative_speed = relativeSpeed(agent.currentHit.pred_vel, agent.me.velocity)
    if (
        offensive
        and relative_speed * 1.2 > targToGoalDistance
        and agent.ballDelay < 0.6
        and targToGoalDistance > 1000
    ):
        return handleBounceShot(agent, waitForShot=False)

    mirror_info = mirrorshot_qualifier(agent)
    is_mirror_shot = (
        mirror_info[0]
        and len(mirror_info[1]) < 1
        and agent.lastMan == agent.me.location
    )

    futurePos = agent.me.location + agent.me.velocity.scale(
        agent.currentHit.time_difference()
    )

    lined_up = extendToGoal(agent, targetVec, agent.me.location)
    if lined_up:
        expedite = True

    require_lineup = False
    if (
        targetVec[1] * sign(agent.team) < -3500
        and not lined_up
        and abs(targetVec[0]) < 3000
        and len(agent.allies) < 2
        and not is_mirror_shot
    ):
        require_lineup = True

    _direction = direction(targetVec, goalSpot)

    shot_scorable = is_shot_scorable(
        targetVec, agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]
    )[2]
    if not shot_scorable and len(agent.allies) < 1:
        expedite = False

    if not destination:
        if (
            agent.contested
            and (not require_lineup or lined_up)
            and (
                distance2D(agent.closestEnemyToBall.location, attackTarget)
                < distance2D(agent.me.location, attackTarget)
            )
        ):
            # if agent.contested and agent.me.boostLevel < 5 or agent.enemyBallInterceptDelay < agent.currentHit.time_difference():
            # if agent.me.boostLevel < 1 and agent.currentSpd < 2000:
            if not is_mirror_shot:
                destination = get_aim_vector(
                    agent,
                    goalSpot.flatten(),
                    targetVec.flatten(),
                    agent.currentHit.pred_vel,
                    offset_min,
                )[0]
            else:
                destination = aim_wallshot_naive(agent, agent.currentHit, offset_min)
            moddedOffset = False

    if not destination and require_lineup:
        offset = clamp(1800, offset_min, targDistance * 0.5)
        positioningOffset = offset
        destination = targetVec + _direction.scale(positioningOffset)
        if not is_mirror_shot:
            destination = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
            )[0]
            moddedOffset = positioningOffset > offset_min
        else:
            destination = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)
            moddedOffset = positioningOffset > offset_min
            # moddedOffset = True
        # print(f"defensive altered shot {agent.time}")

    if not destination and abs(targetVec[0]) < 3500:
        # if not agent.contested:
        if (
            targDistance > totalOffset
            and targDistance > (agent.currentSpd * agent.currentHit.time_difference())
            and abs(targetVec[1]) <= 4000
        ):
            # print(f"in here {agent.time}")
            offset = clamp(1800, offset_min, targDistance * 0.25)
            # _direction = direction(attackTarget, targetVec)
            positioningOffset = offset
            destination = targetVec + _direction.scale(positioningOffset)
            if agent.team != 3:
                if not is_mirror_shot:
                    destination = get_aim_vector(
                        agent,
                        goalSpot.flatten(),
                        targetVec.flatten(),
                        agent.currentHit.pred_vel,
                        positioningOffset,
                    )[0]
                else:
                    destination = aim_wallshot_naive(
                        agent, agent.currentHit, positioningOffset
                    )
            moddedOffset = positioningOffset > offset_min
            # print(f"defensive altered shot {agent.time}")

    # if destination and len(agent.allies) > 0 and destination[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team):
    #     destination = None

    if not destination:
        # _direction = direction(targetVec, attackTarget)
        positioningOffset = offset_min
        destination = targetVec + _direction.scale(positioningOffset)
        if agent.team != 3:
            if not is_mirror_shot:
                destination = get_aim_vector(
                    agent,
                    goalSpot.flatten(),
                    targetVec.flatten(),
                    agent.currentHit.pred_vel,
                    positioningOffset,
                )[0]
            else:
                destination = aim_wallshot_naive(
                    agent, agent.currentHit, positioningOffset
                )
        moddedOffset = False

    if moddedOffset:
        modifiedDelay = clamp(
            6,
            0,
            agent.currentHit.time_difference()
            - (
                (positioningOffset - offset_min)
                / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
            ),
        )

    else:
        modifiedDelay = agent.currentHit.time_difference()

    # result = timeDelayedMovement(agent, destination, agent.ballDelay,True)

    flipping = True

    if agent.team == 3:
        modifiedDelay -= agent.fakeDeltaTime

    destination.data[2] = agent.defaultElevation

    result = driveController(
        agent,
        destination,
        agent.time + modifiedDelay,
        expedite=expedite,
        flippant=flippant,
        flips_enabled=flipping,
    )

    # destination.data[2] = 75
    agent.renderCalls.append(
        renderCall(
            agent.renderer.draw_line_3d,
            agent.me.location.toList(),
            destination.toList(),
            agent.renderer.blue,
        )
    )

    return result

def findEnemyClosestToLocation(agent, location):
    if len(agent.enemies) > 0:
        closest = agent.enemies[0]
        cDist = math.inf
        for e in agent.enemies:
            x = findDistance(e.location, location)
            if x < cDist:
                cDist = x
                closest = e
        return closest, cDist
    else:
        return None, None


def findEnemyClosestToLocation3D(agent, location):
    if len(agent.enemies) > 0:
        closest = agent.enemies[0]
        cDist = math.inf
        for e in agent.enemies:
            if not e.demolished:
                x = distance2D(e.location, location)
                if x < cDist:
                    cDist = x
                    closest = e
        return closest, cDist
    else:
        return None, None


def findEnemyClosestToLocation2D(agent, location):
    if len(agent.enemies) > 0:
        closest = None
        cDist = math.inf
        for e in agent.enemies:
            if not e.demolished:
                x = distance2D(e.location, location)
                if x < cDist:
                    cDist = x
                    closest = e
        return closest, cDist
    else:
        return None, None


def findAllyClosestToLocation2D(agent, location):
    if len(agent.allies) > 0:
        closest = None
        cDist = math.inf
        for a in agent.allies:
            if not a.demolished:
                x = distance2D(a.location, location)
                if x < cDist:
                    cDist = x
                    closest = a
        return closest, cDist
    else:
        return None, None


def cornerDetection(_vec):
    # a simple function for determining if a vector is located within the corner of the field
    # if the vector is, will return the corner number, otherwise will return -1
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


def teammate_nearby(agent, location, distanceLimit):
    for a in agent.allies:
        e_dist = distance2D(agent.me.location, a.location)
        if e_dist <= distanceLimit:
            return True, e_dist

    return False, 0


def naive_hit_prediction(agent):
    primaryDirection = direction(
        agent.closestEnemyToBall.location, agent.enemyTargetVec
    )
    normed = primaryDirection.normalize()
    naivePosition = agent.currentHit.pred_vector + normed.scale(maxPossibleSpeed)
    placeVecWithinArena(naivePosition)
    return naivePosition


def handleBounceShot(agent, waitForShot=True, forceDefense=False):
    variance = 5
    leftPost = Vector([-sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    rightPost = Vector([sign(agent.team) * 450, 5200 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])
    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector
    mirrorShot = False

    offensive = agent.ball.location[1] * sign(agent.team) < 0

    # defensiveTouch = False
    if forceDefense:
        defensiveTouch = True
    else:
        defensiveTouch = (
            inTheMiddle(
                targetVec[1], [2000 * sign(agent.team), 5500 * sign(agent.team)]
            )
            and not agent.openGoal
            # and len(agent.enemies) > 1
        )
        if defensiveTouch:
            if agent.currentHit.hit_type != 4:
                if abs(targetVec[0]) > 1500 and not agent.ignore_kickoffs:
                    defensiveTouch = False

    # if agent.me.velocity[1] * sign(agent.team) > 0:
    #     defensiveTouch = True

    mirror_info = mirrorshot_qualifier(agent)
    is_mirror_shot = (
        mirror_info[0]
        and len(mirror_info[1]) < 1
        and agent.lastMan == agent.me.location
    )

    # if len(agent.allies) < 1 and offensive and agent.me.boostLevel < 50:
    #     if mirror_info[0] and 2 in mirror_info[1]:
    #         return playBack(agent)

    ballToGoalDist = distance2D(center, targetVec)
    targDistance = distance2D(agent.me.location, targetVec)
    dist3D = findDistance(agent.me.location, targetVec)
    carToGoalDistance = distance2D(agent.me.location, center)

    targetLocal = toLocal(targetVec, agent.me)
    carToTargAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

    ballLocal = agent.ball.local_location
    if abs(carToTargAngle) <= 40:
        carOffset = agent.carLength * 0.5
    elif abs(carToTargAngle) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5



    ballOffset = 91.25
    if agent.currentHit.pred_vector[2] <= agent.groundCutOff:
        ballOffset = get_ball_offset(agent,agent.currentHit)

    totalOffset = (carOffset + ballOffset) * 0.8
    # if targetVec[2] >= agent.double_point_limit:
    #     totalOffset = (carOffset + ballOffset) * 0.7
    offset_min = totalOffset * 0.9
    shotViable = False
    hurry = True

    corner = cornerDetection(targetVec)

    if len(agent.allies) < 1:
        if agent.team == 0:
            if corner == 0 or corner == 1:
                hurry = False
        else:
            if corner == 2 or corner == 3:
                hurry = False

    if (
        agent.goalPred == None
        and len(agent.allies) < 1
        and agent.currentHit.time_difference() - agent.enemyBallInterceptDelay >= 1
        and offensive
    ):
        hurry = False

    # shot_scorable = is_shot_scorable(targetVec, agent.enemyGoalLocations[0], agent.enemyGoalLocations[2])[2]
    # if not shot_scorable:
    #     if len(agent.allies) < 1:
    #         hurry = False

    # lined_up = extendToGoal(agent, targetVec, agent.me.location)
    #
    # require_lineup = False
    # if targetVec[1] * sign(agent.team) < -4000 and not lined_up and abs(targetVec[0]) < 2500:
    #     require_lineup = True

    futurePos = agent.me.location + (
        agent.me.velocity.scale(agent.currentHit.time_difference())
    )
    fpos_pred_distance = distance2D(futurePos, targetVec)

    if fpos_pred_distance <= totalOffset:
        shotViable = True

    goalSpot, ballGoalAngle = goal_selector_revised(agent, mode=0)
    if len(agent.allies) < 1:
        if abs(ballGoalAngle) >= agent.angleLimit:
            hurry = False
            if (
                agent.contested
                or agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                or agent.me.boostLevel < agent.boostThreshold
            ):
                return playBack(agent)
                # return thirdManPositioning(agent)

    # if len(agent.allies) == 0:
    challenge = interceptGuidance(agent, ballToGoalDist)
    if challenge[0]:
        return challenge[1]

    annoyingShot = False
    if targetVec[2] < agent.groundCutOff:
        annoyingShot = True

    ballToGoalDist = distance2D(center, targetVec)
    modifiedDelay = agent.currentHit.time_difference()
    waitingShotPosition = None

    bad_direction = direction(targetVec, myGoal).normalize()
    badPosition = targetVec + bad_direction.scale(offset_min)

    if defensiveTouch or is_mirror_shot:
        waitingShotPosition = aim_wallshot_naive(agent, agent.currentHit, offset_min)
        # badPosition = aim_wallshot_naive(agent,agent.currentHit,-(offset_min))

    if agent.team != 3 and waitingShotPosition == None:
        # waitingShotPosition = get_aim_vector(agent,goalSpot.flatten(), targetVec.flatten(), agent.currentHit.pred_vel,
        #                              totalOffset * 0.7)
        # badPosition = get_aim_vector(agent,goalSpot.flatten(), targetVec.flatten(), agent.currentHit.pred_vel,
        #                              -(totalOffset * 0.7))
        if agent.team == 4:
            target_position = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                totalOffset * 0.75,
            )
            if (
                abs(target_position[1]) <= 90
                or butterZone(targetVec)
                or targDistance >= 2000
            ):
                waitingShotPosition = target_position[0]
                # badPosition = get_aim_vector(agent, goalSpot.flatten(), targetVec.flatten(),
                #                             agent.currentHit.pred_vel, -(totalOffset*.75))[0]
            else:
                waitingShotPosition = aim_wallshot_naive(
                    agent, agent.currentHit, totalOffset * 0.75
                )
                # badPosition = aim_wallshot_naive(agent, agent.currentHit, -(totalOffset * .75))
                mirrorShot = True
        else:
            waitingShotPosition = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                offset_min,
            )[0]
            # badPosition = aim_wallshot_naive(agent, agent.currentHit, -(offset_min))

    positioningOffset = offset_min
    launching = False
    targetLoc = None
    boostHog = True
    # targetHeight,targetHeightTimer,heightMax,maxHeightTime
    if agent.currentHit.jumpSim == None:
        # agent.currentHit.jumpSim = jumpSimulatorNormalizing(agent,agent.currentHit.time_difference(),targetVec[2],doubleJump = targetVec[2] > agent.singleJumpLimit)
        agent.currentHit.jumpSim = jumpSimulatorNormalizingJit(
            float32(agent.gravity),
            float32(agent.fakeDeltaTime),
            np.array(agent.me.velocity, dtype=np.dtype(float)),
            float32(agent.defaultElevation),
            float32(agent.currentHit.time_difference()),
            float32(targetVec[2]),
            False,
        )

    variance = agent.fakeDeltaTime * 3
    # if agent.team == 1:
    #     variance = agent.fakeDeltaTime
    if annoyingShot:
        # shotlimit = 0.4
        # agent.log.append(f"we got an annoying shot here! {agent.time}")
        if agent.currentHit.jumpSim[1] != 0:
            shotlimit = clamp(0.6, 0.2, agent.currentHit.jumpSim[1] + variance)
        else:
            shotlimit = clamp(0.6, 0.2, agent.currentHit.jumpSim[3] + variance)

    else:
        maxValue = agent.doubleJumpShotTimer
        if agent.currentHit.hit_type == 1:
            maxValue = agent.singleJumpShotTimer

        if agent.currentHit.jumpSim[1] != 0:
            shotlimit = clamp(
                maxValue,
                agent.currentHit.jumpSim[1],
                agent.currentHit.jumpSim[1] + variance,
            )
        else:
            shotlimit = clamp(
                maxValue,
                agent.currentHit.jumpSim[3],
                agent.currentHit.jumpSim[3] + variance,
            )

    if (
        not defensiveTouch
        and agent.me.boostLevel > 0
        and agent.currentHit.hit_type != 4
        and not mirrorShot
    ):
        if agent.currentHit.time_difference() > shotlimit + 0.5 and targDistance > 500:
            offset = clamp(2000, offset_min, targDistance * 0.25)
            modifiedDelay = clamp(
                6,
                0.0001,
                agent.currentHit.time_difference()
                - (offset - (offset_min) / agent.currentSpd),
            )
            # modifiedDelay = clamp(6, 0.0001, agent.ballDelay - (
            #         (offset) / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)))
            # waitingShotPosition = targetVec.flatten() + direction(targetVec.flatten(),goalSpot.flatten()).scale(offset)
            waitingShotPosition = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                offset,
            )[0]

    if agent.currentHit.time_difference() <= shotlimit:

        if targetLoc == None:
            # if agent.contested or agent.goalward or len(agent.allies) > 0:
            if distance2D(futurePos, waitingShotPosition) < distance2D(
                futurePos, badPosition
            ):
                if agent.currentSpd * agent.currentHit.time_difference() >= clamp(
                    99999, 0, targDistance - totalOffset
                ):
                    if not agent.onWall and agent.onSurface:
                        if shotViable:
                            # if agent.team == 0:
                            #     targetLoc = targetVec
                            agent.createJumpChain(
                                agent.currentHit.time_difference(),
                                targetVec[2],
                                agent.currentHit.jumpSim,
                            )
                            targetLoc = targetVec
                            launching = True

    if agent.contested:
        maxRange = 1600
    else:
        maxRange = 800

    if not targetLoc:
        targetLoc = waitingShotPosition

    agent.renderCalls.append(
        renderCall(
            agent.renderer.draw_line_3d,
            agent.me.location.toList(),
            waitingShotPosition.flatten().toList(),
            agent.renderer.green,
        )
    )
    flipping = True
    if agent.me.location == agent.lastMan and agent.contested and agent.goalward and agent.me.location[1] * sign(agent.team) > targetVec[1] * sign(agent.team):
        flipping = False

    if len(agent.allies) >= 2:
        hurry = True

    return driveController(
        agent,
        targetLoc.flatten(),
        agent.time + modifiedDelay,
        expedite=hurry,
        flips_enabled=flipping,
    )


def playDefensive(agent):
    # centerGoal = Vector([0, 5200 * sign(agent.team), 200])
    # rightPost = Vector([900, 5200 * sign(agent.team), 200])
    # leftPost = Vector([-900, 5200 * sign(agent.team), 200])
    return gate(agent)


def prototype_rotations(agent):
    allies = agent.allies + [agent.me]
    sorted(allies, key=lambda x: x.index)
    relavent_data = []
    positions = []

    for ally in allies:
        relavent_data.append(
            [
                distance2D(ally.location, agent.ball.location),
                ally.location[1] * sign(ally.team)
                >= agent.ball.location[1] * sign(ally.team)
                or agent.ball.location[1] * sign(agent.team) < 4600,
                ally,
            ]
        )

    def find_next_man(ignore_positioning=False, ignore_retreating=False):

        best_canidate = None
        best_dist = math.inf

        for ally in relavent_data:
            if ally[2].index in positions:
                continue

            if not ignore_positioning and not ally[1]:
                continue

            if (
                not ignore_retreating
                and ally[2].retreating
                and agent.ball.location[1] * sign(agent.team) < 4600
            ):
                continue

            if ally[0] < best_dist:
                best_canidate = ally
                best_dist = ally[0]

        if best_canidate != None:
            return best_canidate

        else:
            if ignore_retreating:
                return find_next_man(ignore_positioning=True, ignore_retreating=True)
            else:
                return find_next_man(ignore_retreating=True)

    for i in range(int(clamp(4, 1, len(allies)))):
        positions.append(find_next_man()[2].index)

    if len(relavent_data) > 3:
        for ally in relavent_data:
            if ally[2].index not in positions:
                positions.append(ally[2].index)

    return positions


def assign_rotations(team_list, ball_location: Vector, lastman_location: Vector):
    def find_first(sides_matter=True, retreating_matters=True, goal_side_matters=True):
        best = None
        best_dist = math.inf

        for tm in team_list:
            if sides_matter:
                if ball_location[0] > 0:
                    if tm.location[0] < 0:
                        continue
                else:
                    if tm.location[0] > 0:
                        continue

            if retreating_matters:
                if tm.retreating:
                    continue

            if goal_side_matters:
                if tm.location[1] * sign(tm.team) < ball_location[1] * sign(tm.team):
                    continue

            dist = distance2D(tm.location, ball_location)

            if dist < best_dist:
                best_dist = dist
                best = tm

        if best == None:
            if sides_matter == False and retreating_matters == False:
                return find_first(
                    sides_matter=False,
                    retreating_matters=False,
                    goal_side_matters=False,
                )

            if sides_matter == False and retreating_matters == True:
                return find_first(sides_matter=False, retreating_matters=False)

            if sides_matter == True:
                return find_first(sides_matter=False)

            else:
                print("condition slipped through 'assign_rotations'!")
                return team_list[0]

        return best

    def find_second(first_loc, over_extended_bias=True):
        best_second = None
        best_dist = math.inf
        if ball_location[0] > 0:
            x = 2500
        else:
            x = -2500
        ideal_location = Vector(
            [x, ball_location[1] + sign(team_list[0].team) * 2500, 0]
        )

        for tm in team_list:
            if tm.location == first_loc:
                continue
            if over_extended_bias:
                if tm.location[1] * sign(tm.team) > ball_location[1] * sign(tm.team):
                    continue

            dist = distance2D(tm.location, ideal_location)
            if dist < best_dist:
                best_dist = dist
                best_second = tm

        if best_second == None:
            return find_second(first_loc, over_extended_bias=False)

        return best_second

    first_man = find_first()
    second_man = find_second(first_man.location)

    return first_man, second_man


def defensive_posture(agent):
    enemyShot = agent.enemyTargetVec
    guard_direction = direction(
        enemyShot.flatten(), Vector([0, 5200 * sign(agent.team), 0])
    )
    target = enemyShot + guard_direction.scale(
        clamp(
            1500, 600, distance2D(agent.enemyTargetVec, agent.closestEnemyToBall) * 0.5
        )
    )
    return driveController(agent, target, agent.time + agent.enemyBallInterceptDelay)


def SortHits(hit_list):
    no_nones = list(filter(None, hit_list))
    return sorted(no_nones, key=lambda x: x.prediction_time)


def secondManPositioning(agent):
    # if agent.team == 0:
    #     return playBack(agent,buffer = 3000,get_boost=True)

    playerGoal = Vector([0, 5200 * sign(agent.team), 0])

    boostTarget, dist = boostSwipe(agent)
    if (
        (
            boostTarget != None
            and dist < 2000
            and agent.me.boostLevel < 100
            and agent.me.location[1] * sign(agent.team)
            < agent.ball.location[1] * sign(agent.team)
        )
        or boostTarget != None
        and dist < 900
        and agent.me.boostLevel < 100
    ):
        return driveController(agent, boostTarget.flatten(), agent.time, expedite=True)

    offensive = agent.ball.location[1] * sign(agent.team) < 0

    # test demo code
    if agent.team == 3:
        # if len(agent.allies) > 1:
        if offensive or teammate_nearby(agent, playerGoal, 1200)[0]:
            agressive_demo = advancing_demo_handler(agent)
            if agressive_demo != None:
                # print(f"demo stuff {agent.time}")
                return agressive_demo

            if agent.ball.location[1] * sign(agent.team) > 0:
                if agent.ball.velocity[1] * sign(agent.team) > 5:
                    if not teammate_nearby(agent, playerGoal, 1500)[0]:
                        return smart_retreat(agent)
                if agent.lastMan != agent.me.location:
                    demo_action = naive_retreating_demo_handler(agent)
                    if demo_action != None:
                        # print(f"demo stuff {agent.time}")
                        return demo_action
    # if agent.team == 0:

    # x_target = agent.ball.location[0] + 3500
    # if agent.ball.location[0] > 0:
    #     x_target = agent.ball.location[0] - 3500

    x_target = agent.ball.location[0]+1000
    if agent.ball.location[0] < 0:
        x_target = agent.ball.location[0] - 1000

    x_target = clamp(2500,-2500,x_target)

    y_dist = 2500
    # if agent.team == 0:
    #     y_dist = 1500

    y_target = agent.ball.location[1] + (sign(agent.team) * y_dist)

    if abs(y_target) < 4500:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
        ):
            return rotate_back(agent)
            # pass
    # if agent.me.boostLevel < agent.boostThreshold and agent.ball.location[1] * -sign(agent.team) > 0:
    #     return backmanBoostGrabber(agent,buffer=3000,mode = 2)
    if agent.me.boostLevel < agent.boostThreshold:
        if agent.me.boostLevel >= 35:
            mode = 1
        else:
            mode = 0
        boost_suggestion = boost_suggester(agent, buffer=3000, mode=mode)
        if boost_suggestion != None:
            target = boost_suggestion.location.scale(1)
            # target.data[2] = 0
            return driveController(agent, target.flatten(), 0)

    if abs(y_target) < 4000:
        return driveController(
            agent,
            Vector([x_target, y_target, 0]),
            agent.time+10,
            expedite=False,
            maintainSpeed=True,
        )

    return smart_retreat(agent)



def thirdManPositioning(agent):
    playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    boostTarget, dist = boostSwipe(agent)
    if (
        (
            boostTarget != None
            and dist < 2000
            and agent.me.boostLevel < 100
            and agent.me.location[1] * sign(agent.team)
            < agent.ball.location[1] * sign(agent.team)
        )
        or boostTarget != None
        and dist < 900
        and agent.me.boostLevel < 100
    ):
        return driveController(agent, boostTarget, agent.time, expedite=True)

    offensive = agent.ball.location[1] * sign(agent.team) < 0

    # test demo code
    if agent.team == 3:
        # if len(agent.allies) >1:
        if offensive or teammate_nearby(agent, playerGoal, 1200)[0]:
            agressive_demo = advancing_demo_handler(agent)
            if agressive_demo != None:
                # print(f"demo stuff {agent.time}")
                return agressive_demo

            if agent.ball.location[1] * sign(agent.team) > 0:
                if agent.ball.velocity[1] * sign(agent.team) > 5:
                    if not teammate_nearby(agent, playerGoal, 1500)[0]:
                        return smart_retreat(agent)
                if agent.lastMan != agent.me.location:
                    demo_action = naive_retreating_demo_handler(agent)
                    if demo_action != None:
                        # print(f"demo stuff {agent.time}")
                        return demo_action


    x_target = 1500
    if agent.ball.location[0] > 0:
        x_target *= -1


    y_target = agent.ball.location[1] + (sign(agent.team) * 5500)

    if abs(y_target) < 4500:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
        ):
            return smart_retreat(agent)

        if (
            agent.me.boostLevel < agent.boostThreshold
            and agent.ball.location[1] * -sign(agent.team) > 0
        ):
            if agent.me.boostLevel >= 35:
                mode = 2
            else:
                mode = 0
            boost_suggestion = boost_suggester(agent, buffer=5000, mode=mode)
            if boost_suggestion != None:
                target = boost_suggestion.location.scale(1)
                target.data[2] = 0
                return driveController(agent, boost_suggestion.location.flatten(), 0)

        return driveController(
            agent,
            Vector([x_target, y_target, 0]),
            agent.time+10,
            expedite=False,
            maintainSpeed=True,
        )

    return smart_retreat(agent)


def playBack2(agent, buffer=5500):
    playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    enemyGoal = Vector([0, 5500 * -sign(agent.team), 200])
    ball_x = clamp(3200, -3200, agent.ball.location[0])

    if agent.rotationNumber != 3:
        _direction = direction(enemyGoal, agent.currentHit.pred_vector.flatten())
        centerField = agent.currentHit.pred_vector.flatten() - _direction.scale(buffer)
    else:
        _direction = direction(agent.enemyTargetVec, playerGoal)
        centerField = agent.enemyTargetVec.flatten() + _direction.scale(buffer)

    centerField.data[0] = clamp(3300, -3300, centerField[0])

    boostTarget, dist = boostSwipe(agent)
    if (
        boostTarget != None
        and dist < 1500
        and agent.me.boostLevel < 100
        and agent.me.location[1] * sign(agent.team)
        < agent.ball.location[1] * sign(agent.team)
    ):
        return driveController(agent, boostTarget, agent.time, expedite=True)

    agent.forward = True

    if centerField[1] * sign(agent.team) > 4000:
        if agent.me.location == agent.lastMan:
            return gate(agent)
        else:
            return goFarPost(agent)

    if agent.ball.location[1] * sign(agent.team) > 0:
        if agent.ball.velocity[1] * sign(agent.team) > 5:
            if not teammate_nearby(agent, playerGoal, 1000)[0]:
                return gate(agent)

    if len(agent.allies) > 0:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
        ):
            rightBoost = Vector([-3584.0, sign(agent.team) * 10, 73.0])
            leftBoost = Vector([3584.0, sign(agent.team) * 10, 73.0])

            backRightBoost = Vector([-3072, 4096 * sign(agent.team), 73.0])
            backLeftBoost = Vector([3072, 4096 * sign(agent.team), 73.0])

            if agent.me.location[1] * sign(agent.team) < 0:
                if agent.ball.location[0] > 0:
                    return driveController(
                        agent, rightBoost, agent.time, expedite=False
                    )
                else:
                    return driveController(agent, leftBoost, agent.time, expedite=False)
            else:
                if agent.ball.location[0] > 0:
                    return driveController(
                        agent, backRightBoost, agent.time, expedite=False
                    )
                else:
                    return driveController(
                        agent, backLeftBoost, agent.time, expedite=False
                    )

    if (
        agent.me.boostLevel < agent.boostThreshold
        and agent.ball.location[1] * sign(agent.team) < 0
    ):
        if len(agent.allies) < 1:
            return backmanBoostGrabber(agent)
        else:
            if agent.rotationNumber == 1:
                return backmanBoostGrabber(agent, buffer=1500)
            elif agent.rotationNumber == 2:
                return backmanBoostGrabber(agent, buffer=2500)
            else:
                return backmanBoostGrabber(agent, buffer=4500)

    else:
        if agent.rotationNumber != 2:
            agent.forward = True
            return driveController(
                agent, centerField, agent.time, expedite=False, maintainSpeed=True
            )
        else:
            return secondManPositioning(agent)


# def playBack(agent, buffer=4500):
#     #return playBack_old(agent,buffer = buffer)
#     playerGoal = Vector([0, sign(agent.team) * 5200, 0])
#     enemyGoal = Vector([0, 5500 * -sign(agent.team), 200])
#     ball_x = clamp(3200, -3200, agent.ball.location[0])
#
#     _direction = direction(enemyGoal, agent.currentHit.pred_vector.flatten())
#     centerField = agent.currentHit.pred_vector.flatten() - _direction.scale(buffer)
#
#     centerField.data[0] = clamp(3300, -3300, centerField[0])
#
#     boostTarget, dist = boostSwipe(agent)
#     if (
#         boostTarget != None
#         and dist < 2000
#         and agent.me.boostLevel < 100
#         and agent.me.location[1] * sign(agent.team)
#         < agent.ball.location[1] * sign(agent.team)
#     ):
#         return driveController(agent, boostTarget, agent.time, expedite=True)
#
#     if centerField[1] * sign(agent.team) > 4000:
#         region_info = teammate_nearby(agent, playerGoal, 500)
#         if region_info[0] and region_info[1] < distance2D(agent.me.location,playerGoal):
#             return goFarPost(agent)
#         else:
#             return gate(agent)
#
#     if agent.ball.location[1] * sign(agent.team) > 0:
#         if agent.ball.velocity[1] * sign(agent.team) > 5:
#             region_info = teammate_nearby(agent, playerGoal, 500)
#             if not region_info[0]:
#                 return gate(agent)
#
#     if len(agent.allies) > 0:
#         if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
#             agent.team
#         ):
#             # rightBoost = Vector([-3584.0, sign(agent.team) * 10, 73.0])
#             # leftBoost = Vector([3584.0, sign(agent.team) * 10, 73.0])
#
#             backRightBoost = Vector([-3072, 4096 * sign(agent.team), 73.0])
#             backLeftBoost = Vector([3072, 4096 * sign(agent.team), 73.0])
#
#             # if agent.me.location[1] * sign(agent.team) < 0:
#             #     if agent.ball.location[0] > 0:
#             #         return driveController(
#             #             agent, rightBoost, agent.time, expedite=False
#             #         )
#             #     else:
#             #         return driveController(agent, leftBoost, agent.time, expedite=False)
#             # else:
#             if agent.ball.location[0] > 0:
#                 return driveController(
#                     agent, backRightBoost, agent.time, expedite=False
#                 )
#             else:
#                 return driveController(
#                     agent, backLeftBoost, agent.time, expedite=False
#                 )
#
#     if (
#         agent.me.boostLevel < agent.boostThreshold
#         and agent.ball.location[1] * sign(agent.team) < 0
#     ):
#         if len(agent.allies) < 1:
#             return backmanBoostGrabber(agent)
#         else:
#             if agent.rotationNumber == 1:
#                 return backmanBoostGrabber(agent, buffer=1500)
#             elif agent.rotationNumber == 2:
#                 return backmanBoostGrabber(agent, buffer=2500)
#             else:
#                 return backmanBoostGrabber(agent, buffer=4500,stayOnSide=False)
#
#     else:
#         if agent.rotationNumber != 2:
#             agent.forward = True
#             return driveController(
#                 agent, centerField, agent.time, expedite=False, maintainSpeed=True
#             )
#         else:
#             return secondManPositioning(agent)


def goalie_shot(agent, goal_violator: hit):
    vec = goal_violator.pred_vector
    if abs(vec[0]) < 1000:
        if abs(vec[1]) * sign(agent.team) > 4300:
            if abs(vec[2]) < 1000:
                return True

    if agent.goalPred != None:
        if agent.goalPred.game_seconds - agent.time < 2.5:
            return True

    return False


def smart_retreat(agent):
    playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    if agent.lastMan == agent.me.location:
        return gate(agent)
    else:
        return goFarPost(agent)


def rotate_back(agent, onside=False):
    rightBoost = Vector([-3584.0, sign(agent.team) * 10, 73.0])
    leftBoost = Vector([3584.0, sign(agent.team) * 10, 73.0])

    backRightBoost = Vector([-3072, 4096 * sign(agent.team), 73.0])
    backLeftBoost = Vector([3072, 4096 * sign(agent.team), 73.0])

    if agent.ball.location[0] > 0 and not onside:
        difference = agent.me.location - rightBoost
    else:
        difference = agent.me.location - leftBoost

    if (
        agent.me.location[1] * sign(agent.team) < 0
        and agent.me.location != agent.lastMan
        and agent.ball.location[1] * sign(agent.team) < 0
        and len(agent.allies) > 0
        and abs(difference[0]) < abs(difference[1])
    ):
        if agent.ball.location[0] > 0 and not onside:
            return driveController(agent, rightBoost, agent.time, expedite=False)
        else:
            return driveController(agent, leftBoost, agent.time, expedite=False)
    else:
        if agent.ball.location[0] > 0 and not onside:
            return driveController(agent, backRightBoost, agent.time, expedite=False)
        else:
            return driveController(agent, backLeftBoost, agent.time, expedite=False)


def playBack(agent, buffer=6000, get_boost=True):
    playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    enemyGoal = Vector([0, 5500 * -sign(agent.team), 200])

    _direction = direction(agent.ball.location.flatten(), enemyGoal.flatten())
    fo_target = agent.ball.location + _direction.normalize().scale(4000)
    centerField = Vector(
        [
            clamp(2500, -2500, fo_target[0]),
            agent.ball.location[1] + sign(agent.team) * buffer,
            agent.defaultElevation,
        ]
    )

    boostTarget, dist = boostSwipe(agent)
    if (
        boostTarget != None
        and dist < 2000
        and agent.me.boostLevel < 100
        # and agent.me.location[1] * sign(agent.team)
        # < agent.ball.location[1] * sign(agent.team)
    ):
        return driveController(agent, boostTarget, agent.time, expedite=True)

    offensive = agent.ball.location[1] * sign(agent.team) < 0

    if agent.team == 0:
        if centerField[1] < -4500:
            return smart_retreat(agent)
    else:
        if centerField[1] > 4500:
            return smart_retreat(agent)

    if agent.ball.location[1] * sign(agent.team) > 0:
        if agent.ball.velocity[1] * sign(agent.team) > 5:
            if not teammate_nearby(agent, playerGoal, 700)[0]:
                return smart_retreat(agent)

    if len(agent.allies) > 1:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
        ):
            rightBoost = Vector([-3584.0, sign(agent.team) * 10, 73.0])
            leftBoost = Vector([3584.0, sign(agent.team) * 10, 73.0])

            backRightBoost = Vector([-3072, 4096 * sign(agent.team), 73.0])
            backLeftBoost = Vector([3072, 4096 * sign(agent.team), 73.0])

            if agent.me.location[1] * sign(agent.team) < 0:
                if agent.ball.location[0] > 0:
                    return driveController(
                        agent, rightBoost, agent.time, expedite=False
                    )
                else:
                    return driveController(agent, leftBoost, agent.time, expedite=False)
            else:
                if agent.ball.location[0] > 0:
                    return driveController(
                        agent, backRightBoost, agent.time, expedite=False
                    )
                else:
                    return driveController(
                        agent, backLeftBoost, agent.time, expedite=False
                    )

    if (
        agent.me.boostLevel < agent.boostThreshold
        and agent.ball.location[1] * -sign(agent.team) > 0
    ):
        boost_suggestion = boost_suggester(agent, buffer=3000, mode=1)
        if boost_suggestion != None:
            target = boost_suggestion.location.scale(1)
            # target.data[2] = 0
            # print(target.data[2])
            return driveController(agent, target, 0)

    else:
        agent.forward = True
        # centerField.data[1] = clamp(3500, -3500, centerField.data[1])
        return driveController(
            agent, centerField, agent.time+10, expedite=False, maintainSpeed=True
        )


def boostSwipe(agent):
    enemyBackBoostLocations = [
        Vector([3072, -sign(agent.team) * 4096, 0]),
        Vector([-3072, -sign(agent.team) * 4096, 0]),
    ]

    backBoosts = []
    minDist = math.inf
    bestBoost = None
    for b in agent.boosts:
        if b.bigBoost:
            if b.spawned:
                for eb in enemyBackBoostLocations:
                    if distance2D(eb, b.location) < 300:
                        backBoosts.append(eb)
                        dist = distance2D(eb, agent.me.location)
                        if dist < minDist:
                            bestBoost = eb
                            minDist = dist
                        # return b.location

    if bestBoost != None and minDist < 2000:
        agent.boost_gobbling = True

    return bestBoost, minDist


def bringToCorner(agent):
    print(f"in bring to corner! {agent.time}")
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
        carOffset = (agent.carLength / 3) * 0.5
    else:
        carOffset = (agent.carWidth / 2) * 0.5

    totalOffset = carOffset + get_ball_offset(agent,agent.currentHit)

    positioningOffset = totalOffset * 0.85
    if targVec[0] > 0:
        target = leftCorner
    else:
        target = rightCorner

    distance = distance2D(agent.me.location, targVec)
    targetLoc = None

    if abs(targVec[0]) > 2500 or distance < 500:
        _direction = direction(target, targVec)
        targetLoc = targVec - _direction.scale(totalOffset * 0.8)
        positioningOffset = totalOffset * 0.8
        modifiedDelay = agent.currentHit.time_difference()

    if not targetLoc:
        multiCap = clamp(0.5, 0.25, distance / 10000)
        multi = clamp(multiCap, 0.15, (5000 - abs(agent.me.location[0])) / 10000)
        _direction = direction(target, targVec)
        positioningOffset = clamp(1000, carOffset, distance * multi)
        targetLoc = targVec - _direction.scale(positioningOffset)
        modifiedDelay = clamp(
            6,
            0,
            agent.currentHit.time_difference() - (positioningOffset / agent.currentSpd),
        )
    # print(f"bringing to corner! {agent.time}")
    return driveController(
        agent, targetLoc, agent.time + modifiedDelay, expedite=True, flippant=True
    )


def shadowDefense(
    agent,
):  # remake shadow defense anticipating enemy hit trajectories as opposed to simply guarding net
    myGoal = Vector([0, 5200 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector

    distanceFromGoal = distance2D(targetVec, myGoal)

    _direction = direction(myGoal, targetVec)
    destination = myGoal - _direction.scale(distanceFromGoal * 0.5)

    return driveController(
        agent,
        destination,
        agent.time + agent.currentHit.time_difference(),
        expedite=False,
    )


def groundTackler(agent):
    center = Vector([0, 5500 * sign(agent.team), 200])
    target = agent.currentHit.pred_vector
    targetLocal = toLocal(target, agent.me)
    targDist = distance2D(agent.me.location, target)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

    if abs(carToBallAngle) <= 40:
        carOffset = agent.carLength * 0.6
    elif abs(carToBallAngle) >= 140:
        carOffset = agent.carLength * 0.2
    else:
        carOffset = agent.carWidth * 0.4

    ballOffset = 90
    totalOffset = (carOffset + ballOffset) * 0.8

    futurePos = agent.me.location + (agent.me.velocity.scale(agent.ballDelay))
    fpos_pred_distance = distance2D(futurePos, target)
    shotViable = False
    if fpos_pred_distance <= totalOffset:
        shotViable = True

    _direction = direction(target, center)

    targetLoc = target - _direction.scale(totalOffset * 0.5)

    if shotViable:
        if agent.enemyBallInterceptDelay < 0.3:
            agent.setJumping(6, target=agent.enemyTargetVec)
            agent.log.append(f"ground tacking! {agent.time}")
    return driveController(
        agent, targetLoc, agent.time + agent.enemyBallInterceptDelay, expedite=True
    )


def boostDrive(agent):
    closestBoostToMe = None
    closestBoostToMeDistance = math.inf
    bestTargetBoost = None
    bestTargetBoostDistance = math.inf

    for boost in agent.bigBoosts:
        dist = distance2D(agent.me.location, boost.location)
        if dist < closestBoostToMeDistance:
            closestBoostToMeDistance = dist
            closestBoostToMe = boost

        if agent.team == 0:
            if boost.location[1] > agent.currentHit.pred_vector[1]:
                if dist < bestTargetBoostDistance:
                    bestTargetBoostDistance = dist
                    bestTargetBoost = boost
        else:
            if boost.location[1] < agent.currentHit.pred_vector[1]:
                if dist < bestTargetBoostDistance:
                    bestTargetBoostDistance = dist
                    bestTargetBoost = boost

    if closestBoostToMeDistance <= 300:
        return driveController(
            agent, closestBoostToMe.location, agent.time, expedite=True
        )

    if bestTargetBoost != None:
        _direction = (
            bestTargetBoost.location - agent.currentHit.pred_vector
        ).normalize()
        offset = _direction.scale(90)
        destination = closestBoostToMe.location + offset
        return driveController(
            agent,
            destination,
            agent.time + agent.currentHit.time_difference(),
            expedite=True,
        )

    return None


def targetViable(agent, _vector):
    ballRadius = 93
    goalWidth = 893 - ballRadius
    goal_y = 5120 - ballRadius

    if abs(_vector[0]) <= 800:
        return True

    xDiff = abs(_vector[0]) - goalWidth
    y_diff = goal_y - abs(_vector[1])

    if y_diff >= xDiff * 4:
        # print(f"shot viable {agent.time}")
        return True

    # print(f"{_vector[0]} and {_vector[1]} not viable {agent.time}")
    return False


def get_around_ball(agent, hit, end_target):
    max_dist = 1000
    min_dist = 225

    _direction = direction(hit.pred_vector.flatten(), end_target.flatten())
    offset = clamp(max_dist, min_dist, distance2D(agent.me.location, end_target) * 0.4)

    drive_target = hit.pred_vector + _direction.scale(offset)
    placeVecWithinArena(drive_target)
    modifiedDelay = clamp(
        6,
        0.0001,
        hit.time_difference()
        - ((offset) / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)),
    )

    return driveController(agent, drive_target, modifiedDelay, expedite=True)


def lineupShot(agent, multi):
    variance = 5
    leftPost = Vector([-500, 5500 * -sign(agent.team), 200])
    rightPost = Vector([500, 5500 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])

    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector

    hurry = True
    distance = distance2D(agent.me.location, targetVec)
    # dist3D = findDistance(agent.me.location, targetVec)
    goalDist = distance2D(center, targetVec)
    ballToGoalDist = distance2D(targetVec, center)
    targetLocal = toLocal(targetVec, agent.me)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))
    carToGoalDistance = distance2D(center, agent.me.location)
    # carToBallDistance = distance2D(targetVec, agent.me.location)
    defensiveDistance = distance2D(agent.ball.location, myGoal)
    offensive = agent.ball.location[1] * sign(agent.team) < 0
    goalDistance = distance2D(targetVec, myGoal)
    carDistance = distance2D(agent.me.location, myGoal)

    carToBallAngle = correctAngle(carToBallAngle)

    _mode = 0
    if agent.scorePred:
        _mode = 1
    goalSpot, correctedAngle = goal_selector_revised(agent, mode=_mode)

    if len(agent.allies) < 1:
        if abs(correctedAngle) >= agent.angleLimit:
            hurry = False
            if (
                agent.contested
                or agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                or agent.me.boostLevel < agent.boostThreshold
            ):
                # if not butterZone(targetVec):
                return playBack(agent)
                # return thirdManPositioning(agent)

    corner = cornerDetection(targetVec)
    if len(agent.allies) < 1:
        if agent.team == 0:
            if corner == 0 or corner == 1:
                hurry = False
        else:
            if corner == 2 or corner == 3:
                hurry = False

    if (
        agent.goalPred == None
        and len(agent.allies) < 1
        and agent.currentHit.time_difference() - agent.enemyBallInterceptDelay >= 1
        and offensive
    ):
        hurry = False

    shot_scorable = is_shot_scorable(
        targetVec, agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]
    )[2]
    if not shot_scorable and len(agent.allies) < 1:
        hurry = False

    challenge = interceptGuidance(agent, defensiveDistance)
    if challenge[0]:
        return challenge[1]

    targetLoc = None

    if abs(carToBallAngle) <= 40:
        carOffset = agent.carLength * 0.5
    elif abs(carToBallAngle) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5

    ballOffset = get_ball_offset(agent, agent.currentHit)

    # totalOffset = carOffset + ballOffset
    totalOffset = (carOffset + ballOffset) * 0.9
    adjustedOffset = totalOffset * 1
    offset_min = totalOffset * 0.85

    # totalOffset *= 0.95

    positioningOffset = offset_min
    # print(offset_min)
    shotOffset = carOffset + ballOffset
    futurePos = agent.me.location + agent.me.velocity.scale(
        agent.currentHit.time_difference()
    )
    fpos_pred_distance = distance2D(futurePos, targetVec)
    shotViable = False
    adjustedOffset = carOffset + ballOffset
    if fpos_pred_distance <= adjustedOffset:
        shotViable = True

    lined_up = extendToGoal(agent, targetVec, agent.me.location)
    if lined_up and shot_scorable:
        hurry = True

    maxRange = 1800
    if agent.contested:
        maxRange = 800  # clamp(800,100,agent.closestEnemyToBallDistance)
        # maxRange = clamp(maxRange,100,agent.closestEnemyToBallDistance)

    shotlimit = 0.5

    _direction = direction(targetVec, goalSpot)

    max_dist_multi = 0.4
    if targetVec[1] * sign(agent.team) < 0:
        max_dist_multi = 0.5

    mirror_info = mirrorshot_qualifier(agent)
    is_mirror_shot = (
        mirror_info[0]
        and len(mirror_info[1]) < 1
        and distance < 3500
        and not offensive
        and agent.lastMan == agent.me.location
    )

    # if len(agent.allies) < 1 and offensive and agent.me.boostLevel < 50:
    #     if mirror_info[0] and 2 in mirror_info[1]:
    #         return playBack(agent)

    if (
        not is_mirror_shot
        and targetVec[2] >= agent.groundCutOff * 0.85
        and not agent.openGoal
        and ballToGoalDist > 3000
        and not agent.contested
    ):
        offset_min = totalOffset * 0.15
        positioningOffset = offset_min
        max_dist_multi = 0.25

    # else:
    # is_mirror_shot = mirror_info[0] and 3 not in mirror_info[1]

    # print(f"going for mirrorshot in lineup {agent.time}")

    challenge_flip(agent, targetVec)

    require_lineup = False
    if (
        targetVec[1] * sign(agent.team) < -3500
        and not lined_up
        and abs(targetVec[0]) < 3000
        and len(agent.allies) < 2
        and not is_mirror_shot
    ):
        require_lineup = True

    if agent.team == 3:
        test_direction = optimal_intercept_vector(
            targetVec.flatten(), agent.currentHit.pred_vel.flatten(), center.flatten()
        )
        if abs(angleBetweenVectors(agent.me.velocity, test_direction)) < 90:
            _direction = test_direction

    # if agent.openGoal:
    if agent.currentHit.time_difference() <= shotlimit:
        if agent.currentSpd >= 1500 or ballToGoalDist < 5000 or not agent.forward:
            if agent.me.boostLevel <= 5 or not agent.forward:
                if lined_up:
                    # if abs(carToBallAngle) <= 25:
                    if agent.currentHit.jumpSim == None:
                        agent.currentHit.jumpSim = jumpSimulatorNormalizingJit(
                            float32(agent.gravity),
                            float32(agent.fakeDeltaTime),
                            np.array(agent.me.velocity, dtype=np.dtype(float)),
                            float32(agent.defaultElevation),
                            float32(agent.currentHit.time_difference()),
                            float32(targetVec[2]),
                            False,
                        )
                        # if agent.currentSpd >= 1500 or ballToGoalDist < 5000:
                        if agent.currentSpd * agent.currentHit.time_difference() >= clamp(
                            99999, 0, distance - totalOffset * 1.1
                        ):
                            if not agent.onWall and agent.onSurface:
                                if shotViable:
                                    if (
                                        agent.openGoal
                                        or distance2D(
                                            agent.closestEnemyToBall.location, center
                                        )
                                        > carToGoalDistance
                                    ):
                                        # if fpos_pred_distance >= 75:
                                        if agent.forward:
                                            if abs(carToBallAngle) <= 35:
                                                agent.setJumping(0)
                                                agent.log.append("ground shot")
                                                targetLoc = get_aim_vector(
                                                    agent,
                                                    goalSpot.flatten(),
                                                    targetVec.flatten(),
                                                    agent.currentHit.pred_vel,
                                                    positioningOffset,
                                                )[0]
                                                modifiedDelay = (
                                                    agent.currentHit.time_difference()
                                                )
                                        else:
                                            if (
                                                abs(correctAngle(carToBallAngle - 180))
                                                < 45
                                            ):
                                                agent.setHalfFlip()
                                                agent.stubbornessTimer = 2
                                                agent.stubborness = agent.stubbornessMax
                                                targetLoc = get_aim_vector(
                                                    agent,
                                                    goalSpot.flatten(),
                                                    targetVec.flatten(),
                                                    agent.currentHit.pred_vel,
                                                    positioningOffset,
                                                )[0]
                                                modifiedDelay = (
                                                    agent.currentHit.time_difference()
                                                )

                        else:
                            pass
                            # if agent.currentSpd * agent.currentHit.time_difference() >= clamp(
                            #         99999, 0, distance - totalOffset * 1.1
                            # ):

    flipHappy = False

    challenge_flip(agent, targetVec)

    if (
        not targetLoc
        and agent.contested
        and not agent.openGoal
        and (not require_lineup or lined_up)
        and (
            distance2D(agent.closestEnemyToBall.location, center)
            < distance2D(agent.me.location, center)
        )
    ):
        if not is_mirror_shot:
            targetLoc = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
            )[0]

        else:
            targetLoc = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)
        modifiedDelay = agent.ballDelay

    if not targetLoc:
        if not agent.contested or require_lineup:
            # if ballToGoalDist < 5000:
            if abs(targetVec[0]) < 3000:
                if agent.forward:
                    if abs(targetVec[1]) < 4800:
                        positioningOffset = clamp(
                            maxRange, offset_min, distance * max_dist_multi
                        )
                        if not is_mirror_shot:
                            targetLoc = get_aim_vector(
                                agent,
                                goalSpot.flatten(),
                                targetVec.flatten(),
                                agent.currentHit.pred_vel,
                                positioningOffset,
                            )[0]

                        else:
                            targetLoc = aim_wallshot_naive(
                                agent, agent.currentHit, positioningOffset
                            )

                        modifiedDelay = agent.currentHit.time_difference()
                        if positioningOffset > offset_min:
                            modifiedDelay = clamp(
                                6,
                                0.0001,
                                agent.ballDelay
                                - (
                                    (positioningOffset - offset_min)
                                    / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                                ),
                            )

    if not targetLoc:
        if agent.forward and not agent.contested:
            if (
                sign(agent.team) * targetVec[1] <= 0
            ):  # or agent.openGoal: # or (agent.team == 0 and not agent.contested): #and agent.enemyBallInterceptDelay > 1:
                # capTop = max_dist_multi
                multiCap = clamp(max_dist_multi, 0.3, distance / 10000)
                # print("in second shot")
                multi = clamp(multiCap, 0.2, (5000 - abs(agent.me.location[0])) / 10000)
                positioningOffset = clamp(maxRange, offset_min, (distance * multi))
                # if agent.contested:
                #     positioningOffset = clamp(800,totalOffset*.5,positioningOffset)

                targetLoc = targetVec + _direction.scale(positioningOffset)
                if agent.team != 3:

                    if not is_mirror_shot:
                        targetLoc = get_aim_vector(
                            agent,
                            goalSpot.flatten(),
                            targetVec.flatten(),
                            agent.currentHit.pred_vel,
                            positioningOffset,
                        )[0]

                    else:
                        targetLoc = aim_wallshot_naive(
                            agent, agent.currentHit, positioningOffset
                        )

                modifiedDelay = agent.currentHit.time_difference()
                if positioningOffset > offset_min:
                    modifiedDelay = clamp(
                        6,
                        0.0001,
                        agent.ballDelay
                        - (
                            (positioningOffset - offset_min)
                            / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                        ),
                    )

    # if targetLoc and len(agent.allies) > 0 and targetLoc[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team):
    #     targetLoc = None

    if not targetLoc:
        # positioningOffset = totalOffset * 0.7
        targetLoc = targetVec + _direction.scale(positioningOffset)
        if agent.team != 3:
            positioningOffset = clamp(maxRange, offset_min, (distance * 0.15))
            if not is_mirror_shot:
                targetLoc = get_aim_vector(
                    agent,
                    goalSpot.flatten(),
                    targetVec.flatten(),
                    agent.currentHit.pred_vel,
                    positioningOffset,
                )[0]

            else:
                targetLoc = aim_wallshot_naive(
                    agent, agent.currentHit, positioningOffset
                )

        modifiedDelay = agent.currentHit.time_difference()
        if positioningOffset > offset_min:
            modifiedDelay = clamp(
                6,
                0.0001,
                agent.ballDelay
                - (
                    (positioningOffset - offset_min)
                    / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                ),
            )

    flipping = True
    targetLoc.data[2] = agent.defaultElevation
    if len(agent.allies) >= 2:
        hurry = True

    result = driveController(
        agent,
        targetLoc,
        agent.time + modifiedDelay,
        expedite=hurry,
        flippant=flipHappy,
        flips_enabled=flipping,
    )

    # targetLoc.data[2] = 95
    agent.renderCalls.append(
        renderCall(
            agent.renderer.draw_line_3d,
            agent.me.location.toList(),
            targetLoc.toList(),
            agent.renderer.purple,
        )
    )
    return result


def maxSpeedAdjustment(agent, target):
    tar_local = toLocal(target, agent.me)
    angle = abs(correctAngle(math.degrees(math.atan2(tar_local[1], tar_local[0]))))
    dist = findDistance(agent.me.location, target)
    distCorrection = dist / 300

    if dist >= 2000:
        return maxPossibleSpeed

    if abs(angle) <= 3:
        return maxPossibleSpeed

    if not agent.forward:
        return maxPossibleSpeed

    cost_inc = maxPossibleSpeed / 180
    if dist < 1200:
        cost_inc *= 2
    # angle = abs(angle) -10
    angle = abs(angle)
    newSpeed = clamp(maxPossibleSpeed, 350, maxPossibleSpeed - (angle * cost_inc))
    # print(f"adjusting speed to {newSpeed}")

    return newSpeed


def extend_to_sidewall(agent, targ_vec, startPos):
    _slope = simple_slope(startPos, targ_vec)
    slope = _slope[0] / _slope[1]
    if startPos[0] >= targ_vec[0]:
        x_diff = -(4096 - 93) - (targ_vec[0] - startPos[0])
        x_tar = -(4096 - 93)
    else:
        x_diff = (4096 - 93) - (targ_vec[0] - startPos[0])
        x_tar = 4096 - 93

    y_inter = targ_vec[1] + slope * x_diff

    return Vector([x_tar, y_inter, 0])


def extendToGoal(agent, ball_vec, startPos, buffer=120, send_back=False):

    acceptable = True

    if ball_vec[0] >= 893 and startPos[0] <= ball_vec[0]:
        acceptable = False

    if ball_vec[0] <= 893 and startPos[0] >= ball_vec[0]:
        acceptable = False

    if startPos[1] * sign(agent.team) < ball_vec[1] * sign(agent.team):
        acceptable = False

    _slope = simple_slope(startPos, ball_vec)
    if _slope[0] == 0:
        _slope.data[0] = 0.0001
    slope = _slope[1] / _slope[0]
    y_diff = ((5120 + 93) * -sign(agent.team)) - ball_vec[1]
    x_inter = ball_vec[0] + slope * y_diff
    if not send_back:
        return abs(x_inter) < 893 - buffer and acceptable
    else:
        return [abs(x_inter) < 893 - buffer and acceptable, x_inter]


def own_goal_check(agent, ball_vec, startPos, buffer=90, send_back=False):
    _slope = simple_slope(startPos, ball_vec)
    if _slope[0] == 0:
        _slope.data[0] = 0.0001
    slope = _slope[1] / _slope[0]
    y_diff = (5120 * sign(agent.team)) - ball_vec[1]
    x_inter = ball_vec[0] + slope * y_diff
    if not send_back:
        return abs(x_inter) < 893 - buffer
    else:
        return abs(x_inter) < 893 - buffer, x_inter


def direction(source, target) -> Vector:
    return (getLocation(source) - getLocation(target)).normalize()


def angle2(target_location, object_location):
    difference = getLocation(target_location) - getLocation(object_location)
    return math.atan2(difference[1], difference[0])


def getVelocity(_obj):
    return math.sqrt(sum([x * x for x in _obj]))


def getVelocity2D(_obj):
    return math.sqrt(sum[_obj.velocity[0] ** 2, _obj.velocity[0] ** 2])


def findDistance(origin, destination):
    difference = getLocation(origin) - getLocation(destination)
    return abs(math.sqrt(sum([x * x for x in difference])))


def distance2D(origin, destination):
    _origin = getLocation(origin)
    _destination = getLocation(destination)
    _origin = Vector([_origin[0], _origin[1]])
    _destination = Vector([_destination[0], _destination[1]])
    difference = _origin - _destination
    return abs(math.sqrt(sum([x * x for x in difference])))


def weighted_distance_2D(origin, destination):
    _origin = getLocation(origin).flatten()
    _destination = getLocation(destination).flatten()
    difference = _origin - _destination
    difference.data[0] = difference[0] * 1.5
    return abs(math.sqrt(sum([x * x for x in difference])))


def correctAngle(x):
    y = x * 1
    if y > 360:
        y -= 360
    if y < -360:
        y += 360

    if y > 180:
        y = 360
    elif y < -180:
        y += 360

    return y


def localizeVector(target_object, our_object):
    x = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
        our_object.matrix[0]
    )
    y = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
        our_object.matrix[1]
    )
    z = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
        our_object.matrix[2]
    )
    return Vector([x, y, z])


# def cast_local(self, global_vector: Vec3) -> Vec3:
#     return Vec3(
#         global_vector.dot(self.forward),
#         global_vector.dot(self.right),
#         global_vector.dot(self.up)
# )


def localizeRotation(target_rotation, agent):
    return Vector(
        [
            target_rotation.dotProduct(agent._forward),
            target_rotation.dotProduct(agent.left),
            target_rotation.dotProduct(agent.up),
        ]
    )


def toLocal(target, our_object):
    if isinstance(target, physicsObject):
        return target.local_location
    else:
        return localizeVector(target, our_object)


def ruleOneCheck(agent):
    if agent.closestEnemyToMeDistance < 250:
        if agent.currentSpd < 200:
            if relativeSpeed(agent.me.velocity, agent.closestEnemyToMe.velocity) < 100:
                return True
    if len(agent.allies) > 0:
        for ally in agent.allies:
            if distance2D(agent.me.location, ally.location) < 200:
                if relativeSpeed(agent.me.velocity, ally.velocity) < 100:
                    return True

    return False


def aim_adjustment(velocity, team):
    vel = velocity.flatten()
    mag = vel.magnitude()
    return vel.normalize().scale(clamp(50, 0, mag / 40))


def get_aim_vector(
    agent, end_target_vec, target_ball_vec, target_ball_velocity, offset_length
):
    _direction = direction(target_ball_vec.flatten(), end_target_vec.flatten())
    vel_offset = aim_adjustment(target_ball_velocity, agent.team)
    # if agent.team == 1 and target_ball_vec[1] < -10 or agent.team == 0 and target_ball_vec[1] > 10:
    #     vel_offset = Vector([0,0,0])
    _direction_offset = _direction.scale(offset_length - vel_offset.magnitude())
    angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), _direction)

    # if (_direction_offset+vel_offset).magnitude() > offset_length:
    #     print(f"We got issues in gem aim: target offset == {offset_length}. Returned offset: {(_direction_offset+vel_offset).magnitude()}")
    # if agent.team == 1:
    #     return target_ball_vec + (_direction_offset + vel_offset), angle
    # else:
    return target_ball_vec + _direction.scale(offset_length), angle


def aim_back_corner(agent, _hit, offset_length):
    corner_1 = Vector([4190, -sign(agent.team) * 5120, 0])
    corner_2 = Vector([-4190, -sign(agent.team) * 5120, 0])
    target_vec = _hit.pred_vector

    target_corner = corner_2
    if agent.me.location[0] < target_vec[0]:
        target_corner = corner_1

    return get_aim_vector(
        agent, target_corner, target_vec, _hit.pred_vel, offset_length
    )[0]


def aim_wallshot_naive(agent, _hit, offset_length):
    # if agent.team == 0:
    #   return aim_back_corner(agent, _hit, offset_length)
    target_vec = _hit.pred_vector
    # aiming short corner
    goal_x = -300

    if agent.me.location[0] >= target_vec[0]:
        goal_x = 300


    enemy_goal = Vector([0, (5120+agent.ball_size*2) * -sign(agent.team), 0])

    enemy_goal.data[0] = (4096 * 2)+goal_x
    if agent.me.location[0] > target_vec[0]:
        enemy_goal.data[0] = -(4096 * 2)+goal_x

    # extend the shot through the wall to the mirrors goal as if the vector never flipped

    return get_aim_vector(agent, enemy_goal, target_vec, _hit.pred_vel, offset_length)[
        0
    ]


def unroll_path_from_ground_to_wall(target_location: Vector) -> Vector:

    # orange back wall = north
    # 0 = orange backboard, 1 = east wall, 2 = blue backboard, 3 = west wall
    wall = which_wall(target_location)

    if wall in [0, 2]:
        index_g, index_a = 1, 2
    else:
        index_g, index_a = 0, 2

    ground_target = target_location.scale(1)
    if ground_target.data[index_g] > 0:
        ground_target.data[index_g] += target_location[index_a]
    else:
        ground_target.data[index_g] -= target_location[index_a]

    ground_target.data[index_a] = 0
    # if wall == 0:
    #     ground_target.data[1]+=200
    # elif wall == 1:
    #     ground_target.data[0]-=200
    # elif wall == 2:
    #     ground_target.data[1]-=200
    # else:
    #     ground_target.data[0] += 200

    return ground_target


def unroll_path_from_wall_to_ground(
    agent_location: Vector, target_location: Vector
) -> Vector:

    # orange back wall = north
    # 0 = orange backboard, 1 = east wall, 2 = blue backboard, 3 = west wall

    wall = which_wall(agent_location)
    wall_target = target_location.scale(1)
    wall_target.data[2] = 0

    if wall in [0, 2]:
        y_diff = distance2D(Vector([0, agent_location[1]]), Vector([0, wall_target[1]]))
        wall_target.data[2] = -y_diff
        wall_target.data[1] = agent_location[1]

    elif wall in [1, 3]:
        # index_g,index_a = 0,2
        x_diff = distance2D(Vector([agent_location[0], 0]), Vector([wall_target[0], 0]))
        wall_target.data[2] = -x_diff
        wall_target.data[0] = agent_location[0]

    else:
        wall_target.data[2] = -200

    # if wall == 0:
    #     wall_target.data[1]-=200
    # elif wall == 1:
    #     wall_target.data[0]+=200
    # elif wall == 2:
    #     wall_target.data[1]+=200
    # else:
    #     wall_target.data[0] -= 200

    return wall_target


def relativeSpeed(vec_a, vec_b):
    # takes in 2 velocity vectors and returns the relative speed difference
    return (vec_a - vec_b).magnitude()


def dirtyCarryCheck(agent):
    # return False

    maxRange = 250
    ball_distance = findDistance(agent.me.location, agent.ball.location)
    acceptableDistance = ball_distance <= maxRange

    error = ""

    ballRadius = 93
    # print("being called")
    if agent.onSurface:
        if abs(agent.ball.location[0]) < 3900:
            if not agent.onWall:
                if agent.touch.player_index == agent.index:
                    # if agent.time - agent.touch.time_seconds < 1:
                    if acceptableDistance:
                        if (
                            agent.ball.location[2] >= ballRadius + 20
                            and distance2D(agent.me.location, agent.ball.location) < 155
                        ):
                            # if (
                            #     relativeSpeed(
                            #         agent.ball.velocity, agent.me.velocity
                            #     )
                            #     <= 500
                            # ):
                            # print("dribbling")
                            # print(f"True {ball_distance} {agent.ball.location[2]}")
                            return True

    # print(f"False {ball_distance} {agent.ball.location[2]} {error}")
    return False


# self.current_time = current_time
#         self.prediction_time = prediction_time
#         self.hit_type = hit_type  # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot,5 aerial shot
#         self.pred_vector = pred_vector
#         self.pred_vel = pred_vel
#         self.guarenteed_hittable = hittable
#         self.fastestArrival = fastestTime
#         self.jumpSim = jumpSim
#         self.aerialState = aerialState


def ballCatchViable(agent):
    if agent.hits[1] != None:
        if not agent.openGoal:
            if abs(agent.hits[1].pred_vector[0]) < 3800 or abs(
                agent.me.location[0]
            ) > abs(agent.hits[1].pred_vector[0]):
                if abs(agent.hits[1].pred_vector[1]) < 4200:
                    if not ballHeadedTowardsMyGoal_testing(agent, agent.hits[1]):
                        if (
                            agent.hits[1].prediction_time - agent.time
                            < (agent.enemyBallInterceptDelay - agent.contestedTimeLimit)
                            - 0.5
                        ):
                            if not agent.contested:
                                if not butterZone(agent.hits[1].pred_vector):
                                    if not extendToGoal(
                                        agent,
                                        agent.hits[1].pred_vector,
                                        agent.me.location,
                                    ):
                                        if agent.me.boostLevel >= 20:
                                            return True

    return False


def new_ball_catcher(agent):
    center = Vector([0, 5200 * -sign(agent.team), 200])
    _direction = optimal_intercept_vector(
        agent.currentHit.pred_vector, agent.currentHit.pred_vel, center
    )
    return driveController(
        agent,
        agent.currentHit.pred_vector + _direction.scale(15),
        agent.time + agent.currentHit.time_difference(),
        expedite=True,
    )


def catch_ball(agent):  # should be called from lineupshot()
    return catch_ball_revised(agent)
    # print(f"catching ball {agent.time}")
    center = Vector([0, 5200 * -sign(agent.team), 200])

    maxOffset = 12
    if agent.goalward:
        maxOffset = 25
    targetVec = agent.currentHit.pred_vector

    ball_velocity = agent.currentHit.pred_vel
    if agent.currentHit.pred_vel.magnitude() > 0:
        vel_offset = clamp(25, 1, agent.currentHit.pred_vel.magnitude() / 100)
    else:
        vel_offset = 0

    _direction = direction(targetVec, center)
    targetLoc = (
        targetVec
        + _direction.scale(maxOffset)
        + ball_velocity.flatten().normalize().scale(vel_offset)
    )
    # print(f"catching {agent.time}")
    return driveController(
        agent,
        targetLoc,
        agent.time + agent.currentHit.time_difference(),
        expedite=True,
    )


def catch_ball_revised(agent):
    print(f"catching {agent.time}")
    center = Vector([0, 5200 * -sign(agent.team), 200])
    targetVec = agent.currentHit.pred_vector
    max_offset = 20
    momentum_offset = (
        agent.currentHit.pred_vel.flatten()
        .normalize()
        .scale(agent.currentHit.pred_vel.magnitude() / 100)
    )
    momentum_offset += direction(targetVec, center).scale(5)

    if momentum_offset.magnitude() > max_offset:
        momentum_offset = momentum_offset.normalize().scale(max_offset)

    destination = targetVec.flatten() + momentum_offset

    return driveController(
        agent,
        destination,
        agent.time + agent.currentHit.time_difference(),
        expedite=True,
    )


def simple_slope(p1: Vector, p2: Vector):
    return Vector([(p2[1] - p1[1]), (p2[0] - p1[0])])


def enough_takeoff_room(agent, target):

    height = target.data[2]
    distance = distance2D(agent.me.location, target)

    if distance >= height * 0.85:
        return True, 0

    if agent.currentSpd < 500:
        return True, 0

    return False, -1


def takeoff_goldielox_zone(agent, target):
    height = target.data[2]
    distance = distance2D(agent.me.location, target)

    if distance > height * 0.85 and distance < height * 1.15:
        return True, 0
    if distance > height * 1.15:
        return False, 1

    if distance < height * 0.85:
        return False, -1

    print("omg, what happened?!?!?")
    return False, -5


def newCarry(agent):
    center = Vector([0, 5500 * -sign(agent.team), 200])
    _direction = direction(agent.ball.location, center)
    directionIncrement = _direction.scale(1 / 60)

    ballVelocity2D = Vector(agent.ball.velocity.data).flatten()
    carVelocity2D = Vector(agent.me.velocity.data).flatten()
    relativeVelocity = carVelocity2D - ballVelocity2D

    RV_increment = relativeVelocity.scale(1 / 60)
    hybridIncrement = RV_increment - directionIncrement

    destination = agent.ball.location + hybridIncrement
    cradled = False
    if (
        agent.touch.player_index == agent.index
        and findDistance(agent.me.location, agent.ball.location) < 160
    ):
        if agent.ball.location[2] <= 140:
            cradled = True

    flick = False
    if (agent.contested) or agent.closestEnemyToBallDistance <= 600:
        flick = True

    elif distance2D(agent.me.location, center) < 1500:
        flick = True

    if flick and cradled:
        # print("flicking!")
        agent.setJumping(0)

    return driveController(agent, destination, agent.time + (1 / 60))


# def optimal_intercept_vector(collider_location: np.ndarray, collider_velocity: np.ndarray, target_location: np.ndarray):
#     """Provides vector for correcting an object's velocity vector towards the target vector"""
#     target_dir = normalize(target_location - collider_location)
#     correct_vel = dot(collider_velocity, target_dir) * target_dir
#     incorrect_vel = collider_velocity - correct_vel
#     extra_vel = math.sqrt(math.pow(6000, 2) - math.pow(norm(incorrect_vel), 2))
#     return target_dir * extra_vel - incorrect_vel


def challenge_flip(agent, targetVec):
    # challenge disabled 103:48 @ 70 minutes kam(blue) in lead vs Diablo
    # 74:34 @ 64 minutes as orange
    if agent.team == 5:
        if distance2D(agent.me.location, agent.ball.location) <= 200:
            if targetVec[2] <= 120 and agent.ball.location[2] <= 120:
                if len(agent.enemies) > 0:
                    if (
                        distance2D(
                            agent.closestEnemyToBall.location, agent.ball.location
                        )
                        < 450
                    ):
                        if agent.closestEnemyToBall.location[1] * sign(
                            agent.team
                        ) < agent.me.location[1] * sign(agent.team):
                            # print("challenge flipping")
                            agent.setJumping(0)


def mirrorshot_qualifier(agent):
    center_limit = 500
    wall_buffer = 93

    error_codes = []

    center = Vector([0, 5200 * -sign(agent.team), 0])
    targetVec = agent.currentHit.pred_vector

    # return False,error_codes

    if agent.me.location[1] * sign(agent.team) < targetVec[1] * sign(agent.team):
        # return False
        # error 1 : bot on wrong side of the ball
        error_codes.append(1)

    wall_inter = extend_to_sidewall(agent, targetVec, agent.me.location)
    if wall_inter[1] * -sign(agent.team) < -3800:
        # return False
        # error 2: mirror shot would bounce off corner
        error_codes.append(2)

    x_scale = 1
    x_scale += abs(targetVec[0]) / (4096 - 95)

    if butterZone(targetVec) and targetVec[1] * sign(agent.team) < 0:
        # error 3: ball is right in front of enemy goal
        error_codes.append(3)

    if distance2D(targetVec, agent.me.location) > 5000:
        # error 4: ball is too far away to force locking into mirror shot
        error_codes.append(4)

    # if len(agent.enemies) >= 2: #and agent.team == 0:
    #     error_codes.append(5)
    # pass

    # if abs(targetVec[0]) > 4096-wall_buffer: # and agent.team == 0:
    #     error_codes.append(6)

    # if targetVec[1] * sign(agent.team) < 0 and len(agent.allies) > 1:
    #     error_codes.append(7)

    vec_difference = targetVec.flatten() - agent.me.location.flatten()

    if abs(vec_difference[0]) * x_scale >= abs(vec_difference[1]):
        if targetVec[0] >= center_limit and agent.me.location[0] < targetVec[0]:
            return True, error_codes

        if targetVec[0] < -center_limit and agent.me.location[0] > targetVec[0]:
            return True, error_codes

    return False, error_codes


def optimal_intercept_vector(
    collider_location: Vector, collider_velocity: Vector, target_location: Vector
):
    """Provides vector for correcting an object's velocity vector towards the target vector"""
    target_dir = (target_location - collider_location).normalize()
    correct_vel = target_dir.scale(collider_velocity.dotProduct(target_dir))
    incorrect_vel = collider_velocity - correct_vel
    extra_vel = math.sqrt(math.pow(6000, 2) - math.pow(incorrect_vel.magnitude(), 2))
    return (target_dir.scale(extra_vel) - incorrect_vel).normalize().scale(-1)


def norm(vec: np.ndarray):
    return math.sqrt(math.pow(vec[0], 2) + math.pow(vec[1], 2) + math.pow(vec[2], 2))


def angleBetweenVectors(vec1: Vector, vec2: Vector):
    return math.degrees(math.acos((vec1.normalize().dotProduct(vec2.normalize()))))
    # return math.degrees(math.acos((vec1.normalize().dotProduct(vec2.normalize()))))


def dribble_carry_revised(agent):
    target_speed = 1050
    max_offset = 30
    if agent.me.boostLevel > 20 and agent.forward:
        max_offset = 40

    speed_limiter = 0
    alignment_cap = 500
    y_targ = 5250 * -sign(agent.team)
    x_targ = 0
    if agent.ball.location[0] > 1200:
        x_targ = -400
    elif agent.ball.location[0] < -1200:
        x_targ = 400
    min_offset = 8
    if not agent.forward:
        min_offset = 12

    carry_delay = 20  # agent.ball.velocity.magnitude()/10 # how many frames ahead are we shooting for?
    cradled = agent.ball.location[2] <= agent.carHeight + 125
    cradle_location = agent.ball.location.flatten() + agent.ball.velocity.flatten().scale(
        agent.fakeDeltaTime * carry_delay
    )
    current_trajectory = agent.ball.velocity.flatten().normalize()

    extend_info = extendToGoal(
        agent,
        agent.ball.location.flatten(),
        agent.ball.location.flatten()
        - agent.ball.velocity.flatten().normalize().scale(20),
        send_back=True,
    )

    extend_info[0] = (
        extend_info[0]
        and distance2D(Vector([0, 5250 * -sign(agent.team), 0]), agent.ball.location)
        > 3000
    )

    if not agent.scorePred:

        if not extend_info[0]:
            if (
                extend_info[1] > 0
                and agent.me.location[0] > 0
                or extend_info[1] < 0
                and agent.me.location[0] < 0
            ):

                test_y_targ = agent.ball.location[1] + 200 * -sign(agent.team)
                if abs(test_y_targ) < 5250:
                    y_targ = test_y_targ

    enemy_goal = Vector([x_targ, y_targ, 0])
    target_trajectory = (cradle_location - enemy_goal).normalize()

    # happy = (agent.scorePred != None or extend_info[0]) and (agent.ball.velocity.flatten().magnitude() < target_speed and abs(target_speed - agent.ball.velocity.flatten().magnitude()) < 250)
    happy = agent.scorePred != None or extend_info[0]  # and (
    #     agent.ball.velocity.flatten().magnitude() < target_speed and abs(
    # target_speed - agent.ball.velocity.flatten().magnitude()) < 200)

    if (not cradled or happy) and agent.ball.velocity.magnitude() >= target_speed - 500:
        offset = min_offset
        if not cradled and agent.me.boostLevel > 10:
            offset = min_offset * 1.5
    else:
        offset = max_offset

    flick = (
        agent.enemyBallInterceptDelay <= 0.55
    ) or agent.closestEnemyToBallDistance <= clamp(
        1000, 500, agent.ball.velocity.magnitude() * 0.6
    )

    if (
        cradled
        and not agent.scorePred
        and cradle_location[1] * sign(agent.team) < -4300
        and abs(cradle_location[0]) < 1100
    ):
        flick = True

    speed_alignment = (
        clamp(1, 0.0, (agent.ball.velocity.magnitude() - target_speed) * 1.0) / 500.0
    )

    targetDirection = optimal_intercept_vector(
        cradle_location.flatten(), agent.ball.velocity.flatten(), enemy_goal.flatten()
    )

    # blended_direction = (agent.ball.velocity.flatten().normalize().scale(speed_alignment)+ targetDirection.scale(1-speed_alignment)).normalize()
    blended_direction = agent.ball.velocity.flatten().normalize().scale(
        speed_alignment
    ) + targetDirection.scale(1 - speed_alignment)

    target = cradle_location + blended_direction.scale(offset)

    if flick:
        if cradled:
            if (
                agent.scorePred != None
                and findDistance(agent.me.location, agent.ball.location) < 135
            ):  # and distance2D(agent.ball.location,enemy_goal) > 1500:
                if (
                    distance2D(
                        agent.me.location, Vector([0, 5200 * -sign(agent.team), 0])
                    )
                    > 3000
                ):
                    # print("greater than 3k")
                    agent.setJumping(20)
                    # agent.setJumping(2)
                    # print("big pop!")
                else:
                    # print("closer than 3k")
                    agent.setJumping(20)
                    # print("medium pop")
            else:
                # print("not on target")
                agent.setJumping(0)
                # print(f"mini jump? {agent.time}")
        else:
            if (
                distance2D(agent.me.location, agent.ball.location) < 40
                and agent.enemyAttacking
                and not agent.scorePred
            ):
                # agent.setJumping(2)
                # print("forcing hop")
                agent.setJumping(2)

    # print(f"cradled: {cradled} happy: {happy}  {agent.time}")

    if (
        cradled
        and agent.ball.velocity[1] * sign(agent.team) > 50
        and agent.ball.location[1] * sign(agent.team) > 3500
    ):
        agent.setJumping(0)

    return driveController(
        agent, target, agent.time + carry_delay * agent.fakeDeltaTime, expedite=True
    )


def carry_flick_new(agent, cradled=False):

    return dribble_carry_revised(agent)

    if abs(agent.me.location[0]) > 800:
        yTarget = 5000
    else:
        yTarget = 5500

    center = Vector([0, yTarget * -sign(agent.team), 0])  # 5500 * sign(agent.team)
    # center = Vector([0, 0, 0])
    minOffset = 5
    flick = False
    cradled = False
    lameFlick = False

    if (
        agent.touch.player_index == agent.index
        and findDistance(agent.me.location, agent.ball.location) < 160
    ):
        if agent.ball.location[2] <= agent.carHeight + 118:
            cradled = True

    # if agent.enemyBallInterceptDelay <= 0.5 or agent.closestEnemyToBallDistance <= 600:
    #     flick = True
    #     if butterZone(agent.ball.location):
    #         # if agent.team == 1:
    #         lameFlick = True

    if agent.scorePred != None:
        lameFlick = True

    if butterZone(agent.ball.location):
        if agent.me.location[1] * sign(agent.team) > 3500:
            flick = True
            agent.log.append(f"bad dribble position! {agent.time}")

    if agent.ball.velocity[1] * -sign(agent.team) < -200:
        flick = True
        agent.log.append(f"bad dribble velocity {agent.time}")

    deltaCount = 2

    timeWindow = agent.fakeDeltaTime * deltaCount

    # availableAcceleration = getNaturalAccelerationJitted(agent.currentSpd) * deltaCount
    availableAcceleration = getNaturalAccelerationJitted(
        agent.currentSpd, agent.gravity, False
    )
    if (
        agent.forward
        and agent.me.boostLevel > 5
        and agent.currentSpd < maxPossibleSpeed
    ):
        availableAcceleration += 991.666 * deltaCount
        # pass

    speedTarget = 1000

    offsetCap = clamp(30, minOffset, availableAcceleration * agent.fakeDeltaTime)
    vel_norm = agent.ball.velocity.flatten().normalize()

    cradlePos = (
        agent.ball.location.flatten()
        + agent.ball.velocity.flatten().scale(timeWindow)
        + agent.ball.velocity.flatten().normalize().scale(-8)
    )

    # targetDirection = (cradlePos.flatten() - center.flatten()).normalize()
    targetDirection = optimal_intercept_vector(
        cradlePos.flatten(), agent.ball.velocity.flatten(), center.flatten()
    )

    vel_correction = (vel_norm + targetDirection).normalize()
    difference = (
        vel_correction.scale(speedTarget) - agent.ball.velocity.flatten()
    ).magnitude()
    offset = clamp(offsetCap, minOffset, difference)

    testPosition = cradlePos + vel_correction.scale(offset)

    if flick and cradled:
        if agent.scorePred != None:
            agent.setJumping(2)
            agent.log.append("lame flicking")
        else:
            agent.setJumping(0)

    return driveController(
        agent, testPosition, agent.time + timeWindow, expedite=agent.currentSpd > 1200
    )


def carry_flick(agent, cradled=False):
    center = Vector([0, 5500 * -sign(agent.team), 200])
    if agent.scorePred == None:
        if abs(agent.ball.location[1] + (1000 * -sign(agent.team))) < 5500:
            center.data[1] = agent.ball.location[1] + (1000 * -sign(agent.team))

    offsetCap = 30
    minOffset = 5
    if agent.me.boostLevel >= 5:
        if agent.forward:
            if agent.currentSpd <= maxPossibleSpeed - 100:
                if agent.scorePred == None:
                    offsetCap = 45
    flick = False

    if agent.hits[1] != None:
        agent.currentHit = agent.hits[1]

    targetVec = agent.currentHit.pred_vector
    delay = agent.currentHit.time_difference()
    dist2D = distance2D(agent.me.location, center)

    targetLocal = toLocal(targetVec, agent.me)
    carToBallAngle = correctAngle(
        math.degrees(math.atan2(targetLocal[1], targetLocal[0]))
    )

    goalTarget, angle = goal_selector_revised(agent, mode=0)

    goalLocal = toLocal(goalTarget, agent.me)
    goalAngle = math.degrees(math.atan2(goalLocal[1], goalLocal[0]))
    goalAngle = correctAngle(goalAngle)

    if (
        agent.touch.player_index == agent.index
        and findDistance(agent.me.location, agent.ball.location) < 160
    ):
        if agent.ball.location[2] <= agent.carHeight + 118:
            cradled = True
    if (
        agent.enemyBallInterceptDelay <= 0.8 and agent.enemyAttacking
    ) or agent.closestEnemyToBallDistance <= 500:
        flick = True

    offset = clamp(
        offsetCap, minOffset, ((abs(carToBallAngle) + abs(goalAngle) * 5) / 2) * 16
    )

    targetLoc = findOppositeSide(agent, targetVec, goalTarget, offset)

    if flick and cradled:
        if agent.scorePred == None:
            agent.setJumping(0)
        else:
            agent.setJumping(2)

    targetLoc.data[2] = agent.defaultElevation

    return driveController(agent, targetLoc, agent.time + delay, expedite=True)


def inTheMiddle(testNumber, guardNumbersList):
    return min(guardNumbersList) <= testNumber <= max(guardNumbersList)


"""
# orange = north
    if destination[1] >= 4900:
        # orange backboard
        return 0
    elif destination[1] < -4900:
        # blue backboard
        return 2
    elif destination[0] < -3900:
        # east wall
        return 1
    else:
        # west wall
        return 3
"""


def handleWallShot(agent):
    enemyGoal = Vector([0, -sign(agent.team) * 5200, 1500])
    myGoal = enemyGoal = Vector([0, sign(agent.team) * 5200, 500])
    targetVec = agent.currentHit.pred_vector
    destination = targetVec
    wall = which_wall(targetVec)
    # if agent.team == 1 and wall == 0 or agent.team == 0 and wall == 2:
    #     # _direction = direction(myGoal.flatten(), targetVec.flatten())
    #     # # _direction = (myGoal - targetVec).normalize()
    #     # destination = targetVec + _direction.scale(60)
    _direction = direction(myGoal.flatten(), targetVec.flatten())
    modified = targetVec + _direction.scale(70)

    if wall == 0:
        modified.data[1] = 5120 - agent.defaultElevation

    elif wall == 2:
        modified.data[1] = -5120 + agent.defaultElevation

    elif wall == 1:
        modified.data[0] = -4096 + agent.defaultElevation

    else:
        modified.data[0] = 4096 - agent.defaultElevation

    destination = modified

    return driveController(
        agent,
        destination,
        agent.time + agent.currentHit.time_difference(),
        expedite=True,
    )


def wallMover(agent, target, targetSpd, arrivalTime, expedite=False):
    # agent.forward = True
    if agent.boostMonster:
        expedite = True
    target = getLocation(target)
    currentSpd = agent.currentSpd
    controller_state = SimpleControllerState()
    if agent.forward:
        controller_state.throttle = 1
    else:
        controller_state.throttle = -1
        # print(f"on wall backwards? {agent.time}")

    if targetSpd > maxPossibleSpeed:
        targetSpd = maxPossibleSpeed
    jumpingDown = False

    if agent.currentHit.hit_type != 2:
        target = unroll_path_from_wall_to_ground(agent.me.location, target)
    # intersection, wall, valid = guided_find_wall_intesection(agent, target)
    # # intersection,wall = find_wall_intersection(agent.me, target)  #0 = orange backboard, 1 = east wall, 2 = blue backboard, 3 = west wall
    # # placeVecWithinArena(target)
    # needsIntersection = True
    # if not agent.onWall and agent.wallShot:
    #     #we shouldn't ever be in here since wallmover is only called if agent is on the wall
    #     if wall == 0:
    #         if agent.me.location[1] < intersection[1]:
    #             needsIntersection = False
    #     elif wall == 1:
    #         if agent.me.location[0] > intersection[0]:
    #             needsIntersection = False
    #     elif wall == 2:
    #         if agent.me.location[1] > intersection[1]:
    #             needsIntersection = False
    #     elif wall == 3:
    #         if agent.me.location[0] < intersection[0]:
    #             needsIntersection = False
    #
    #     if needsIntersection:
    #         intersectDist = findDistance(agent.me.location, intersection)
    #         intersect_to_target_dist = findDistance(intersection, target)
    #         percentage = intersectDist / intersect_to_target_dist
    #         newArrivalTime = arrivalTime * percentage
    #         return driveController(
    #             agent, intersection, agent.time + newArrivalTime, expedite=expedite # agent, intersection, agent.time, expedite=expedite
    #         )

    # elif agent.onWall and not agent.wallShot:
    #     targetSpd = maxPossibleSpeed
    #     target = intersection.scale(1)
    #     target.data[2] = -50
    #     if wall == 0:
    #         target.data[1] += 500
    #     elif wall == 1:
    #         target.data[0] += 500
    #     elif wall == 2:
    #         target.data[1] -= 500
    #     elif wall == 3:
    #         target.data[0] -= 500

    location = toLocal(target, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    angle_degrees = correctAngle(math.degrees(angle_to_target))
    # angle_degrees = math.degrees(angle_to_target)
    if agent.onWall and not agent.wallShot:
        if abs(angle_degrees) < 5:
            if agent.me.location[2] < 1500:
                jumpingDown = True

    # if needsIntersection:
    #     _distance = findDistance(agent.me.location, intersection) + findDistance(
    #         intersection, target
    #     )
    # else:
    #     _distance = findDistance(agent.me.location, target)
    if agent.currentHit.hit_type != 2:
        _distance = agent.me.location.data[2] + distance2D(agent.me.location, target)
    else:
        _distance = findDistance(agent.me.location, target)
    createTriangle(agent, target)
    steering, slide = rockSteer(angle_to_target, _distance)
    if not agent.forward:
        # steering = -steering
        slide = False
    if slide:
        if abs(agent.me.avelocity[2]) < 1:
            slide = False

    if abs(steering) >= 0.90:
        optimalSpd = maxSpeedAdjustment(agent, target)

        if targetSpd > optimalSpd:
            targetSpd = clamp(maxPossibleSpeed, 0, math.ceil(optimalSpd))

    if targetSpd > currentSpd:
        if agent.onSurface and not slide:
            spedup = False
            if not agent.boostMonster:
                if agent.me.location[2] > 200:
                    if agent.currentSpd > 300:
                        if not agent.forward:
                            targetAngle = abs(
                                correctAngle(math.degrees(angle_to_target)) - 180
                            )
                        else:
                            targetAngle = abs(
                                correctAngle(math.degrees(angle_to_target))
                            )
                        if targetAngle < 5:
                            spedup = agent.wallHyperSpeedJump()

            if not spedup:
                if agent.forward:
                    if (
                        targetSpd > agent.currentSpd + agent.accelerationTick * 8
                        and agent.currentSpd < maxPossibleSpeed
                    ):
                        if agent.currentSpd < maxPossibleSpeed - 50:
                            if expedite:
                                controller_state.boost = True

    elif (
        targetSpd < currentSpd
    ):  # and (targetSpd < maxPossibleSpeed and currentSpd >maxPossibleSpeed):
        if agent.forward:
            controller_state.throttle = -1
        else:
            controller_state.throttle = 1
    controller_state.steer = steering
    if jumpingDown:
        if abs(correctAngle(math.degrees(angle_to_target))) < 5:
            if agent.me.location[2] >= agent.wallLimit:
                agent.setJumping(-1)
                # agent.log.append("jumping down")

    return controller_state


def decelerationSim(agent, timeAlloted):
    increment = 525 * agent.fakeDeltaTime
    currentSpeed = agent.currentSpd * 1
    distance = 0
    while timeAlloted > 0 or currentSpeed > 0:
        timeAlloted -= agent.fakeDeltaTime
        currentSpeed -= increment
        distance += currentSpeed * agent.fakeDeltaTime
    return distance


def brake_sim(agent, timeAlloted):
    increment = 3500 * agent.fakeDeltaTime
    currentSpeed = agent.currentSpd * 1
    distance = 0
    while timeAlloted > 0 or currentSpeed > 0:
        timeAlloted -= agent.fakeDeltaTime
        currentSpeed -= increment
        distance += currentSpeed * agent.fakeDeltaTime
    return distance


def lastManFinder(agent):
    lastMan = None
    lastManY = math.inf * -sign(agent.team)
    allies = agent.allies + [agent.me]
    sorted(allies, key=lambda x: x.index)

    if agent.team == 0:
        # lastManY = math.inf
        for ally in allies:
            if ally.location[1] < lastManY:
                lastManY = ally.location[1]
                lastMan = ally
    else:
        # lastManY = -math.inf
        for ally in allies:
            if ally.location[1] > lastManY:
                lastManY = ally.location[1]
                lastMan = ally

    return lastMan


# def naiveDirectionSim(agent, position, expedite):
#     boostAmount = agent.me.boostLevel
#     boostConsumptionRate = agent.boostConsumptionRate
#     localPosition = toLocal(position, agent.me)
#     angle = math.degrees(math.atan2(localPosition[1], localPosition[0]))
#     distance = distance2D(agent.me.location, position)
#     behind = False
#     timeDelta = agent.fakeDeltaTime
#     currentSpd = agent.currentSpd
#     accelBase = 3500
#     boostAccel = agent.boostAccelerationRate
#     forwardSpeed = currentSpd * 1
#     reverseSpeed = currentSpd * 1
#
#     forwardSimTime = 0
#     reverseSimTime = 0
#     # print(abs(angle))
#
#     # if abs(angle) > 90:
#     #     if distance <= 800:
#     #         return 10,1
#     #
#     # else:
#     #     if distance <=800:
#     #         return 1,10
#
#     if abs(angle) > 90:
#         if agent.forward:
#             forwardSpeed = -forwardSpeed * (abs(angle) * (100 / 180)) * 0.01
#         else:
#             reverseSpeed = -reverseSpeed * ((abs(angle) - 90) * (100 / 90)) * 0.01
#
#         reverseDist = distance * 1
#         while reverseDist > 0:
#             if reverseSpeed < 1410:
#                 reverseSpeed += getNaturalAccelerationJitted(reverseSpeed) * timeDelta
#
#             reverseDist -= reverseSpeed * timeDelta
#             reverseSimTime += timeDelta
#
#         forwardDist = distance * 1
#         while forwardSpeed < 0:
#             if boostAmount > 0 and expedite:
#                 forwardSpeed += (accelBase + boostAccel) * timeDelta
#                 boostAmount -= boostConsumptionRate
#             else:
#                 forwardSpeed += accelBase * timeDelta
#             forwardDist += forwardSpeed * timeDelta
#             forwardSimTime += timeDelta
#
#         while forwardDist > 0:
#             if forwardSpeed < maxPossibleSpeed:
#                 if boostAmount > 0 and expedite:
#                     forwardSpeed += (
#                         getNaturalAccelerationJitted(forwardSpeed) + boostAccel
#                     ) * timeDelta
#                     boostAmount -= boostConsumptionRate
#                 else:
#                     forwardSpeed += (
#                         getNaturalAccelerationJitted(forwardSpeed) * timeDelta
#                     )
#
#             forwardDist -= forwardSpeed * timeDelta
#             forwardSimTime += timeDelta
#
#         if agent.forward:
#             foDist = distance + abs(angle) * 20
#             foSpd = agent.currentSpd
#             boostAmount = agent.me.boostLevel
#             foSimTime = 0
#             while foDist > 0:
#                 if foSpd < maxPossibleSpeed:
#                     if boostAmount > 0 and expedite:
#                         foSpd += (
#                             getNaturalAccelerationJitted(foSpd) + boostAccel
#                         ) * timeDelta
#                         boostAmount -= boostConsumptionRate
#                     else:
#                         foSpd += getNaturalAccelerationJitted(foSpd) * timeDelta
#
#                 foDist -= foSpd * timeDelta
#                 foSimTime += timeDelta
#
#             forwardSimTime = min([forwardSimTime, foSimTime])
#
#         return forwardSimTime, reverseSimTime
#
#     else:
#         if agent.forward:
#             reverseSpeed = -((180 - abs(angle) * 100 / 180) * 0.01 * reverseSpeed)
#         else:
#             forwardSpeed = -((abs(angle) * 100 / 90) * 0.01 * forwardSpeed)
#
#         forwardDist = distance * 1
#         while forwardDist > 0:
#             if forwardSpeed < maxPossibleSpeed:
#                 if boostAmount > 0 and expedite:
#                     forwardSpeed += (
#                         getNaturalAccelerationJitted(forwardSpeed) + boostAccel
#                     ) * timeDelta
#                     boostAmount -= boostConsumptionRate
#                 else:
#                     forwardSpeed += (
#                         getNaturalAccelerationJitted(forwardSpeed) * timeDelta
#                     )
#
#             forwardDist -= forwardSpeed * timeDelta
#             forwardSimTime += timeDelta
#
#         reverseDist = distance * 1
#         while reverseSpeed < 0:
#             reverseSpeed += accelBase * timeDelta
#             reverseDist += reverseSpeed * timeDelta
#             reverseSimTime += timeDelta
#
#         while reverseDist > 0:
#             if reverseSpeed < 1410:
#                 reverseSpeed += getNaturalAccelerationJitted(reverseSpeed) * timeDelta
#
#             reverseDist -= reverseSpeed * timeDelta
#             reverseSimTime += timeDelta
#
#         if not agent.forward:
#             reDist = distance + abs(angle) * 20
#             reSpd = agent.currentSpd
#             boostAmount = agent.me.boostLevel
#             reSimTime = 0
#             while reDist > 0:
#                 if reSpd < maxPossibleSpeed:
#                     if boostAmount > 0 and expedite:
#                         reSpd += (
#                             getNaturalAccelerationJitted(reSpd) + boostAccel
#                         ) * timeDelta
#                         boostAmount -= boostConsumptionRate
#                     else:
#                         reSpd += getNaturalAccelerationJitted(reSpd) * timeDelta
#
#                 reDist -= reSpd * timeDelta
#                 reSimTime += timeDelta
#
#             reverseSimTime = min([reverseSimTime, reSimTime])
#
#         return forwardSimTime, reverseSimTime


def target_in_goal(target: Vector):
    if abs(target[1]) >= 5120:
        if abs(target[0]) <= 893:
            return True


def new_goal_safe_adjuster(agent, target: Vector):
    tig = target_in_goal(target)
    big = target_in_goal(agent.me.location)

    if tig and big:
        return target
    if sign(agent.team) * agent.ball.location[1] < 0:
        return target

    x_buffer = 140
    y_buffer = 100

    xMax = 893 - x_buffer
    xMin = -893 + x_buffer

    yMax = 5120 - y_buffer
    yMin = -5120 + y_buffer

    if big and not tig:
        x = clamp(xMax, xMin, target[0])
        y = clamp(yMax, yMin, target[1])
        return Vector([x, y, target[2]])

    if tig and not big:
        x = clamp(xMax, xMin, target[0])
        # y = clamp(yMax, yMin, target[1])
        return Vector([x, target[1], target[2]])

    return target


def in_goal_check(agent):
    if abs(agent.me.location[1] >= 5120):
        return True
    return False


def goalBoxFixer(agent, target):
    y_limit = 5085
    if abs(agent.me.location[1]) <= y_limit:
        return target
        # not in goal, continue as normal
    else:
        xMin = -835
        xMax = 835
        if agent.me.location[1] > y_limit:
            # in orange goal
            yMax = y_limit + 700

            if target[0] < xMin:
                target.data[0] = xMin
            elif target[0] > xMax:
                target.data[0] = xMax

            if target[1] > yMax:
                target.data[1] = yMax

        else:
            # in blue goal
            yMin = -y_limit - 700

            if target[0] < xMin:
                target.data[0] = xMin
            elif target[0] > xMax:
                target.data[0] = xMax

            if target[1] < yMin:
                target.data[1] = yMin
        # if agent.team == 1:
        #     print(f"agent in goal? {agent.time}")
        return target


# def goalBoxFixer(agent, target):
#     if abs(agent.me.location[1]) < 5120:
#         return target
#         # not in goal, continue as normal
#     else:
#         xMin = -820
#         xMax = 820
#         if agent.me.location[1] > 5150:
#             # in orange goal
#             yMax = 5120 + 600
#
#             if target[0] < xMin:
#                 target.data[0] = xMin
#             elif target[0] > xMax:
#                 target.data[0] = xMax
#
#             if target[1] > yMax:
#                 target.data[1] = yMax
#
#         else:
#             # in blue goal
#             yMin = -5120 - 600
#
#             if target[0] < xMin:
#                 target.data[0] = xMin
#             elif target[0] > xMax:
#                 target.data[0] = xMax
#
#             if target[1] < yMin:
#                 target.data[1] = yMin
#         return target


def wallsafe(position: Vector):
    if abs(position[0]) < 3800:
        if abs(position[1]) < 4800:
            return True

    return False


# self.map(t, 0,1410,-.01,1)


def scaleMap(unscaled_min, unscaled_max, scaled_min, scaled_max, t_value):
    if t_value == 0:
        return scaled_min
    clamped_t = clamp(unscaled_max, unscaled_min, t_value * 1)

    unscaled_dif = abs(unscaled_max - unscaled_min)
    scaled_dif = abs(scaled_max - unscaled_max)

    return clamp(scaled_max, scaled_min, t_value / unscaled_dif)


def driveController(
    agent,
    target,
    arrivalTime,
    expedite=False,
    flippant=False,
    maintainSpeed=False,
    flips_enabled=True,
    kickoff=False,
):
    if agent.boostMonster:
        expedite = True
        flips_enabled = False
        flippant = False

    tta = clamp(6, 0.001, arrivalTime - agent.time)

    OT = target.scale(1)

    if not kickoff:

        if target[2] == 0 or target[2] < agent.defaultElevation:
            target.data[2] = agent.defaultElevation

        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
        ):
            own_goal_info = own_goal_check(
                agent,
                agent.ball.location.flatten(),
                agent.me.location.flatten(),
                buffer=0,
                send_back=True,
            )
            if own_goal_info[0] and agent.ball.location[2] < 140:
                if agent.me.location[0] > agent.ball.location[0]:
                    targ_x = 300
                else:
                    targ_x = -300

                target = target + Vector([targ_x, sign(agent.team) * 50, 0])
                tta = 0.001
                # print(f"{agent.index} own goal avoidance {agent.time}")

        if not agent.demo_monster:

            if agent.onWall:  # and not agent.dribbling:
                flips_enabled = False
                # if target[2] <= agent.defaultElevation:
                if (
                    agent.currentHit != None
                    and agent.currentHit.hit_type != 2
                    and agent.me.location[2] > 75
                ):
                    target = unroll_path_from_wall_to_ground(agent.me.location, target)
                else:
                    placeVecWithinArena(
                        target, offset=agent.defaultElevation
                    )  # ,offset=agent.defaultElevation

            else:
                if agent.currentHit.hit_type == 2:
                    target = unroll_path_from_ground_to_wall(target)
                else:
                    placeVecWithinArena(
                        target, offset=agent.defaultElevation
                    )  # ,offset=agent.defaultElevation
        prefixer = target.scale(1)
        target = goalBoxFixer(agent, target)
        if prefixer != target:
            flips_enabled=False

    if abs(agent.me.location[1]) > 5100:
        flips_enabled = False

    if not kickoff:
        _distance = findDistance(agent.me.location, target)
    else:
        _distance = distance2D(agent.me.location, target)

    if OT != target:
        OT_dist = findDistance(agent.me.location, OT)
        # tta *= OT_dist/_distance
        _distance = OT_dist

    idealSpeed = clamp(maxPossibleSpeed, 0, math.ceil(_distance / tta))

    avoiding = False
    target_to_avoid = Vector([0, 0, 0])

    arrival_boostless = (
        inaccurateArrivalEstimatorBoostless(agent, target, onWall=False, offset=-100)
        + agent.time
    )

    if agent.dribbling:
        min_dur = 12
        boost_req = clamp(
            min_dur, 1, abs(min_dur - clamp(min_dur, 0, agent.boost_counter))
        ) * (agent.boostAccelerationRate * agent.fakeDeltaTime)
        if arrival_boostless < arrivalTime and not agent.boostMonster:
            boost_req = 5000
    else:
        boost_req = agent.boostAccelerationRate * agent.fakeDeltaTime
        # min_dur = 4
        # boost_req = clamp(min_dur, 1,abs(min_dur - clamp(min_dur, 1, agent.boost_counter)))*(agent.boostAccelerationRate * agent.fakeDeltaTime)
        if arrival_boostless < arrivalTime and not agent.boostMonster:
            boost_req = 5000

    localTarget = toLocal(target, agent.me)
    angle = math.atan2(localTarget[1], localTarget[0])
    angle_degrees = math.degrees(angle)
    goForward = agent.forward

    if avoiding:
        localTarget = toLocal(target_to_avoid, agent.me)
        angle = math.atan2(localTarget[1], localTarget[0])
        angle_degrees = math.degrees(angle)

    if _distance < 650:
        if abs(angle_degrees) <= 110:
            goForward = True
        else:
            goForward = False

    if maintainSpeed:
        goForward = True

    createTriangle(agent, target)
    if idealSpeed >= 200:
        if ruleOneCheck(agent):
            agent.setJumping(6, target=target)
            # print("breaking rule #1")

    if goForward:
        throttle = 1
    else:
        throttle = -1

        angle_degrees -= 180
        if angle_degrees < -180:
            angle_degrees += 360
        if angle_degrees > 180:
            angle_degrees -= 360

        angle = math.radians(angle_degrees)

        if agent.onSurface:
            # if _distance > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500) * 2.2:
            if (
                clamp(math.inf, 1, _distance - 120)
                > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500)
                * 1.75
            ):
                if abs(angle_degrees) <= clamp(10, 0, _distance / 1000):
                    if not agent.onWall:
                        agent.setHalfFlip()
                        agent.stubbornessTimer = 2
                        agent.stubborness = agent.stubbornessMax
                    # pass

    wallFlip = False
    if agent.onWall and target[2] <= agent.defaultElevation:
        bot_wall = which_wall(agent.me.location)
        index = 0
        if bot_wall == 0 or bot_wall == 2:
            index = 1
        _target = target.scale(1)
        _target.data[index] = agent.me.location[index]
        wall_localTarget = toLocal(_target, agent.me)
        wall_angle = math.atan2(wall_localTarget[1], wall_localTarget[0])
        wall_angle_degrees = math.degrees(wall_angle)
        if not goForward:
            wall_angle_degrees -= 180
        wall_angle_degrees = correctAngle(wall_angle_degrees)
        # print(f"wall angle is: {wall_angle_degrees}")

        if abs(wall_angle_degrees) < 5:
            if (
                agent.me.location[2] < 2500
                and agent.me.location[2] > 300
                and (tta > 1.5 or _distance / agent.currentSpd > 1.5)
            ):
                agent.setJumping(-1)
                # print("jumping off wall!")
            elif (
                agent.me.location[2] <= 500 and not agent.demo_monster
                and agent.currentHit.hit_type != 2
                and (tta > 1.5 or _distance / agent.currentSpd > 1.5)
            ):
                wallFlip = True

    boost = False

    # if not in_goal_check(agent):
    limit = 1
    steer, handbrake = rockSteer(angle, _distance, modifier=300, turnLimit=limit)

    if abs(angle_degrees) > 40 and abs(angle_degrees) < 140:
        if _distance < 250 and _distance > 30:
            if agent.currentSpd <= 600:
                if (
                    not agent.dribbling
                    and not agent.onWall
                    and agent.currentHit.hit_type != 1
                    and agent.currentHit.hit_type != 4
                ):
                    if tta < 0.5:
                        agent.setJumping(6, target=target)
                        # print(f"YOLO!!! {agent.time}")
        if (
            _distance <= abs(90 - angle_degrees) * 10
            and agent.currentSpd <= 600
            and _distance > 30
            and not maintainSpeed
            and not agent.dribbling
        ):
            handbrake = True
            # print(f"Scrambling! {agent.time}")
    # else:
    #     steer, handbrake = newSteer(angle)

    if not goForward:
        steer = -steer

    if avoiding:
        steer = -steer

    nearTurnLimit = False

    if not maintainSpeed:
        if abs(steer) >= 0.9 and goForward and not kickoff:
            _idealSpeed = maxSpeedAdjustment(agent, target)
            if _idealSpeed < idealSpeed:
                idealSpeed = _idealSpeed
            if abs(agent.currentSpd - _idealSpeed) < 10:
                nearTurnLimit = True
        # idealSpeed = clamp(maxPossibleSpeed, 0, math.ceil(idealSpeed))

    if agent.currentSpd > idealSpeed and idealSpeed < maxPossibleSpeed:
        limit = 0.1
        dist_limit = 525

        if not agent.demo_monster and agent.currentHit.hit_type == 4:
            limit = 0.25
            dist_limit = 1000

        if (
            _distance > clamp(dist_limit, 100, agent.currentSpd * limit)
            and not nearTurnLimit
            and idealSpeed > 1000
            and not agent.dribbling
        ):
            # if decelerationSim(agent, tta) < _distance:
            # if brake_sim(agent,tta) < _distance-clamp(250,100,agent.currentSpd*0.1):
            if brake_sim(agent, tta) < _distance - clamp(
                dist_limit, 100, agent.currentSpd * limit
            ):
                if goForward:
                    throttle = 0.1
                else:
                    throttle = -0.1
            else:
                if goForward:
                    throttle = -1
                else:
                    throttle = 1
        else:
            if (
                (_distance > 75 or agent.dribbling)
                and not nearTurnLimit
                and decelerationSim(agent, tta) < _distance
            ):
                throttle = 0
            else:
                if goForward:
                    throttle = -1
                else:
                    throttle = 1

    elif agent.currentSpd < idealSpeed:
        if (
            idealSpeed >= agent.currentSpd + boost_req
        ):  # or idealSpeed >= maxPossibleSpeed:
            if (
                agent.onSurface
                and expedite
                and agent.currentSpd < maxPossibleSpeed - 25
                and goForward
                and not nearTurnLimit
                and idealSpeed >= 1000
            ):
                boost = True

        if agent.me.boostLevel > 0 and expedite:
            minFlipSpeed = maxPossibleSpeed - 500
        else:
            minFlipSpeed = 1075

        if (
            agent.currentSpd > minFlipSpeed
            and flips_enabled
            and (agent.currentHit != None and agent.currentHit.hit_type != 2)
        ):
            if (
                clamp(math.inf, 1, _distance - 90)
                > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500)
                * 1.9
                or flippant
            ):
                if abs(angle_degrees) <= clamp(5, 0, _distance / 1000):
                    if not agent.onWall or wallFlip:  # or not agent.wallShot:
                        if agent.onSurface:
                            if wallFlip:
                                print("wall flipping")
                            if goForward:
                                agent.setJumping(1)
                                # print(f"pew pew? {flips_enabled} {agent.boostMonster}")
                            else:
                                agent.setHalfFlip()
                                agent.stubbornessTimer = 1.5
                                agent.stubborness = agent.stubbornessMax

    else:
        if goForward:
            throttle = 0.15
        else:
            throttle = -0.15

    if abs(agent.me.avelocity[2]) < 1:
        handbrake = False

    if agent.forward != goForward:
        handbrake = False

    if handbrake:
        boost = False

    if maintainSpeed:
        handbrake = False
        throttle = 1
        if not agent.demo_monster:
            boost = False

    if kickoff:
        handbrake = False
        throttle = 1
        if not agent.currentSpd > 2200:
            boost = True

    controler = SimpleControllerState()
    controler.steer = steer
    controler.throttle = throttle
    controler.handbrake = handbrake
    controler.boost = boost

    return controler


def Gsteer(angle):
    final = ((10 * angle + sign(angle)) ** 3) / 20
    return clamp(1, -1, final)


def rockSteer(angle, distance, forward=True, modifier=600, turnLimit=1):
    turn = Gsteer(angle)
    # turn = clamp(1,-1,angle*4)
    slide = False
    distanceMod = clamp(10, 0.3, distance / modifier)
    _angle = correctAngle(math.degrees(angle))

    adjustedAngle = _angle / distanceMod
    if abs(turn) >= turnLimit:
        if abs(adjustedAngle) > 90:
            slide = True

    return turn, slide


def greedyMover(agent, target_object):
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


def isBallHitNearWall(ball_vec, defaultDistance=120):
    if abs(ball_vec[0]) < 950:
        return False

    if ball_vec[0] > 4096 - defaultDistance:
        return True
    if ball_vec[0] < -4096 + defaultDistance:
        return True

    if ball_vec[1] < -5120 + defaultDistance:
        return True

    if ball_vec[1] > 5120 - defaultDistance:
        return True

    return False


def isBallNearWall(ballstruct, defaultDistance=120):
    if abs(ballstruct.physics.location.x) < 950:
        return False

    if ballstruct.physics.location.x > 4096 - defaultDistance:
        return True
    if ballstruct.physics.location.x < -4096 + defaultDistance:
        return True

    if ballstruct.physics.location.y < -5120 + defaultDistance:
        return True

    if ballstruct.physics.location.y > 5120 - defaultDistance:
        return True

    return False


def isBallHittable_hit(hit, agent, maxHeight, defaultDistance=110):
    if agent.wallShotsEnabled:
        multi = 20
    else:
        multi = 1
    if hit.pred_vector[2] <= maxHeight:
        return True
    if hit.pred_vector[0] > 4096 - defaultDistance:
        if hit.pred_vector[2] <= 200 * multi:
            return True
    if hit.pred_vector[0] < -4096 + defaultDistance:
        if hit.pred_vector[2] <= 200 * multi:
            return True
    if len(agent.allies) > 0:
        if hit.pred_vector[1] < -5120 + defaultDistance:
            if hit.pred_vector[2] <= 200 * multi:
                if abs(hit.pred_vector[0]) > 900:
                    return True
        if hit.pred_vector[1] > 5120 - defaultDistance:
            if hit.pred_vector[2] <= 200 * multi:
                if abs(hit.pred_vector[0]) > 900:
                    return True

    return False


def isBallHittable(ballStruct, agent, maxHeight, defaultDistance=110):
    # multi = clamp(3, 1, len(agent.allies)+1)
    # offset = (agent.carHeight + 93) * .9
    if agent.wallShotsEnabled:
        multi = 20
    else:
        multi = 1
    if ballStruct.physics.location.z <= maxHeight:
        return True
    if ballStruct.physics.location.x > 4096 - defaultDistance:
        if ballStruct.physics.location.z <= 200 * multi:
            return True
    if ballStruct.physics.location.x < -4096 + defaultDistance:
        if ballStruct.physics.location.z <= 200 * multi:
            return True
    if len(agent.allies) > 0:
        if ballStruct.physics.location.y < -5120 + defaultDistance:
            if ballStruct.physics.location.z <= 200 * multi:
                if abs(ballStruct.physics.location.x) > 900:
                    return True
        if ballStruct.physics.location.y > 5120 - defaultDistance:
            if ballStruct.physics.location.z <= 200 * multi:
                if abs(ballStruct.physics.location.x) > 900:
                    return True

    return False


def turnTowardsPosition(agent, targetPosition, threshold):
    localTarg = toLocal(targetPosition, agent.me)
    localAngle = correctAngle(math.degrees(math.atan2(localTarg[1], localTarg[0])))
    controls = SimpleControllerState()
    # print("ttp being called")

    if abs(localAngle) > threshold:
        if agent.forward:
            if localAngle > 0:
                controls.steer = 1
            else:
                controls.steer = -1

            controls.handbrake = True
            if agent.currentSpd < 250:
                controls.throttle = 1
            else:
                controls.throttle = -1
        else:
            if localAngle > 0:
                controls.steer = -1
            else:
                controls.steer = 1
            controls.handbrake = True
            if agent.currentSpd < 250:
                controls.throttle = -1
            else:
                controls.throttle = 1

    return controls


def isBallGrounded(agent, heightMax, frameMin):
    if agent.ballPred is not None:
        for i in range(0, frameMin):
            if agent.ballPred.slices[i].physics.location.z > heightMax:
                return False
        return True
    return False


def find_soonest_hit(agent):
    lowest = math.inf
    best = None

    for hit in agent.hits:
        if hit != None:
            if hit.time_difference() < lowest:
                lowest = hit.time_difference()
                best = hit

    if best == None:
        agent.log.append("none value in soonest hit!")
    return best


def findEnemyHits_old(agent):
    enemyOnWall = False
    enemyInAir = False
    enemyOnGround = True
    enemyTarget = None
    found = False
    jumpshotLimit = 500
    if agent.closestEnemyToBall:

        if agent.closestEnemyToBall.onSurface:
            if agent.closestEnemyToBall.location[2] > 100:
                enemyOnWall = True
                # enemyOnGround = False
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
            pred = agent.ballPred.slices[i]
            location = convertStructLocationToVector(pred)

            if enemyOnWall:
                if isBallNearWall(pred, defaultDistance=400):
                    timeToTarget, distance = enemyWallMovementEstimator(
                        agent.closestEnemyToBall, location, agent
                    )
                    if (
                        timeToTarget
                        < pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                        )
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        # print(f"enemy on wall {timeToTarget}")
                        break

            if enemyOnGround:
                if location[2] > jumpshotLimit:
                    continue
                else:
                    timeToTarget = enemyArrivalEstimator(
                        agent, agent.closestEnemyToBall, location
                    )
                    if (
                        timeToTarget
                        <= pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                        )
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        # print(f"enemy Delay: {agent.enemyBallInterceptDelay}, my Delay: {agent.ballDelay} || {agent.contested}  ||  {agent.timid}")
                        break

            if enemyInAir:
                pass  # do air stuffs!

    if not found:
        agent.enemyBallInterceptDelay = 10
        agent.enemyTargetVec = convertStructLocationToVector(
            agent.ballPred.slices[agent.ballPred.num_slices - 2]
        )
        agent.enemyPredTime = agent.time + 10
    # print("got here")


def find_ally_hit(agent, ally):
    enemyOnWall = False
    enemyInAir = False
    enemyOnGround = True
    enemyTarget = None
    found = False
    jumpshotLimit = agent.doubleJumpLimit
    if ally and not ally.demolished:

        if ally.onSurface:
            if ally.location[2] > 100:
                enemyOnWall = True
                # enemyOnGround = False
            else:
                enemyOnGround = True
        else:
            if ally.boostLevel > 0:
                if ally.location[2] > 500:
                    enemyInAir = True
                else:
                    enemyInAir = False
                    enemyOnGround = True
            else:
                enemyInAir = False
                enemyOnGround = True

        for i in range(0, agent.ballPred.num_slices):
            if i % 5 != 0:
                continue
            pred = agent.ballPred.slices[i]
            location = convertStructLocationToVector(pred)
            if pred.game_seconds - agent.gameInfo.seconds_elapsed <= 0:
                continue

            if enemyOnWall:
                if isBallNearWall(pred, defaultDistance=400):
                    timeToTarget, distance = enemyWallMovementEstimator(
                        ally, location, agent
                    )
                    if (
                        timeToTarget
                        < pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        found = True
                        ally_hit = predictionStruct(location, pred.game_seconds)
                        break

            if enemyOnGround:
                if location[2] > jumpshotLimit + agent.allowableJumpDifference:
                    continue
                else:
                    timeToTarget = enemyArrivalEstimator(agent, ally, location)
                    if (
                        timeToTarget
                        <= pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        found = True
                        ally_hit = predictionStruct(location, pred.game_seconds)
                        break

            if enemyInAir:
                if ally.velocity[2] > 0 and ally.boostLevel > 0:
                    if findDistance(location, ally.location) < 2300 * (
                        pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):

                        found = True
                        ally_hit = predictionStruct(location, pred.game_seconds)
                        break

    if not found:
        ally_hit = predictionStruct(
            convertStructLocationToVector(
                agent.ballPred.slices[agent.ballPred.num_slices - 2]
            ),
            agent.time + 20,
        )

    return ally_hit


def findEnemyHits(agent):
    enemyOnWall = False
    enemyInAir = False
    enemyOnGround = True
    enemyTarget = None
    found = False
    jumpshotLimit = agent.doubleJumpLimit
    if agent.closestEnemyToBall:

        if agent.closestEnemyToBall.onSurface:
            if agent.closestEnemyToBall.location[2] > 100:
                enemyOnWall = True
                # enemyOnGround = False
            else:
                enemyOnGround = True
        else:
            if agent.closestEnemyToBall.boostLevel > 0:
                if agent.closestEnemyToBall.location[2] > 500:
                    enemyInAir = True
                else:
                    enemyInAir = False
                    enemyOnGround = True
            else:
                enemyInAir = False
                enemyOnGround = True
        # if enemyInAir:
        #     enemyOnGround = True
        #     enemyInAir = False
        for i in range(0, agent.ballPred.num_slices):
            if i % 5 != 0:
                continue
            pred = agent.ballPred.slices[i]
            location = convertStructLocationToVector(pred)
            if pred.game_seconds - agent.gameInfo.seconds_elapsed <= 0:
                continue

            if enemyOnWall:
                if isBallNearWall(pred, defaultDistance=400):
                    timeToTarget, distance = enemyWallMovementEstimator(
                        agent.closestEnemyToBall, location, agent
                    )
                    if (
                        timeToTarget
                        < pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                        )
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        # print(f"enemy on wall {timeToTarget}")
                        break

            if enemyOnGround:
                if location[2] > jumpshotLimit:
                    continue
                else:
                    timeToTarget = enemyArrivalEstimator(
                        agent, agent.closestEnemyToBall, location
                    )
                    if (
                        timeToTarget
                        <= pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                        )
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        # print(f"enemy Delay: {agent.enemyBallInterceptDelay}, my Delay: {agent.ballDelay} || {agent.contested}  ||  {agent.timid}")
                        break

            if enemyInAir:
                # if not agent.closestEnemyToBall.onSurface:
                #     if agent.closestEnemyToBall.location[2] > 500:
                if agent.closestEnemyToBall.velocity[2] > 0:
                    if findDistance(
                        location, agent.closestEnemyToBall.location
                    ) < 2300 * (pred.game_seconds - agent.gameInfo.seconds_elapsed):
                        agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                        )
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        # print(f"Found aerial threat! {agent.time}")
                        break

    if not found:
        agent.enemyBallInterceptDelay = 6
        agent.enemyTargetVec = convertStructLocationToVector(
            agent.ballPred.slices[agent.ballPred.num_slices - 2]
        )
        agent.enemyPredTime = agent.time + 6
    # print("got here")


def npVector(nparray):
    return Vector([nparray[0], nparray[1], nparray[2]])


def convertToArray(agent):
    predictions = np.ctypeslib.as_array(agent.ballPred.slices).view(agent.dtype)[
        : agent.ballPred.num_slices
    ]


def newConvertToArray(agent):
    buf_from_mem = ctypes.pythonapi.PyMemoryView_FromMemory
    buf_from_mem.restype = ctypes.py_object
    buf_from_mem.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
    ball_prediction = agent.ballPred

    buffer = buf_from_mem(
        ctypes.addressof(ball_prediction.slices),
        agent.Dtype.itemsize * ball_prediction.num_slices,
        0x100,
    )
    return np.frombuffer(buffer, agent.Dtype)


def find_pred_at_time(agent, _time):
    t_offset = 1.0 / 120.0
    pred = None
    for i in range(0, agent.ballPred.num_slices):
        if _time < agent.ballPred.slices[i].game_seconds + t_offset:
            pred = agent.ballPred.slices[i]
            break
    return pred


def determine_if_shot_goalward(shot_vel: Vector, team: int):
    if shot_vel[1] * sign(team) > 5:
        return True
    return False


def calculate_delta_acceleration(
    displacement: Vector, initial_velocity: Vector, time: float, gravity: float
) -> Vector:
    # lifted from dacoolone's tutorial
    time = clamp(10, 0.000001, time)
    return Vector(
        [
            (2 * (displacement[0] - initial_velocity[0] * time)) / (time * time),
            (2 * (displacement[1] - initial_velocity[1] * time)) / (time * time),
            (2 * (displacement[2] - initial_velocity[2] * time)) / (time * time)
            - gravity,
        ]
    )


def validate_ground_shot(agent, groundHit, grounder_cutoff):
    offset = agent.reachLength
    if groundHit.pred_vector[2] <= grounder_cutoff:
        if not agent.onWall:
            timeToTarget = inaccurateArrivalEstimator(
                agent, groundHit.pred_vector, False, offset=offset
            )
        else:
            timeToTarget = new_ground_wall_estimator(agent, groundHit.pred_vector)[0]

        if timeToTarget < groundHit.time_difference():
            return True

    return False


def validate_jump_shot(
    agent, jumpshotHit, grounder_cutoff, jumper_cutoff, doublejump_cutoff
):
    offset = agent.reachLength
    if (
        jumpshotHit.pred_vector[2] > grounder_cutoff
        and jumpshotHit.pred_vector[2] < jumper_cutoff
    ):
        if isBallHittable_hit(jumpshotHit, agent, jumper_cutoff):
            if not agent.onWall:
                distance = distance2D(jumpshotHit.pred_vector, agent.me.location)
                timeToTarget = inaccurateArrivalEstimator(
                    agent, jumpshotHit.pred_vector, False, offset=offset
                )
            else:
                timeToTarget, distance, valid = new_ground_wall_estimator(
                    agent, jumpshotHit.pred_vector
                )

            if timeToTarget <= jumpshotHit.time_difference():
                jumpSim = jumpSimulatorNormalizingJit(
                    float32(agent.gravity),
                    float32(agent.fakeDeltaTime),
                    np.array(agent.me.velocity, dtype=np.dtype(float)),
                    float32(agent.defaultElevation),
                    float32(jumpshotHit.time_difference()),
                    float32(jumpshotHit.pred_vector[2]),
                    False,
                )
                if (
                    abs(jumpSim[2] - jumpshotHit.pred_vector[2])
                    <= agent.allowableJumpDifference
                ):

                    if jumpshotHit.time_difference() > jumpSim[3]:
                        jumpshotHit.jumpSim = jumpSim
                        return True

    return False


def validate_double_jump_shot(
    agent, doubleJumpShotHit, jumper_cutoff, doublejump_cutoff
):
    offset = agent.reachLength
    if (
        doubleJumpShotHit.pred_vector[2] > jumper_cutoff
        and doubleJumpShotHit.pred_vector[2] <= doublejump_cutoff
    ):
        if isBallHittable_hit(doubleJumpShotHit, agent, doublejump_cutoff):
            if not agent.onWall:
                distance = distance2D(doubleJumpShotHit.pred_vector, agent.me.location)
                timeToTarget = inaccurateArrivalEstimator(
                    agent, doubleJumpShotHit.pred_vector, False, offset=offset
                )
            else:
                timeToTarget, distance, valid = new_ground_wall_estimator(
                    agent, doubleJumpShotHit.pred_vector
                )

            if timeToTarget <= doubleJumpShotHit.time_difference():
                jumpSim = jumpSimulatorNormalizingJit(
                    float32(agent.gravity),
                    float32(agent.fakeDeltaTime),
                    np.array(agent.me.velocity, dtype=np.dtype(float)),
                    float32(agent.defaultElevation),
                    float32(doubleJumpShotHit.time_difference()),
                    float32(doubleJumpShotHit.pred_vector[2]),
                    True,
                )
                if (
                    abs(jumpSim[2] - doubleJumpShotHit.pred_vector[2])
                    <= agent.allowableJumpDifference
                ):

                    if doubleJumpShotHit.time_difference() > jumpSim[3]:
                        doubleJumpShotHit.jumpSim = jumpSim
                        return True

    return False


def validate_wall_shot(agent, wallshot_hit, grounder_cutoff):
    pred_vec = wallshot_hit.pred_vector
    tth = wallshot_hit.time_difference()
    offset = agent.reachLength

    if isBallHittable_hit(wallshot_hit, agent, grounder_cutoff):
        if isBallHitNearWall(pred_vec, defaultDistance=120):
            if agent.onWall:
                distance = findDistance(agent.me.location, pred_vec)
                timeToTarget = inaccurateArrivalEstimator(
                    agent, pred_vec, True, offset=offset
                )

                if timeToTarget < tth:
                    agent.targetDistance = distance
                    agent.timeEstimate = timeToTarget
                    return True

            else:
                timeToTarget, distance, valid = new_ground_wall_estimator(
                    agent, pred_vec
                )
                if timeToTarget < tth:
                    if valid:
                        agent.targetDistance = distance
                        agent.timeEstimate = timeToTarget
                        return True

    return False


def validate_aerial_shot(agent, aerial_shot, aerial_min, doubleCutOff):
    pred_vec = aerial_shot.pred_vector
    tth = aerial_shot.time_difference()
    offset = agent.reachLength
    center = Vector([0, 5500 * -sign(agent.team), 0])
    myGoal = Vector([0, 5200 * sign(agent.team), 0])

    if agent.me.boostLevel >= 1:
        if agent.me.velocity[2] > -100 or pred_vec[2] < agent.me.location[2]:
            if inaccurateArrivalEstimator(agent, pred_vec, False, offset=offset) < tth:

                defensiveTouch = inTheMiddle(
                    pred_vec[1], [2000 * sign(agent.team), 5500 * sign(agent.team)]
                )
                if defensiveTouch:
                    if abs(pred_vec[0]) > 1000:
                        defensiveTouch = False
                if not defensiveTouch:

                    if distance2D(pred_vec, center) > 2000:
                        _direction = direction(pred_vec.flatten(), center.flatten())
                        _direction_angle = angleBetweenVectors(
                            agent.me.velocity.flatten(), _direction.flatten(),
                        )

                    else:
                        _direction = direction(pred_vec, center.flatten())
                        _direction_angle = angleBetweenVectors(
                            agent.me.velocity.flatten(), _direction.flatten(),
                        )
                else:
                    if pred_vec[0] > 0:
                        shot_target = Vector(
                            [
                                4500,
                                pred_vec[1] + -sign(agent.team) * 4000,
                                pred_vec[2] + 1000,
                            ]
                        )
                    else:
                        shot_target = Vector(
                            [
                                -4500,
                                pred_vec[1] + -sign(agent.team) * 4000,
                                pred_vec[2] + 1000,
                            ]
                        )
                    _direction = direction(pred_vec, shot_target)

                target = pred_vec + _direction.scale(agent.reachLength * 0.5)

                aerial_accepted = False
                if agent.onSurface:
                    if enough_takeoff_room(agent, pred_vec)[0] or agent.onWall:
                        if pred_vec[2] > doubleCutOff + 100:
                            if agent.me.location[1] * sign(agent.team) > pred_vec[
                                1
                            ] * sign(agent.team):
                                # accel_req_limit = clamp(
                                #     1000, 750, 1060 - (((6 - tth) * 0.25)) * 100,
                                # )
                                accel_req_limit = clamp(
                                    1060,
                                    750,
                                    1060
                                    - (((6 - tth) * 0.35)) * 100,
                                )
                                expected_jump_boost = 400
                                if agent.onWall:
                                    expected_jump_boost = 200
                                delta_a = calculate_delta_acceleration(
                                    target - agent.me.location,
                                    agent.me.velocity + agent.up.scale(expected_jump_boost),
                                    tth,
                                    agent.gravity,
                                )
                                if delta_a.magnitude() < accel_req_limit:
                                    if (
                                        delta_a.magnitude() * tth
                                        < agent.available_delta_v
                                    ):
                                        aerial_accepted = True
                                else:
                                    approach_direction = direction(
                                        agent.me.location.flatten(), pred_vec.flatten()
                                    ).normalize()
                                    pseudo_position = pred_vec.flatten() - approach_direction.scale(
                                        pred_vec[2]
                                    )
                                    req_delta_a = calculate_delta_acceleration(
                                        pseudo_position - agent.me.location,
                                        approach_direction.scale(2300)
                                        + agent.up.scale(300),
                                        tth,
                                        agent.gravity,
                                    )
                                    req_delta_v = req_delta_a.magnitude() * tth
                                    if (
                                        req_delta_v < agent.available_delta_v
                                        and req_delta_a.magnitude() < accel_req_limit
                                    ):
                                        aerial_accepted = True

                                    if not agent.onWall:
                                        if tth < 2:
                                            aerial_accepted = False

                                    if len(agent.allies) < 1:
                                        aerial_accepted = False
                else:
                    if pred_vec[2] > aerial_min:
                        delta_a = calculate_delta_acceleration(
                            target - agent.me.location,
                            agent.me.velocity,
                            tth,
                            agent.gravity,
                        )
                        # accel_req_limit = clamp(
                        #     1050, 775, 1050 - (((6 - tth) * 0.1)) * 100
                        # )
                        accel_req_limit = clamp(
                            1060, 750, 1060 - (((6 - tth) * 0.1)) * 100
                        )

                        if delta_a.magnitude() <= accel_req_limit:
                            req_delta_v = delta_a.magnitude() * tth
                            if req_delta_v < agent.available_delta_v - 50:
                                aerial_accepted = True

                if aerial_accepted:
                    return True

    return False


def hit_generator(agent, grounder_cutoff, jumpshot_cutoff, doubleCutOff):

    while agent.game_active:
        if agent.ballPred != None:
            agent.hits = findHits(agent, grounder_cutoff, jumpshot_cutoff, doubleCutOff)


def findHits(agent, grounder_cutoff, jumpshot_cutoff, doubleCutOff, resolution=3):
    ground_shot = None
    jumpshot = None
    wall_shot = None
    doubleJumpShot = None
    ballInGoal = None
    aerialShot = None
    catchCanidate = None

    in_goalbox = in_goal_check(agent)

    # self.left_post = Vector3(team * 850, team * 5100, 320)
    # self.right_post = Vector3(-team * 850, team * 5100, 320)

    leftPost = Vector([893 * sign(agent.team), 5120 * -sign(agent.team), 0])
    center = Vector([0, 5500 * -sign(agent.team), 0])
    rightPost = Vector([893 * -sign(agent.team), 5120 * -sign(agent.team), 0])
    myGoal = Vector([0, 5200 * sign(agent.team), 0])

    o_max_y = 5350
    d_max_y = 5290

    ground_offset = agent.reachLength
    goalward_ground_offset = agent.reachLength
    _offset = agent.reachLength

    # ground_offset = 120
    # goalward_ground_offset = 120
    # _offset = 120

    aboveThreshold = False
    aerialsValid = False

    checkAngles = len(agent.enemies) < 4

    grounded = True

    agent.goalPred = None
    agent.scorePred = None
    pred = agent.ballPred.slices[0]

    if agent.demo_monster:
        ground_shot = hit(
            agent.time,
            agent.time + 6,
            0,
            convertStructLocationToVector(agent.ballPred.slices[agent.ballPred.num_slices-1]),
            convertStructVelocityToVector(agent.ballPred.slices[agent.ballPred.num_slices-1]),
            False,
            6,
        )

        return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot


    for i in range(0, agent.ballPred.num_slices):
        if i > 60 and i % resolution != 0:
            continue

        pred = agent.ballPred.slices[i]
        tth = pred.game_seconds - agent.gameInfo.seconds_elapsed

        pred_vec = convertStructLocationToVector(pred)
        pred_vel = convertStructVelocityToVector(pred)

        if tth < agent.fakeDeltaTime:
            continue

        # if not is_shot_scorable(pred_vec, agent.enemyGoalLocations[0], agent.enemyGoalLocations[2])[2]:
        #     continue

        if grounded:
            if pred_vec[1] > grounder_cutoff:
                agent.grounded_timer = tth
                grounded = False

        # if findDistance(agent.me.location,pred_vec)-agent.reachLength > 2300 * tth:
        #     continue

        # acceptableAngle = is_shot_scorable(pred_vec, leftPost, rightPost)[2]

        grounder = False
        if not aboveThreshold:
            if pred.physics.location.z > doubleCutOff:
                aboveThreshold = True
                aerialsValid = True

        if aboveThreshold:
            if pred.physics.location.z <= doubleCutOff:
                aerialsValid = False

        if ground_shot == None or wall_shot == None:
            if isBallHittable(pred, agent, grounder_cutoff):
                wallshot = isBallNearWall(pred)
                if not wallshot or pred_vec[2] <= grounder_cutoff:
                    grounder = True
                    if ground_shot == None:
                        if determine_if_shot_goalward(pred_vel, agent.team):
                            tempOffset = goalward_ground_offset
                        else:
                            tempOffset = ground_offset
                        if not agent.onWall:
                            timeToTarget = inaccurateArrivalEstimator(
                                agent,
                                Vector(
                                    [
                                        pred.physics.location.x,
                                        pred.physics.location.y,
                                        pred.physics.location.z,
                                    ]
                                ),
                                False,
                                offset=tempOffset,
                            )
                        else:
                            timeToTarget = new_ground_wall_estimator(agent, pred_vec)[0]

                        if timeToTarget < tth:
                            if (
                                not checkAngles
                                or is_shot_scorable(
                                    pred_vec,
                                    agent.enemyGoalLocations[0],
                                    agent.enemyGoalLocations[2],
                                )[2]
                            ):
                                ground_shot = hit(
                                    agent.time,
                                    pred.game_seconds,
                                    0,
                                    pred_vec,
                                    convertStructVelocityToVector(pred),
                                    True,
                                    timeToTarget,
                                )
                            # print(f"found ground shot {agent.time}")
                else:
                    if wall_shot == None:
                        _wall = which_wall(pred_vec)
                        if not (
                            (agent.team == 0 and _wall == 0)
                            or (agent.team == 1 and _wall == 2)
                        ):
                            if agent.onWall and wallshot:
                                distance = findDistance(agent.me.location, pred_vec)
                                timeToTarget = inaccurateArrivalEstimator(
                                    agent, pred_vec, True, offset=_offset
                                )

                                if timeToTarget < tth:
                                    if (
                                        not checkAngles
                                        or is_shot_scorable(
                                            pred_vec,
                                            agent.enemyGoalLocations[0],
                                            agent.enemyGoalLocations[2],
                                        )[2]
                                    ):
                                        wall_shot = hit(
                                            agent.time,
                                            pred.game_seconds,
                                            2,
                                            pred_vec,
                                            convertStructVelocityToVector(pred),
                                            True,
                                            timeToTarget,
                                        )
                                        agent.targetDistance = distance
                                        agent.timeEstimate = timeToTarget

                            else:
                                if wallshot:
                                    (
                                        timeToTarget,
                                        distance,
                                        valid,
                                    ) = new_ground_wall_estimator(agent, pred_vec)
                                    if timeToTarget < tth:
                                        if valid:
                                            if (
                                                not checkAngles
                                                or is_shot_scorable(
                                                    pred_vec,
                                                    agent.enemyGoalLocations[0],
                                                    agent.enemyGoalLocations[2],
                                                )[2]
                                            ):
                                                wall_shot = hit(
                                                    agent.time,
                                                    pred.game_seconds,
                                                    2,
                                                    pred_vec,
                                                    convertStructVelocityToVector(pred),
                                                    True,
                                                    timeToTarget,
                                                )
                                                agent.targetDistance = distance
                                                agent.timeEstimate = timeToTarget
                                            # print("wallshot valid")
                                        else:
                                            pass

        if jumpshot == None:
            if (
                pred.physics.location.z > grounder_cutoff
                and pred.physics.location.z <= jumpshot_cutoff
            ):
                # tempOffset = _offset
                if pred_vec[1] * sign(agent.team) > 0:
                    tempOffset = agent.reachLength
                if isBallHittable(agent.ballPred.slices[i], agent, doubleCutOff):
                    if not agent.onWall:
                        distance = distance2D(pred_vec, agent.me.location)
                        timeToTarget = inaccurateArrivalEstimator(
                            agent, pred_vec, False, offset=_offset
                        )
                    else:
                        timeToTarget, distance, valid = new_ground_wall_estimator(
                            agent, pred_vec
                        )

                    if timeToTarget <= tth:
                        jumpSim = jumpSimulatorNormalizingJit(
                            float32(agent.gravity),
                            float32(agent.fakeDeltaTime),
                            np.array(agent.me.velocity, dtype=np.dtype(float)),
                            float32(agent.defaultElevation),
                            float32(tth),
                            float32(pred.physics.location.z),
                            False,
                        )

                        # print(f"{jumpSim[2],pred.physics.location.z,tth}")
                        if (
                            abs(jumpSim[2] - pred.physics.location.z)
                            <= agent.allowableJumpDifference
                        ):
                            # if jumpSim[2] + agent.allowableJumpDifference >= pred.physics.location.z:
                            if tth > jumpSim[3]:
                                if (
                                    not checkAngles
                                    or is_shot_scorable(
                                        pred_vec,
                                        agent.enemyGoalLocations[0],
                                        agent.enemyGoalLocations[2],
                                    )[2]
                                ):
                                    jumpshot = hit(
                                        agent.time,
                                        pred.game_seconds,
                                        1,
                                        pred_vec,
                                        convertStructVelocityToVector(pred),
                                        True,
                                        timeToTarget,
                                        jumpSim=jumpSim,
                                    )

        # if catchCanidate == None:
        #     pass
        if agent.DoubleJumpShotsEnabled:
            if doubleJumpShot == None:
                if (
                    pred.physics.location.z > jumpshot_cutoff
                    and pred.physics.location.z <= doubleCutOff
                    and (
                        pred_vec[2] < 525
                        or not butterZone(pred_vec)
                        or pred_vec[1] * sign(agent.team) < 0
                    )
                ):
                    if isBallHittable(agent.ballPred.slices[i], agent, doubleCutOff):
                        if not agent.onWall:
                            distance = distance2D(pred_vec, agent.me.location)
                            timeToTarget = inaccurateArrivalEstimator(
                                agent, pred_vec, False, offset=_offset
                            )
                        else:
                            timeToTarget, distance, valid = new_ground_wall_estimator(
                                agent, pred_vec
                            )
                        # filtering out predictions that would likely hit top bar on offfense
                        if pred_vec[1] * -sign(agent.team) > 0:
                            if butterZone(pred_vec):
                                if pred_vec[2] > 880 - (93.5 * 2):
                                    timeToTarget = 100  # setting simulated arrival time to fake number to dissuade attempt

                        if timeToTarget <= tth:
                            # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z)
                            jumpSim = jumpSimulatorNormalizingJit(
                                float32(agent.gravity),
                                float32(agent.fakeDeltaTime),
                                np.array(agent.me.velocity, dtype=np.dtype(float)),
                                float32(agent.defaultElevation),
                                float32(tth),
                                float32(pred.physics.location.z),
                                True,
                            )

                            # print(f"{jumpSim[2],pred.physics.location.z,tth}")
                            if (
                                abs(jumpSim[2] - pred.physics.location.z)
                                <= agent.allowableJumpDifference
                            ):
                                # if jumpSim[2] + agent.allowableJumpDifference >= pred.physics.location.z:
                                if tth > jumpSim[3]:
                                    if (
                                        not checkAngles
                                        or is_shot_scorable(
                                            pred_vec,
                                            agent.enemyGoalLocations[0],
                                            agent.enemyGoalLocations[2],
                                        )[2]
                                    ):
                                        doubleJumpShot = hit(
                                            agent.time,
                                            pred.game_seconds,
                                            4,
                                            pred_vec,
                                            convertStructVelocityToVector(pred),
                                            True,
                                            timeToTarget,
                                            jumpSim=jumpSim,
                                        )

        if (
            aerialShot == None and not agent.goalPred and agent.aerialsEnabled
        ):  # ORIGINAL!!!!
            # if not in_goal_check(agent):
            if (
                pred_vec[1] * sign(agent.team)
                <= agent.me.location[1] * sign(agent.team)
                or pred_vec[1] * sign(agent.team) > 3500
            ):
                if (agent.me.location != agent.lastMan or not agent.onSurface) or len(
                    agent.allies
                ) > 1:
                    # if not checkAngles or (
                    #     checkAngles and is_shot_scorable(pred_vec, leftPost, rightPost)[2]
                    # ):
                    if True:
                        """
                        Cull aerials that the enemy can easily touch first
                        """
                        # if agent.team == 0:
                        # if (agent.onSurface and agent.enemyBallInterceptDelay >= tth) or (not agent.onSurface and tth > agent.enemyBallInterceptDelay+1):
                        #     continue

                        if (
                            agent.me.boostLevel >= 1
                        ):  # and agent.me.location[1] * sign(agent.team) > pred_vec[1] * sign(
                            # agent.team):

                            if (
                                agent.me.velocity[2] > -50
                                or pred_vec[2] < agent.me.location[2]
                            ):
                                if (
                                    inaccurateArrivalEstimator(
                                        agent, pred_vec, False, offset=_offset
                                    )
                                    < tth
                                ):
                                    defensiveTouch = False
                                    if not defensiveTouch:
                                        if (
                                            butterZone(pred_vec)
                                            or distance2D(pred_vec, center) < 2000
                                        ):
                                            target = get_aim_vector(
                                                agent,
                                                center.flatten(),
                                                pred_vec,
                                                pred_vel,
                                                agent.reachLength * 0.5,
                                            )[0]
                                        else:
                                            if (
                                                agent.gravity <= -650
                                                or pred_vec[1] * sign(agent.team) > 0
                                            ):
                                                _direction = direction(
                                                    pred_vec.flatten(), center.flatten()
                                                ).normalize()
                                                target = pred_vec + _direction.scale(
                                                    agent.reachLength * 0.5
                                                )
                                            else:
                                                _direction = direction(
                                                    pred_vec, center
                                                ).normalize()
                                                target = pred_vec + _direction.scale(
                                                    agent.reachLength * 0.5
                                                )

                                    else:
                                        if pred_vec[0] > agent.me.location[0]:
                                            shot_target = Vector(
                                                [
                                                    4500,
                                                    pred_vec[1]
                                                    + -sign(agent.team) * 4000,
                                                    pred_vec[2] + 1000,
                                                ]
                                            )
                                        else:
                                            shot_target = Vector(
                                                [
                                                    -4500,
                                                    pred_vec[1]
                                                    + -sign(agent.team) * 4000,
                                                    pred_vec[2] + 1000,
                                                ]
                                            )
                                        _direction = direction(
                                            pred_vec, shot_target
                                        ).normalize()
                                        # _direction = direction(pred_vec, Vector([0,center[0],3000]))
                                        target = pred_vec + _direction.scale(
                                            agent.reachLength * 0.5
                                        )

                                    aerial_accepted = False

                                    if agent.onSurface and not agent.aerialsLimited:
                                        if (
                                                enough_takeoff_room(agent, pred_vec)[0]
                                            or agent.onWall
                                        ):
                                            if (
                                                pred_vec[2] > doubleCutOff + 100
                                            ):  # and tth < agent.enemyBallInterceptDelay:
                                                if agent.me.location[1] * sign(
                                                    agent.team
                                                ) > pred_vec[1] * sign(agent.team):

                                                    accel_req_limit = clamp(
                                                        1060,
                                                        750,
                                                        1060
                                                        - (((6 - tth) * 0.35)) * 100,
                                                    )
                                                    expected_jump_boost = 400
                                                    if agent.onWall:
                                                        expected_jump_boost = 200
                                                    delta_a = calculate_delta_acceleration(
                                                        target - agent.me.location,
                                                        agent.me.velocity
                                                        + agent.up.scale(expected_jump_boost),
                                                        tth,
                                                        agent.gravity,
                                                    )
                                                    if (
                                                        delta_a.magnitude()
                                                        < accel_req_limit
                                                    ):
                                                        if (
                                                            delta_a.magnitude() * tth
                                                            < agent.available_delta_v
                                                        ):
                                                            if (
                                                                agent.me.velocity
                                                                + delta_a
                                                            ).magnitude() < maxPossibleSpeed:
                                                                aerial_accepted = True
                                                    else:
                                                        approach_direction = direction(
                                                            agent.me.location.flatten(),
                                                            pred_vec.flatten(),
                                                        ).normalize()
                                                        pseudo_position = pred_vec.flatten() - approach_direction.scale(
                                                            pred_vec[2]
                                                        )
                                                        req_delta_a = calculate_delta_acceleration(
                                                            pseudo_position
                                                            - agent.me.location,
                                                            approach_direction.scale(
                                                                2300
                                                            )
                                                            + agent.up.scale(300),
                                                            tth,
                                                            agent.gravity,
                                                        )
                                                        req_delta_v = (
                                                            req_delta_a.magnitude()
                                                            * tth
                                                        )
                                                        if (
                                                            req_delta_v
                                                            < agent.available_delta_v
                                                            and req_delta_a.magnitude()
                                                            < accel_req_limit
                                                        ):
                                                            if (
                                                                agent.me.velocity
                                                                + req_delta_a
                                                            ).magnitude() < maxPossibleSpeed:
                                                                aerial_accepted = True

                                                        if not agent.onWall:
                                                            if tth < 2:
                                                                aerial_accepted = False

                                                        if len(agent.allies) < 1:
                                                            aerial_accepted = False

                                                    # if agent.team == 0:
                                                    ideal_velocity = (
                                                        agent.me.velocity + delta_a
                                                    )
                                                    if (
                                                        ideal_velocity.magnitude()
                                                        >= maxPossibleSpeed
                                                    ):
                                                        aerial_accepted = False
                                    else:
                                        if pred_vec[2] > agent.aerial_min:
                                            delta_a = calculate_delta_acceleration(
                                                target - agent.me.location,
                                                agent.me.velocity,
                                                tth,
                                                agent.gravity,
                                            )
                                            accel_req_limit = clamp(
                                                1060,
                                                750,
                                                1060 - (((6 - tth) * 0.1)) * 100,
                                            )

                                            # if agent.team == 0:
                                            # accel_req_limit = 1000

                                            if delta_a.magnitude() <= accel_req_limit:
                                                req_delta_v = delta_a.magnitude() * tth
                                                if (
                                                    req_delta_v
                                                    < agent.available_delta_v - 10
                                                ):
                                                    aerial_accepted = True
                                            # if agent.team == 0:
                                            ideal_velocity = agent.me.velocity + delta_a
                                            if (
                                                ideal_velocity.magnitude()
                                                >= maxPossibleSpeed
                                            ):
                                                aerial_accepted = False

                                        if aerial_accepted and agent.aerialsLimited:
                                            if findDistance(
                                                agent.me.location, pred_vec
                                            ) > 1000 or pred_vec[1] * sign(
                                                agent.team
                                            ) > agent.me.location[
                                                1
                                            ] * sign(
                                                agent.team
                                            ):
                                                aerial_accepted = False

                                    if aerial_accepted:

                                        _aerial = agent.aerialGetter(pred, target, tth)

                                        aerialShot = hit(
                                            agent.time,
                                            pred.game_seconds,
                                            5,
                                            pred_vec,
                                            convertStructVelocityToVector(pred),
                                            True,
                                            tth,
                                            aerialState=_aerial,
                                        )

        precariousSituation = False
        if agent.team == 0:
            if pred.physics.location.y <= -d_max_y:
                precariousSituation = True
        elif agent.team == 1:
            if pred.physics.location.y >= d_max_y:
                precariousSituation = True

        if not agent.scorePred:
            if not precariousSituation:
                if abs(pred.physics.location.y) >= o_max_y:
                    # (self, location, _time):
                    agent.scorePred = predictionStruct(pred_vec, pred.game_seconds)

        if precariousSituation:
            # if pred.physics.location.y * sign(agent.team) <= 5250* sign(agent.team):
            # print(f"in here {agent.time}")
            # if abs(pred.physics.location.y) >= 5250:
            timeToTarget = inaccurateArrivalEstimator(
                agent,
                Vector(
                    [
                        pred.physics.location.x,
                        pred.physics.location.y,
                        pred.physics.location.z,
                    ]
                ),
                False,
                offset=ground_offset,
            )
            if agent.ballPred.slices[i].physics.location.z <= grounder_cutoff:
                if ground_shot == None:
                    ground_shot = hit(
                        agent.time,
                        agent.ballPred.slices[i].game_seconds,
                        0,
                        convertStructLocationToVector(agent.ballPred.slices[i]),
                        convertStructVelocityToVector(agent.ballPred.slices[i]),
                        False,
                        timeToTarget,
                    )

            elif agent.ballPred.slices[i].physics.location.z <= jumpshot_cutoff:
                if jumpshot == None:
                    # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z, doubleJump=False)
                    jumpSim = jumpSimulatorNormalizingJit(
                        float32(agent.gravity),
                        float32(agent.fakeDeltaTime),
                        np.array(agent.me.velocity, dtype=np.dtype(float)),
                        float32(agent.defaultElevation),
                        float32(tth),
                        float32(pred.physics.location.z),
                        False,
                    )
                    # if jumpSim[2] + agent.allowableJumpDifference >= pred.physics.location.z:
                    # if tth > jumpSim[3]:
                    jumpshot = hit(
                        agent.time,
                        pred.game_seconds,
                        1,
                        convertStructLocationToVector(pred),
                        convertStructVelocityToVector(pred),
                        True,
                        timeToTarget,
                        jumpSim=jumpSim,
                    )

            else:
                if agent.DoubleJumpShotsEnabled:
                    if doubleJumpShot == None:
                        # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z)
                        jumpSim = jumpSimulatorNormalizingJit(
                            float32(agent.gravity),
                            float32(agent.fakeDeltaTime),
                            np.array(agent.me.velocity, dtype=np.dtype(float)),
                            float32(agent.defaultElevation),
                            float32(tth),
                            float32(pred.physics.location.z),
                            True,
                        )
                        doubleJumpShot = hit(
                            agent.time,
                            pred.game_seconds,
                            4,
                            convertStructLocationToVector(pred),
                            convertStructVelocityToVector(pred),
                            True,
                            timeToTarget,
                            jumpSim=jumpSim,
                        )

            agent.goalPred = agent.ballPred.slices[i]
            if (
                ground_shot == None
                and jumpshot == None
                and wall_shot == None
                and doubleJumpShot == None
            ):

                if pred_vec[2] <= agent.groundCutOff:
                    ground_shot = hit(
                        agent.time,
                        pred.game_seconds,
                        0,
                        convertStructLocationToVector(agent.ballPred.slices[i]),
                        convertStructVelocityToVector(agent.ballPred.slices[i]),
                        False,
                        tth,
                    )
                elif (
                    pred_vec[2] > agent.groundCutOff
                    and pred_vec[2] < agent.doubleJumpLimit
                ):
                    jumpSim = jumpSimulatorNormalizingJit(
                        float32(agent.gravity),
                        float32(agent.fakeDeltaTime),
                        np.array(agent.me.velocity, dtype=np.dtype(float)),
                        float32(agent.defaultElevation),
                        float32(tth),
                        float32(pred.physics.location.z),
                        False,
                    )
                    jumpshot = hit(
                        agent.time,
                        pred.game_seconds,
                        1,
                        convertStructLocationToVector(pred),
                        convertStructVelocityToVector(pred),
                        True,
                        timeToTarget,
                        jumpSim=jumpSim,
                    )

                else:

                    if agent.DoubleJumpShotsEnabled:
                        jumpSim = jumpSimulatorNormalizingJit(
                            float32(agent.gravity),
                            float32(agent.fakeDeltaTime),
                            np.array(agent.me.velocity, dtype=np.dtype(float)),
                            float32(agent.defaultElevation),
                            float32(tth),
                            float32(pred.physics.location.z),
                            True,
                        )
                        doubleJumpShot = hit(
                            agent.time,
                            pred.game_seconds,
                            4,
                            convertStructLocationToVector(pred),
                            convertStructVelocityToVector(pred),
                            True,
                            timeToTarget,
                            jumpSim=jumpSim,
                        )
            if grounded:
                agent.grounded_timer = tth
                grounded = False
            return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot

    if (
        ground_shot == None
        and jumpshot == None
        and wall_shot == None
        and doubleJumpShot == None
    ):
        ground_shot = hit(
            agent.time,
            agent.time + 6,
            0,
            convertStructLocationToVector(agent.ballPred.slices[i]),
            convertStructVelocityToVector(agent.ballPred.slices[i]),
            False,
            6,
        )

        agent.timid = True

    if grounded:
        agent.grounded_timer = tth
        grounded = False

    return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot


def inaccurateArrivalEstimatorRemote(agent, start, destination):
    distance = clamp(math.inf, 1, distance2D(start, destination))
    currentSpd = clamp(2300, 1, agent.currentSpd)

    if agent.me.boostLevel > 0:
        maxSpd = clamp(2300, currentSpd, currentSpd + (distance * 0.3))
    else:
        maxSpd = clamp(maxPossibleSpeed, currentSpd, currentSpd + (distance * 0.15))

    return distance / maxSpd


def inaccurateArrivalEstimator(agent, destination, onWall=False, offset=120):
    if onWall:
        distance = clamp(
            math.inf, 0.00001, findDistance(agent.me.location, destination) - offset
        )
    else:
        distance = clamp(
            math.inf, 0.00001, distance2D(agent.me.location, destination) - offset
        )
    moreAccurateEstimation = timeWithAccelAgentless(
        agent.currentSpd,
        agent.me.boostLevel,
        distance,
        agent.fakeDeltaTime,
        agent.boostConsumptionRate,
        agent.gravity,
        onWall,
    )

    return moreAccurateEstimation


def inaccurateArrivalEstimatorBoostless(agent, destination, onWall=False, offset=120):
    if onWall:
        distance = clamp(
            math.inf, 0.00001, findDistance(agent.me.location, destination) - offset
        )
    else:
        distance = clamp(
            math.inf, 0.00001, distance2D(agent.me.location, destination) - offset
        )
    moreAccurateEstimation = timeWithAccelAgentless(
        agent.currentSpd,
        0,
        distance,
        agent.fakeDeltaTime,
        agent.boostConsumptionRate,
        agent.gravity,
        False,
    )

    return moreAccurateEstimation


def enemyArrivalEstimator(agent, phys_obj, destination):
    distance = clamp(
        math.inf, 0.00001, distance2D(phys_obj.location, destination) - 155,
    )
    moreAccurateEstimation = calcEnemyTimeWithAcceleration(agent, distance, phys_obj)
    return moreAccurateEstimation


def calcEnemyTimeWithAcceleration(agent, distance, enemyPhysicsObject):
    estimatedSpd = abs(enemyPhysicsObject.velocity.magnitude())
    estimatedTime = 0
    distanceTally = 0
    boostAmount = enemyPhysicsObject.boostLevel
    boostingCost = 33.3 * agent.deltaTime
    linearChunk = 1600 / 1410
    # print("enemy started")
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = getNaturalAccelerationJitted(
                estimatedSpd, agent.gravity, False
            )
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            if acceleration > 0:
                estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.deltaTime
            estimatedTime += agent.deltaTime
        else:
            distanceTally += estimatedSpd * agent.deltaTime
            estimatedTime += agent.deltaTime

    # print("enemy ended")
    return estimatedTime


def which_wall(destination):
    # orange = north
    if destination[1] >= 4800:
        # orange backboard
        return 0
    elif destination[1] < -4800:
        # blue backboard
        return 2
    elif destination[0] < -3800:
        # east wall
        return 1

    elif destination[0] > 3800:
        # west wall
        return 3
    else:
        # not near wall
        return -1


def guided_find_wall_intesection(agent, destination):
    partDist = clamp(1000, 500, distance2D(agent.me.location, destination) * 0.5)
    partDist = clamp(1500, partDist, destination[2] * 0.5)

    y_intercept = destination[1] + (sign(agent.team) * partDist)

    if destination[0] > 0:
        if sign(agent.team) * destination[1] > 4500:
            x_intercept = destination[0]  # - partDist
        else:
            x_intercept = destination[0]  # + partDist
    else:
        if sign(agent.team) * destination[1] > 4500:
            x_intercept = destination[0]  # + partDist
        else:
            x_intercept = destination[0]  # - partDist

    wall = which_wall(destination)
    if wall == 0:
        intersection = Vector([x_intercept, 5200, 0])
    elif wall == 1:
        intersection = Vector([-4100, y_intercept, 0])
    elif wall == 2:
        intersection = Vector([x_intercept, -5200, 0])
    else:
        intersection = Vector([4100, y_intercept, 0])

    # print(f"original intercept: {destination[1]}, new intercept: {intersection[1]}, team: {agent.team}")

    return intersection, wall, distance2D(agent.me.location, intersection) >= partDist


def find_wall_intersection(phys_obj, destination):
    y_intercept = (destination.data[1] + phys_obj.location[1]) / 2
    x_intercept = (destination.data[0] + phys_obj.location[0]) / 2

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


def enemyWallMovementEstimator(phys_obj, destination, agent):
    intersection = find_wall_intersection(phys_obj, destination)[0]
    _distance = clamp(
        math.inf, 0.0001, findDistance(intersection, phys_obj.location) - 140
    )
    _distance += findDistance(intersection, destination)
    return (
        timeWithAccelAgentless(
            phys_obj.velocity.magnitude(),
            phys_obj.boostLevel,
            _distance,
            agent.fakeDeltaTime,
            agent.boostConsumptionRate,
            agent.gravity,
            False,
        ),
        _distance,
    )


# # orange = north
#     if destination[1] >= 4900:
#         # orange backboard
#         return 0
#     elif destination[1] < -4900:
#         # blue backboard
#         return 2
#     elif destination[0] < -3900:
#         # east wall
#         return 1
#     else:
#         # west wall
#         return 3
def validateWallAttempt(agent, intersection, wall):
    if wall == 0 or wall == 1:
        index = 0
    else:
        index = 1
    if distance2D(agent.me.location, intersection):
        pass


def new_ground_wall_estimator(agent, destination):
    offset = agent.reachLength
    if agent.onWall:
        flattened_destination = unroll_path_from_wall_to_ground(
            agent.me.location, destination
        )
    else:
        flattened_destination = unroll_path_from_ground_to_wall(destination)
        offset = 90
    estimation = inaccurateArrivalEstimator(
        agent, flattened_destination, True, offset=1,
    )
    return (
        estimation,
        distance2D(agent.me.location, flattened_destination),
        True,
    )


# def new_ground_wall_estimator(agent, destination):
#     intersection, wall, valid = guided_find_wall_intesection(agent, destination)
#     _distance1 = findDistance(intersection, agent.me.location)
#     _distance2 = findDistance(intersection, destination)
#     sim1 = 0
#     sim2 = 0
#     if agent.onWall:
#         sim1 = timeWithAccelAgentless(
#             agent.currentSpd,
#             agent.me.boostLevel,
#             _distance1,
#             agent.fakeDeltaTime,
#             agent.boostConsumptionRate,
#             True,
#         )
#         sim2 = timeWithAccelAgentless(
#             agent.currentSpd,
#             agent.me.boostLevel,
#             _distance2,
#             agent.fakeDeltaTime,
#             agent.boostConsumptionRate,
#             False,
#         )
#     else:
#         sim1 = timeWithAccelAgentless(
#             agent.currentSpd,
#             agent.me.boostLevel,
#             _distance1,
#             agent.fakeDeltaTime,
#             agent.boostConsumptionRate,
#             False,
#         )
#         sim2 = timeWithAccelAgentless(
#             agent.currentSpd,
#             agent.me.boostLevel,
#             _distance2,
#             agent.fakeDeltaTime,
#             agent.boostConsumptionRate,
#             True,
#         )
#
#     return (
#         sim1 + sim2,
#         _distance1 + _distance2,
#         valid,
#     )


def groundWallArrivalEstimator(agent, destination):
    if agent.me.location[2] > destination[2]:
        wallVec = agent.me.location
        groundVec = destination
    else:
        wallVec = destination
        groundVec = agent.me.location

    totalDistance = find_L_distance(groundVec, wallVec)
    # return calcTimeWithAcceleration(agent,totalDistance),totalDistance
    return (
        timeWithAccelAgentless(
            agent.currentSpd,
            agent.me.boostLevel,
            totalDistance,
            agent.fakeDeltaTime,
            agent.boostConsumptionRate,
        ),
        totalDistance,
    )


def lerp(v0, v1, t):  # linear interpolation
    return (1 - t) * v0 + t * v1


@jit(float32(float32, float32, boolean))
def getNaturalAccelerationJitted(currentSpd, gravityValue, onWall):
    normalIncrement = 1440.0 / 1400.0
    topIncrement = 160.0 / 10.0

    if currentSpd <= 1400:
        if not onWall:
            return (1440 - (currentSpd * normalIncrement)) + 160
        else:
            return clamp(
                5000, 0, (1440 - (currentSpd * normalIncrement)) + 160 - gravityValue
            )
    elif currentSpd <= 1410:
        if not onWall:
            return 160 - ((currentSpd - 1400) * topIncrement)
        else:
            return clamp(
                5000, 0, 160 - ((currentSpd - 1400) * topIncrement) - gravityValue
            )
    else:
        return 0


# (agent.currentSpd,agent.me.boostLevel,distance,agent.fakeDeltaTime,agent.boostConsumptionRate)
@jit(float32(float32, float32, float32, float32, float32, float32, boolean))
def timeWithAccelAgentless(
    estimatedSpd, boostAmount, distance, fakeDelta, boostingCost, gravity, onWall
):
    estimatedTime = 0
    distanceTally = 0
    flipped = False
    while distanceTally < distance and estimatedTime < 7:
        if estimatedSpd < 2300:
            acceleration = getNaturalAccelerationJitted(estimatedSpd, gravity, onWall)
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            else:
                if (
                    not flipped
                    and (distance - distanceTally) > estimatedSpd * 1.8
                    and not onWall
                    and estimatedSpd > 1100
                ):
                    flipped = True
                    # acceleration += 500
                    estimatedSpd = clamp(2300, 1, estimatedSpd + 500)
            if acceleration > 0:
                estimatedSpd += acceleration * fakeDelta
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta
        else:
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta

    # print("friendly ended")
    return estimatedTime


def timeWithAccelAgentless_normal(
    currentSpd, currentBoost, distance, fakeDelta, boostingCost
):
    estimatedSpd = currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = currentBoost
    # boostingCost = boostingCost
    flipped = False
    while distanceTally < distance and estimatedTime < 7:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = getNaturalAccelerationJitted(
                estimatedSpd
            )  # 1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            else:
                if not flipped and (distance - distanceTally) > 1500:
                    flipped = True
                    # acceleration += 500
                    estimatedSpd = clamp(maxPossibleSpeed, 1, estimatedSpd + 500)
            if acceleration > 0:
                estimatedSpd += acceleration * fakeDelta
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta
        else:
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta

    # print("friendly ended")
    return estimatedTime


@jit(
    typeof(np.array([float32(1.1), float32(1.1), float32(1.1)], dtype=np.dtype(float)))(
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float)))
    )
)
def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


@jit(
    typeof((float32(1), float32(1), float32(1), float32(1), True))(
        float32,
        float32,
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float))),
        float32,
        float32,
        float32,
        typeof(False),
    ),
    nopython=True
)
def jumpSimulatorNormalizingJit(
    gravity,
    fakeDeltaTime,
    velocity_np,
    defaultElevation,
    timeAllloted,
    targetHeight,
    doubleJump,
):
    initialJumpVel = 292
    jumpHoldBonusVelocity = 1458
    firstJumpBonusMaxTimer = 0.2
    minimumHoldTimer = fakeDeltaTime * 3
    stickyforce = -325  # magnetic force pulling wheels to ground/walls
    stickyTimer = fakeDeltaTime * 3
    secondJumpVel = 292
    # second jump timer limit = 1.25s after first jump is released or 0.2s, whichever is soonest
    # secondJumpTimeLimit = 1.25

    secondJumped = False
    if not doubleJump:
        simTimeMax = clamp(1.44, 0.001, timeAllloted)
    else:
        simTimeMax = clamp(6, 0, timeAllloted)  # allowing for weird gravity
    if not doubleJump:
        if simTimeMax < 0.2 + fakeDeltaTime * 2:
            simTimeMax -= fakeDeltaTime * 2
    simTime = 0
    firstJumpTimer = 0
    secondJumpTimer = 0
    additionalAltitude = defaultElevation

    estimatedVelocity = np.linalg.norm(velocity_np)

    heightMax = float32(0)
    maxHeightTime = float32(0)

    targetHeightTimer = float32(0)

    firstPauseTimer = 0
    secondPauseTimer = 0

    while simTime < simTimeMax:
        upwardsVelocity = 0
        if simTime == 0:
            velocity_np[2] += initialJumpVel

        if simTime < stickyTimer:
            upwardsVelocity += stickyforce * fakeDeltaTime

        if simTime < 0.2 and simTime < simTimeMax:
            upwardsVelocity += jumpHoldBonusVelocity * fakeDeltaTime

        else:
            if doubleJump:
                if not secondJumped:
                    velocity_np[2] += secondJumpVel
                    # upwardsVelocity+= secondJumpVel
                    secondJumped = True

        upwardsVelocity += gravity * fakeDeltaTime

        velocity_np[2] += upwardsVelocity

        estimatedVelocity = np.linalg.norm(velocity_np)
        if estimatedVelocity > 2300:
            velocity_np = np.multiply(
                velocity_np / np.sqrt(np.sum(velocity_np ** 2)), 2300
            )

        additionalAltitude += velocity_np[2] * fakeDeltaTime
        simTime += fakeDeltaTime

        if additionalAltitude > heightMax:
            heightMax = additionalAltitude * 1
            maxHeightTime = simTime * 1

        if targetHeightTimer == 0:
            if additionalAltitude >= targetHeight:
                targetHeightTimer = simTime

        if additionalAltitude < heightMax:
            break

    return (
        float32(targetHeight),
        float32(targetHeightTimer),
        float32(heightMax),
        float32(maxHeightTime - fakeDeltaTime),
        doubleJump,
    )



def jumpSimulatorNormalizing(agent, timeAllloted, targetHeight, doubleJump=True):
    initialJumpVel = 292
    jumpHoldBonusVelocity = 1458
    firstJumpBonusMaxTimer = 0.2
    minimumHoldTimer = agent.fakeDeltaTime * 3
    stickyforce = -325  # magnetic force pulling wheels to ground/walls
    stickyTimer = agent.fakeDeltaTime * 3
    secondJumpVel = 292
    # second jump timer limit = 1.25s after first jump is released or 0.2s, whichever is soonest
    secondJumpTimeLimit = 1.25
    cached_simulation = []  # simulated time, simulated z velocity, simulated height

    secondJumped = False
    simTimeMax = clamp(1.6, 0, timeAllloted)
    if simTimeMax < 0.2 + agent.fakeDeltaTime * 2:
        simTimeMax -= agent.fakeDeltaTime * 2
    simTime = 0
    firstJumpTimer = 0
    secondJumpTimer = 0
    additionalAltitude = agent.defaultElevation * 1

    estimatedVelocity = agent.me.velocity.scale(1)

    heightMax = 0
    maxHeightTime = 0

    targetHeightTimer = 0

    firstPauseTimer = 0
    secondPauseTimer = 0

    while simTime < simTimeMax:
        upwardsVelocity = 0
        if simTime == 0:
            upwardsVelocity += initialJumpVel

        if simTime < stickyTimer:
            upwardsVelocity += stickyforce * agent.fakeDeltaTime

        if simTime < 0.2 and simTime < simTimeMax:
            upwardsVelocity += jumpHoldBonusVelocity * agent.fakeDeltaTime

        else:
            if doubleJump:
                if not secondJumped:
                    upwardsVelocity += secondJumpVel
                    secondJumped = True

        upwardsVelocity += agent.gravity * agent.fakeDeltaTime

        estimatedVelocity.data[2] += upwardsVelocity

        magnitude = estimatedVelocity.magnitude()
        # print(f"magnitude is {magnitude}")
        if magnitude > 2300:
            normalized = estimatedVelocity.normalize()
            estimatedVelocity = normalized.scale(2300)

        additionalAltitude += estimatedVelocity[2] * agent.fakeDeltaTime
        simTime += agent.fakeDeltaTime

        if additionalAltitude > heightMax:
            heightMax = additionalAltitude * 1
            maxHeightTime = simTime * 1

        if targetHeightTimer == 0:
            if additionalAltitude >= targetHeight:
                targetHeightTimer = simTime

        cached_simulation.append([simTime, estimatedVelocity[2], additionalAltitude])

    return targetHeight, targetHeightTimer, heightMax, maxHeightTime, cached_simulation


def jumpSimulatorStationary(agent, timeAllloted, doubleJump=True):
    initialJumpVel = 292
    jumpHoldBonusVelocity = 1458
    firstJumpBonusMaxTimer = 0.2
    minimumHoldTimer = agent.fakeDeltaTime * 3
    stickyforce = -325  # magnetic force pulling wheels to ground/walls
    stickyTimer = agent.fakeDeltaTime * 3
    secondJumpVel = 292
    # second jump timer limit = 1.25s after first jump is released or 0.2s, whichever is soonest
    secondJumpTimeLimit = 1.25

    secondJumped = False
    simTimeMax = clamp(2, 0, timeAllloted)
    simTime = 0
    firstJumpTimer = 0
    secondJumpTimer = 0
    additionalAltitude = 0

    upwardsVelocity = 0

    while simTime < simTimeMax:
        if simTime == 0:
            upwardsVelocity += initialJumpVel

        if simTime < stickyTimer:
            upwardsVelocity += stickyforce * agent.fakeDeltaTime

        if simTime < 0.2:
            upwardsVelocity += jumpHoldBonusVelocity * agent.fakeDeltaTime

        else:
            if doubleJump:
                if not secondJumped:
                    upwardsVelocity += secondJumpVel
                    secondJumped = True

        upwardsVelocity += agent.gravity * agent.fakeDeltaTime

        additionalAltitude += upwardsVelocity * agent.fakeDeltaTime
        simTime += agent.fakeDeltaTime

    return additionalAltitude


def calcTimeWithAcceleration(agent, distance):
    estimatedSpd = agent.currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = agent.me.boostLevel
    boostingCost = 33.3 * agent.fakeDeltaTime
    flipped = False
    # linearChunk = 1600/1400
    while distanceTally < distance and estimatedTime < 7:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = getNaturalAcceleration(
                estimatedSpd
            )  # 1600 - (estimatedSpd*linearChunk)
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            else:
                if not flipped and (distance - distanceTally) > 1500:
                    flipped = True
                    acceleration += 500
            if acceleration > 0:
                estimatedSpd += acceleration * agent.fakeDeltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime
        else:
            # estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime

    # print("friendly ended")
    return estimatedTime


def calcTimeWithAcceleration_OLD(agent, distance):
    estimatedSpd = agent.currentSpd
    estimatedTime = 0
    distanceTally = 0
    boostAmount = agent.me.boostLevel
    boostingCost = 33.3 * agent.fakeDeltaTime
    linearChunk = 1600 / 1400
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = 1600 - (estimatedSpd * linearChunk)
            if boostAmount > 0:
                acceleration += 991
                boostAmount -= boostingCost
            if acceleration > 0:
                estimatedSpd += acceleration * agent.fakeDeltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime
        else:
            # estimatedSpd += acceleration * agent.deltaTime
            distanceTally += estimatedSpd * agent.fakeDeltaTime
            estimatedTime += agent.fakeDeltaTime

    # print("friendly ended")
    return estimatedTime


def ballHeadedTowardsMyGoal_testing(agent, hit):
    # return hit.pred_vel[1] * sign(agent.team) > 50
    myGoal = Vector([0, 5100 * sign(agent.team), 200])
    if (
        distance1D(myGoal, hit.pred_vector, 1)
        - distance1D(myGoal, hit.pred_vector + hit.pred_vel, 1)
    ) > 0:
        if hit.pred_vel.magnitude() > 5:
            return True

    return False


def ballHeadedTowardsMyGoal(agent):
    myGoal = Vector([0, 5100 * sign(agent.team), 200])
    if (
        distance1D(myGoal, agent.ball.location, 1)
        - distance1D(myGoal, agent.ball.location + agent.ball.velocity, 1)
    ) > 0:
        if agent.ball.velocity.magnitude() > 5:
            return True

    return False


def objectHeadedTowardMyGoal(phys_object, team):
    myGoal = Vector([0, 5100 * sign(team), 200])
    if (
        distance1D(myGoal, phys_object.location, 1)
        - distance1D(myGoal, phys_object.location + phys_object.velocity, 1)
    ) > 0:
        if phys_object.velocity.magnitude() > 5:
            return True

    return False


def openGoalOpportunity(agent):
    enemyGoal = Vector([0, 5100 * -sign(agent.team), 200])
    ballDistance = distance2D(agent.ball.location, enemyGoal)
    playerDistance = distance2D(agent.me.location, enemyGoal)

    for e in agent.enemies:
        _dist = distance2D(e.location, enemyGoal)
        if _dist < ballDistance or _dist < playerDistance:
            return False

    return True


def radius(v):
    return 139.059 + (0.1539 * v) + (0.0001267716565 * v * v)


def turnController(_angle, turnRate):
    return clamp(1, -1, (_angle + turnRate) * 7)


def match_vel(agent, vel_local):
    yaw_angle = math.atan2(vel_local[1], vel_local[0])
    steer = turnController(yaw_angle, 1)
    yaw = turnController(yaw_angle, -agent.me.rotational_velocity[2] / 6)
    pitch_angle = math.atan2(vel_local[2], vel_local[0])
    pitch = turnController(pitch_angle, agent.me.rotational_velocity[1] / 6)
    roll = turnController(-agent.me.rotation[2], agent.me.rotational_velocity[0] / 6)

    return steer, yaw, pitch, roll, abs(yaw_angle) + abs(pitch_angle)


def align_car_to(
    controller: SimpleControllerState, angular_velocity: Vector, forward: Vector, agent
):

    # local_forward = rotation.cast_local(forward)
    local_forward = localizeRotation(forward, agent)
    ang_vel_local = localizeRotation(angular_velocity, agent)

    pitch_angle = math.atan2(-local_forward[2], local_forward[0])
    yaw_angle = math.atan2(-local_forward[1], local_forward[0])

    pitch_angular_velocity = ang_vel_local[1]
    yaw_angular_velocity = ang_vel_local[2]

    p = 4
    d = 0.9

    controller.pitch = clamp(1, -1, -pitch_angle * p + pitch_angular_velocity * d)
    controller.yaw = clamp(1, -1, -yaw_angle * p - yaw_angular_velocity * d)


def align_with_vector(agent, _direction: Vector):
    local_direction = localizeRotation(_direction, agent)
    return match_vel(agent, _direction)


def point_at_position(agent, position: Vector):
    local_position = toLocal(position, agent.me)

    yaw_angle = math.atan2(local_position[1], local_position[0])
    steer = turnController(yaw_angle, 1)
    yaw = turnController(yaw_angle, -agent.me.rotational_velocity[2] / 4)
    pitch_angle = math.atan2(local_position[2], local_position[0])
    pitch = turnController(pitch_angle, agent.me.rotational_velocity[1] / 4)
    roll = turnController(-agent.me.rotation[2], agent.me.rotational_velocity[0] / 4)

    return steer, yaw, pitch, roll, abs(yaw_angle) + abs(pitch_angle)


def matrixDot(_matrix, vector):
    return Vector(
        [
            _matrix[0].dotProduct(vector),
            _matrix[1].dotProduct(vector),
            _matrix[2].dotProduct(vector),
        ]
    )


def drawAsterisks(vec, agent):
    if agent.debugging:
        if agent.team == 0:
            color = agent.renderer.red
        else:
            color = agent.renderer.green

        segmentLength = 55

        topVertical = vec + Vector([0, 0, segmentLength])
        bottomVertical = vec + Vector([0, 0, -segmentLength])
        leftHorizontal = vec + Vector([-segmentLength, 0, 0])
        rightHorizontal = vec + Vector([segmentLength, 0, 0])
        forwardHorizontal = vec + Vector([0, -segmentLength, 0])
        backHorizontal = vec + Vector([0, segmentLength, 0])

        topLeftFrontDiagnal = vec + Vector(
            [-segmentLength, segmentLength, segmentLength]
        )
        topRightFrontDiagnal = vec + Vector(
            [segmentLength, segmentLength, segmentLength]
        )
        bottomLeftFrontDiagnal = vec + Vector(
            [-segmentLength, segmentLength, -segmentLength]
        )
        bottomRightFrontDiagnal = vec + Vector(
            [segmentLength, segmentLength, -segmentLength]
        )

        bottomRightBackDiagnal = vec + Vector(
            [segmentLength, -segmentLength, -segmentLength]
        )
        bottomLeftBackDiagnal = vec + Vector(
            [-segmentLength, -segmentLength, -segmentLength]
        )
        topRightBackDiagnal = vec + Vector(
            [segmentLength, -segmentLength, segmentLength]
        )
        topLeftBackDiagnal = vec + Vector(
            [-segmentLength, -segmentLength, segmentLength]
        )

        points = [
            topVertical,
            bottomVertical,
            leftHorizontal,
            rightHorizontal,
            forwardHorizontal,
            backHorizontal,
            topLeftFrontDiagnal,
            topRightFrontDiagnal,
            bottomLeftFrontDiagnal,
            bottomRightFrontDiagnal,
            bottomRightBackDiagnal,
            bottomLeftBackDiagnal,
            topRightBackDiagnal,
            topLeftBackDiagnal,
        ]

        for p in points:
            agent.renderCalls.append(
                renderCall(
                    agent.renderer.draw_line_3d,
                    p.toList(),
                    (vec + Vector([agent.index, agent.index, agent.index])).toList(),
                    color,
                )
            )


def createBox(agent, _vector):

    if agent.debugging:
        if agent.team == 0:
            color = agent.renderer.blue
        else:
            color = agent.renderer.orange
        half = 55
        tbl = _vector + Vector([-half, half, half])
        tbr = _vector + Vector([half, half, half])
        tfl = _vector + Vector([-half, -half, half])
        tfr = _vector + Vector([half, -half, half])

        bbl = _vector + Vector([-half, half, -half])
        bbr = _vector + Vector([half, half, -half])
        bfl = _vector + Vector([-half, -half, -half])
        bfr = _vector + Vector([half, -half, -half])

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, tbl.toList(), tbr.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, tfr.toList(), tbr.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, tfr.toList(), tfl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, tbl.toList(), tfl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bbl.toList(), bbr.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bfr.toList(), bbr.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bfr.toList(), bfl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bfl.toList(), bbl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bbl.toList(), tbl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bbr.toList(), tbr.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bfl.toList(), tfl.toList(), color)
        )

        agent.renderCalls.append(
            renderCall(agent.renderer.draw_line_3d, bfr.toList(), tfr.toList(), color)
        )


def createTriangle(agent, _vector):
    if agent.debugging:
        _vector = _vector.scale(1)
        _vector.data[2] = 40
        length = 65
        top = _vector + Vector([0, 0, length])
        right = _vector + Vector([length, length, 0])
        left = _vector + Vector([-length, length, 0])
        back = _vector + Vector([0, -length, 0])

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                top.toList(),
                right.toList(),
                agent.renderer.purple,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                top.toList(),
                left.toList(),
                agent.renderer.purple,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                top.toList(),
                back.toList(),
                agent.renderer.purple,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                left.toList(),
                right.toList(),
                agent.renderer.purple,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                back.toList(),
                right.toList(),
                agent.renderer.purple,
            )
        )

        agent.renderCalls.append(
            renderCall(
                agent.renderer.draw_line_3d,
                back.toList(),
                left.toList(),
                agent.renderer.purple,
            )
        )


class field_square:
    def __init__(self, xMin, xMax, yMin, yMax):
        self.corner_one = Vector([xMin, yMin, 0])
        self.corner_two = Vector([xMin, yMax, 0])
        self.corner_three = Vector([xMax, yMin, 0])
        self.corner_four = Vector([xMax, yMax, 0])

        self.xMin = xMin
        self.xMax = xMax
        self.yMin = yMin
        self.yMax = yMax

    def in_boundries(self, vec):
        if inTheMiddle(vec[0], [self.xMin, self.xMax]):
            if inTheMiddle(vec[1], [self.yMin, self.yMax]):
                return True

        return False


if __name__ == "__main__":
    print("You probably shouldn't be running this script like this.")
