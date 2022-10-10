import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
import numpy as np
import ctypes
from time import time
from numba import jit, float32, typeof, boolean

# from functools import lru_cache

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


class Action:
    def __init__(self, action_dict):
        self.action = action_dict
        self.vector = None

    def __repr__(self):
        return self.action

    def __eq__(self, other: dict) -> boolean:
        if self.action["type"] != other.action["type"]:
            return False

        if self.action["type"] == "BALL":
            return self.action["time"] == other.action["time"]

        if self.action["type"] == "BOOST":
            return self.action["target"] == other.action["target"]

        if self.action["type"] == "DEMO":
            return (
                    self.action["target"] == other.action["target"]
                    and self.action["time"] == other.action["time"]
            )

        if self.action["type"] == "READY":
            return self.action["time"] == other.action["time"]

        if self.action["type"] == "DEFEND" and other.action["type"] == "DEFEND":
            return True

        return False


def TMCP_verifier(msg: dict) -> boolean:
    try:
        assert (
                msg["tmcp_version"] in [[0, 7], [0, 8], [0, 9]]
                or msg["tmcp_version"][0] == 1
        )
        msg["team"] = int(msg["team"])
        msg["index"] = int(msg["index"])
        assert type(msg["action"]) == dict
        assert msg["action"]["type"] in [
            "READY",
            "BALL",
            "DEFEND",
            "BOOST",
            "DEMO",
            "WAIT",
        ]
        assert msg["team"] in [0, 1]
        assert msg["index"] >= 0
        if msg["action"]["type"] == "BALL":
            msg["action"]["time"] = float(msg["action"]["time"])

        elif msg["action"]["type"] == "BOOST":
            assert type(msg["action"]["target"]) == int

        elif msg["action"]["type"] == "DEMO":
            msg["action"]["time"] = float(msg["action"]["time"])
            assert type(msg["action"]["target"]) == int

        elif msg["action"]["type"] == "WAIT":
            msg["action"]["type"] = "READY"
            msg["action"]["time"] = float(msg["action"]["ready"])

        elif msg["action"]["type"] == "READY":
            msg["action"]["time"] = float(msg["action"]["time"])

        # if msg['action']['type'] == 'DEFEND':
        #     pass

        return True

    except:
        print("Recieved an invalid TMCP message!", msg)
        return False


# def TMCP_verifier(msg):
#     if msg['tmcp_version'] != [0,7]:return False
#     #if type(msg['team']) != int:return False
#     if not isinstance(msg['team'], int):return False
#     #if type(msg['index']) != int:return False
#     if not isinstance(msg['index'], int): return False
#     #if type(msg['action']) != dict:return False
#     if not isinstance(msg['action'], dict): return False
#     if msg['action']['type'] not in ['WAIT','BALL','DEFEND','BOOST','DEMO']:return False
#     if msg['team'] not in [0,1]: return False
#     if msg['index'] < 0:return False
#     if msg['action']['type'] == 'BALL':
#         #if type(msg['action']['time']) != float:return False
#         if not isinstance(msg['action']['time'], float): return False
#
#     if msg['action']['type'] == 'BOOST':
#         #if type(msg['action']['target']) != int:return False
#         if not isinstance(msg['action']['target'], int): return False
#
#     if msg['action']['type'] == 'DEMO':
#         #if type(msg['action']['time']) != float:return False
#         #if type(msg['action']['target']) != int:return False
#         if not isinstance(msg['action']['time'], float): return False
#         if not isinstance(msg['action']['target'], int): return False
#
#     if msg['action']['type'] == 'WAIT':
#         #if type(msg['action']['ready']) != float:return False
#         if not isinstance(msg['action']['ready'], float): return False
#
#     # if msg['action']['type'] == 'DEFEND':
#     #     pass
#
#     return True


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
    def __init__(self, location, bigBoost, spawned, index):
        self.location = Vector(location)  # list of 3 coordinates
        self.bigBoost = bigBoost  # bool indicating if it's a cannister or just a pad
        self.spawned = spawned  # bool indicating whether it's currently
        self.index = index


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


def validateExistingPred(agent, pred_struct, max_variance=25):
    if pred_struct.time <= agent.time:
        return False

    updatedPredAtTime = find_pred_at_time(agent, pred_struct.time)
    if updatedPredAtTime is None:
        return False

    if (
            findDistance(
                convertStructLocationToVector(updatedPredAtTime), pred_struct.location
            )
            > max_variance
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
    if cannister is not None:
        cannVal = cornerDetection(cannister.location)
    else:
        return False

    if agentVal == ballVal and agentVal == cannVal:
        if agentVal != -1:
            return cannister, cannVal
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


class Vector:
    def __init__(self, content):  # accepts list of float/int values
        if type(content) == np.array:
            self.data = content.tolist()
        else:
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


def TMCP_rotations_sorter(agent):
    timers = []
    for ally in agent.allies + [agent.me]:
        if ally.index not in agent.ally_actions:
            return False
        t = agent.time + 6
        if agent.ally_actions[ally.index]["action"] == "READY" or agent.ally_actions[ally.index]["action"] == "BALL":
            t = agent.ally_actions[ally.index]["action"]["time"]
            if t < agent.time:
                t = agent.time + 6
        timers.append([t, ally.index])

    return True


def retreating_tally(teamPlayerList):
    count = 0
    for player in teamPlayerList:
        if player.retreating:
            count += 1
    return count


def player_retreat_status(ally: physicsObject, ball: Vector, team: int, num_allies=2):
    retreat_threshold = 500  # if team == 0 else 200
    retreat_distance = 2500  # if team == 0 else 3500
    dist = distance2D(ally.location, ball)
    # if ball[1] * sign(team) > 0:
    #     return False

    if dist < retreat_distance and ally.location[1] * sign(team) < 3000:
        # if ally.location[1] * sign(team) < 4500:
        #     retreat_threshold *=2
        if dist > retreat_threshold:
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
            agent_team: int,
            jumpSim=None,
            aerialState=None,
            aim_target=None,
            scorable=None,
    ):
        self.current_time = current_time
        self.prediction_time = prediction_time
        self.hit_type = hit_type  # 0 ground, 1 jumpshot, 2 wallshot , 3 catch canidate,4 double jump shot,5 aerial shot
        self.pred_vector = pred_vector
        self.pred_vel = pred_vel
        self.guarenteed_hittable = hittable
        self.fastestArrival = fastestTime
        self.agent_team = agent_team
        self.jumpSim = jumpSim
        self.aerialState = aerialState
        self.aim_target = aim_target
        self._scorable = scorable
        self.shotlimit = None

    def __str__(self):
        return f"hit type: {self.hit_type} delay: {self.time_difference()}"

    def update(self, current_time):
        self.current_time = current_time

    def time_difference(self):
        return self.prediction_time - self.current_time

    def scorable(self):
        if self._scorable is not None:
            return self._scorable

        # self._scorable = is_shot_scorable(self.pred_vector,self.goal_info[0],self.goal_info[0])[2]
        self._scorable = is_shot_scorable(self.agent_team, self.pred_vector)
        return self._scorable


def butterZone(vec: Vector, x: float = 800, y: float = 4400):
    return abs(vec.data[0]) < x and abs(vec.data[1]) > y


def steer_handler(angle, rate):
    final = ((35 * (angle + rate)) ** 3) / 20
    return clamp(1, -1, final)


def utilities_manager():
    return time()


def add_car_offset(agent, projecting=False):
    up = agent.up.scale(agent.defaultOffset[2])
    forward = agent._forward.scale(agent.defaultOffset[0])
    left = agent.left.scale(agent.defaultOffset[1])
    agent.me.location = agent.me.location + up + forward + left
    if not agent.roof_height:
        agent.roof_height = math.floor(
            (agent.me.location + agent.up.scale(agent.carHeight * 0.5))[2]
        )
        # print(f"roof height is: {agent.roof_height}")

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


def is_shot_scorable(agent_team, target_location):
    if abs(target_location[0]) < 800:
        return True
    shot_angle = math.degrees(
        angle2(target_location, Vector([0, 5213 * -sign(agent_team), 0]))
    )
    shot_angle = correctAngle(shot_angle + 90 * -sign(agent_team))
    # print(abs(shot_angle))
    return abs(shot_angle) <= 70


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
            # raise ValueError(
            #     f"Can not do comparisan operations of balltouch and {type(other)} objects."
            # )
            return False

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


def boost_limping(agent):
    return None, None
    if agent.me.location[0] > 0:
        targ_index = 18
    else:
        targ_index = 15

    target = None
    go_ahead = False
    if agent.boosts[targ_index].spawned:
        target = agent.boosts[targ_index].location + Vector(
            [0, -sign(agent.team) * 10, 0]
        )
        if agent.currentHit.pred_vector[1] * sign(agent.team) < 0:
            if abs(agent.ball.location[0]) >= 2000:
                go_ahead = True
                agent.boosts[targ_index].location
            else:
                target = None

    return target, go_ahead


def goal_selector_revised(
        agent, mode=0
):  # 0 angles only, closest corner #1 enemy consideration, 2 center only
    leftPost = Vector([500 * -sign(agent.team), 5320 * -sign(agent.team), 0])
    rightPost = Vector([500 * sign(agent.team), 5320 * -sign(agent.team), 0])
    center = Vector([0, 5600 * -sign(agent.team), 0])
    real_center = center = Vector([0, 5320 * -sign(agent.team), 0])
    maxAngle = 60

    targetVec = agent.currentHit.pred_vector

    shotAngles = [
        math.degrees(angle2(targetVec, leftPost)),
        math.degrees(angle2(targetVec, center)),
        math.degrees(angle2(targetVec, rightPost)),
    ]

    correctedAngles = [correctAngle(x + 90 * -sign(agent.team)) for x in shotAngles]
    dist = distance2D(targetVec, center)

    if dist >= 6500 or (dist < 1500 and abs(targetVec[0]) < 820) or mode == 2:
        aim = Vector([0, 5250 * -sign(agent.team), 0])
        #createBox(agent, aim)
        return aim, correctedAngles[1]

    if correctedAngles[1] <= -maxAngle:
        #createBox(agent, leftPost)
        return leftPost, correctedAngles[1]

    if correctedAngles[1] >= maxAngle:
        #createBox(agent, rightPost)
        return rightPost, correctedAngles[1]

    if mode == 0 or agent.openGoal:
        #createBox(agent, center)
        return real_center, correctedAngles[1]

    goalie, dist = findEnemyClosestToLocation(agent, real_center)

    if goalie is not None and dist < 1000:
        left_distance = distance2D(goalie.location, leftPost)
        right_distance = distance2D(goalie.location, rightPost)
        if left_distance >= right_distance:
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


def get_min_boost_duration(agent):
    return agent.boost_duration_min - clamp(
        agent.boost_duration_min, 1, agent.boost_counter
    )


def directional_demo_picker(
        agent, direction=0
):  # 0 = any, 1 = towards enemy goal, 2 = towards player goal
    best_target = None
    best_distance = math.inf
    # print(f"function called {agent.time}")

    for enemy in agent.enemies:
        if (enemy.onSurface or enemy.location[2] <= 145) and not enemy.demolished:
            if (
                    direction == 0
                    or (
                    direction == 1
                    and (enemy.location[1] * sign(agent.team))
                    < (agent.me.location[1] * sign(agent.team))
            )
                    or (
                    direction == 2
                    and (enemy.location[1] * sign(agent.team))
                    > (agent.me.location[1] * sign(agent.team))
            )
            ):
                _distance = findDistance(agent.me.location, enemy.location)
                # print(f"{_distance}")
                if _distance < best_distance:
                    best_target = enemy
                    best_distance = _distance

    return best_target


def unpicky_demo_picker(agent):
    best_target = None
    best_distance = math.inf

    for enemy in agent.enemies:
        if (enemy.onSurface or enemy.location[2] < 140) and not enemy.demolished:
            _distance = findDistance(agent.me.location, enemy.location)
            if _distance < best_distance:
                best_target = enemy
                best_distance = _distance

    return best_target


def demo_check(agent, target_car):
    if target_car.demolished or target_car.team == agent.team:
        return False
    return True


def demoTarget(agent, targetCar):
    currentSpd = clamp(maxPossibleSpeed, 100, agent.currentSpd)
    distance = distance2D(agent.me.location, targetCar.location)

    currentTimeToTarget = inaccurateArrivalEstimator(
        agent, targetCar.location, offset=105
    )
    lead = clamp(2, 0, currentTimeToTarget)

    enemyspd = targetCar.velocity.magnitude()
    multi = clamp(1000, 0, enemyspd * currentTimeToTarget)
    targPos = targetCar.location + (targetCar.velocity.normalize().scale(multi))

    if not targetCar.onSurface or (agent.currentSpd < 2200 and agent.me.boostLevel < 1):
        if currentTimeToTarget < 0.1:
            local_target = localizeVector(targPos, agent.me)
            angle = math.atan2(local_target[1], local_target[0])
            angle_degrees = correctAngle(math.degrees(angle))
            if abs(angle_degrees) < 30:
                agent.setJumping(1)

    agent.update_action(
        {
            "type": "DEMO",
            "time": float(
                agent.time
                + findDistance(agent.me.location, targPos)
                / clamp(2300, 0.001, agent.currentSpd)
            ),
            "target": targetCar.index,
        }
    )

    return driveController(
        agent, targPos, agent.time, expedite=True, demos=True
    )


def kickOffTest(agent):
    if agent.ignore_kickoffs or agent.ball.location.flatten() != Vector([0, 0, 0]):
        return False

    if (
            agent.gameInfo.is_kickoff_pause or not agent.gameInfo.is_round_active
    ) or agent.ball.location.flatten() != Vector([0, 0, 0]):
        if len(agent.allies) > 0:
            myDist = distance2D(agent.me.location, agent.ball.location)
            equalAlly = None
            for ally in agent.allies:
                ally_dist = distance2D(ally.location, agent.ball.location)
                if abs(ally_dist - myDist) < 50:
                    equalAlly = ally
                elif ally_dist < myDist:
                    return False
            if equalAlly is not None:
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
    if hasattr(_object, "data"):
        return _object
    if hasattr(_object, "location"):
        return _object.location
    raise ValueError(
        f"{str(type(_object))} is not a valid input for 'getLocation' function "
    )


@jit(float32(float32, float32, float32), nopython=True)
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
        if 70 < abs(degrees) < 180:
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


def find_closest_cannister(agent):
    big_cans = [x for x in agent.boosts if x.spawned and x.bigBoost]
    if len(big_cans) > 0:
        closest_cannister = min(
            big_cans, key=lambda k: distance2D(k.location, agent.me.location)
        )
        return (
            closest_cannister,
            distance2D(agent.me.location, closest_cannister.location),
        )
    return None, math.inf


def boost_suggester(
        agent, mode=1, buffer=3000, strict=False
):  # mode 0: any side, mode:1 stay on side, mode:2 stay on opposite side
    if agent.aerial_hog or agent.demo_monster:
        mode = 0
    minY = agent.ball.location[1] + (buffer * sign(agent.team))
    closestBoost = None
    bestDistance = math.inf
    bestAngle = 0
    multiplier = 1
    if mode == 1:
        if agent.ball.location[0] < 0:
            multiplier = -1

    elif mode == 2:
        if agent.ball.location[0] > 0:
            multiplier = -1

    for boost in agent.boosts:
        if boost.spawned and boost.index not in agent.ignored_boosts:
            if (
                    (boost.location[1] <= minY and agent.team == 0)
                    or (boost.location[1] >= minY and agent.team == 1)
                    or (
                    not strict
                    and boost.bigBoost
                    and boost.location[1] * sign(agent.team)
                    > agent.me.location[1] * sign(agent.team)
            )
            ):
                if mode == 0 or boost.location[0] * multiplier >= 0:
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

    if closestBoost is not None:
        agent.boost_gobbling = True

    return closestBoost


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


def find_L_distance(groundVector, wallVector):
    groundedWallSpot = Vector([wallVector.data[0], wallVector.data[1], 0])
    return distance2D(groundVector, groundedWallSpot) + findDistance(
        groundedWallSpot, wallVector
    )


def goFarPost(agent, hurry=True):
    rightPost = Vector([800, 4800 * sign(agent.team), 0])
    leftPost = Vector([-800, 4800 * sign(agent.team), 0])
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

    return driveController(
        # agent, post, agent.time + 0.25, expedite=True
        agent,
        post,
        agent.time,
        expedite=hurry,
    )


def gate(agent, hurry=True):
    # print(f"{agent.index} in gate")
    rightPost = Vector([840, 4600 * sign(agent.team), 0])
    leftPost = Vector([-840, 4600 * sign(agent.team), 0])
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

    if rightDist < leftDist:
        post = rightPost
        selectedDist = rightDist
    else:
        post = leftPost
        selectedDist = leftDist
    inPlace = False
    centerDist = distance2D(agent.me.location, center)
    if centerDist <= 450:
        inPlace = True

    if teammate_nearby(agent, post, 500)[0]:
        post = center

    if not inPlace:
        if selectedDist >= 1200:
            return driveController(
                agent,
                post,
                agent.time + (selectedDist / 2300),
                expedite=hurry,
                flippant=(not agent.forward or not agent.on_correct_side),
            )

        elif centerDist > 350:
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
            if (
                    abs(angle) > 35
                    and distance2D(agent.me.location, agent.ball.location) > 3000
                    and agent.goalPred is None
            ):
                agent.setGuidance(enemy_goal)
        # return SimpleControllerState()
        return arrest_movement(agent)

    return driveController(agent, center, agent.time + 0.6, expedite=False)


def arrest_movement(agent):
    controls = SimpleControllerState()
    if agent.currentSpd > 20:
        if agent.forward:
            controls.throttle = -1

        else:
            controls.throttle = 1

    return controls


def get_ball_offset_simple(agent, ball_location):
    if ball_location[2] > agent.groundCutOff:
        return 60
    adjusted_roof_height = agent.roof_height - (ball_location[2] - agent.ball_size)
    return math.floor(
        math.sqrt(clamp(200, 0.0001, adjusted_roof_height * (agent.ball_size * 2 - adjusted_roof_height)))
    )


def get_ball_offset(agent, hit):
    if hit.pred_vector[2] > agent.groundCutOff:
        return 65
    adjusted_roof_height = agent.roof_height - (hit.pred_vector[2] - agent.ball_size)
    # if adjusted_roof_height < 1:
    #     print("roof height too low!")
    return math.floor(
        math.sqrt(clamp(200, 0.0001, adjusted_roof_height * (agent.ball_size * 2 - adjusted_roof_height)))
    )


def find_defensive_target(agent):
    start = agent.ball.location
    if agent.enemyTargetVec is not None:
        start = agent.enemyTargetVec

    if abs(start[0]) < 500:
        return agent.goal_locations[1]

    if distance2D(start, agent.goal_locations[0]) < distance2D(start, agent.goal_locations[2]):
        return agent.goal_locations[0]
    else:
        return agent.goal_locations[2]


def ShellTime(agent, retreat_enabled=True, aim_target=None):
    defendTarget = Vector([0, 5500 * sign(agent.team), 200])
    attackTarget = Vector([0, 5200 * -sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector
    carDistance = distance2D(agent.me.location, defendTarget)
    ballGoalDistance = distance2D(agent.ball.location, defendTarget)
    targDistance = distance2D(agent.me.location, targetVec)
    targToGoalDistance = distance2D(attackTarget, targetVec)
    expedite = True
    flippant = False
    offensive = agent.offensive
    defensiveRange = 200
    require_lineup = False
    flipping = True
    force_close = False
    fudging = False
    if agent.currentHit.hit_type == 5:
        agent.activeState = agent.currentHit.aerialState
        return agent.activeState.update()
    is_mirror_shot = False

    mode = 0

    goalSpot = aim_target
    ballGoalAngle = 0

    if not offensive and agent.me.velocity[1] * sign(agent.team) > 0:
        is_mirror_shot = True
        force_close = True

    if not goalSpot:
        goalSpot, ballGoalAngle = goal_selector_revised(agent, mode=mode)

    localPos = toLocal(targetVec, agent.me)
    angleDegrees = correctAngle(math.degrees(math.atan2(localPos[1], localPos[0])))

    if abs(angleDegrees) <= 40 or abs(angleDegrees) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5

    ballOffset = get_ball_offset(agent, agent.currentHit)
    totalOffset = (carOffset + ballOffset) * 0.9
    offset_min = totalOffset * 0.8

    positioningOffset = offset_min


    destination = None
    moddedOffset = False
    if len(agent.allies) > 0:
        retreat_enabled = False


    if carDistance - defensiveRange > ballGoalDistance and retreat_enabled:
        if True:
            cornerShot = cornerDetection(targetVec) != -1
            if not agent.goalPred:  # and agent.lastMan != agent.me.location):
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
                    # return corner_retreat(agent)
                else:
                    return smart_retreat(agent)
            else:
                if not agent.currentHit.guarenteed_hittable and agent.me.boostLevel <= 0:
                    flippant = True

    if len(agent.allies) < 2:
        if abs(ballGoalAngle) >= agent.angleLimit and abs(targetVec[0]) > 800:
            expedite = False
            if retreat_enabled:
                if (
                        agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                        and agent.enemyBallInterceptDelay < 2.5
                        and agent.enemyAttacking
                ) or agent.me.boostLevel < agent.boostThreshold:
                    return playBack(agent)

    # if (agent.superSonic or agent.me.boostLevel > 0) and enemy_carry_check(agent) and \
    #         demo_check(agent, agent.closestEnemyToBall) and (
    #         agent.me.location != agent.lastMan or agent.goalPred is None):
    #     return demoTarget(agent, agent.closestEnemyToBall)

    if defensive_check(agent) and retreat_enabled:
        return defensive_positioning(agent)

    if agent.currentHit.hit_type == 1 or agent.currentHit.hit_type == 4:
        return handleBounceShot(agent, waitForShot=False)

    if agent.currentHit.hit_type == 2:
        agent.wallShot = True
        agent.ballGrounded = False
        return handleWallShot(agent)

    # testing
    if not is_mirror_shot and not agent.ignore_kickoffs:
        mirror_info = mirrorshot_qualifier(agent)
        is_mirror_shot = (
                mirror_info[0]
                and len(mirror_info[1]) < 1
                and (agent.lastMan == agent.me.location)
                and agent.contested
                and not offensive
        )

        if not offensive and not agent.forward:
            is_mirror_shot = True

    # relative_speed = relativeSpeed(
    #     agent.currentHit.pred_vel.flatten(), agent.me.velocity
    # )
    # if agent.currentHit.time_difference() < 1:
    #     if (
    #             (relative_speed * 1.75 >= targToGoalDistance or (butterZone(targetVec) and agent.contested))
    #             and offensive
    #             and agent.team == 0
    #     ):
    #         # print(f"forcing jumpshot {agent.time}")
    #         return handleBounceShot(agent, waitForShot=False)
    #
    #     if agent.team == 0 and agent.me.location[1] * sign(agent.team) > targetVec[1] * sign(agent.team) and targetVec[2] > agent.groundCutOff * 0.85 and relative_speed > 1800:
    #         return handleBounceShot(agent, waitForShot=False)

    if targetVec[1] * sign(agent.team) < agent.me.location[1] * sign(agent.team) and agent.contested and agent.currentHit.time_difference() < 1:
        return handleBounceShot(agent, waitForShot=False)


    max_swoop = 900 if agent.contested else 1800
    lined_up = agent.lineup_check()

    if (
            not lined_up
            and targetVec[1] * sign(agent.team) < -3500
            and abs(targetVec[0]) < 3000
            and not is_mirror_shot
            and agent.goalPred is None
    ):
        require_lineup = True

    _direction = direction(targetVec.flatten(), goalSpot.flatten())
    simple_pos = targetVec.flatten() + _direction.scale(positioningOffset)
    simple_pos.data[2] = agent.defaultElevation

    if len(agent.allies) < 2:
        shot_scorable = agent.currentHit.scorable()

        if not shot_scorable:
            require_lineup = True
            max_swoop = 900
            if (
                    agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                    and agent.enemyBallInterceptDelay < 2.5
                    and agent.enemyAttacking
            ) or agent.me.boostLevel < agent.boostThreshold:
                return playBack(agent)

    if not destination and (agent.goalPred is not None or agent.scared or lined_up):
        destination = get_aim_vector(
            agent,
            goalSpot.flatten(),
            targetVec.flatten(),
            agent.currentHit.pred_vel,
            offset_min,
        )[0]

    if not destination:
        if (
                agent.contested
                and not require_lineup
                and (
                distance2D(agent.closestEnemyToBall.location, attackTarget)
                < distance2D(agent.me.location, attackTarget)
                )
        ):
            if not is_mirror_shot:
                destination = get_aim_vector(
                    agent,
                    goalSpot.flatten(),
                    targetVec.flatten(),
                    agent.currentHit.pred_vel,
                    offset_min,
                )[0]
            else:
                destination = aim_wallshot_naive(
                    agent, agent.currentHit, offset_min, force_close=force_close
                )

    if not destination and require_lineup:
        offset = clamp(max_swoop, offset_min, targDistance * 0.5)
        positioningOffset = offset
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
            destination = aim_wallshot_naive(
                agent, agent.currentHit, positioningOffset, force_close=force_close
            )
            moddedOffset = positioningOffset > offset_min

    if not destination and abs(targetVec[0]) < 3500:
        # if not agent.contested:
        if (
                targDistance > totalOffset
                and targDistance > (agent.currentSpd * agent.currentHit.time_difference())
                and abs(targetVec[1]) <= 4000
        ):
            # print(f"in here {agent.time}")
            offset = clamp(max_swoop, offset_min, targDistance * 0.25)
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
                        agent,
                        agent.currentHit,
                        positioningOffset,
                        force_close=force_close,
                    )
            moddedOffset = positioningOffset > offset_min

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
                    agent, agent.currentHit, positioningOffset, force_close=force_close
                )
        moddedOffset = False

    if moddedOffset:
        modifiedDelay = clamp(
            6,
            0,
            agent.currentHit.time_difference()
            - (
                # (positioningOffset - offset_min)
                    positioningOffset
                    / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
            ),
        )
        fudging = True

    else:
        modifiedDelay = agent.currentHit.time_difference()

    if agent.team == 3:
        modifiedDelay -= agent.fakeDeltaTime

    destination.data[2] = agent.defaultElevation
    if agent.ball.location[1] * sign(agent.team) > agent.me.location[1] * sign(
            agent.team
    ) or targetVec[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team):
        expedite = True



    result = driveController(
        agent,
        destination,
        agent.time + modifiedDelay,
        expedite=expedite,
        flippant=flippant,
        flips_enabled=flipping,
        fudging=fudging,
        offset_dist=0 if not fudging else findDistance(destination, simple_pos)
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

    agent.update_action({"type": "BALL", "time": agent.currentHit.prediction_time})

    return result


def findEnemyClosestToLocation(agent, location, demo_bias=False):
    if len(agent.enemies) > 0:
        closest = agent.enemies[0]
        cDist = math.inf
        for e in agent.enemies:
            x = math.inf if (demo_bias and e.demolished) else findDistance(e.location, location)
            if x < cDist:
                cDist = x
                closest = e
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


def naive_flip_relocator(agent):
    flip_window = 0.5
    contact_time = agent.currentHit.time_difference()
    flip_time = 0
    if contact_time > flip_window:
        flip_time = contact_time - flip_window

def handleBounceShot(agent, waitForShot=True, forceDefense=False, aim_target=None):
    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector
    mirrorShot = False
    force_close = False
    offensive = agent.offensive
    in_zone = butterZone(targetVec)

    if len(agent.allies) < 1 and agent.offensive and agent.contested and agent.me.boostLevel < 50 and agent.enemyBallInterceptDelay < agent.ballDelay:
        return playBack(agent)

    if forceDefense:
        defensiveTouch = True
    else:
        defensiveTouch = (
            # inTheMiddle(
            #     targetVec[1], [2000 * sign(agent.team), 5500 * sign(agent.team)]
            # )
                targetVec[1] * sign(agent.team) > 2000
                and not agent.openGoal
            # and len(agent.enemies) > 1
        )
        if defensiveTouch:
            if agent.currentHit.hit_type != 4:
                if abs(targetVec[0]) > 1500:
                    defensiveTouch = False

    is_mirror_shot = False
    flipping = True

    if agent.me.location[1] * sign(agent.team) < targetVec[1] * sign(agent.team):
        is_mirror_shot = True

    # testing
    if not is_mirror_shot and not agent.ignore_kickoffs:
        mirror_info = mirrorshot_qualifier(agent)
        is_mirror_shot = (
                mirror_info[0]
                and len(mirror_info[1]) < 1
                and not offensive
                and (agent.lastMan == agent.me.location)
                and agent.contested
        )

    if is_mirror_shot and offensive and in_zone:
        is_mirror_shot = False
    targDistance = distance2D(agent.me.location, targetVec)

    targetLocal = toLocal(targetVec, agent.me)
    carToTargAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))

    if abs(carToTargAngle) <= 40 or abs(carToTargAngle) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5

    lined_up = agent.lineup_check()

    require_lineup = False
    annoyingShot = False

    ballOffset = agent.ball_size  # 91.25
    modifier = 0.99999
    totalOffset = (carOffset + ballOffset) * modifier
    # if agent.currentHit.hit_type == 4:
    #     offset_min = totalOffset * 0.8
    # else:
    offset_min = (carOffset + ballOffset) * 0.65
    safety_margin = 0

    if agent.currentHit.pred_vector[2] <= agent.groundCutOff:
        #ballOffset = get_ball_offset(agent, agent.currentHit)
        totalOffset = (ballOffset + carOffset)+30
        offset_min = totalOffset * 0.5
        annoyingShot = True
        safety_margin = -50
        #print(f"annoying shot {agent.time}")


    shotViable = False
    hurry = True

    is_shooting = True
    if len(agent.allies) < 2:
        shot_scorable = agent.currentHit.scorable()
        if not shot_scorable:  # and len(agent.allies) < 1:
            hurry = False
            is_shooting = False

    mode = 0

    goalSpot = aim_target
    ballGoalAngle = 0

    if agent.me.velocity[1] * sign(agent.team) > 0:
        is_mirror_shot = True
        force_close = True

    if not goalSpot:
        goalSpot, ballGoalAngle = goal_selector_revised(agent, mode=mode)
    if len(agent.allies) < 1:
        if abs(ballGoalAngle) >= agent.angleLimit and abs(targetVec[0]) > 800:
            if (
                    agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                    and agent.enemyBallInterceptDelay < 2.5
                    and agent.enemyAttacking
                    # and agent.team == 0
            ) or agent.me.boostLevel < agent.boostThreshold:
                # return secondManPositioning(agent)
                return playBack(agent)

    if agent.scared:
        return turtle_mode(agent)

    if agent.currentHit.hit_type != 2:
        repos_action = reposition_handler(agent, targetVec)
        if repos_action is not None:
            return repos_action


    if not annoyingShot:
        if defensive_check(agent):
            return defensive_positioning(agent)


    if agent.currentHit.jumpSim is None or agent.currentHit.current_time < agent.time:
        if agent.currentHit.hit_type != 4:
            agent.currentHit.jumpSim = jumpSimulatorNormalizingJit(
                float32(agent.gravity),
                float32(agent.physics_tick),
                np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                np.array(agent.up.data, dtype=np.dtype(float)),
                np.array(agent.me.location.data, dtype=np.dtype(float)),
                float32(agent.defaultElevation),
                float32(agent.currentHit.time_difference()),
                float32(targetVec[2]),
                False,
            )
        else:
            agent.currentHit.jumpSim = jumpSimulatorNormalizingJit(
                float32(agent.gravity),
                float32(agent.physics_tick),
                np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                np.array(agent.up.data, dtype=np.dtype(float)),
                np.array(agent.me.location.data, dtype=np.dtype(float)),
                float32(agent.defaultElevation),
                float32(agent.currentHit.time_difference()),
                float32(targetVec[2]),
                False,
            )
        agent.currentHit.current_time = agent.time

    test_offset = clamp(
        1500, offset_min, agent.currentSpd * agent.currentHit.time_difference()
    )
    # safety_margin = 10 if targetVec[2] > agent.singleJumpLimit else 0

    if (
            #distance2D(Vector(agent.currentHit.jumpSim[4]), targetVec)
            findDistance(Vector(agent.currentHit.jumpSim[4]), targetVec)
            < totalOffset - safety_margin
    ):
        shotViable = True

    waiting = False


    positioningOffset = offset_min
    launching = False
    targetLoc = None
    boostHog = True
    variance = agent.fakeDeltaTime
    if annoyingShot:
        variance *= 6
        if agent.currentHit.jumpSim[1] != 0:
            shotlimit = clamp(1, 0.07, agent.currentHit.jumpSim[1] + variance)
        else:
            shotlimit = clamp(1, 0.07, agent.currentHit.jumpSim[3] + variance)

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

    agent.currentHit.shotlimit = shotlimit
    modifiedDelay = agent.currentHit.time_difference()
    waitingShotPosition = None
    _direction = (goalSpot.flatten() - targetVec.flatten()).normalize()
    bad_direction = _direction.scale(-1)
    if not agent.offensive:
        bad_direction= (myGoal.flatten() - targetVec.flatten()).normalize()
    badPosition = targetVec.flatten() + bad_direction.scale(offset_min)
    fudging = False

    lineup_grace = 0.33334

    if defensiveTouch or is_mirror_shot:
        waitingShotPosition = aim_wallshot_naive(
            agent, agent.currentHit, offset_min, force_close=force_close
        )

    else:
        if (
                not lined_up
                and offensive
                and agent.forward
                and agent.currentHit.time_difference() > shotlimit + lineup_grace
                and agent.me.velocity[1] * sign(agent.team) < 0
                and not annoyingShot
                and (agent.me.boostLevel > 0 or in_zone)
                and targDistance > 500
                and agent.currentSpd * agent.currentHit.time_difference() - shotlimit
                < targDistance
                and agent.goalPred is None
                and agent.currentHit.hit_type != 4
        ):
            require_lineup = True

    #_direction = direction(goalSpot.flatten(), targetVec.flatten())
    simple_pos = targetVec.flatten() + _direction.scale(positioningOffset)
    simple_pos.data[2] = agent.defaultElevation

    if waitingShotPosition is None:
        if not require_lineup:
            waitingShotPosition = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                offset_min,
                # test_offset
            )[0]
        else:
            positioningOffset = clamp(2100, offset_min, targDistance * lineup_grace)

            if positioningOffset > offset_min:
                modifiedDelay = clamp(
                    6,
                    0.0001,
                    agent.ballDelay
                    - (
                        # (positioningOffset - offset_min)
                            positioningOffset
                            / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                    ),
                )
                fudging = True

            waitingShotPosition = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
                # test_offset
            )[0]

    if agent.currentHit.time_difference() <= shotlimit:

        # if targetLoc == None:
        if annoyingShot or agent.goalPred is not None or distance2D(
                Vector(agent.currentHit.jumpSim[4]), waitingShotPosition
        ) < distance2D(Vector(agent.currentHit.jumpSim[4]), badPosition):
            if not agent.onWall and agent.onSurface and is_shooting:
                if shotViable:
                    agent.createJumpChain(
                        agent.currentHit.time_difference(),
                        targetVec[2],
                        agent.currentHit.jumpSim,
                    )
                    targetLoc = targetVec
                    launching = True
                    if annoyingShot:
                        agent.log.append(f"taking annoying shot! {agent.time}")

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

    if agent.ball.location[1] * sign(agent.team) > agent.me.location[1] * sign(
            agent.team
    ) or targetVec[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team):
        hurry = True
    if waiting and distance2D(agent.me.location, myGoal) < distance2D(targetVec, myGoal):
        hurry = False

    agent.update_action({"type": "BALL", "time": agent.currentHit.prediction_time})

    return driveController(
        agent,
        targetLoc.flatten(),
        agent.time + modifiedDelay,
        expedite=hurry,
        flips_enabled=flipping,
        fudging=fudging,
        offset_dist=0 if not fudging else findDistance(targetLoc, simple_pos)
    )


def SortHits(hit_list):
    no_nones = list(filter(None, hit_list))
    return sorted(no_nones, key=lambda x: x.prediction_time)


def intercept_handler(agent):
    if agent.goalPred is None and agent.me.location == agent.lastMan:
        if agent.enemyBallInterceptDelay + 1 < agent.ballDelay:
            # print(f"Falling back cause I scared {agent.time}")
            return thirdManPositioning(agent)

    return None


def secondManPositioning(agent):
    # print("in second man",agent.time)
    playerGoal = Vector([0, 5200 * sign(agent.team), 0])
    enemyGoal = playerGoal.scale(-1)
    stealing_range = 2000
    boostTarget, dist = boostSwipe(agent)
    maintain_speed = True
    if (
            boostTarget is not None
            and dist < stealing_range
            # and agent.me.boostLevel < 100
            and not agent.boostMonster
            and (
                    agent.me.location[1] * sign(agent.team)
                    < agent.ball.location[1] * sign(agent.team)
            )
    ) or (
            boostTarget is not None and dist < 900 and not agent.boostMonster
    ):  # and agent.me.boostLevel < 100):
        agent.update_action({"type": "BOOST", "target": boostTarget.index})
        controller = driveController(
            agent, boostTarget.location.flatten(), agent.time, expedite=True
        )
        if agent.me.boostLevel == 100:
            controller.boost = True
        return controller

    offensive = agent.offensive
    cannister_info = None

    if agent.me.boostLevel < agent.boostThreshold and (
            agent.me.location != agent.lastMan or offensive
    ):
        cannister_info = find_closest_cannister(agent)
        if cannister_info[1] <= agent.cannister_greed:
            boost_suggestion = cannister_info[0]
            target = boost_suggestion.location.scale(1)
            target.data[2] = 0
            agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
            return driveController(agent, target.flatten(), 0, flips_enabled=True)

    # agent.update_action({"type": "READY", "time": agent.currentHit.prediction_time})

    # test demo code
    if (
            agent.me.location != agent.lastMan
            and agent.demo_rotations
            and (agent.me.boostLevel > 0 or agent.currentSpd > 2200)
    ):
        # 0 = any, 1 = towards enemy goal, 2 = towards player goal
        _dir = -1
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
                agent.team
        ):
            if (
                    agent.me.retreating
                    or agent.currentSpd < 500
                    or agent.me.velocity[1] * sign(agent.team) > 500 * sign(agent.team)
            ):
                _dir = 2
            else:
                if (
                        False
                        and offensive
                        and agent.me.location[1] * sign(agent.team)
                        < agent.ball.location[1] * sign(agent.team)
                        and agent.me.location != agent.lastMan
                        and agent.lastMan[1] * sign(agent.team)
                        > agent.ball.location[1] * sign(agent.team)
                        and agent.me.velocity[1] * sign(agent.team) < -400
                        and (agent.me.boostLevel >= 0 or agent.me.currentSpd >= 2200)
                ):
                    _dir = 1

            if _dir != -1:
                demo_target = directional_demo_picker(agent, direction=_dir)
                if demo_target is not None and demo_check(agent, demo_target):
                    difference = agent.me.location - demo_target.location
                    if abs(difference[0]) < abs(difference[1]) + 350:
                        if _dir != 2 or demo_target.location[1] * sign(
                                agent.team
                        ) < agent.ball.location[1] * sign(agent.team):
                            return demoTarget(agent, demo_target)

    if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
    ):
        return smart_retreat(agent)

    scaler = 2500
    if not agent.offensive:
        scaler = 1500
    _direction = (agent.ball.location.flatten() - enemyGoal).normalize()
    destination = agent.ball.location.flatten() + _direction.scale(scaler)
    x_target = clamp(3000, -3000, destination[0])
    destination.data[1] += abs(destination[0] - x_target) * sign(agent.team)
    destination.data[0] = x_target
    y_target = destination[1]



    # y_dist = 1500
    #
    # if agent.ball.location[0] > 0:
    #     x_target = agent.ball.location[0]-1500
    # else:
    #     x_target = agent.ball.location[0]+1500
    #
    # y_target = agent.ball.location[1] + (sign(agent.team) * y_dist)

    if not offensive:
        #_direction = (playerGoal - agent.ball.location.flatten()).normalize()
        #destination = agent.ball.location.flatten() + _direction.scale(1000)
        # x_target = clamp(2000, -2000, destination[0])
        # y_target = destination[1]
        maintain_speed = False

    if y_target * sign(agent.team) > 4700:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
                agent.team
        ):
            return rotate_back(agent)
    # mode 0: any side, mode:1 stay on side, mode:2 stay on opposite side
    boost_suggestion = None
    if agent.me.boostLevel < agent.boostThreshold:
        if cannister_info is None:
            cannister_info = find_closest_cannister(agent)
        if cannister_info[1] <= 1000 and cannister_info[0].location[1] * sign(
                agent.team
        ) > agent.ball.location[1] * sign(agent.team):
            boost_suggestion = cannister_info[0]
        else:
            mode = 2
            # if offensive:
            #     if agent.me.boostLevel >= 35:
            #         mode = 2
            #     else:
            #         mode = 0

            if boost_suggestion is None and agent.me.boostLevel <= 35:
                boost_suggestion = boost_suggester(agent, buffer=1500, mode=mode)
        if boost_suggestion is not None:
            target = boost_suggestion.location.scale(1)
            agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
            return driveController(agent, target.flatten(), 0, flips_enabled=True)

    if y_target * sign(agent.team) < 4700:
        timer = agent.currentHit.prediction_time
        # if (
        #     agent.me.location[1] * sign(agent.team)
        #     < agent.currentHit.pred_vector[1] * sign(agent.team)
        #     and agent.me.location != agent.lastMan
        # ):
        #     timer = float(-1)
        #
        # elif agent.me.retreating and agent.me.location != agent.lastMan:
        #     timer = float(-1)
        agent.update_action({"type": "READY", "time": timer})

        return driveController(
            agent,
            Vector([x_target, y_target, 0]),
            0,
            expedite=False,
            maintainSpeed=maintain_speed,
            flips_enabled=False,
        )

    return smart_retreat(agent)


def linger(agent):
    stealing_range = 2000
    boostTarget, dist = boostSwipe(agent)
    if (
            boostTarget is not None
            and dist < stealing_range
            # and agent.me.boostLevel < 100
            and not agent.boostMonster
            and (
                    agent.me.location[1] * sign(agent.team)
                    < agent.ball.location[1] * sign(agent.team)
            )
    ) or (
            boostTarget is not None and dist < 900 and not agent.boostMonster
    ):  # and agent.me.boostLevel < 100):
        agent.update_action({"type": "BOOST", "target": boostTarget.index})
        controller = driveController(
            agent, boostTarget.location.flatten(), agent.time, expedite=True
        )
        if agent.me.boostLevel == 100:
            controller.boost = True
        return controller

    cannister_info = None

    if agent.me.boostLevel < agent.boostThreshold:
        cannister_info = find_closest_cannister(agent)
        if cannister_info[1] <= agent.cannister_greed:
            boost_suggestion = cannister_info[0]
            target = boost_suggestion.location.scale(1)
            target.data[2] = 0
            agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
            return driveController(
                agent, target.flatten(), agent.time, flips_enabled=True
            )

    if cannister_info is None:
        cannister_info = find_closest_cannister(agent)
    if cannister_info[1] <= 1000 and cannister_info[0].location[1] * sign(
            agent.team
    ) > agent.ball.location[1] * sign(agent.team):
        boost_suggestion = cannister_info[0]
    else:
        mode = 0
        boost_suggestion = boost_suggester(agent, mode=mode, buffer=500)
    if boost_suggestion is not None:
        target = boost_suggestion.location.scale(1)
        target.data[2] = 0
        agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
        return driveController(agent, target.flatten(), agent.time, flips_enabled=True)

    offset_amount = 500
    y_target = agent.ball.location[1]  # + (sign(agent.team) * offset_amount)
    x_target = clamp(3500, -3500, agent.ball.location[0])

    if y_target * sign(agent.team) > 4800:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
                agent.team
        ):
            return smart_retreat(agent)

    return driveController(
        agent,
        Vector([x_target, y_target, 9]),
        agent.time,
        expedite=False,
        maintainSpeed=True,
    )


def thirdManPositioning(agent, buffer=None):
    # print("in third man", agent.time)
    playerGoal = Vector([0, 5200 * sign(agent.team), 0])
    stealing_range = 2000
    boostTarget, dist = boostSwipe(agent)
    if (
            boostTarget is not None
            and dist < stealing_range
            # and agent.me.boostLevel < 100
            and not agent.boostMonster
            and (
                    agent.me.location[1] * sign(agent.team)
                    < agent.ball.location[1] * sign(agent.team)
            )
    ) or (
            boostTarget is not None and dist < 900 and not agent.boostMonster
    ):  # and agent.me.boostLevel < 100):
        agent.update_action({"type": "BOOST", "target": boostTarget.index})
        controller = driveController(
            agent, boostTarget.location.flatten(), agent.time, expedite=True
        )
        if agent.me.boostLevel == 100:
            controller.boost = True
        return controller

    offensive = agent.offensive

    cannister_info = None

    if agent.me.boostLevel < agent.boostThreshold and (
            agent.me.location != agent.lastMan or offensive
    ):
        cannister_info = find_closest_cannister(agent)
        if cannister_info[1] <= agent.cannister_greed:
            boost_suggestion = cannister_info[0]
            target = boost_suggestion.location.scale(1)
            target.data[2] = 0
            agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
            return driveController(agent, target.flatten(), 0, flips_enabled=True)

    # test demo code
    if (
            agent.me.location != agent.lastMan
            and agent.demo_rotations
            and (agent.me.boostLevel > 0 or agent.currentSpd > 2200)
    ):
        # 0 = any, 1 = towards enemy goal, 2 = towards player goal
        _dir = -1
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
                agent.team
        ):
            if (
                    agent.me.retreating
                    or agent.currentSpd < 500
                    or agent.me.velocity[1] * sign(agent.team) > 500 * sign(agent.team)
            ):
                _dir = 2
            else:
                if (
                        False
                        and offensive
                        and agent.me.location[1] * sign(agent.team)
                        < agent.ball.location[1] * sign(agent.team)
                        and agent.me.location != agent.lastMan
                        and agent.lastMan[1] * sign(agent.team)
                        > agent.ball.location[1] * sign(agent.team)
                        and agent.me.velocity[1] * sign(agent.team) < -400
                        and (agent.me.boostLevel >= 0 or agent.me.currentSpd >= 2200)
                ):
                    _dir = 1

            if _dir != -1:
                demo_target = directional_demo_picker(agent, direction=_dir)
                if demo_target is not None and demo_check(agent, demo_target):
                    difference = agent.me.location - demo_target.location
                    if abs(difference[0]) < abs(difference[1]) + 350:
                        if _dir != 2 or demo_target.location[1] * sign(
                                agent.team
                        ) < agent.ball.location[1] * sign(agent.team):
                            return demoTarget(agent, demo_target)

    if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
            agent.team
    ):
        return smart_retreat(agent)



    _direction = (
            agent.ball.location.flatten() - Vector([0, 5200 * -sign(agent.team), 0])
    ).normalize()
    target_loc = agent.ball.location.flatten() + _direction.scale(5000)
    x_target = clamp(1500, -1500, target_loc[0])
    y_target = target_loc[1]
    if abs(agent.ball.location[1] - target_loc[1]) < 5500:
        y_target = agent.ball.location[1] + 5500 * sign(agent.team)

    if abs(y_target) * sign(agent.team) - agent.me.location[1] * sign(agent.team) > 1000:
        return smart_retreat(agent)

    boost_suggestion = None
    if abs(y_target) < 4500:
        if agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(
                agent.team
        ):
            return smart_retreat(agent)

        if (
                agent.me.boostLevel < agent.boostThreshold
                and agent.ball.location[1] * -sign(agent.team) > 0
        ):
            if cannister_info is None:
                cannister_info = find_closest_cannister(agent)
            if cannister_info[1] <= 1000 and cannister_info[0].location[1] * sign(
                    agent.team
            ) > agent.ball.location[1] * sign(agent.team):
                boost_suggestion = cannister_info[0]
            else:
                if agent.me.boostLevel >= 35:
                    mode = 1
                else:
                    mode = 0

                if boost_suggestion is None and agent.me.boostLevel <= 35:
                    boost_suggestion = boost_suggester(agent, mode=mode, buffer=4500)
            if boost_suggestion is not None:
                target = boost_suggestion.location.scale(1)
                target.data[2] = 0
                # agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
                return driveController(agent, target.flatten(), 0, flips_enabled=True)

        # if abs(y_target) < 4500:
        agent.update_action({"type": "READY", "time": agent.currentHit.prediction_time})
        # agent.forward = True
        return driveController(
            agent,
            Vector([x_target, y_target, 0]),
            0,
            expedite=False,
            maintainSpeed=False,
            flips_enabled=False,
        )

    return smart_retreat(agent)


def goalie_shot(agent, goal_violator: hit):
    vec = goal_violator.pred_vector
    if abs(vec[0]) < 1000:
        if abs(vec[1]) * sign(agent.team) > 4300:
            if abs(vec[2]) < 1000:
                return True

    if agent.goalPred is not None:
        if agent.goalPred.time - agent.time < 2.5:
            return True

    return False


def smart_retreat(agent):
    timer = float(agent.currentHit.prediction_time)
    if (
            agent.me.location[1] * sign(agent.team)
            < agent.currentHit.pred_vector[1] * sign(agent.team)
            and abs(agent.me.location[1]) < 4000
    ) and agent.me.location != agent.lastMan:
        timer = float(-1)

    elif (
            agent.me.retreating
            and agent.me.location != agent.lastMan
            and abs(agent.me.location[1]) < 4000
    ):
        timer = float(-1)

    agent.update_action({"type": "READY", "time": timer})
    #playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    hurry = agent.me.location[1] * sign(agent.team) < agent.ball.location[1] * sign(agent.team)
    if agent.lastMan == agent.me.location:  # and len(agent.allies) < 1:
        return gate(agent, hurry=hurry)
    else:
        return goFarPost(agent, hurry=hurry)


def rotate_back(agent, onside=False):
    rightBoost = Vector([-3584.0, sign(agent.team) * 10, 73.0])
    leftBoost = Vector([3584.0, sign(agent.team) * 10, 73.0])

    backRightBoost = Vector([-3072, 4096 * sign(agent.team), 73.0])
    backLeftBoost = Vector([3072, 4096 * sign(agent.team), 73.0])

    if agent.ball.location[0] > 0 and not onside:
        difference = agent.me.location - rightBoost
    else:
        difference = agent.me.location - leftBoost

    timer = agent.currentHit.prediction_time
    if (
            agent.me.location[1] * sign(agent.team)
            < agent.currentHit.pred_vector[1] * sign(agent.team)
            and agent.me.location != agent.lastMan
    ):
        timer = float(-1)

    elif agent.me.retreating and agent.me.location != agent.lastMan:
        timer = float(-1)
    agent.update_action({"type": "READY", "time": timer})

    if (
            agent.me.location[1] * sign(agent.team) < 0
            and agent.me.location != agent.lastMan
            and agent.ball.location[1] * sign(agent.team) < 0 < len(agent.allies)
            and abs(difference[0]) < abs(difference[1])
    ):
        if agent.ball.location[0] > 0 and not onside:
            return driveController(
                agent, rightBoost, agent.time, expedite=False, maintainSpeed=True
            )
        else:
            return driveController(
                agent, leftBoost, agent.time, expedite=False, maintainSpeed=True
            )
    else:
        if agent.ball.location[0] > 0 and not onside:
            return driveController(
                agent, backRightBoost, agent.time, expedite=False, maintainSpeed=True
            )
        else:
            return driveController(
                agent, backLeftBoost, agent.time, expedite=False, maintainSpeed=True
            )


def boost_steal(agent):
    boostTarget, dist = boostSwipe(agent)
    if boostTarget is not None and dist < 2000 and agent.me.boostLevel < 100:
        agent.update_action({"type": "BOOST", "target": boostTarget.index})
        return driveController(agent, boostTarget.location, agent.time, expedite=True)
    return None


def corner_retreat(agent):
    # print(f"corner retreating! {agent.time}")
    threatening_shot = is_shot_scorable(1 if agent.team == 0 else 0, agent.enemyTargetVec)
    if (not threatening_shot or (agent.enemyBallInterceptDelay > 2 and not agent.enemyAttacking) and agent.goalPred is None):
        if agent.me.boostLevel < 50:
            boost_target = boost_suggester(agent, buffer=0, mode=1)
            if boost_target is not None:
                return driveController(agent, boost_target.location, agent.time, expedite=boost_target.bigBoost)
        else:
            return smart_retreat(agent)

    if not agent.enemyAttacking:
        return smart_retreat(agent)

    corner_1 = Vector([4096, 5120 * sign(agent.team), 0])
    corner_2 = Vector([-4096, 5120 * sign(agent.team), 0])

    target_vec = agent.currentHit.pred_vector
    target = corner_1 if distance2D(corner_1, target_vec) < distance2D(corner_2, target_vec) else corner_2
    return ShellTime(agent, retreat_enabled=False, aim_target=target)


def playBack(agent, buffer=4000, get_boost=True):
    playerGoal = Vector([0, sign(agent.team) * 5200, 0])
    enemyGoal = Vector([0, 5500 * -sign(agent.team), 200])

    # _direction = direction(playerGoal.flatten(), agent.ball.location.flatten())
    # fo_target = agent.ball.location + _direction.normalize().scale(buffer)
    # if agent.team == 0:
    #_direction = (agent.ball.location.flatten() - enemyGoal.flatten()).normalize()
    _direction = (agent.currentHit.pred_vector.flatten()- enemyGoal.flatten()).normalize()
    fo_target = agent.ball.location.flatten() + _direction.normalize().scale(buffer)

    centerField = Vector(
        [
            clamp(3500, -3500, fo_target[0]),
            agent.ball.location[1] + sign(agent.team) * buffer,
            agent.defaultElevation,
        ]
    )
    boostTarget, dist = boostSwipe(agent)
    if (
            boostTarget is not None
            and dist < 2000
            # and agent.me.boostLevel < 100
            and not agent.boostMonster
            and agent.me.boostLevel < 100
    ) or (
            boostTarget is not None and dist < 900 and not agent.boostMonster
    ):  # and agent.me.boostLevel < 100):
        agent.update_action({"type": "BOOST", "target": boostTarget.index})
        controller = driveController(
            agent, boostTarget.location.flatten(), agent.time, expedite=True
        )
        if agent.me.boostLevel == 100:
            controller.boost = True

        agent.set_boost_grabbing(boostTarget.index)
        return controller

    offensive = agent.offensive

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

            right_index, left_index = 15, 18
            bri, bli = 3, 4
            if agent.team != 0:
                bri, bli = 29, 30

            if agent.me.location[1] * sign(agent.team) < 0:
                if agent.ball.location[0] > 0:
                    agent.update_action({"type": "BOOST", "target": right_index})
                    return driveController(
                        agent, rightBoost, agent.time, expedite=False
                    )
                else:
                    agent.update_action({"type": "BOOST", "target": left_index})
                    return driveController(agent, leftBoost, agent.time, expedite=False)
            else:
                if agent.ball.location[0] > 0:
                    agent.update_action({"type": "BOOST", "target": bri})
                    return driveController(
                        agent, backRightBoost, agent.time, expedite=False
                    )
                else:
                    agent.update_action({"type": "BOOST", "target": bli})
                    return driveController(
                        agent, backLeftBoost, agent.time, expedite=False
                    )

    # mode 0: any side, mode:1 stay on side, mode:2 stay on opposite side
    if agent.me.boostLevel < agent.boostThreshold:
        cannister_info = find_closest_cannister(agent)
        if cannister_info[1] <= 1000 and cannister_info[0].location[1] * sign(
                agent.team
        ) > agent.ball.location[1] * sign(agent.team):
            boost_suggestion = cannister_info[0]
        else:
            mode = 1
            boost_suggestion = boost_suggester(agent, buffer=3000, mode=mode)
        if boost_suggestion is not None:
            target = boost_suggestion.location.scale(1)
            agent.update_action({"type": "BOOST", "target": boost_suggestion.index})
            if boost_suggestion.bigBoost:
                agent.set_boost_grabbing(boost_suggestion.index)
            return driveController(agent, target.flatten(), 0, flips_enabled=True)

    # maintainspeed = False
    # if agent.team == 0:
    agent.forward = True
    maintainspeed = True
    # testing maintainspeed
    return driveController(
        agent, centerField, agent.time, expedite=False, floppies=False, maintainSpeed=maintainspeed
    )
    # return turtle_mode(agent)


def boostSwipe(agent):
    backBoosts = []
    minDist = math.inf
    bestBoost = None
    for b in agent.boosts:
        if b.bigBoost and b.spawned and b.index not in agent.ignored_boosts:
            if b.location[1] * -sign(agent.team) > 4000:
                dist = distance2D(b, agent.me.location)
                if dist < minDist:
                    bestBoost = b
                    minDist = dist

    if bestBoost is not None and minDist < 2000:
        agent.boost_gobbling = True

    return bestBoost, minDist


def naive_boostless_push(agent):
    return None
    # targetVec = agent.ball.location
    dist_2d = distance2D(agent.me.location, agent.ball.location)
    if (
            dist_2d < (agent.reachLength + agent.ball_size) * 1.2
            and agent.onSurface
            and not agent.onWall
            and agent.ball.location[2] <= 120
    ):
        targetLocal = toLocal(agent.ball.location, agent.me)
        carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))
        carToBallAngle = correctAngle(carToBallAngle)
        if abs(carToBallAngle) <= 35 or abs(carToBallAngle) >= 135:
            carOffset = agent.carLength * 0.5
        else:
            carOffset = agent.carWidth * 0.5

        ballOffset = get_ball_offset_simple(agent, agent.ball.location)
        totalOffset = carOffset + ballOffset

        lined_up = extendToGoal(
            agent, agent.ball.location, agent.me.location, buffer=agent.ball_size * 3
        )

        if lined_up or agent.contested: #and relativeSpeed(agent.me.velocity.flatten(), agent.ball.velocity.flatten()) < 400:
            if not agent.forward and abs(carToBallAngle) >= 145:
                agent.setHalfFlip()
                print(f"Naively pushing! {agent.time}")
            else:
                if abs(carToBallAngle) < 35:
                    agent.setJumping(0)
                    print(f"Naively pushing! {agent.time}")
            # print(f"Naively pushing! {agent.time}")


def turtle_mode(agent):
    myGoal = Vector([0, 5120 * sign(agent.team), 0])
    targetVec = agent.enemyTargetVec
    ball_delay = agent.enemyBallInterceptDelay
    if distance2D(agent.closestEnemyToBall.location, targetVec) > 2500:
        targetVec = agent.ball.location
        ball_delay = 0
        # expedite = False

    target_dist = distance2D(targetVec, myGoal)
    agent_dist = distance2D(agent.me.location, myGoal)

    expedite = target_dist < agent_dist
    if agent.me.boostLevel <= 0 and expedite:
        return smart_retreat(agent)

    multi = 1
    min_offset = clamp(3000, 250, (targetVec[2]) + agent.ball_size)
    # dist_diff = distance2D(agent.me.location, targetVec)
    # speed_offset = agent.closestEnemyToBall.velocity.magnitude()
    speed_offset = max(
        [
            relativeSpeed(
                agent.closestEnemyToBall.velocity.flatten(),
                agent.enemyTargetVel.flatten(),
            ),
            agent.closestEnemyToBall.velocity.magnitude(),
        ]
    )
    # dist_offset = distance2D(agent.me.location, targetVec) * 0.5
    # offset = clamp(4000, min_offset, min_offset + dist_offset)
    offset = clamp(5000, min_offset, (min_offset + speed_offset) * multi)
    _direction = (myGoal - targetVec.flatten()).normalize()
    destination = targetVec + _direction.scale(offset)

    pre_clamp = destination.data[0]
    destination.data[0] = clamp(3500, -3500, destination[0])
    clamp_diff = abs(pre_clamp - destination.data[0])
    destination.data[1] += clamp_diff * sign(agent.team)
    destination.data[2] = 0

    if distance2D(destination, myGoal) < agent_dist - 100:
        # print(f"Retreating where we weren't before {agent.time}")
        return smart_retreat(agent)

    if (agent.team == 0 and destination.data[1] * sign(agent.team) < -4900) or (
            agent.team == 1 and destination.data[1] * sign(agent.team) > 4900
    ):
        # print(f"target location: {targetVec.data} destination: {destination} calculated offset: {offset}")
        return smart_retreat(agent)

    return driveController(
        agent, destination, agent.time + ball_delay, expedite=expedite, floppies=False
    )


def verify_alignment(agent, target_vector, car_offset):
    if (
            distance2D(agent.me.location.flatten(), target_vector.flatten())
            <= car_offset + agent.ball_size
    ):
        return extendToGoal(
            agent, target_vector, agent.me.location, buffer=agent.ball_size * 3
        )

    car_to_ball_dir = (agent.me.location - target_vector).flatten().normalize()
    ball_to_car_dir = car_to_ball_dir.scale(-1)

    car_contact_point = agent.me.location + (car_to_ball_dir.scale(car_offset))
    ball_contact_point = target_vector + (ball_to_car_dir.scale(agent.ball_size))

    return extendToGoal(
        agent, ball_contact_point, car_contact_point, buffer=agent.ball_size * 3
    )


def defensive_check(agent):
    return False
    if len(agent.allies) > 0:
        return False
    if agent.lastMan == agent.me.location and agent.me.location[1] * sign(agent.team) < 4000 and agent.enemyTargetVec[1] * sign(agent.team) < 4000:
        myGoal = Vector([0, 5300 * sign(agent.team), 100])

        if not agent.goalPred and not(agent.offensive and butterZone(agent.currentHit.pred_vector)) and agent.enemyBallInterceptDelay - agent.time < 3 and agent.contested and \
                agent.currentHit.time_difference() > 0.5 and agent.enemyBallInterceptDelay < agent.currentHit.time_difference() \
                and distance2D(myGoal, agent.enemyTargetVec) < distance2D(myGoal, agent.closestEnemyToBall.location) and \
                agent.me.location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team) and not butterZone(
                agent.enemyTargetVec):
            return True

        if (agent.offensive and butterZone(agent.currentHit.pred_vector) and agent.currentHit.time_difference() < 1) or agent.closestEnemyToBall.velocity[1] * -(sign(agent.team)) > 0:
            return False



    return False


def defensive_positioning(agent):
    # myGoal = Vector([0, 5300 * sign(agent.team), 100])
    myGoal = find_defensive_target(agent)
    defensive_target = agent.enemyTargetVec
    if defensive_target[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team):
        return smart_retreat(agent)
    protect_direction = (myGoal.flatten() - defensive_target.flatten()).normalize()
    hit_direction = (defensive_target.flatten() - agent.closestEnemyToBall.location.flatten()).normalize()
    # if agent.contested:
    #     blended_direction = (hit_direction+protect_direction).normalize()
    # else:
    blended_direction = protect_direction



    min_distance = 100
    max_distance = clamp(3500, min_distance + 1, distance2D(agent.me.location, defensive_target))
    defensive_offset = max(agent.closestEnemyToBall.velocity.magnitude(),
                           relativeSpeed(agent.closestEnemyToBall.velocity, agent.enemyTargetVel))
    defensive_offset = clamp(max_distance, min_distance, defensive_offset)

    protect_projection = defensive_target + blended_direction.scale(defensive_offset)

    # simple_slope - find target within 90 degrees of agent velocity if target would cause reversal

    protect_projection.data[0] += -agent.me.velocity[0] * 0.1
    protect_projection.data[1] += -agent.me.velocity[1] * 0.1



    if protect_projection[0] > 4040:
        protect_projection.data[0] -= abs(protect_projection[0] - 4040)

    elif protect_projection[0] < -4040:
        protect_projection.data[0] += abs(protect_projection[0] + 4040)

    if abs(protect_projection[1]) > 5000:
        protect_projection.data[1] = 5000 * sign(protect_projection[1])

    # angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), protect_projection.flatten().normalize())
    # if abs(angle) > 90:
    #     print(angle)

    discrepancy = distance2D(protect_projection, myGoal) - distance2D(agent.me.location, myGoal)
    if discrepancy < -500:
        return smart_retreat(agent)

    expedite = discrepancy < -100

    result = driveController(
        agent,
        protect_projection,
        # agent.enemyPredTime + 0.1,
        agent.time,
        expedite=expedite,
        floppies=False
    )

    protect_projection.data[2] = 20
    agent.renderCalls.append(
        renderCall(
            agent.renderer.draw_line_3d,
            agent.me.location.toList(),
            protect_projection.toList(),
            agent.renderer.purple,
        )
    )
    agent.update_action({"type": "BALL", "time": agent.currentHit.prediction_time})
    return result

def reposition_handler(agent, target):
    return None
    if len(agent.allies) > 0:
        return None

    elif agent.contested:
        return None

    elif not agent.offensive:
        return None

    if wrong_side_check(agent, target):
        return go_wide(agent,target)

    return None


def wrong_side_check(agent, target):
    return None
    if abs(target[0]) < 650: #just shove in balls down the middle
        return False

    if target[0] > agent.me.location[0] and target[0] > 0:
        return True
    elif target[0] < agent.me.location[0] and target[0] < 0:
        return True

    return False

def go_wide(agent, target):
    dir = (target - agent.me.location).normalize()
    x_dist = abs((target-agent.me.location)[0])
    y_dist = clamp(2000, 500, x_dist)
    y_off = y_dist*sign(agent.team)
    x_off = x_dist * sign(dir[0])
    offset = Vector([x_off, y_off, 0])
    return driveController(agent, target+offset, agent.time, expedite=True)




def lineupShot(agent, multi, aim_target=None):
    variance = 5
    leftPost = Vector([-500, 5500 * -sign(agent.team), 200])
    rightPost = Vector([500, 5500 * -sign(agent.team), 200])
    center = Vector([0, 5500 * -sign(agent.team), 200])

    myGoal = Vector([0, 5300 * sign(agent.team), 200])

    targetVec = agent.currentHit.pred_vector
    if agent.me.location[1] * sign(agent.team) < targetVec[1] * sign(agent.team):
        return ShellTime(agent, aim_target)

    if len(agent.allies) < 1 and agent.offensive and agent.contested and agent.me.boostLevel < 50:
        return playBack(agent)

    hurry = True
    distance = distance2D(agent.me.location, targetVec)
    targToGoalDistance = distance2D(targetVec, center)
    targetLocal = toLocal(targetVec, agent.me)
    carToBallAngle = math.degrees(math.atan2(targetLocal[1], targetLocal[0]))
    offensive = agent.offensive
    require_lineup = False
    flipping = True

    carToBallAngle = correctAngle(carToBallAngle)

    mode = 0
    if targToGoalDistance < agent.aim_range:
        mode = 1
    goalSpot = aim_target
    correctedAngle = 0

    if not goalSpot:
        goalSpot, correctedAngle = goal_selector_revised(agent, mode=mode)

    shot_scorable = agent.currentHit.scorable()

    # if agent.scorePred is not None and agent.closestEnemyToBall.onSurface and demo_check(agent, agent.closestEnemyToBall) and agent.me.location != agent.lastMan:
    #     return demoTarget(agent, agent.closestEnemyToBall)

    if not shot_scorable and len(agent.allies) < 2:
        hurry = False
        # flipping = False
        # goalSpot.data[2] = 5000 * (-sign(agent.team))
        if (
                agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                and agent.enemyBallInterceptDelay < 2.5
                and agent.enemyAttacking
                # and agent.team == 0
        ) or agent.me.boostLevel < agent.boostThreshold:
            # return secondManPositioning(agent)
            return playBack(agent)

    # if (
    #     agent.goalPred is None
    #     and len(agent.allies) < 1
    #     and agent.currentHit.time_difference() - agent.enemyBallInterceptDelay >= 1
    #     and agent.on_correct_side
    # ):
    #     hurry = False

    if len(agent.allies) < 2:
        if abs(correctedAngle) >= agent.angleLimit and abs(targetVec[0]) > 800:
            hurry = False
            # flipping = False
            if (
                    agent.enemyBallInterceptDelay < agent.currentHit.time_difference()
                    and agent.enemyBallInterceptDelay < 2.5
                    and agent.enemyAttacking
                    # and agent.team == 0
            ) or agent.me.boostLevel < agent.boostThreshold:
                # return secondManPositioning(agent)
                return playBack(agent)

        # if not agent.openGoal and agent.me.boostLevel < agent.boostThreshold and offensive and agent.me.location[1] * sign(agent.team) > 0:
        #     return playBack(agent)

    if agent.scared:
        return turtle_mode(agent)

    if defensive_check(agent):
        return defensive_positioning(agent)

    corner = cornerDetection(targetVec)

    mirror_info = mirrorshot_qualifier(agent)

    # testing
    fudging = False

    is_mirror_shot = (
            mirror_info[0]
            and len(mirror_info[1]) < 1
            and distance < 3500
            #and not offensive
            #and (agent.lastMan == agent.me.location)
            #and agent.contested
    )
    maxRange = 1800 if not agent.contested else 900

    if len(agent.allies) < 2:
        if not shot_scorable:  # and len(agent.allies) < 1:
            # return playBack(agent)
            # hurry = False
            require_lineup = True
            # testing
            goalSpot.data[1] = 5000 * -sign(agent.team)
            maxRange = 900

    targetLoc = None

    if abs(carToBallAngle) <= 40 or abs(carToBallAngle) >= 140:
        carOffset = agent.carLength * 0.5
    else:
        carOffset = agent.carWidth * 0.5

    ballOffset = get_ball_offset(agent, agent.currentHit)

    totalOffset = (carOffset + ballOffset) * 0.9
    offset_min = totalOffset * 0.75

    positioningOffset = totalOffset



    _direction = direction(targetVec.flatten(), goalSpot.flatten())
    lined_up = agent.lineup_check()

    scooching = False
    max_dist_multi = 0.5
    if not agent.offensive:
        max_dist_multi = 0.4
    if agent.scorePred is None and (
            # (not is_mirror_shot and distance < offset_min * 0.85)
            not is_mirror_shot
            and targetVec[2] >= agent.ball_size + 20
            and not butterZone(targetVec)
            and distance2D(agent.closestEnemyToBall.location, center) < distance2D(targetVec, center)
            and not agent.contested
            and (agent.currentHit.pred_vel.flatten().magnitude() < 1500)
    ):
        offset_min = totalOffset * 0.5
        positioningOffset = offset_min
        max_dist_multi = 0.2
        scooching = True

    if agent.currentHit.time_difference() < 0.5 and hurry and not scooching:
        if agent.me.location[1] * sign(agent.team) > targetVec[1] * sign(agent.team):
            if ((not agent.forward or agent.me.boostLevel < 1) or lined_up) and agent.contested:
                return handleBounceShot(agent, waitForShot=False)

    repos_action = reposition_handler(agent, targetVec)
    if repos_action is not None:
        return repos_action

    # testing
    if is_mirror_shot and offensive:
        is_mirror_shot = False

    if (
            targetVec[1] * sign(agent.team) < -3500
            # and not lined_up
            and abs(targetVec[0]) < 3000
            # and len(agent.allies) < 2
            and not is_mirror_shot
    ):
        require_lineup = True
        # maxRange = 1800 if not lined_up else maxRange

    # if agent.team == 0 and not is_mirror_shot and offensive and not agent.contested:
    #     require_lineup = True

    flipHappy = False
    # challenge_flip(agent, targetVec)

    # if agent.contested and agent.me.boostLevel < 1:
    #     if not is_mirror_shot:
    #         targetLoc = get_aim_vector(
    #             agent,
    #             goalSpot.flatten(),
    #             targetVec.flatten(),
    #             agent.currentHit.pred_vel,
    #             positioningOffset,
    #         )[0]
    #
    #     else:
    #         targetLoc = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)
    #     modifiedDelay = agent.ballDelay

    #_direction = direction(targetVec.flatten(), goalSpot.flatten())
    simple_pos = targetVec.flatten() + _direction.scale(positioningOffset)
    simple_pos.data[2] = agent.defaultElevation

    if not targetLoc and agent.scared:
        # if agent.scorePred == None and agent.team != 0:
        #     positioningOffset = clamp(
        #         maxRange, offset_min, distance * 0.1
        #     )
        #     targetLoc = get_aim_vector(
        #         agent,
        #         goalSpot.flatten(),
        #         targetVec.flatten(),
        #         agent.currentHit.pred_vel,
        #         positioningOffset,
        #     )[0]
        # else:
        targetLoc = get_aim_vector(
            agent,
            goalSpot.flatten(),
            targetVec.flatten(),
            agent.currentHit.pred_vel,
            positioningOffset,
            #vel_adjust=False,
        )[0]

        modifiedDelay = agent.ballDelay

    if (
            not targetLoc
            and agent.contested
            and not agent.openGoal
            #and (not require_lineup or lined_up or agent.me.boostLevel < 1)
            and (not require_lineup or agent.me.boostLevel < 1)
            and (
            distance2D(agent.closestEnemyToBall.location, center)
            < distance2D(agent.me.location, center)
            or agent.me.boostLevel < 1
    )
    ):
        if not is_mirror_shot:
            targetLoc = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
                #vel_adjust=False,
            )[0]

        else:
            targetLoc = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)
        modifiedDelay = agent.ballDelay

    if not targetLoc:
        if not agent.contested or require_lineup:
            # if ballToGoalDist < 5000:
            if abs(targetVec[0]) < 3000:
                if agent.forward:
                    # if offensive:
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
                            #vel_adjust=False,
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
                                # (positioningOffset - offset_min)
                                    positioningOffset
                                    / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                            ),
                        )
                        fudging = True

    if not targetLoc:
        if agent.forward and not agent.contested and agent.me.boostLevel > 0:
            if sign(agent.team) * targetVec[1] <= 0:
                # multiCap = clamp(max_dist_multi, 0.3, distance / 10000)
                # testing
                multiCap = max_dist_multi
                # print("in second shot")
                multi = clamp(
                    multiCap, 0.25, (5000 - abs(agent.me.location[0])) / 10000
                )
                positioningOffset = clamp(maxRange, offset_min, (distance * multi))
                # if agent.contested:
                #     positioningOffset = clamp(800,totalOffset*.5,positioningOffset)

                targetLoc = targetVec + _direction.scale(positioningOffset)

                if not is_mirror_shot:
                    targetLoc = get_aim_vector(
                        agent,
                        goalSpot.flatten(),
                        targetVec.flatten(),
                        agent.currentHit.pred_vel,
                        positioningOffset,
                        #vel_adjust=False,
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
                            # (positioningOffset - offset_min)
                                positioningOffset
                                / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                        ),
                    )
                    fudging = True

    if (
            targetLoc
            and len(agent.allies) > 0
            and targetLoc[1] * sign(agent.team) > agent.me.location[1] * sign(agent.team)
    ):
        targetLoc = None

    if not targetLoc:
        positioningOffset = clamp(maxRange, offset_min, (distance * 0.2))
        if not is_mirror_shot:
            targetLoc = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
                #vel_adjust=False,
            )[0]

        else:
            targetLoc = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)

        modifiedDelay = agent.currentHit.time_difference()
        if positioningOffset > offset_min:
            modifiedDelay = clamp(
                6,
                0.0001,
                agent.ballDelay
                - (
                    # (positioningOffset - offset_min)
                        positioningOffset
                        / clamp(maxPossibleSpeed, 0.001, agent.currentSpd)
                ),
            )
            fudging = True

    if not targetLoc:
        if not is_mirror_shot:
            targetLoc = get_aim_vector(
                agent,
                goalSpot.flatten(),
                targetVec.flatten(),
                agent.currentHit.pred_vel,
                positioningOffset,
                #vel_adjust=False,
            )[0]

        else:
            targetLoc = aim_wallshot_naive(agent, agent.currentHit, positioningOffset)
        modifiedDelay = agent.currentHit.time_difference()

    if (
            not agent.forward
            #or butterZone(targetVec)
            or (agent.me.boostLevel < 12 and distance2D(agent.me.location, agent.enemyGoalLocations[1]) < distance2D(agent.closestEnemyToBall.location, agent.enemyGoalLocations[1]))
    ):
        naive_boostless_push(agent)

    targetLoc.data[2] = agent.defaultElevation

    result = driveController(
        agent,
        targetLoc,
        agent.time + modifiedDelay,
        expedite=hurry,
        flippant=flipHappy,
        flips_enabled=flipping,
        fudging=fudging,
        offset_dist=0 if not fudging else findDistance(targetLoc, simple_pos)
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
    agent.update_action({"type": "BALL", "time": agent.currentHit.prediction_time})
    return result


def turn_radius(v: float) -> float:
    if v == 0:
        return 0
    return 1.0 / curvature(v)


def curvature(v: float) -> float:
    # v is the magnitude of the velocity in the car's forward direction
    if 0.0 <= v < 500.0:
        return 0.006900 - 5.84e-6 * v
    if 500.0 <= v < 1000.0:
        return 0.005610 - 3.26e-6 * v
    if 1000.0 <= v < 1500.0:
        return 0.004300 - 1.95e-6 * v
    if 1500.0 <= v < 1750.0:
        return 0.003025 - 1.1e-6 * v
    if 1750.0 <= v < 2500.0:
        return 0.001800 - 4e-7 * v

    return 0.0


def max_speed_of_curvature(c: float) -> float:
    if c >= 0.0069:
        return 0
    if c > 0.00398:
        return (0.0069 - c) / 0.00000584
    if c > 0.00235:
        return 500 + (0.00398 - c) / 0.00000584
    if c > 0.001375:
        return 1000 + (0.00235 - c) / 0.00000584
    if c > 0.0011:
        return 1500 + (0.001375 - c) / 0.0000011
    if c > 0.00088:
        return 1750 + (0.0011 - c) / 0.0000004

    return 2400


# def find_arc_length(local_target:Vector,radius:float,curve:float):
#     circumference = math.pi * 2 * radius
#     _dir = local_target.flatten().normalize()
#     #dist = local_target.flatten().magnitude()
#     midpoint = local_target.scale(0.5)
#     x2 = (math.cos(90)*_dir[0])-(math.sin(90)*_dir[1])
#     y2 = (math.sin(90)*_dir[0]) + (math.cos(90)*_dir[1])
#     c1 = midpoint + Vector([x2,y2,0]).scale(radius)
#     c2 = midpoint + Vector([x2,y2,0]).scale(-radius)
#     #print(c1,c2,local_target.flatten())
#
#     # dist1 = abs(distance2D(c1,local_target)-distance2D(c1,Vector([0,0,0])))
#     # dist2= abs(distance2D(c2, local_target)-distance2D(c2, Vector([0,0,0])))
#
#
#     ang1 = abs(angleBetweenVectors(c1-local_target.flatten(),c1))
#     ang2 = abs(angleBetweenVectors(c2-local_target.flatten(),c2))
#     ang = min(ang1,ang2)
#
#     # print(radius)
#     # print(distance2D(c1,local_target),distance2D(c1,Vector([0,0])))
#     # print(distance2D(c2, local_target), distance2D(c2, Vector([0, 0])))
#     #print(dist1,dist2)
#     # print(ang,circumference)
#     # print(abs(circumference*(ang/360)))
#     return abs(circumference*(ang/360))
#
# def find_max_speed(curvature:float,speed_maximums):
#     curvature = abs(curvature)
#     index = -1
#     for i in range(len(speed_maximums)):
#         if curvature > speed_maximums[i][1]:
#             index = i
#             break
#
#     if index == -1:
#         return 2300
#
#     elif index == 0:
#         return 0
#
#     else:
#         start = index-1
#         speed_diff = speed_maximums[index][0] - speed_maximums[start][0]
#         normalized_vals = []
#         _max = speed_maximums[start][1]
#         _min = speed_maximums[index][1]
#         curve_norm = 1 - ((curvature-_min)/(_max-_min))
#         # print(start,index)
#         # print(curve_norm)
#         return speed_maximums[start][0] + (speed_diff*curve_norm)
#
# def find_curve(local_target:Vector):
#     _radius = max(local_target.data[:2])
#     return 1/_radius,_radius

def radius_from_local_point(a):
    try:
        a = a.flatten()
        return 1 / (2 * a[1] / a.dotProduct(a))
    except ZeroDivisionError:
        return 0.000000001


def find_arc_distance(angle_degrees, radius):
    circumference = math.pi * 2 * radius
    return circumference * abs(angle_degrees) / 180


def find_curve(agent, global_target):
    x = agent._forward.dotProduct(global_target - agent.me.position)
    y = agent.left.dotProduct(global_target - agent.me.position)
    return (2 * y) / (x * x + y * y)


def get_path_info(local_target, angle):
    radius = radius_from_local_point(local_target)
    c = 1 / radius
    distance = find_arc_distance(angle, radius)
    return abs(radius), abs(c), abs(distance)


# def horrible_curve_finder(agent, target, angle):
#     speed = agent.currentSpd
#     speed_inc = 10
#     if target[0] < 0:
#         target = target.scale(-1)
#
#     _rad = turn_radius(speed)
#     center = agent.me.location + agent.left.scale(-_rad)
#     center_dist = distance2D(center, agent.me.location+target)
#
#
#     if center_dist > _rad:
#         while speed < maxPossibleSpeed:
#             _rad = turn_radius(speed)
#             center = agent.me.location + agent.left.scale(-_rad)
#             center_dist = distance2D(center, agent.me.location + target)
#             if center_dist < _rad:
#                 break
#             speed += speed_inc
#     else:
#         while speed > 350:
#             _rad = turn_radius(speed)
#             center = agent.me.location + agent.left.scale(-_rad)
#             center_dist = distance2D(center, agent.me.location + target)
#             if center_dist > _rad:
#                 break
#             speed -= speed_inc
#
#     _rad = turn_radius(speed)
#     c = curvature(clamp(maxPossibleSpeed, 350, speed))
#     circumference = math.pi * 2 * radius
#     arc_distance = circumference * abs(angle)/180
#
#     return c, turn_radius(speed), arc_distance


def maxSpeedAdjustment(agent, target, angle, _distance, curve, fudging):
    if agent.onWall or fudging:
        return maxSpeedAdjustmentWall(agent, target, angle, _distance)
    _angle = abs(angle)
    if _angle > 180:
        _angle -= 180

    if (_angle <= 60 or _angle >= 120) and _distance <= agent.ball_size + 30:
        return maxPossibleSpeed

    return max_speed_of_curvature(curve)


def maxSpeedAdjustmentWall(agent, local_target, angle, dist):
    if abs(angle) <= 3:
        return maxPossibleSpeed

    if not agent.forward:
        return maxPossibleSpeed

    if (abs(angle) <= 45 or abs(angle) >= 135) and dist <= agent.groundReachLength:
        return maxPossibleSpeed

    cost_inc = maxPossibleSpeed / 180
    if dist < 1200:
        cost_inc *= 2
    new_speed = clamp(maxPossibleSpeed, 350, maxPossibleSpeed - (abs(angle) * cost_inc))
    # print(f"adjusting speed to {newSpeed}")

    return new_speed


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

    elif ball_vec[0] <= 893 and startPos[0] >= ball_vec[0]:
        acceptable = False

    elif startPos[1] * sign(agent.team) < ball_vec[1] * sign(agent.team):
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


@jit
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


def weighted_distance_2D(player_location: Vector, ball_location: Vector):
    _origin = getLocation(player_location).flatten()
    _destination = getLocation(ball_location).flatten()
    difference = _origin - _destination
    if abs(ball_location[0]) > 500:
        if (ball_location[0] > 0 and player_location[0] < ball_location[0]) or (
                ball_location[0] < 0 and player_location[0] > ball_location[0]
        ):
            difference.data[0] = difference[0] * 1.5
    return difference.magnitude()


@jit
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


def localizeVector(target_object, our_object, remote_location=None):
    if remote_location is None:
        x = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
            our_object.matrix[0]
        )
        y = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
            our_object.matrix[1]
        )
        z = (getLocation(target_object) - getLocation(our_object.location)).dotProduct(
            our_object.matrix[2]
        )

    else:
        x = (getLocation(target_object) - remote_location).dotProduct(our_object.matrix[0])
        y = (getLocation(target_object) - remote_location).dotProduct(our_object.matrix[1])
        z = (getLocation(target_object) - remote_location).dotProduct(our_object.matrix[2])

    return Vector([x, y, z])


def localizeRotation(target_rotation, agent):
    return Vector(
        [
            target_rotation.dotProduct(agent._forward),
            target_rotation.dotProduct(agent.left),
            target_rotation.dotProduct(agent.up),
        ]
    )


def toLocal(target, our_object):
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



# def get_aim_vector(
#         agent, end_target_vec, target_ball_vec, target_ball_velocity, offset_length, vel_adjust=True
# ):
#     if agent.me.location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team) and vel_adjust:
#         vel_difference = abs(angleBetweenVectors(
#             agent.me.velocity.flatten(), target_ball_velocity.flatten()
#         ))
#         _direction = direction(target_ball_vec.flatten(), end_target_vec.flatten())
#         vel_difference = angleBetweenVectors(_direction.flatten(), target_ball_velocity.flatten())
#         ovd = vel_difference * 1
#         # alignment = abs(90 - abs(vel_difference - 90)) / 100
#         vel_difference -= 90
#         if vel_difference < 0:
#             vel_difference += 180
#
#         if vel_difference > 90:
#             alignment = abs((180 - vel_difference) / 100.0)
#         else:
#             alignment = abs((90 - vel_difference) / 100.0)
#
#         # print(ovd, vel_difference, alignment)
#         chunk = 100 / 90
#         percentage = alignment * chunk
#         # print(percentage)
#         divisor = 65.0
#         max_alteration = 15
#         clamped_max = clamp(max_alteration, 0, offset_length * 0.5)
#
#         adjusted_target_location = target_ball_vec + target_ball_velocity.flatten().normalize().scale(
#             clamp(clamped_max, 0, target_ball_velocity.flatten().magnitude() / divisor)
#             * percentage
#         )
#         angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), _direction)
#         return (
#             adjusted_target_location
#             + _direction.scale(
#                 offset_length - (target_ball_vec - adjusted_target_location).magnitude()
#             ),
#             angle,
#         )
#     else:
#         _direction = direction(target_ball_vec.flatten(), end_target_vec.flatten())
#         angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), _direction)
#         return target_ball_vec + _direction.scale(offset_length), angle

def get_aim_vector(
        agent, end_target_vec, target_ball_vec, target_ball_velocity, offset_length, vel_adjust=True
):
    if agent.me.location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team) and vel_adjust:
        # vel_difference = abs(angleBetweenVectors(
        #     agent.me.velocity.flatten(), target_ball_velocity.flatten()
        # ))
        _direction = direction(target_ball_vec.flatten(), end_target_vec.flatten())
        vel_difference = angleBetweenVectors(_direction.flatten(), target_ball_velocity.flatten())
        ovd = vel_difference * 1
        # alignment = abs(90 - abs(vel_difference - 90)) / 100
        vel_difference -= 90
        if vel_difference < 0:
            vel_difference += 180

        if vel_difference > 90:
            alignment = abs((180 - vel_difference) / 100.0)
        else:
            alignment = abs((90 - vel_difference) / 100.0)

        #alignment = 1

        # print(ovd, vel_difference, alignment)
        chunk = 100 / 90
        percentage = alignment * chunk
        # print(percentage)
        divisor = 100
        max_alteration = 20
        clamped_max = clamp(max_alteration, 0, offset_length * 0.5)

        adjusted_target_location = target_ball_vec + target_ball_velocity.flatten().normalize().scale(
            clamp(clamped_max, 0, target_ball_velocity.flatten().magnitude() / divisor)
            * percentage
        )
        angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), _direction)
        return (
            adjusted_target_location
            + _direction.scale(
                offset_length - (target_ball_vec - adjusted_target_location).magnitude()
            ),
            angle,
        )
    else:
        _direction = direction(target_ball_vec.flatten(), end_target_vec.flatten())
        angle = angleBetweenVectors(agent.me.velocity.flatten().normalize(), _direction)
        return target_ball_vec + _direction.scale(offset_length), angle



def aim_wallshot_naive_hitless(agent, targ_bal_vec, targ_ball_vel, offset_length):
    enemy_goal = Vector(
        [0, (5120 + agent.ball_size * 2) * -sign(agent.team), targ_bal_vec.data[2]]
    )

    enemy_goal.data[0] = 4096 * 2
    # if not defensive:
    if agent.me.location[0] > targ_bal_vec[0]:
        enemy_goal.data[0] = -(4096 * 2)
    # else:
    #     if targ_bal_vec[0] < 0:
    #         enemy_goal.data[0] = 4096 * -2

    return get_aim_vector(
        agent, enemy_goal, targ_bal_vec, targ_ball_vel, offset_length
    )[0]


def aim_wallshot_naive(agent, _hit, offset_length, force_close=False):
    target_vec = _hit.pred_vector
    multi = 2.0
    if not agent.offensive and len(agent.allies) > 0:
        multi = 1

    force_close = (
        False if agent.goalPred is not None else agent.me.velocity[1] * sign(agent.team) > 0
    )
    # if not force_close and not agent.offensive and len(agent.enemies) > 1:
    #     multi = 1.25

    enemy_goal = Vector(
        [0, (5120 + agent.ball_size * 2) * -sign(agent.team), target_vec.data[2]]
    )

    if not force_close:
        enemy_goal.data[0] = 4096 * multi
        if agent.me.location[0] > target_vec[0]:
            enemy_goal.data[0] = -(4096 * multi)

    else:
        enemy_goal.data[0] = 4096 * multi
        if target_vec[0] < 0:
            enemy_goal.data[0] = -(4096 * multi)

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


def oldDirtyCarryCheck(agent):
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


def enemy_carry_check(agent):
    maxRange = 275
    ball_distance = findDistance(agent.closestEnemyToBall.location, agent.ball.location)
    acceptableDistance = ball_distance <= maxRange
    ballRadius = agent.ball_size
    xy_range = agent.carLength + (ballRadius * 0.7)
    min_height = 35

    if (
            agent.closestEnemyToBall.onSurface
            and (abs(agent.ball.location[0]) < 3900)
            # and not agent.onWall
            and agent.touch.player_index == agent.closestEnemyToBall.index
            and acceptableDistance
            and (
            agent.ball.location[2] >= (ballRadius + min_height)
            and distance2D(agent.closestEnemyToBall.location, agent.ball.location) < xy_range
    )
            # testing velocity matching
            and relativeSpeed(agent.ball.velocity, agent.closestEnemyToBall.velocity) < 500

    ):
        return True

    # print(f"False {ball_distance} {agent.ball.location[2]} {error}")
    return False

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
# def dirtyCarryCheck(agent):
#     maxRange = 295
#     ball_distance = findDistance(agent.me.location, agent.ball.location)
#     acceptableDistance = ball_distance <= maxRange
#     ballRadius = agent.ball_size
#     xy_range = agent.carLength + (ballRadius * 0.7)
#     min_height = 25
#
#     if (
#             agent.onSurface
#             and (abs(agent.ball.location[0]) < 3900)
#             and not agent.onWall
#             and agent.touch.player_index == agent.index
#             and acceptableDistance
#             and (
#             agent.ball.location[2] >= (ballRadius + min_height)
#             and distance2D(agent.me.location, agent.ball.location) < xy_range
#     )
#             and abs(agent.ball.velocity[2]) < 200
#             and relativeSpeed(agent.ball.velocity, agent.me.velocity) < 550
#
#
#     ):
#         return True
#
#     # print(f"False {ball_distance} {agent.ball.location[2]} {error}")
#     return False


def simple_slope(p1: Vector, p2: Vector):
    return Vector([(p2[1] - p1[1]), (p2[0] - p1[0])])


def challenge_flip(agent, targetVec):
    # challenge disabled 103:48 @ 70 minutes kam(blue) in lead vs Diablo 0.466
    # 74:34 @ 64 minutes as orange .4594
    # return False
    if distance2D(agent.me.location, agent.ball.location) <= 200:
        if targetVec[2] <= 120 and agent.ball.location[2] <= 120:
            if len(agent.enemies) > 0:
                if (
                        distance2D(agent.closestEnemyToBall.location, agent.ball.location)
                        < 450
                ):
                    if agent.closestEnemyToBall.location[1] * sign(
                            agent.team
                    ) < agent.me.location[1] * sign(agent.team):
                        print("challenge flipping")
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
    if wall_inter[1] * -sign(agent.team) < -4000:
        # return False
        # error 2: mirror shot would bounce off corner
        error_codes.append(2)

    x_scale = 1
    # if abs(targetVec[0]) >= 3900:
    #     x_scale = 2

    if butterZone(targetVec) and targetVec[1] * sign(agent.team) < 0:
        # error 3: ball is right in front of enemy goal
        error_codes.append(3)

    if distance2D(targetVec, agent.me.location) > 5000:
        # error 4: ball is too far away to force locking into mirror shot
        error_codes.append(4)

    if targetVec[1] * sign(agent.team) < -3500:
        # error 5: Much better to force center than do weird corner redirect
        error_codes.append(5)

    vec_difference = targetVec.flatten() - agent.me.location.flatten()

    if abs(vec_difference[0]) * x_scale >= abs(vec_difference[1]):
        if (targetVec[0] >= center_limit or not agent.offensive) and agent.me.location[0] < targetVec[0]:
            return True, error_codes

        if (targetVec[0] < -center_limit or not agent.offensive) and agent.me.location[0] > targetVec[0]:
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
    happy = agent.scorePred is not None or extend_info[0]  # and (
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
                    agent.scorePred is not None
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


def carry_flick_new(agent):  # take the dot product of the wanted velocity and the ball velocity and add the negative to offset
    target_speed = 1000
    #print(agent.ball.location[2])
    if agent.forward and agent.me.boostLevel > 20:
        target_speed = 1700
    y_targ = 5250 * -sign(agent.team)
    x_targ = 0
    cradle_location = agent.ball.location.flatten() + agent.ball.velocity.flatten().scale(0.16666667)
    ball_speed = agent.ball.velocity.flatten().magnitude()
    extend_info = extendToGoal(
        agent,
        agent.ball.location.flatten(),
        agent.ball.location.flatten()
        - agent.ball.velocity.flatten().normalize().scale(20),
        buffer=agent.ball_size * 3,
        send_back=True,
    )
    lined_up = True
    extend_info[0] = (
            extend_info[0]
            and distance2D(Vector([0, 5250 * -sign(agent.team), 0]), agent.ball.location)
            > 3000
    )

    if extend_info[1] > 800:
        x_targ = -700
    elif extend_info[1] < -800:
        x_targ = 700

    max_offset = 20
    # if ball_speed < 1000:
    #     max_offset = 35
    # if not agent.scorePred:

    if not extend_info[0]:
        if (
                extend_info[1] > 0
                and agent.me.location[0] > 0
                or extend_info[1] < 0
                and agent.me.location[0] < 0
        ):
            lined_up = False
            test_y_targ = cradle_location[1] + 300 * -sign(agent.team)
            if abs(test_y_targ) < 5250:
                y_targ = test_y_targ

            target_speed = 500
            max_offset = clamp(75, max_offset, ball_speed)

    goal_loc = Vector([x_targ, y_targ, 0])
    # if not agent.forward:
    #     min_offset = 10
    if lined_up:
        return old_reliable(agent)

    go_under = False

    cradled = agent.ball.location[2] <= agent.carHeight + 125
    if cradled and ball_speed < 1000:
        max_offset = 35

    # current_trajectory = agent.ball.velocity.flatten().normalize()
    target_trajectory = (agent.ball.location.flatten() - goal_loc).normalize()
    traj_dot_norm = target_trajectory.dotProduct(agent.ball.velocity.flatten().normalize())
    stupid_dot = -(agent.ball.velocity.flatten().dotProduct(target_trajectory) / target_speed)

    aligned_vel = ball_speed * traj_dot_norm
    # print(traj_dot_norm, agent.currentSpd)
    # 65 if cradled else 15
    max_vel_offset = clamp(max_offset * .5, -(max_offset * .5), max((agent.me.boostLevel, 30)))

    counter_vel_mag = clamp(max_vel_offset, -max_vel_offset, (ball_speed - target_speed) / 20)
    if agent.ball.velocity[1] * sign(agent.team) > 100:
        counter_vel_mag = 120
    max_offset = clamp(max_offset, 0, max_offset - abs(counter_vel_mag))
    diff = target_trajectory
    corrective_offset = max_offset
    if not lined_up:
        corrective_offset = max_offset * clamp(1, -1, 1 + traj_dot_norm)
    diff = diff.scale(corrective_offset)
    # if diff.magnitude() > max_offset:
    #     diff = diff.normalize().scale(max_offset)
    target = cradle_location + diff + agent.ball.velocity.flatten().normalize().scale(counter_vel_mag)

    # offset = bonus_offset
    # print(offset)

    flick = (
                    agent.enemyBallInterceptDelay <= 0.55
            ) or agent.closestEnemyToBallDistance <= clamp(
        1000, 500, agent.ball.velocity.magnitude() * 0.6
    )

    if (
            cradled
            and not agent.scorePred
            and cradle_location[1] * sign(agent.team) < -4200
            and abs(cradle_location[0]) < 1100
    ):
        flick = True

    if flick:
        if not go_under:
            # if cradled:
            if (
                    agent.scorePred != None
                    and findDistance(agent.me.location, agent.ball.location) < 135
            ):  # and distance2D(agent.ball.location,enemy_goal) > 1500:
                if (
                        # distance2D(
                        #     agent.me.location, Vector([0, 5200 * -sign(agent.team), 0])
                        # )
                        # >= 2500
                        agent.currentSpd * 4
                        > distance2D(
                    agent.me.location, Vector([0, 5120 * -sign(agent.team), 0])
                )
                ):
                    agent.setJumping(20)
                else:
                    # agent.setJumping(-1)
                    agent.setJumping(20, target=False)
            else:
                if agent.forward:
                    agent.setJumping(6, target=cradle_location)
                else:
                    agent.setHalfFlip()
            # else:
            #     if (
            #         distance2D(agent.me.location, agent.ball.location) < 40
            #         and agent.enemyAttacking
            #         and not agent.scorePred
            #     ):
            #         if agent.forward:
            #             agent.setJumping(2)
            #         else:
            #             agent.setHalfFlip()
        else:
            print(f"Going under! {agent.time}")
            offset = 200

    # direction = (agent.enemyGoalLocations[1] - cradle_location).normalize().scale(-40)
    # offset = target_trajectory.scale(offset)
    # offset += direction
    # offset = offset.scale(0.5)
    # print(offset.magnitude())
    # target = cradle_location + offset

    if (
            cradled
            and agent.ball.velocity[1] * sign(agent.team) > 50
            and agent.ball.location[1] * sign(agent.team) > 3500
    ):
        agent.setJumping(0)

    agent.update_action({"type": "BALL", "time": agent.time + 0.166666667})

    return driveController(agent, target, agent.time + 0.166666667, expedite=True)


"""
above: new mess
below: mid creation copy?
"""

# def carry_flick_new(agent):
#     target_speed = 1050
#     max_offset = 35
#     if agent.me.boostLevel > 20 and agent.forward:
#         max_offset = 45
#
#     speed_limiter = 0
#     alignment_cap = 500
#     y_targ = 5250 * -sign(agent.team)
#     x_targ = 0
#     if agent.ball.location[0] > 1200:
#         x_targ = -500
#     elif agent.ball.location[0] < -1200:
#         x_targ = 500
#
#     # max_bouncing_corrective_offset = 20
#     min_offset = 8
#     # if agent.me.boostLevel > 15 and agent.currentSpd < 1800 and agent.forward:
#     #     min_offset = 12
#     if not agent.forward:
#         min_offset = 20
#
#     go_under = len(agent.enemies) < 2 and not agent.closestEnemyToBall.onSurface
#
#     # carry_delay = 10  # agent.ball.velocity.magnitude()/10 # how many frames ahead are we shooting for?
#     cradled = agent.ball.location[2] <= agent.carHeight + 125
#     cradle_location = agent.ball.location.flatten() + agent.ball.velocity.flatten().scale(
#         0.16666667
#     )
#     current_trajectory = agent.ball.velocity.flatten().normalize()
#
#     extend_info = extendToGoal(
#         agent,
#         agent.ball.location.flatten(),
#         agent.ball.location.flatten()
#         - agent.ball.velocity.flatten().normalize().scale(20),
#         buffer=agent.ball_size * 3,
#         send_back=True,
#     )
#
#     extend_info[0] = (
#         extend_info[0]
#         and distance2D(Vector([0, 5250 * -sign(agent.team), 0]), agent.ball.location)
#         > 3000
#     )
#
#     if not agent.scorePred:
#
#         if not extend_info[0]:
#             if (
#                 extend_info[1] > 0
#                 and agent.me.location[0] > 0
#                 or extend_info[1] < 0
#                 and agent.me.location[0] < 0
#             ):
#
#                 test_y_targ = agent.ball.location[1] + 200 * -sign(agent.team)
#                 if abs(test_y_targ) < 5250:
#                     y_targ = test_y_targ
#
#     enemy_goal = Vector([x_targ, y_targ, 0])
#     target_trajectory = (cradle_location - enemy_goal).normalize()
#     happy = agent.scorePred != None or extend_info[0]
#
#     if (not cradled or happy) and agent.ball.velocity.magnitude() >= target_speed - 500:
#         offset = min_offset
#         if not cradled and agent.me.boostLevel > 10 and agent.forward:
#             offset = min_offset * 1.5
#
#     else:
#         offset = max_offset
#
#     # flick = (agent.enemyBallInterceptDelay <= 0.6
#     #     and agent.enemyAttacking
#     #     or agent.enemyBallInterceptDelay <= 0.4
#     # ) or agent.closestEnemyToBallDistance <= clamp(
#     #     1200, 600, agent.ball.velocity.magnitude() * 0.6
#     # )
#     flick = (
#         agent.enemyBallInterceptDelay <= 0.55
#     ) or agent.closestEnemyToBallDistance <= clamp(
#         1000, 500, agent.ball.velocity.magnitude() * 0.6
#     )
#
#     if (
#         cradled
#         and not agent.scorePred
#         and cradle_location[1] * sign(agent.team) < -4200
#         and abs(cradle_location[0]) < 1100
#     ):
#         flick = True
#
#     speed_alignment = (
#         clamp(1, 0.0, (agent.ball.velocity.magnitude() - target_speed) * 1.0) / 500.0
#     )
#
#     targetDirection = optimal_intercept_vector(
#         cradle_location.flatten(), agent.ball.velocity.flatten(), enemy_goal.flatten()
#     )
#
#     # blended_direction = (agent.ball.velocity.flatten().normalize().scale(speed_alignment)+ targetDirection.scale(1-speed_alignment)).normalize()
#     blended_direction = agent.ball.velocity.flatten().normalize().scale(
#         speed_alignment
#     ) + targetDirection.scale(1 - speed_alignment)
#
#     if flick:
#         if not go_under:
#             if cradled:
#                 if (
#                     agent.scorePred != None
#                     and findDistance(agent.me.location, agent.ball.location) < 135
#                 ):  # and distance2D(agent.ball.location,enemy_goal) > 1500:
#                     if (
#                         # distance2D(
#                         #     agent.me.location, Vector([0, 5200 * -sign(agent.team), 0])
#                         # )
#                         # >= 2500
#                         agent.currentSpd * 4
#                         > distance2D(
#                             agent.me.location, Vector([0, 5120 * -sign(agent.team), 0])
#                         )
#                     ):
#                         agent.setJumping(20)
#                     else:
#                         # agent.setJumping(-1)
#                         agent.setJumping(20, target=False)
#                 else:
#                     if agent.forward:
#                         agent.setJumping(6, target=cradle_location)
#                     else:
#                         agent.setHalfFlip()
#             else:
#                 if (
#                     distance2D(agent.me.location, agent.ball.location) < 40
#                     and agent.enemyAttacking
#                     and not agent.scorePred
#                 ):
#                     if agent.forward:
#                         agent.setJumping(2)
#                     else:
#                         agent.setHalfFlip()
#         else:
#             print(f"Going under! {agent.time}")
#             offset = 200
#     target = cradle_location + blended_direction.scale(offset)
#
#     if (
#         cradled
#         and agent.ball.velocity[1] * sign(agent.team) > 50
#         and agent.ball.location[1] * sign(agent.team) > 3500
#     ):
#         agent.setJumping(0)
#
#     agent.update_action({"type": "BALL", "time": agent.time + 0.166666667})
#
#     return driveController(agent, target, agent.time + 0.166666667, expedite=True)

"""
old hotness
"""


def old_reliable(agent):
    target_speed = 1050
    max_offset = 30
    if agent.me.boostLevel > 20 and agent.forward:
        max_offset = 40

    speed_limiter = 0
    alignment_cap = 500
    y_targ = 5250 * -sign(agent.team)
    x_targ = 0

    min_offset = 8
    if agent.me.boostLevel > 20 and agent.currentSpd < 1600 and agent.forward:
        min_offset = 12
    if not agent.forward:
        min_offset = 20

    # vels_difference = angleBetweenVectors(agent.ball.velocity.flatten(),direction(Vector([0,5250*-sign(agent.team),0]),agent.ball.location.flatten()))
    # c_offset = clamp(max_offset,min_offset,((max_offset/180)*clamp(180,0,vels_difference*2))*current_saturation)


    go_under = False  # agent.closestEnemyToBall.location[2] > 75

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
        buffer=agent.ball_size * 3,
        send_back=True,
    )

    extend_info[0] = (
        extend_info[0]
        and distance2D(Vector([0, 5250 * -sign(agent.team), 0]), agent.ball.location)
        > 3000
    )

    if extend_info[1] > 800:
        x_targ = -700
    elif extend_info[1] < -800:
        x_targ = 700

    if not agent.scorePred:

        if not extend_info[0]:
            if (
                extend_info[1] > 0
                and agent.me.location[0] > 0
                or extend_info[1] < 0
                and agent.me.location[0] < 0
            ):

                test_y_targ = cradle_location[1] + 10 * -sign(agent.team)
                if abs(test_y_targ) < 5250:
                    y_targ = test_y_targ

    enemy_goal = Vector([x_targ, y_targ, 0])
    target_trajectory = (cradle_location - enemy_goal).normalize()
    happy = agent.scorePred is not None or extend_info[0]

    offset = min_offset

    # if (not cradled or not happy) and agent.ball.velocity.magnitude() >= target_speed:
    #     offset = min_offset
    #     if not cradled and agent.me.boostLevel > 10 and agent.forward:
    #         offset = min_offset * 1.5
    #     else:
    #         offset = max_offset
    if cradled and not happy:
        offset = max_offset



    flick = (
        agent.enemyBallInterceptDelay <= 0.45
        and agent.enemyAttacking
        or agent.enemyBallInterceptDelay <= 0.3
    ) or agent.closestEnemyToBallDistance <= clamp(
        1000, 500, agent.ball.velocity.magnitude() * 0.5
    )

    if (
        cradled
        and not agent.scorePred
        and cradle_location[1] * sign(agent.team) < -4000
        and abs(cradle_location[0]) < 1500
    ):
        flick = True

    speed_alignment = (
        clamp(1, 0.0, (agent.ball.velocity.magnitude() - target_speed) * 1.0) / 500.0
    )

    targetDirection = optimal_intercept_vector(
        cradle_location.flatten(), agent.ball.velocity.flatten(), enemy_goal.flatten()
    )

    # blended_direction = (agent.ball.velocity.flatten().normalize().scale(speed_alignment)+ targetDirection.scale(1-speed_alignment)).normalize()
    blended_direction = agent.ball.velocity.flatten().normalize().scale(speed_alignment) + targetDirection.scale(1 - speed_alignment)

    if flick:
        if not go_under:
            if cradled:
                if (
                    agent.scorePred is not None
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
                    if agent.forward:
                        agent.setJumping(6, target=cradle_location)
                    else:
                        agent.setHalfFlip()
            else:
                if (
                    distance2D(agent.me.location, agent.ball.location) < 40
                    and agent.enemyAttacking
                    and not agent.scorePred
                ):
                    if agent.forward:
                        agent.setJumping(2)
                    else:
                        agent.setHalfFlip()
        else:
            # print(f"Going under! {agent.time}")
            offset = 100
    target = cradle_location + blended_direction.scale(offset)

    if (
        cradled
        and agent.ball.velocity[1] * sign(agent.team) > 50
        and agent.ball.location[1] * sign(agent.team) > 3500
    ):
        agent.setJumping(0)

    return driveController(
        agent, target, agent.time + carry_delay * agent.fakeDeltaTime, expedite=True
    )


def inTheMiddle(testNumber, guardNumbersList):
    return min(guardNumbersList) <= testNumber <= max(guardNumbersList)


def handleWallShot(agent):
    enemyGoal = Vector([0, -sign(agent.team) * 5200, 1500])
    myGoal = enemyGoal = Vector([0, sign(agent.team) * 5200, 500])
    targetVec = agent.currentHit.pred_vector
    destination = targetVec
    wall = which_wall(targetVec)
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

    agent.update_action({"type": "BALL", "time": agent.currentHit.prediction_time})

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

    location = toLocal(target, agent.me)
    angle_to_target = math.atan2(location.data[1], location.data[0])
    angle_degrees = correctAngle(math.degrees(angle_to_target))
    # angle_degrees = math.degrees(angle_to_target)
    if agent.onWall and not agent.wallShot:
        if abs(angle_degrees) < 5:
            if agent.me.location[2] < 1500:
                jumpingDown = True
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

    if abs(steering) >= 0.90 and not agent.dribbling:
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

@jit
def decelerationSim(dt, current_spd, timeAlloted):
    # def decelerationSim(agent, timeAlloted):
    increment = 525 * dt
    currentSpeed = current_spd * 1
    distance = 0
    while timeAlloted > 0 or currentSpeed > 0:
        timeAlloted -= dt
        currentSpeed = clamp(currentSpeed, 0, currentSpeed - increment)
        distance += currentSpeed * dt
    return distance


# @jit
def brake_sim(dt, current_spd, timeAlloted):
    # def brake_sim(agent, timeAlloted):
    increment = 3500 * dt
    currentSpeed = current_spd * 1
    distance = 0
    while timeAlloted > 0 or currentSpeed > 0:
        timeAlloted -= dt
        currentSpeed = clamp(currentSpeed, 0, currentSpeed - increment)
        distance += currentSpeed * dt
    return distance

def brake_time(spd):
    return spd/3500.0


# def decelerationSim(agent, timeAlloted):
#     increment = 525 * agent.fakeDeltaTime
#     currentSpeed = agent.currentSpd * 1
#     distance = 0
#     while timeAlloted > 0 or currentSpeed > 0:
#         timeAlloted -= agent.fakeDeltaTime
#         currentSpeed -= increment
#         distance += currentSpeed * agent.fakeDeltaTime
#     return distance
#
#
# def brake_sim(agent, timeAlloted):
#     increment = 3500 * agent.fakeDeltaTime
#     currentSpeed = agent.currentSpd * 1
#     distance = 0
#     while timeAlloted > 0 or currentSpeed > 0:
#         timeAlloted -= agent.fakeDeltaTime
#         currentSpeed -= increment
#         distance += currentSpeed * agent.fakeDeltaTime
#     return distance


def lastManFinder(agent):
    lastMan = None
    lastManY = math.inf * -sign(agent.team)
    allies = agent.allies + [agent.me]
    sorted(allies, key=lambda x: x.index)
    back_count = 0

    if agent.team == 0:
        # lastManY = math.inf
        for ally in allies:
            if ally.location[1] < lastManY:
                lastManY = ally.location[1]
                lastMan = ally
            if ally.location[1] * sign(agent.team) > agent.ball.location[1] * sign(
                    agent.team
            ):
                back_count += 1
    else:
        # lastManY = -math.inf
        for ally in allies:
            if ally.location[1] > lastManY:
                lastManY = ally.location[1]
                lastMan = ally
            if ally.location[1] * sign(agent.team) > agent.ball.location[1] * sign(
                    agent.team
            ):
                back_count += 1

    agent.ally_back_count = back_count

    return lastMan


def in_goal_check(agent):
    if abs(agent.me.location[1]) >= 4900 and abs(agent.me.location[0]) < 900:
        return True
    return False


def goalBoxFixer(agent, target):
    y_limit = 5085
    if abs(agent.me.location[1]) < y_limit:
        return target
        # not in goal, continue as normal
    else:
        xMin = -825
        xMax = 825
        y_extension = 400

        if agent.me.location[1] > y_limit:
            # in orange goal
            yMax = y_limit + y_extension

            if target[0] < xMin:
                target.data[0] = xMin
            elif target[0] > xMax:
                target.data[0] = xMax

            if target[1] > yMax:
                target.data[1] = yMax

        elif agent.me.location[1] < -y_limit or target[1] < -y_limit:
            # in blue goal
            yMin = -y_limit - y_extension

            if target[0] < xMin:
                target.data[0] = xMin
            elif target[0] > xMax:
                target.data[0] = xMax

            if target[1] < yMin:
                target.data[1] = yMin
        return target


def greedy_mover(agent, target_object):
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


def driveController(
        agent,
        target,
        arrivalTime,
        expedite=False,
        flippant=False,
        maintainSpeed=False,
        flips_enabled=True,
        kickoff=False,
        demos=False,
        floppies=True,
        going_for_aerial=False,
        fudging=False,
        offset_dist=0
):
    tta = clamp(6, 0.001, arrivalTime - agent.time)

    OT = target.scale(1)

    if not kickoff:

        if agent.boostMonster:
            expedite = True
            if agent.forward:
                flips_enabled = False
                flippant = False

        # testing
        if (
                flips_enabled
                and agent.forward
                and agent.goalPred == None
                and not agent.boostMonster
                and not agent.demo_monster
                and not demos
                and agent.contested
                and agent.rotationNumber == 1
                and agent.lastMan == agent.me.location
                and agent.me.location[1] * sign(agent.team)
                > agent.ball.location[1] * sign(agent.team)
        ):
            flips_enabled = agent.enemyBallInterceptDelay > 1

        if not agent.forward:
            expedite = True
            flips_enabled = True

        if target[2] == 0 or target[2] < agent.defaultElevation:
            target.data[2] = agent.defaultElevation

        if (agent.me.location[1] * sign(agent.team)) - (sign(agent.team) * 65) < agent.ball.location[1] * sign(
                agent.team
        ):
            own_goal_info = own_goal_check(
                agent,
                agent.ball.location.flatten(),
                agent.me.location.flatten(),
                buffer=-90,
                send_back=True,
            )

            if own_goal_info[0] and agent.ball.location[2] <= 160:
                #target = (agent.ball.location.flatten()) + agent.ball.velocity.flatten().normalize().scale(200)
                target = agent.ball.location.flatten() + Vector([0,sign(agent.team)*300, 0])
                if own_goal_info[1] > 0:
                    target += Vector([-200, 0, 0])
                else:
                    target += Vector([200, 0, 0])

                tta = 0.001
                fudging = True

        if not agent.demo_monster:

            if agent.onWall:
                flips_enabled = False
                if (
                        agent.currentHit != None
                        and agent.currentHit.hit_type != 2
                        and agent.me.location[2] > 75
                ):
                    target = unroll_path_from_wall_to_ground(agent.me.location, target)
                else:
                    placeVecWithinArena(
                        target, offset=agent.defaultElevation
                    )

            else:
                if agent.currentHit.hit_type == 2:
                    target = unroll_path_from_ground_to_wall(target)
                else:
                    placeVecWithinArena(
                        target, offset=agent.defaultElevation
                    )
        prefixer = target.scale(1)
        target = goalBoxFixer(agent, target)
        if prefixer != target:
            maintainSpeed = False
            flips_enabled = False
            tta = 0.000001
            if agent.goalPred is None:
                expedite = False
            flippant = False

    if abs(agent.me.location[1]) > 5100:
        flips_enabled = False

    if not kickoff:
        _distance = findDistance(agent.me.location, target)
        if fudging and offset_dist > 100:
            _distance += offset_dist
        #flat_dist = distance2D(agent.me.location, target)
    else:
        _distance = distance2D(agent.me.location, target)
        #flat_dist = _distance

    # if OT != target:
    #     OT_dist = findDistance(agent.me.location, OT)
    #     #tta = max(0.0001, tta * OT_dist/_distance)
    #     _distance = OT_dist

    localTarget = toLocal(target, agent.me)
    angle = math.atan2(localTarget[1], localTarget[0])
    angle_degrees = math.degrees(angle)
    avoiding = False
    target_to_avoid = Vector([0, 0, 0])
    boost_req = agent.boost_req
    if agent.dribbling:
        boost_req = agent.boost_req * 2

    goForward = agent.forward

    if avoiding:
        localTarget = toLocal(target_to_avoid, agent.me)
        angle = math.atan2(localTarget[1], localTarget[0])
        angle_degrees = math.degrees(angle)

    if _distance < 700 or agent.currentSpd < 500 or agent.goalPred is not None:
        goForward = abs(angle_degrees) <= 100


    if maintainSpeed:
        goForward = True

    if not goForward:
        expedite = True
        flips_enabled = True
        angle_degrees -= 180
        if angle_degrees < -180:
            angle_degrees += 360
        if angle_degrees > 180:
            angle_degrees -= 360

        angle = math.radians(angle_degrees)

    path_info = get_path_info(localTarget, angle_degrees)  # radius, c, distance
    if not kickoff and not agent.onWall:
        _distance = path_info[2]

    idealSpeed = clamp(maxPossibleSpeed, 0, math.ceil(_distance / tta))

    createTriangle(agent, target)
    if idealSpeed >= 200:
        if ruleOneCheck(agent):
            agent.setJumping(6, target=target)

    if goForward:
        throttle = 1
    else:
        throttle = -1

    if not goForward or fudging:
        if agent.onSurface and arrivalTime > 1.85:
            # if _distance > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500) * 2.2:
            if (
                    clamp(math.inf, 1, _distance - 160)
                    > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500)
                    * 1.85
            ):
                if abs(angle_degrees) <= clamp(5, 0, _distance / 1000):
                    if not agent.onWall and flips_enabled and goForward == agent.forward:
                        if not goForward:
                            agent.setHalfFlip()
                        else:
                            agent.setJumping(1)

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
                    2500 > agent.me.location[2] > 300
                    and (tta > 1.5 or _distance / agent.currentSpd > 1.5)
                    and (agent.forward == goForward)
            ):
                agent.setJumping(-1)
                # print("jumping off wall!")
            elif (
                    agent.me.location[2] <= 500
                    and not agent.demo_monster
                    and agent.currentHit.hit_type != 2
                    and (tta > 1.5 or _distance / agent.currentSpd > 1.5)
                    and (agent.forward == goForward)
            ):
                wallFlip = True

    boost = False

    steer, handbrake = rockSteer(angle, _distance, modifier=300, turnLimit=1)

    if not going_for_aerial and (40 < abs(angle_degrees) < 140) and floppies:
        if 250 > _distance > 30:
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
                abs(90 - angle_degrees) * 10 >= _distance > 30
                and agent.currentSpd <= 600
                and not maintainSpeed
                and not agent.dribbling
                and not demos
                and not agent.demo_monster
        ):
            handbrake = True
            # print(f"Scrambling! {agent.time}")
    # else:
    #     steer, handbrake = newSteer(angle)


    if not goForward and not agent.forward:
        steer = -steer

    if goForward != agent.forward:
        #if not agent.forward:
        steer = -steer

    if avoiding:
        steer = -steer

    nearTurnLimit = False
    turn_limiter = 10

    speed_limit = maxSpeedAdjustment(agent, localTarget, angle_degrees, _distance, path_info[1], fudging)
    if abs(angle_degrees) > 90:
        limit = max(agent.currentSpd, 600)
        if limit < speed_limit:
            speed_limit = limit

    if not kickoff and not maintainSpeed and not demos and not agent.demo_monster and not agent.dribbling:
        idealSpeed = clamp(speed_limit, 0, idealSpeed)
        # if agent.currentSpd > idealSpeed or abs(agent.currentSpd - idealSpeed) < turn_limiter:
        if speed_limit - agent.currentSpd <= 75:
            nearTurnLimit = True
            steer = 1 if steer > 0 else -1

    if agent.currentSpd > idealSpeed:
        # if going_for_aerial or len(agent.allies) > 0:
        required_decel = idealSpeed - agent.currentSpd
        braking_power = -3500 * tta
        coasting_power = -525 * tta
        mode = 0
        if going_for_aerial or (nearTurnLimit and not maintainSpeed):  # not agent.dribbling
            mode = 1

        if mode == 0:
            if agent.rotationNumber == 1 and (
                    _distance < 50
                    or tta < agent.fakeDeltaTime * 5
                    or nearTurnLimit
                    or agent.dribbling
                    #or brake_time(agent.currentSpd)+agent.fakeDeltaTime*4 > tta
                    or (braking_power - (agent.active_decel * 2) * -1) < agent.currentSpd
            ):
                # if _distance < 50 or tta < agent.fakeDeltaTime * 6 or agent.dribbling or (
                # braking_power - (agent.active_decel * 4) * -1) < agent.currentSpd:
                mode = 1
            elif agent.rotationNumber == 1 and agent.currentHit.shotlimit != None:
                if (
                        tta > (agent.currentHit.shotlimit + (agent.fakeDeltaTime * 3))
                        and agent.currentSpd * tta < _distance
                ):
                    mode = 0
                else:
                    mode = 1
            else:
                mode = 0
            # mode = 1

        if mode == 0:
            if braking_power + (3500 * agent.fakeDeltaTime * 2) < required_decel:
            #if brake_time(agent.currentSpd) + agent.fakeDeltaTime * 4 < tta:
                throttle = 0.1 if goForward else -0.1
            else:
                throttle = -1 if goForward else 1

        elif mode == 1:
            if required_decel < agent.active_decel:
                throttle = -1 if goForward else 1
            elif required_decel <= agent.coast_decel:
                if (
                        agent.currentSpd
                        - agent.coast_decel * (tta / agent.fakeDeltaTime)
                        <= 0
                ):
                    throttle = 0
                else:
                    throttle = -1 if goForward else 1
            else:
                throttle = 0.1 if goForward else -0.1

        else:
            print("error in drive controller!", agent.time)

    elif agent.currentSpd < idealSpeed:
        if (
                idealSpeed >= agent.currentSpd + boost_req
        ):  # or idealSpeed >= maxPossibleSpeed:
            if (
                    agent.me.boostLevel > 0
                    and agent.onSurface
                    and expedite
                    and agent.currentSpd < (maxPossibleSpeed - 50)
                    and goForward
                    and not nearTurnLimit
                    and idealSpeed >= 1000
                    and (inaccurateArrivalEstimatorBoostless(agent, target, onWall=agent.onWall, offset=-offset_dist) > tta)
            ):
                # print(f"setting boost to true {agent.time}")
                boost = True

        if agent.me.boostLevel > 0 and expedite:
            minFlipSpeed = maxPossibleSpeed - 500
        else:
            minFlipSpeed = 1075

        if (
                agent.currentSpd > minFlipSpeed
                and flips_enabled
                #and ((agent.currentHit != None and agent.currentHit.hit_type != 2) or agent.rotationNumber != 1)
        ):
            if (
                    clamp(math.inf, 1, _distance - 90)
                    > clamp(maxPossibleSpeed, agent.currentSpd, agent.currentSpd + 500)
                    * 1.85
                    or flippant
            ):
                if abs(angle_degrees) <= clamp(5, 0, _distance / 500):
                    if not agent.onWall or wallFlip:  # or not agent.wallShot:
                        if agent.onSurface:
                            if goForward:
                                agent.setJumping(1)
                                # print(f"pew pew? {flips_enabled} {agent.boostMonster}")
                            else:
                                agent.setHalfFlip()
                                # agent.stubbornessTimer = 1.7
                                # agent.stubborness = agent.stubbornessMax

    else:
        if goForward:
            throttle = 0.1
        else:
            throttle = -0.1

    handbrake_barrier = clamp(0.9, 0.5, agent.currentSpd / maxPossibleSpeed)

    # if nearTurnLimit and not maintainSpeed and not fudging and abs(angle_degrees) > 20:
    #     handbrake = True

    if handbrake:
        if abs(agent.me.avelocity[2]) < handbrake_barrier or agent.forward != goForward:
            handbrake = False
        if agent.currentSpd < speed_limit and not nearTurnLimit:
            handbrake = False

    if handbrake:
        boost = False

    if maintainSpeed or demos:  # or agent.demo_monster:
        handbrake = False
        throttle = 1
        if not agent.demo_monster and not demos:
            boost = False
            # print(f'setting boost false {agent.time}')

    if boost:
        if not agent.forward or not goForward:
            boost = False

    if kickoff:
        handbrake = False
        throttle = 1
        if agent.currentSpd < 2200:
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

        # if agent.closestEnemyToBall.onSurface:
        if agent.closestEnemyToBall.location[2] > 200:
            enemyOnWall = True
            # enemyOnGround = False
        else:
            enemyOnGround = True
        # else:
        #     if agent.closestEnemyToBall.boostLevel > 0:
        #         if agent.closestEnemyToBall.location[2] > 350:
        #             enemyInAir = True
        #         else:
        #             enemyOnGround = True
        #     else:
        #         enemyInAir = False
        #         enemyOnGround = True

        for i in range(0, agent.ballPred.num_slices):
            if i % 5 != 0:
                continue
            pred = agent.ballPred.slices[i]
            if pred.game_seconds - agent.gameInfo.seconds_elapsed <= 0:
                continue
            location = convertStructLocationToVector(pred)

            if (
                    isBallNearWall(pred, defaultDistance=250)
                    and location[2] > jumpshotLimit
            ):
                if enemyOnWall:
                    timeToTarget = enemyArrivalEstimator(
                        agent, agent.closestEnemyToBall, location
                    )

                if enemyOnGround:
                    timeToTarget, distance = enemyWallMovementEstimator(
                        agent.closestEnemyToBall, location, agent
                    )

                if timeToTarget < pred.game_seconds - agent.gameInfo.seconds_elapsed:
                    agent.enemyBallInterceptDelay = (
                            pred.game_seconds - agent.gameInfo.seconds_elapsed
                    )
                    agent.enemyTargetVec = location
                    found = True
                    agent.enemyPredTime = pred.game_seconds
                    agent.enemyTargetVel = convertStructVelocityToVector(
                        agent.ballPred.slices[i]
                    )
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
                        agent.enemyTargetVel = convertStructVelocityToVector(
                            agent.ballPred.slices[i]
                        )
                        # print(f"enemy Delay: {agent.enemyBallInterceptDelay}, my Delay: {agent.ballDelay} || {agent.contested}  ||  {agent.timid}")
                        break

            if enemyInAir:
                if location.data[2] <= agent.closestEnemyToBall.location.data[2] or (
                        location.data[2] >= agent.closestEnemyToBall.location.data[2]
                        and agent.closestEnemyToBall.velocity.data[2] > -50
                ):
                    # print(agent.closestEnemyToBall.velocity.data[2])
                    distance = (
                            findDistance(location, agent.closestEnemyToBall.location) - 150
                    )
                    _time = pred.game_seconds - agent.gameInfo.seconds_elapsed

                    wrong_intercept_time = inaccurateArrivalEstimatorHacked(
                        agent.closestEnemyToBall,
                        agent.closestEnemyToBall.location,
                        location,
                        agent.gravity,
                    )

                    if (
                            wrong_intercept_time
                            <= pred.game_seconds - agent.gameInfo.seconds_elapsed
                    ):
                        agent.enemyBallInterceptDelay = pred.game_seconds - agent.time
                        agent.enemyTargetVec = location
                        found = True
                        agent.enemyPredTime = pred.game_seconds
                        agent.enemyTargetVel = convertStructVelocityToVector(
                            agent.ballPred.slices[i]
                        )
                        print(f"Found aerial threat! {agent.time}")
                        print(
                            f"distance: {int(distance)} , time: {_time} , possible distance: {int(2300 * _time)}"
                        )
                        break

    if not found:
        agent.enemyBallInterceptDelay = 6
        agent.enemyTargetVec = convertStructLocationToVector(
            agent.ballPred.slices[agent.ballPred.num_slices - 2]
        )
        agent.enemyTargetVel = convertStructVelocityToVector(
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


# def find_pred_at_time(agent, _time):
#     t_offset = 1.0 / 120.0
#     pred = None
#     for i in range(0, agent.ballPred.num_slices):
#         if _time < agent.ballPred.slices[i].game_seconds + t_offset:
#             pred = agent.ballPred.slices[i]
#             break
#     return pred


def find_pred_at_time(agent, _time):
    start_time = agent.ballPred.slices[0].game_seconds
    approx_index = int(
        (_time - start_time) * 60
    )  # We know that there are 60 slices per second.
    if 0 <= approx_index < agent.ballPred.num_slices:
        return agent.ballPred.slices[approx_index]
    return None


def determine_if_shot_goalward(shot_vel: Vector, team: int):
    if shot_vel[1] * sign(team) > 5:
        return True
    return False


def calculate_delta_acceleration(
        displacement: Vector, initial_velocity: Vector, time: float, gravity: float
) -> Vector:
    # Adapated from dacoolone's tutorial
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
    if groundHit.time_difference() <= 0:
        return False
    offset = agent.reachLength  # if agent.team == 0 else agent.groundReachLength
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
    if jumpshotHit.time_difference() <= 0:
        return False
    offset = agent.reachLength
    if (
            grounder_cutoff < jumpshotHit.pred_vector[2] < jumper_cutoff
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
                    float32(agent.physics_tick),
                    np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                    np.array(agent.up.data, dtype=np.dtype(float)),
                    np.array(agent.me.location.data, dtype=np.dtype(float)),
                    float32(agent.defaultElevation),
                    float32(jumpshotHit.time_difference()),
                    float32(jumpshotHit.pred_vector[2]),
                    False,
                )
                jumpshotHit.jumpSim = jumpSim
                if (
                        abs(jumpSim[2] - jumpshotHit.pred_vector[2])
                        <= agent.ball_size
                ):

                    if jumpshotHit.time_difference() > jumpSim[3]:
                        #jumpshotHit.jumpSim = jumpSim
                        return True

    return False


def validate_double_jump_shot(
        agent, doubleJumpShotHit, jumper_cutoff, doublejump_cutoff
):
    if doubleJumpShotHit.time_difference() < 0:
        return False
    offset = agent.reachLength  # if agent.team == 0 else agent.groundReachLength
    if (
            jumper_cutoff < doubleJumpShotHit.pred_vector[2] <= doublejump_cutoff
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
                    float32(agent.physics_tick),
                    np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                    np.array(agent.up.data, dtype=np.dtype(float)),
                    np.array(agent.me.location.data, dtype=np.dtype(float)),
                    float32(agent.defaultElevation),
                    float32(doubleJumpShotHit.time_difference()),
                    float32(doubleJumpShotHit.pred_vector[2]),
                    True,
                )
                doubleJumpShotHit.jumpSim = jumpSim
                if (
                        abs(jumpSim[2] - doubleJumpShotHit.pred_vector[2])
                        <= agent.allowableJumpDifference
                ):

                    if doubleJumpShotHit.time_difference() > jumpSim[3]:
                        return True

    return False


def validate_wall_shot(agent, wallshot_hit, grounder_cutoff):
    pred_vec = wallshot_hit.pred_vector
    tth = wallshot_hit.time_difference()
    if tth <= 0:
        return False
    offset = agent.groundReachLength

    if isBallHittable_hit(wallshot_hit, agent, grounder_cutoff):
        if isBallHitNearWall(pred_vec, defaultDistance=grounder_cutoff):
            if agent.onWall:
                distance = findDistance(agent.me.location, pred_vec)
                timeToTarget = inaccurateArrivalEstimator(
                    agent, pred_vec, True, offset=offset
                )

                if timeToTarget <= tth:
                    agent.targetDistance = distance
                    agent.timeEstimate = timeToTarget
                    return True

            else:
                timeToTarget, distance, valid = new_ground_wall_estimator(
                    agent, pred_vec
                )
                if timeToTarget <= tth:
                    if valid:
                        agent.targetDistance = distance
                        agent.timeEstimate = timeToTarget
                        return True

    return False


def validate_aerial_shot(agent, aerial_shot: hit, aerial_min, doubleCutOff):
    pred_vec = aerial_shot.pred_vector
    pred_vel = aerial_shot.pred_vel
    target = aerial_shot.aim_target
    tth = aerial_shot.time_difference()
    offset = agent.reachLength
    center = Vector([0, 5500 * -sign(agent.team), 0])
    myGoal = Vector([0, 5200 * sign(agent.team), 0])
    if tth <= 0:
        return False

    if agent.me.boostLevel >= 1 or not agent.onSurface:
        if agent.me.velocity[2] > -50 or pred_vec[2] < agent.me.location[2]:
            if inaccurateArrivalEstimator(agent, pred_vec, False, offset=offset) < tth:

                aerial_accepted = False
                takeoff_tth = tth - agent.takeoff_speed
                # accel_req_limit = 1057
                accel_req_limit = agent.aerial_accel_limit

                if agent.onSurface and not agent.aerialsLimited:
                    if tth > agent.takeoff_speed:
                        if pred_vec[2] > doubleCutOff + agent.min_aerial_buffer:
                            if agent.me.location[1] * sign(agent.team) > pred_vec[
                                1
                            ] * sign(agent.team):

                                # if not agent.onWall:
                                #     accel_req_limit = 1057

                                aerial_jump_sim = jumpSimulatorNormalizingJit(
                                    float32(agent.gravity),
                                    float32(agent.physics_tick),
                                    np.array(
                                        agent.me.velocity.data, dtype=np.dtype(float)
                                    ),
                                    np.array(agent.up.data, dtype=np.dtype(float)),
                                    np.array(
                                        agent.me.location.data, dtype=np.dtype(float)
                                    ),
                                    float32(agent.defaultElevation),
                                    float32(agent.takeoff_speed),
                                    float32(pred_vec[2]),
                                    True,
                                )
                                aerial_shot.jumpSim = aerial_jump_sim

                                delta_a = calculate_delta_acceleration(
                                    target - Vector(aerial_jump_sim[4]),
                                    Vector(aerial_jump_sim[5]),
                                    takeoff_tth,
                                    agent.gravity,
                                )

                                if delta_a.magnitude() < accel_req_limit:
                                    total_req_delta_a = (
                                            delta_a.magnitude() * takeoff_tth
                                    )
                                    if (
                                            total_req_delta_a
                                            < agent.calculate_delta_velocity(takeoff_tth)
                                    ):
                                        # if delta_a.magnitude() < agent.calculate_delta_velocity(
                                        #     takeoff_tth
                                        # ):
                                        if (
                                                agent.me.velocity + delta_a
                                        ).magnitude() < maxPossibleSpeed:
                                            aerial_accepted = True

                                ideal_velocity = Vector(aerial_jump_sim[5]) + delta_a
                                if ideal_velocity.magnitude() >= maxPossibleSpeed:
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
                            1000, 750, 1060 - (((6 - tth) * 0.1)) * 100,
                        )
                        # accel_req_limit = clamp(
                        #     1060, 850, 1060 - (((6 - tth) * 0.05)) * 100,
                        # )
                        # accel_req_limit = 1057

                        if delta_a.magnitude() <= accel_req_limit:
                            total_req_delta_a = delta_a.magnitude() * tth
                            if total_req_delta_a < agent.calculate_delta_velocity(tth):
                                aerial_accepted = True

                if aerial_accepted:
                    return True

    return False


def findHits(agent, grounder_cutoff, jumpshot_cutoff, doubleCutOff, resolution=3):
    ground_shot = None
    jumpshot = None
    wall_shot = None
    doubleJumpShot = None
    ballInGoal = None
    aerialShot = None
    catchCanidate = None
    in_goalbox = in_goal_check(agent)
    agent.first_hit = None

    leftPost = Vector([893 * sign(agent.team), 5120 * -sign(agent.team), 0])
    center = Vector([0, 5500 * -sign(agent.team), 0])
    rightPost = Vector([893 * -sign(agent.team), 5120 * -sign(agent.team), 0])
    myGoal = Vector([0, 5200 * sign(agent.team), 0])

    o_max_y = 5350
    d_max_y = 5210
    # d_max_y = 5200

    offset = agent.groundReachLength
    ground_offset = agent.groundReachLength
    reposition = False

    aboveThreshold = False
    # testing
    checkAngles = len(agent.allies) < 1

    grounded = True

    agent.goalPred = None
    agent.scorePred = None
    pred = agent.ballPred.slices[0]
    aerialsValid = True

    if agent.demo_monster or agent.me.demolished:
        ground_shot = hit(
            agent.time,
            agent.time + 6,
            0,
            convertStructLocationToVector(
                agent.ballPred.slices[agent.ballPred.num_slices - 1]
            ),
            convertStructVelocityToVector(
                agent.ballPred.slices[agent.ballPred.num_slices - 1]
            ),
            False,
            6,
            # [agent.enemyGoalLocations[0],agent.enemyGoalLocations[2]]
            agent.team,
        )
        agent.first_hit = ground_shot

        return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot

    early_exit = len(agent.allies) > 1
    scorable = None

    start_time = agent.time
    if agent.touch.player_index == agent.index:
        start_time = agent.touch.time_seconds + 1
    for i in range(0, agent.ballPred.num_slices):
        if i > 30 and not i % resolution:
            continue

        pred = agent.ballPred.slices[i]
        tth = pred.game_seconds - agent.gameInfo.seconds_elapsed

        if tth <= 0:
            continue

        pred_vec = convertStructLocationToVector(pred)
        pred_vel = convertStructVelocityToVector(pred)
        offensive = pred_vec[1] * sign(agent.team) < 0

        if grounded:
            if pred_vec[1] > grounder_cutoff:
                agent.grounded_timer = tth
                grounded = False

        grounder = False
        if not aboveThreshold:
            if pred.physics.location.z > doubleCutOff:
                aboveThreshold = True

        if aboveThreshold:
            if pred.physics.location.z <= doubleCutOff:
                aerialsValid = False

        if not early_exit or agent.first_hit is None:

            if (
                    findDistance(agent.me.location, pred_vec) - agent.aerial_reach
            ) <= 2300 * tth:
                #if checkAngles:
                scorable = is_shot_scorable(agent.team, pred_vec)

                if ground_shot is None or wall_shot is None:
                    if isBallHittable(pred, agent, grounder_cutoff):
                        wallshot = isBallNearWall(pred)
                        # testing
                        if not wallshot or (pred_vec[2] <= grounder_cutoff):
                            grounder = True
                            if ground_shot is None:
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
                                        offset=ground_offset,
                                        reposition=reposition
                                    )
                                else:
                                    timeToTarget = new_ground_wall_estimator(
                                        agent, pred_vec
                                    )[0]

                                if timeToTarget <= tth:
                                    # testing
                                    if (scorable or agent.first_hit == None or not checkAngles):
                                        ground_shot = hit(
                                            agent.time,
                                            pred.game_seconds,
                                            0,
                                            pred_vec,
                                            convertStructVelocityToVector(pred),
                                            True,
                                            timeToTarget,
                                            agent.team,
                                            scorable=scorable,
                                        )
                                        if agent.first_hit is None:
                                            agent.first_hit = ground_shot

                                        if checkAngles and not scorable:
                                            ground_shot = None

                                    # if early_exit:
                                    #     return (
                                    #         ground_shot,
                                    #         jumpshot,
                                    #         wall_shot,
                                    #         doubleJumpShot,
                                    #         aerialShot,
                                    #     )
                        else:
                            if (
                                    wall_shot is None
                                    and wallshot
                                    and not in_goalbox
                            ):
                                if offensive or pred_vel[1] * sign(agent.team) < 10:
                                    _wall = which_wall(pred_vec)
                                    if not (
                                            (agent.team == 0 and _wall == 0)
                                            or (agent.team == 1 and _wall == 2)
                                    ):
                                        if agent.onWall:
                                            distance = findDistance(
                                                agent.me.location, pred_vec
                                            )
                                            timeToTarget = inaccurateArrivalEstimator(
                                                agent, pred_vec, True, offset=ground_offset,reposition=reposition
                                            )

                                            if timeToTarget <= tth:
                                                if (
                                                        scorable
                                                        or agent.first_hit is None
                                                        or not checkAngles
                                                ):
                                                    wall_shot = hit(
                                                        agent.time,
                                                        pred.game_seconds,
                                                        2,
                                                        pred_vec,
                                                        convertStructVelocityToVector(pred),
                                                        True,
                                                        timeToTarget,
                                                        # [agent.enemyGoalLocations[0],agent.enemyGoalLocations[2]],
                                                        agent.team,
                                                        scorable=scorable,
                                                    )
                                                    if agent.first_hit is None:
                                                        agent.first_hit = wall_shot
                                                        if checkAngles and not scorable:
                                                            wall_shot = None
                                                    agent.targetDistance = distance
                                                    agent.timeEstimate = timeToTarget
                                                    # if early_exit and not agent.dribbler:
                                                    #     return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot

                                        else:
                                            if wallshot:
                                                (
                                                    timeToTarget,
                                                    distance,
                                                    valid,
                                                ) = new_ground_wall_estimator(
                                                    agent, pred_vec
                                                )
                                                if timeToTarget <= tth:
                                                    if valid:
                                                        if (
                                                                scorable
                                                                or agent.first_hit is None
                                                                or not checkAngles
                                                        ):
                                                            wall_shot = hit(
                                                                agent.time,
                                                                pred.game_seconds,
                                                                2,
                                                                pred_vec,
                                                                convertStructVelocityToVector(
                                                                    pred
                                                                ),
                                                                True,
                                                                timeToTarget,
                                                                # [agent.enemyGoalLocations[0],agent.enemyGoalLocations[2]],
                                                                agent.team,
                                                                scorable=scorable,
                                                            )
                                                            if agent.first_hit is None:
                                                                agent.first_hit = wall_shot
                                                                if (
                                                                        checkAngles
                                                                        and not scorable
                                                                ):
                                                                    wall_shot = None
                                                            agent.targetDistance = distance
                                                            agent.timeEstimate = (
                                                                timeToTarget
                                                            )

                if (
                        jumpshot is None
                        and pred.game_seconds > start_time
                        and not agent.aerial_hog
                ):
                    if (
                            grounder_cutoff < pred.physics.location.z <= jumpshot_cutoff
                            and tth >= agent.fakeDeltaTime * 6
                    ):

                        if isBallHittable(agent.ballPred.slices[i], agent, jumpshot_cutoff):
                            if not agent.onWall:
                                distance = distance2D(pred_vec, agent.me.location)
                                timeToTarget = inaccurateArrivalEstimator(
                                    agent, pred_vec, False, offset=offset,reposition=reposition
                                )
                            else:
                                timeToTarget, distance, valid = new_ground_wall_estimator(
                                    agent, pred_vec
                                )

                            if timeToTarget <= tth:
                                jumpSim = jumpSimulatorNormalizingJit(
                                    float32(agent.gravity),
                                    float32(agent.physics_tick),
                                    np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                                    np.array(agent.up.data, dtype=np.dtype(float)),
                                    np.array(agent.me.location.data, dtype=np.dtype(float)),
                                    float32(agent.defaultElevation),
                                    float32(tth),
                                    float32(pred.physics.location.z),
                                    False,
                                )

                                # print(f"{jumpSim[2],pred.physics.location.z,tth}")
                                if (
                                        abs(jumpSim[2] - pred.physics.location.z)
                                        <= agent.ball_size
                                ):
                                    # if jumpSim[2] + agent.allowableJumpDifference >= pred.physics.location.z:
                                    if tth > jumpSim[3]:
                                        if (
                                                scorable
                                                or agent.first_hit is None
                                                or not checkAngles
                                        ):

                                            jumpshot = hit(
                                                agent.time,
                                                pred.game_seconds,
                                                1,
                                                pred_vec,
                                                convertStructVelocityToVector(pred),
                                                True,
                                                timeToTarget,
                                                # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                                                agent.team,
                                                jumpSim=jumpSim,
                                                scorable=scorable,
                                            )
                                            if agent.first_hit is None:
                                                agent.first_hit = jumpshot
                                                if checkAngles and not scorable:
                                                    jumpshot = None

                if agent.DoubleJumpShotsEnabled:
                    if (
                            doubleJumpShot is None
                            and pred.game_seconds > start_time
                            and not agent.aerial_hog
                    ):
                        if (
                                jumpshot_cutoff < pred_vec[2] <= doubleCutOff
                                and (
                                pred_vec[2] < 500
                                or not butterZone(pred_vec)
                                or pred_vec.data[1] * sign(agent.team) > 0
                        )
                                and tth >= 0.2
                        ):
                            if isBallHittable(
                                    agent.ballPred.slices[i], agent, doubleCutOff
                            ):
                                if not agent.onWall:
                                    distance = distance2D(pred_vec, agent.me.location)
                                    timeToTarget = inaccurateArrivalEstimator(
                                        agent, pred_vec, False, offset=offset,reposition=reposition
                                    )
                                else:
                                    (
                                        timeToTarget,
                                        distance,
                                        valid,
                                    ) = new_ground_wall_estimator(agent, pred_vec)
                                # filtering out predictions that would likely hit top bar on offfense
                                if pred_vec[1] * -sign(agent.team) > 0:
                                    if butterZone(pred_vec):
                                        if pred_vec[2] > 880 - (93.5 * 2):
                                            timeToTarget = 100  # setting simulated arrival time to fake number to dissuade attempt

                                if timeToTarget <= tth:
                                    # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z)
                                    jumpSim = jumpSimulatorNormalizingJit(
                                        float32(agent.gravity),
                                        float32(agent.physics_tick),
                                        np.array(
                                            agent.me.velocity.data, dtype=np.dtype(float)
                                        ),
                                        np.array(agent.up.data, dtype=np.dtype(float)),
                                        np.array(
                                            agent.me.location.data, dtype=np.dtype(float)
                                        ),
                                        float32(agent.defaultElevation),
                                        float32(tth),
                                        float32(pred.physics.location.z),
                                        True,
                                    )
                                    # print(f"target height: {pred_vec[2]} simulated max height: {jumpSim[2]}")

                                    # print(f"{jumpSim[2],pred.physics.location.z,tth}")
                                    if (
                                            abs(jumpSim[2] - pred.physics.location.z)
                                            <= agent.allowableJumpDifference
                                    ):
                                        # if jumpSim[2] + agent.allowableJumpDifference >= pred.physics.location.z:
                                        if tth > jumpSim[3]:
                                            if (
                                                    scorable
                                                    or agent.first_hit is None
                                                    or not checkAngles
                                            ):
                                                doubleJumpShot = hit(
                                                    agent.time,
                                                    pred.game_seconds,
                                                    4,
                                                    pred_vec,
                                                    convertStructVelocityToVector(pred),
                                                    True,
                                                    timeToTarget,
                                                    # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                                                    agent.team,
                                                    jumpSim=jumpSim,
                                                    scorable=scorable,
                                                )
                                                if agent.first_hit is None:
                                                    agent.first_hit = doubleJumpShot
                                                    if checkAngles and not scorable:
                                                        doubleJumpShot = None

                if (
                        aerialShot is None
                        and agent.first_hit is None
                        and agent.goalPred is None
                        and agent.scorePred is None
                        and agent.aerialsEnabled
                        and not in_goalbox
                        and (agent.onSurface or tth < agent.aerial_timer_limit)
                ):
                    aerial_jump_sim = None
                    if (
                            pred_vec[2] < 760
                            or abs(pred_vec[0]) > 2000
                            or pred_vec[2]
                            < (5120 - (pred_vec[1] * -sign(agent.team))) * agent.aerial_slope
                            or agent.aerial_hog
                    ):

                        if (
                                (agent.me.boostLevel >= 1 or not agent.onSurface)
                                and (not checkAngles or scorable)
                        ):

                            if (
                                    agent.me.velocity[2] > -50
                                    or pred_vec[2] < agent.me.location[2]
                            ):
                                if (
                                        inaccurateArrivalEstimator(
                                            agent, pred_vec, False, offset=offset,reposition=reposition
                                        )
                                        < tth
                                ):

                                    if distance2D(pred_vec, myGoal) < 3000 or (
                                            agent.me.location[1] * sign(agent.team) < pred_vec[1] * sign(
                                            agent.team) and not offensive):
                                        target = aim_wallshot_naive_hitless(
                                            agent,
                                            pred_vec,
                                            pred_vel,
                                            agent.aerial_reach * 0.7,
                                        )

                                    # elif (
                                    #         distance2D(pred_vec, center) > 2000
                                    #         or pred_vec[2] < 760
                                    # ):
                                    else:
                                        target = get_aim_vector(
                                            agent,
                                            center + Vector([0, 0, pred_vec[2]]),
                                            pred_vec,
                                            pred_vel,
                                            agent.aerial_reach * 0.8,
                                        )[0]
                                    # else:
                                    #     target = get_aim_vector(
                                    #         agent,
                                    #         Vector([0, 5120 * -sign(agent.team), 0]),
                                    #         pred_vec,  # + Vector([0, 0, 25]),
                                    #         pred_vel,
                                    #         agent.aerial_reach * 0.85,
                                    #     )[0]

                                    aerial_accepted = False
                                    takeoff_tth = tth - agent.takeoff_speed
                                    accel_req_limit = agent.aerial_accel_limit
                                    if agent.onSurface and not agent.aerialsLimited:
                                        # if tth > 0.28 and (
                                        if (
                                                tth > agent.takeoff_speed
                                                and abs(agent.me.location[1]) < 5140
                                        ):
                                            if (
                                                    pred_vec[2]
                                                    > doubleCutOff + agent.min_aerial_buffer
                                            ):  # and tth < agent.enemyBallInterceptDelay:
                                                # testing
                                                if agent.me.location[1] * sign(
                                                        agent.team
                                                ) > pred_vec[1] * sign(agent.team):

                                                    # if not agent.onWall:
                                                    #     accel_req_limit = 1057

                                                    aerial_jump_sim = jumpSimulatorNormalizingJit(
                                                        float32(agent.gravity),
                                                        float32(agent.physics_tick),
                                                        np.array(
                                                            agent.me.velocity.data,
                                                            dtype=np.dtype(float),
                                                        ),
                                                        np.array(
                                                            agent.up.data,
                                                            dtype=np.dtype(float),
                                                        ),
                                                        np.array(
                                                            agent.me.location.data,
                                                            dtype=np.dtype(float),
                                                        ),
                                                        float32(agent.defaultElevation),
                                                        float32(agent.takeoff_speed),
                                                        float32(pred.physics.location.z),
                                                        True,
                                                    )

                                                    delta_a = calculate_delta_acceleration(
                                                        target - Vector(aerial_jump_sim[4]),
                                                        Vector(aerial_jump_sim[5]),
                                                        takeoff_tth,
                                                        agent.gravity,
                                                    )

                                                    if (
                                                            delta_a.magnitude()
                                                            < accel_req_limit
                                                    ):
                                                        total_req_delta_a = (
                                                                delta_a.magnitude()
                                                                * takeoff_tth
                                                        )
                                                        if (
                                                                total_req_delta_a + 5
                                                                < agent.calculate_delta_velocity(
                                                            takeoff_tth
                                                        )
                                                        ):
                                                            if (
                                                                    agent.me.velocity + delta_a
                                                            ).magnitude() < maxPossibleSpeed:
                                                                aerial_accepted = True

                                                    ideal_velocity = (
                                                            Vector(aerial_jump_sim[5]) + delta_a
                                                    )
                                                    if (
                                                            ideal_velocity.magnitude()
                                                            >= maxPossibleSpeed
                                                    ):
                                                        aerial_accepted = False

                                    else:
                                        if agent.me.location[2] > 500:

                                            if pred_vec[2] > agent.aerial_min:
                                                delta_a = calculate_delta_acceleration(
                                                    target - agent.me.location,
                                                    agent.me.velocity,
                                                    tth,
                                                    agent.gravity,
                                                )

                                                if delta_a.magnitude() <= accel_req_limit:
                                                    req_delta_v = delta_a.magnitude() * tth
                                                    if (
                                                            req_delta_v + 10
                                                            < agent.calculate_delta_velocity(
                                                        tth
                                                    )
                                                    ):
                                                        aerial_accepted = True
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
                                        # modded_loc = pred_vec.scale(1)
                                        # modded_loc.data[0], modded_loc.data[2] = (
                                        #     modded_loc.data[2],
                                        #     modded_loc.data[0],
                                        # )
                                        #
                                        # modded_left = agent.enemyGoalLocations[0].scale(1)
                                        # modded_right = agent.enemyGoalLocations[2].scale(1)

                                        # modded_left.data[0] = 0
                                        # modded_right.data[0] = 642
                                        if (
                                                scorable
                                                or agent.first_hit is None
                                                or not checkAngles
                                        ):

                                            _aerial = agent.aerialGetter(pred, target, tth)

                                            aerialShot = hit(
                                                agent.time,
                                                pred.game_seconds,
                                                5,
                                                pred_vec,
                                                convertStructVelocityToVector(pred),
                                                True,
                                                tth,
                                                # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                                                agent.team,
                                                jumpSim=aerial_jump_sim,
                                                aerialState=_aerial,
                                                aim_target=target,
                                                scorable=scorable,
                                            )
                                            if agent.first_hit is None:
                                                agent.first_hit = aerialShot
                                                if checkAngles and not scorable:
                                                    aerialShot = None

        precariousSituation = False
        if agent.team == 0:
            if pred.physics.location.y <= -d_max_y:
                precariousSituation = True
        elif agent.team == 1:
            if pred.physics.location.y >= d_max_y:
                precariousSituation = True

        if agent.scorePred is None:
            if not precariousSituation:
                if abs(pred.physics.location.y) >= o_max_y:
                    # (self, location, _time):
                    agent.scorePred = predictionStruct(pred_vec, pred.game_seconds)

        if precariousSituation:
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
                offset=offset,reposition=reposition
            )
            if (
                    agent.ballPred.slices[i].physics.location.z <= grounder_cutoff
                    and ground_shot is None
            ):
                ground_shot = hit(
                    agent.time,
                    agent.ballPred.slices[i].game_seconds,
                    0,
                    convertStructLocationToVector(agent.ballPred.slices[i]),
                    convertStructVelocityToVector(agent.ballPred.slices[i]),
                    False,
                    timeToTarget,
                    # [agent.enemyGoalLocations[0],agent.enemyGoalLocations[2]],
                    agent.team,
                    scorable=scorable,
                )
                if agent.first_hit is None:
                    agent.first_hit = ground_shot

            elif (
                    agent.ballPred.slices[i].physics.location.z <= jumpshot_cutoff
                    and jumpshot is None
            ):
                # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z, doubleJump=False)
                jumpSim = jumpSimulatorNormalizingJit(
                    float32(agent.gravity),
                    float32(agent.physics_tick),
                    np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                    np.array(agent.up.data, dtype=np.dtype(float)),
                    np.array(agent.me.location.data, dtype=np.dtype(float)),
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
                    # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                    agent.team,
                    jumpSim=jumpSim,
                    scorable=scorable,
                )
                if agent.first_hit is None:
                    agent.first_hit = jumpshot

            else:
                if agent.DoubleJumpShotsEnabled and doubleJumpShot is None:
                    # jumpSim = jumpSimulatorNormalizing(agent, tth, pred.physics.location.z)
                    jumpSim = jumpSimulatorNormalizingJit(
                        float32(agent.gravity),
                        float32(agent.physics_tick),
                        np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                        np.array(agent.up.data, dtype=np.dtype(float)),
                        np.array(agent.me.location.data, dtype=np.dtype(float)),
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
                        # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                        agent.team,
                        jumpSim=jumpSim,
                        scorable=scorable,
                    )
                    if agent.first_hit is None:
                        agent.first_hit = doubleJumpShot

            # agent.goalPred = agent.ballPred.slices[i]
            agent.goalPred = predictionStruct(
                pred_vec, agent.ballPred.slices[i].game_seconds
            )
            if (
                    ground_shot is None
                    and jumpshot is None
                    and wall_shot is None
                    and doubleJumpShot is None
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
                        # [agent.enemyGoalLocations[0],agent.enemyGoalLocations[2]],
                        agent.team,
                        scorable=scorable,
                    )
                    if agent.first_hit is None:
                        agent.first_hit = ground_shot
                elif (
                        agent.groundCutOff < pred_vec[2] < agent.doubleJumpLimit
                ):
                    jumpSim = jumpSimulatorNormalizingJit(
                        float32(agent.gravity),
                        float32(agent.physics_tick),
                        np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                        np.array(agent.up.data, dtype=np.dtype(float)),
                        np.array(agent.me.location.data, dtype=np.dtype(float)),
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
                        # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                        agent.team,
                        jumpSim=jumpSim,
                        scorable=scorable,
                    )
                    if agent.first_hit is None:
                        agent.first_hit = jumpshot

                else:

                    if agent.DoubleJumpShotsEnabled:
                        jumpSim = jumpSimulatorNormalizingJit(
                            float32(agent.gravity),
                            float32(agent.physics_tick),
                            np.array(agent.me.velocity.data, dtype=np.dtype(float)),
                            np.array(agent.up.data, dtype=np.dtype(float)),
                            np.array(agent.me.location.data, dtype=np.dtype(float)),
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
                            # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
                            agent.team,
                            jumpSim=jumpSim,
                            scorable=scorable,
                        )
                        if agent.first_hit is None:
                            agent.first_hit = doubleJumpShot
            if grounded:
                agent.grounded_timer = tth
                grounded = False
            # testing
            # return ground_shot, jumpshot, wall_shot, doubleJumpShot, aerialShot

    if (
            ground_shot is None
            and jumpshot is None
            and wall_shot is None
            and doubleJumpShot is None
    ):
        ground_shot = hit(
            agent.time,
            agent.time + 6,
            0,
            convertStructLocationToVector(agent.ballPred.slices[i]),
            convertStructVelocityToVector(agent.ballPred.slices[i]),
            False,
            6,
            # [agent.enemyGoalLocations[0], agent.enemyGoalLocations[2]],
            agent.team,
            scorable=scorable,
        )
        if agent.first_hit is None:
            agent.first_hit = ground_shot

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


def inaccurateArrivalEstimatorHacked(
        phys_obj, starting_loc, destination, gravity, offset=140
):
    distance = clamp(math.inf, 0.00001, distance2D(starting_loc, destination) - offset)

    moreAccurateEstimation = timeWithAccelAgentless(
        991.66667,
        abs(phys_obj.velocity.magnitude()),
        phys_obj.boostLevel,
        distance,
        1 / 60,
        33.334 / 60,
        gravity,
        False,
    )

    return moreAccurateEstimation

# def enemyArrivalEstimator(agent, phys_obj, destination):
#     distance = clamp(
#         math.inf, 0.00001, findDistance(phys_obj.location, destination) - 180,
#     )
#
#     enemy_agent = {}
#     #moreAccurateEstimation = calcEnemyTimeWithAcceleration(agent, distance, phys_obj)
#     return moreAccurateEstimation
#
#
# def calcEnemyTimeWithAcceleration(agent, distance, enemyPhysicsObject):
#     estimatedSpd = abs(enemyPhysicsObject.velocity.magnitude())
#     estimatedTime = 0
#     distanceTally = 0
#     boostAmount = enemyPhysicsObject.boostLevel
#     boostingCost = 33.334 * agent.deltaTime
#     # print("enemy started")
#     while distanceTally < distance and estimatedTime < 6:
#         if estimatedSpd < maxPossibleSpeed:
#             acceleration = getNaturalAccelerationJitted(
#                 estimatedSpd, agent.gravity, False
#             )
#             if boostAmount > 0:
#                 acceleration += 991.667
#                 boostAmount -= boostingCost
#             if acceleration > 0:
#                 estimatedSpd += acceleration * agent.deltaTime
#             distanceTally += estimatedSpd * agent.deltaTime
#             estimatedTime += agent.deltaTime
#         else:
#             distanceTally += estimatedSpd * agent.deltaTime
#             estimatedTime += agent.deltaTime
#
#     # print("enemy ended")
#     return estimatedTime

def inaccurateArrivalEstimator(agent, destination, onWall=False, offset=120, reposition=False):
    bonus_time = 0
    start_loc = agent.me.location
    agent_spd = agent.currentSpd
    wall_value = agent.onWall
    if not agent.onSurface:
        bonus_time = agent.on_ground_estimate - agent.time
        start_loc = agent.collision_location
        agent_spd = agent.simulated_velocity.magnitude()
        wall_value = agent.wall_landing

    if onWall:
        distance = clamp(
            math.inf, 0.00001, findDistance(start_loc, destination) - offset
        )
    else:
        distance = clamp(math.inf, 0.00001, distance2D(start_loc, destination) - offset)
        if reposition and agent.goalPred is None :
            _direction = (agent.enemyGoalLocations[1] - destination.flatten()).normalize()
            new_destination = destination + _direction.scale(offset)
            distance = clamp(math.inf, 0.00001, distance2D(start_loc, new_destination))

        #if agent.team == 0:
        # if distance > 0.00001:
        #     vel_target_alignment = angleBetweenVectors(agent.me.velocity.flatten(), destination.flatten()-agent.me.location.flatten())
        #     braking_time = brake_time(agent.currentSpd)
        #     if agent.forward:
        #         if vel_target_alignment >= 90:
        #             bonus_time += braking_time * ((vel_target_alignment-90)/90)
        #     else:
        #         if vel_target_alignment <= 90:
        #             bonus_time += braking_time * (vel_target_alignment / 90)

    moreAccurateEstimation = timeWithAccelAgentless(
        agent.boostAccelerationRate,
        agent_spd,
        agent.me.boostLevel,
        distance,
        agent.fakeDeltaTime,
        agent.boostConsumptionRate,
        agent.gravity,
        wall_value,
    )

    return moreAccurateEstimation + bonus_time


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
        agent.boostAccelerationRate,
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
        math.inf, 0.00001, findDistance(phys_obj.location, destination) - 160,
    )
    moreAccurateEstimation = calcEnemyTimeWithAcceleration(agent, distance, phys_obj)
    return moreAccurateEstimation


def calcEnemyTimeWithAcceleration(agent, distance, enemyPhysicsObject):
    estimatedSpd = abs(enemyPhysicsObject.velocity.magnitude())
    estimatedTime = 0
    distanceTally = 0
    boostAmount = enemyPhysicsObject.boostLevel
    boostingCost = 33.334 * agent.deltaTime
    # print("enemy started")
    while distanceTally < distance and estimatedTime < 6:
        if estimatedSpd < maxPossibleSpeed:
            acceleration = getNaturalAccelerationJitted(
                estimatedSpd, agent.gravity, False
            )
            if boostAmount > 0:
                acceleration += 991.667
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
            agent.boostAccelerationRate,
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


def lerp(v0, v1, t):  # linear interpolation
    return (1 - t) * v0 + t * v1


@jit(float32(float32, float32, boolean), nopython=True)
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
@jit(float32(float32, float32, float32, float32, float32, float32, float32, boolean), nopython=True)
def timeWithAccelAgentless(
        accel, estimatedSpd, boostAmount, distance, fakeDelta, boostingCost, gravity, onWall
):
    estimatedTime = 0
    distanceTally = 0
    flipped = 2
    while distanceTally < distance and estimatedTime < 6:
        flipped += fakeDelta
        if estimatedSpd < 2300:
            acceleration = getNaturalAccelerationJitted(estimatedSpd, gravity, onWall)
            if boostAmount > 0:
                acceleration += accel
                boostAmount -= boostingCost
            else:
                if (
                        flipped > 2
                        and (distance - distanceTally) > clamp(2300, 0.0001, estimatedSpd + 500) * 1.85
                        and not onWall
                        and estimatedSpd > 1075
                ):
                    flipped = 0
                    estimatedSpd = clamp(2300, 1, estimatedSpd + 500)
            if acceleration > 0:
                estimatedSpd = clamp(
                    2300, 0.0001, estimatedSpd + (acceleration * fakeDelta)
                )
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta
        else:
            distanceTally += estimatedSpd * fakeDelta
            estimatedTime += fakeDelta

    return estimatedTime


@jit(
    typeof(np.array([float32(1.1), float32(1.1), float32(1.1)], dtype=np.dtype(float)))(
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float)))
    ),
    nopython=True
)
def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


@jit(
    typeof(
        (
                float32(1),
                float32(1),
                float32(1),
                float32(1),
                np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float)),
                np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float)),
                True,
        )
    )(
        float32,
        float32,
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float))),
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float))),
        typeof(np.array([float32(1), float32(1), float32(1)], dtype=np.dtype(float))),
        float32,
        float32,
        float32,
        typeof(False),
    ),
    cache=True,
)
def jumpSimulatorNormalizingJit(
        gravity,
        fakeDeltaTime,
        velocity_np,
        local_up_np,
        current_position_np,
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
    simTime = float(0)
    firstJumpTimer = float(0)
    secondJumpTimer = float(0)
    simulated_position = current_position_np
    _gravity = np.array([0, 0, gravity])

    estimatedVelocity = np.linalg.norm(velocity_np)

    heightMax = float32(current_position_np[2])
    maxHeightTime = float32(0)

    targetHeightTimer = float32(0)

    firstPauseTimer = 0
    secondPauseTimer = 0

    while simTime < simTimeMax:
        # upwardsVelocity = 0
        if simTime == 0:
            # velocity_np += local_up_np * initialJumpVel
            np.add(velocity_np, local_up_np * initialJumpVel, velocity_np)

        if simTime < stickyTimer:
            # velocity_np += local_up_np * (stickyforce * fakeDeltaTime)
            np.add(
                velocity_np, local_up_np * (stickyforce * fakeDeltaTime), velocity_np
            )

        if simTime < 0.2 and simTime < simTimeMax:
            # velocity_np += local_up_np * (jumpHoldBonusVelocity * fakeDeltaTime)
            np.add(
                velocity_np,
                local_up_np * (jumpHoldBonusVelocity * fakeDeltaTime),
                velocity_np,
            )

        else:
            if doubleJump:
                if not secondJumped:
                    velocity_np += local_up_np * secondJumpVel
                    secondJumped = True

        # velocity_np += _gravity * fakeDeltaTime
        np.add(velocity_np, _gravity * fakeDeltaTime, velocity_np)

        estimatedVelocity = np.linalg.norm(velocity_np)
        if estimatedVelocity > 2300:
            velocity_np = np.multiply(
                velocity_np / np.sqrt(np.sum(velocity_np ** 2)), 2300
            )

        # simulated_position += velocity_np*fakeDeltaTime
        np.add(simulated_position, velocity_np * fakeDeltaTime, simulated_position)

        simTime += fakeDeltaTime

        if simulated_position[2] > heightMax:
            heightMax = simulated_position[2] * 1
            maxHeightTime = simTime * 1

        if targetHeightTimer == 0:
            if simulated_position[2] >= targetHeight:
                targetHeightTimer = simTime

        if simulated_position[2] < heightMax:
            break

    return (
        float32(targetHeight),
        float32(targetHeightTimer),
        float32(heightMax),
        float32(maxHeightTime - fakeDeltaTime),
        simulated_position,
        velocity_np,
        doubleJump,
    )


def enemy_float_simulation(car_obj, current_time, tick_length=6):
    car_elevation = 17
    tick_duration = 1/120
    default_gravity = -650
    x_limit = 4096 - car_elevation
    y_limit = 5120 - car_elevation
    ground_limit = car_elevation
    ceiling_limit = 2044 - car_elevation
    collision_timer = 0
    collision_location = Vector([0, 0, 0])
    simulated_location = car_obj.location.scale(1)
    simulated_velocity = car_obj.velocity.scale(1)
    simulated_time = 0
    sim_frames = []

    while (
            simulated_time < 10
    ):
        simulated_time += tick_duration * tick_length
        simulated_velocity = simulated_velocity + Vector([0, 0, default_gravity]).scale(
            tick_duration * tick_length
        )
        if simulated_velocity.magnitude() > 2300:
            simulated_velocity = simulated_velocity.normalize().scale(2300)
        simulated_location = simulated_location + simulated_velocity.scale(
            tick_duration * tick_length
        )
        sim_frames.append([simulated_location, simulated_velocity, current_time + simulated_time])


        if simulated_location[2] >= ceiling_limit:
            break
        elif simulated_location[2] <= ground_limit:
            break

        elif simulated_location[0] <= -x_limit:
            break

        elif simulated_location[0] >= x_limit:
            break

        elif simulated_location[1] <= -y_limit:
            break

        elif simulated_location[1] >= y_limit:
            break

    car_obj.collision_timer = simulated_time
    car_obj.on_ground_estimate = current_time + simulated_time
    car_obj.collision_location = simulated_location
    car_obj.simulated_velocity = simulated_velocity
    car_obj.sim_frames = sim_frames

def run_float_simulation(agent, tick_length=3):
    x_limit = 4096 - agent.defaultElevation
    y_limit = 5120 - agent.defaultElevation
    ground_limit = agent.defaultElevation
    ceiling_limit = 2044 - agent.defaultElevation
    ideal_orientation = Vector([0, 0, 0])
    #tick_length = 3
    squash_index = 0
    collision_timer = 0
    collision_location = Vector([0, 0, 0])
    aim_direction = None
    recovery_limit = 1.5
    simulated_location = agent.me.location.scale(1)
    simulated_velocity = agent.me.velocity.scale(1)
    simulated_time = 0
    agent.last_float_sim_time = agent.time
    sim_frames = []

    while (
            simulated_time < 10
    ):
        simulated_time += agent.fakeDeltaTime * tick_length
        simulated_velocity = simulated_velocity + Vector([0, 0, agent.gravity]).scale(
            (agent.fakeDeltaTime) * tick_length
        )
        if simulated_velocity.magnitude() > 2300:
            simulated_velocity = simulated_velocity.normalize().scale(2300)
        simulated_location = simulated_location + simulated_velocity.scale(
            (agent.fakeDeltaTime) * tick_length
        )
        sim_frames.append([simulated_location, simulated_velocity, agent.time + simulated_time])


        if simulated_location[2] >= ceiling_limit:
            agent.roll_type = 2
            agent.squash_index = 2
            # print(f"ceiling recovery {self.agent.time}")
            aim_direction = Vector([0, 0, 1])
            break
        if simulated_location[2] <= ground_limit:
            agent.roll_type = 1
            agent.squash_index = 2
            # print(f"ground recovery {self.agent.time}")
            break

        if simulated_location[0] <= -x_limit:
            # on blue's right wall
            # print(f"side wall recovery {self.agent.time}")
            agent.squash_index = 0
            if simulated_velocity[1] < 0:
                # need to keep top right
                agent.roll_type = 4

            else:
                # need to keep top left
                agent.roll_type = 3
            break

        if simulated_location[0] >= x_limit:
            # on blue's left wall
            agent.squash_index = 0
            # print(f"side wall recovery {self.agent.time}")
            if simulated_velocity[1] < 0:
                # need to keep top left
                agent.roll_type = 3

            else:
                # need to keep top right
                agent.roll_type = 4
            break

        if simulated_location[1] <= -y_limit:
            # on blue's backboard
            # print(f"back wall recovery {self.agent.time}")
            if abs(simulated_location[0]) < 893:
                if simulated_location[2] < 642:
                    agent.roll_type = 1
                    agent.squash_index = 2
                    break
            agent.squash_index = 1
            if simulated_velocity[0] < 0:
                # need to keep top left
                agent.roll_type = 3

            else:
                # need to keep top right
                agent.roll_type = 4
            break

        if simulated_location[1] >= y_limit:
            # on orange's backboard
            # print(f"side wall recovery {self.agent.time}")
            if abs(simulated_location[0]) < 893:
                if simulated_location[2] < 642:
                    agent.roll_type = 1
                    agent.squash_index = 2
                    break
            agent.squash_index = 1
            if simulated_velocity[0] < 0:
                # need to keep top right
                agent.roll_type = 4

            else:
                # need to keep top left
                agent.roll_type = 3
            break
    if simulated_time >= 10:
        agent.roll_type = 1
        agent.squash_index = 2

    if aim_direction is None:
        agent.aim_direction = Vector([0, 0, -1])
    else:
        agent.aim_direction = aim_direction

    agent.collision_timer = simulated_time
    agent.on_ground_estimate = agent.time + simulated_time
    agent.collision_location = simulated_location
    # agent.simulated_velocity = simulated_velocity
    simulated_velocity.data[agent.squash_index] = 0
    agent.simulated_velocity = simulated_velocity

    agent.wall_landing = agent.roll_type == 1
    agent.sim_frames = sim_frames


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


def ballHeadedTowardsMyGoal_testing(agent, hit):
    return hit.pred_vel[1] * sign(agent.team) > 10


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
        _vector.data[2] = 20
        length = 65
        two_pi = math.pi * 2
        right = _vector + Vector([length * math.sin(two_pi * 0.333334), length * math.cos(two_pi * 0.333334), 0])
        left = _vector + Vector([length * math.sin(two_pi * 0.6666667), length * math.cos(two_pi * 0.6666667), 0])
        back = _vector + Vector([length * math.sin(two_pi), length * math.cos(two_pi), 0])

        # right = _vector + Vector([length, length, 0])
        # left = _vector + Vector([-length, length, 0])
        # back = _vector + Vector([0, -length, 0])
        top = _vector.scale(1)
        top.data[2] = _vector.data[2] + length

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


def createSphere(agent, _vector, _radius=92.5, frequency=25, num_points=100):
    if agent.debugging:
        if agent.team == 0:
            color = agent.renderer.blue
        else:
            color = agent.renderer.orange

        t = np.linspace(-1, 1, num_points)
        x = np.sqrt(1 - t ** 2) * np.cos(t * frequency)
        y = np.sqrt(1 - t ** 2) * np.sin(t * frequency)
        z = t

        points = []
        for i in range(num_points):
            points.append((Vector([x[i]*_radius, y[i]*_radius, z[i]*_radius])+_vector).data)

        agent.renderer.begin_rendering('sphere')
        agent.renderer.draw_polyline_3d( points, color())
        agent.renderer.end_rendering()
        # agent.renderCalls.append(
        #     renderCall(agent.renderer.draw_polyline_3d, points, color)
        # )

if __name__ == "__main__":
    print("Surprise! You did a silly thing!")
    #createCircle(None, Vector([0,0,0]), 1, 50, 200)
