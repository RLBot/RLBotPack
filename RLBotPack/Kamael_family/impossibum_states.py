from impossibum_utilities import *
import math
from time import time
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import (
    GameState,
    BallState,
    CarState,
    Physics,
    Vector3,
    Rotator,
)
import random

"""
Right corner	loc: (-2048, -2560), yaw: 0.25 pi	loc: (2048, 2560), yaw: -0.75 pi
Left corner	loc: (2048, -2560), yaw: 0.75 pi	loc: (-2048, 2560), yaw: -0.25 pi
Back right	loc: (-256.0, -3840), yaw: 0.5 pi	loc: (256.0, 3840), yaw: -0.5 pi
Back left	loc: (256.0, -3840), yaw: 0.5 pi	loc: (-256.0, 3840), yaw: -0.5 pi
Far back center	loc: (0.0, -4608), yaw: 0.5 pi	loc: (0.0, 4608), yaw: -0.5 pi
"""

class State:
    RESET = 0
    WAIT = 1
    INITIALIZE = 2
    RUNNING = 3


def locked_in(agent, agentType):
    if agentType == LeapOfFaith:
        return agent.activeState.active
    if agentType == Divine_Mandate:
        return agent.activeState.active
    if agentType == airLaunch:
        return agent.activeState.active

    if agentType == BlessingOfDexterity:
        return agent.activeState.active

    if agentType == Wings_Of_Justice:
        return agent.activeState.active

    if agentType == DivineGuidance:
        return agent.activeState.active

    if agentType == RighteousVolley:
        return agent.activeState.active

    if agentType == Deliverance:
        return agent.activeState.active

    if agentType == Cannister_Grab:
        return agent.activeState.active

    # if agentType == Kickoff_boosties:
    #     return agent.activeState.active

    return False


def getKickoffPosition(vec):
    kickoff_locations = [[2048, 2560], [256, 3848], [0, 4608]]
    # 0 == wide diagonal, 1 == short disgonal, 2 == middle
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


class Player_reporter(baseState):
    def update(self):
        if len(self.agent.allies) > 0:
            center = Vector([0, 5200 * -sign(self.agent.team), 200])
            dummy = self.agent.allies[0]
            shotAngle = math.degrees(angle2(dummy.location, center))
            correctedAngle = correctAngle(shotAngle + 90 * -sign(self.agent.team))
            # agent.log.append(
            #     f"natural angle: {shotAngle} || corrected angle: {correctedAngle}"
            # )
            print(distance2D(self.agent.allies[0].location, self.agent.ball.location))

        else:
            self.agent.log.append("waiting on player to join bot team")

        return SimpleControllerState()



class Cannister_Grab(baseState):
    def __init__(self, agent, boost_index):
        super().__init__(agent)
        self.boost_index = boost_index
        self.last_position = self.agent.goal_locations[1]

    def find_boost_obj(self):
        for b in self.agent.boosts:
            if b.index == self.boost_index:
                return b
        return None


    def update(self):
        target = self.last_position
        target_boost = self.find_boost_obj()
        if target_boost is None:
            self.active = False
        elif not target_boost.spawned:
            self.active = False
        else:
            target = target_boost.location

        if self.agent.goalPred is not None or not self.agent.onSurface or distance2D(self.agent.me.location, self.agent.goal_locations[1]) > distance2D(self.agent.ball.location, self.agent.goal_locations[1]):
            self.active = False

        if self.agent.me.boostLevel > 90:
            self.active = False

        self.last_position = target

        return driveController(self.agent, target, self.agent.time, expedite=True)



class Kickoff_boosties(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        self.active = (
            self.agent.gameInfo.is_kickoff_pause
            or not self.agent.gameInfo.is_round_active
        )
        return kickoff_boost_grabber(self.agent)


class airLaunch(baseState):
    def __init__(self, agent):
        super().__init__(agent)
        self.initiated = agent.time
        self.jumpTimer = agent.time
        self.firstJump = False
        self.secondJump = False
        self.firstJumpHold = 0.5
        self.secondJumpHold = 0.4

    def update(self):
        stateController = SimpleControllerState()

        if not self.firstJump:
            self.firstJump = True
            stateController.jump = True
            self.jumpTimer = self.agent.time

        elif self.firstJump and not self.secondJump:
            if self.agent.time - self.jumpTimer < self.firstJumpHold:
                stateController.jump = True

            elif (
                self.agent.time - self.jumpTimer > self.firstJumpHold
                and self.agent.time - self.jumpTimer < self.firstJumpHold + 0.05
            ):
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

        if (
            self.agent.time - self.jumpTimer > 0.15
            and self.agent.time - self.jumpTimer < 0.35
        ):
            stateController.pitch = 1
        return stateController


class Aerial_Charge:
    def __init__(self, agent, target: Vector):
        self.target = target
        self.agent = agent
        self.active = True
        self.anti_gravity_vec = Vector([0, 0, 1])
        self.timer = 0
        self.wallJump = self.agent.onWall

    def update(self):
        controls = SimpleControllerState()
        controls.throttle = 0
        self.timer += self.agent.deltaTime
        # print(self.timer)

        delta_a = calculate_delta_acceleration(
            self.target - self.agent.me.location,
            self.agent.me.velocity,
            0.01,
            self.agent.gravity,
        )

        if not self.agent.onSurface:
            align_car_to(controls, self.agent.me.avelocity, delta_a, self.agent)

        aim_target = (
            (delta_a.normalize() + self.anti_gravity_vec).normalize().scale(2300)
        )
        if self.wallJump:
            if self.timer <= 0.2:
                controls.boost = (
                    self.agent._forward.dotProduct(delta_a.normalize()) > 0.6
                    and delta_a.magnitude() > 100
                )
                controls.jump = True
                return controls

            elif self.timer <= 0.2 + self.agent.fakeDeltaTime * 3:
                controls.jump = False
                controls.boost = (
                    self.agent._forward.dotProduct(delta_a.normalize()) > 0.6
                    and delta_a.magnitude() > 100
                )
                return controls

            elif self.timer > 0.2 + self.agent.fakeDeltaTime * 3:
                controls.steer, controls.roll, controls.yaw, controls.pitch = 0, 0, 0, 0
                controls.jump = True
                controls.boost = (
                    self.agent._forward.dotProduct(delta_a.normalize()) > 0.6
                    and delta_a.magnitude() > 100
                )
                if self.timer > 0.2 + self.agent.fakeDeltaTime * 6:
                    # print("Launch complete")
                    self.active = False
                return controls

        else:
            controls.boost = (
                self.agent._forward.dotProduct(delta_a.normalize()) > 0.6
                and delta_a.magnitude() > 100
            )

            if self.timer < 0.2:
                controls.jump = True

            elif self.timer < 0.2 + self.agent.fakeDeltaTime * 3:
                controls.jump = False

            elif self.timer < 0.2 + self.agent.fakeDeltaTime * 5:
                controls.steer, controls.roll, controls.yaw, controls.pitch = 0, 0, 0, 0
                controls.jump = True

            else:
                controls.jump = True
                self.active = False

            return controls

        print("error, launch condition out of range!")
        self.active = False
        return controls


class speed_takeoff:
    def __init__(self, agent, target, time):
        self.agent = agent
        self.target = target
        self.time = time
        self.stage = 1
        self.start_time = agent.time * 1
        self.active = True

    def update(self):
        controls = SimpleControllerState()
        controls.throttle = 0
        dt = (self.start_time + 0.2 + self.agent.fakeDeltaTime * 6) - (
            self.agent.time - self.start_time
        )
        timer = abs(self.start_time - self.agent.time)

        delta_a = calculate_delta_acceleration(
            self.target - self.agent.me.location,
            self.agent.me.velocity,
            dt,
            self.agent.gravity,
        )
        total_req_delta_a = delta_a.magnitude() * (
            clamp(10, self.agent.fakeDeltaTime, dt) / self.agent.fakeDeltaTime
        )
        current_alignment = self.agent._forward.dotProduct(delta_a.normalize())
        aligned = current_alignment > 0.6
        controls.boost = aligned and total_req_delta_a > 35
        controls.throttle = True
        controls.jump = False

        if timer < 0.22:
            align_car_to(controls, self.agent.me.avelocity, delta_a, self.agent)
            controls.jump = True

        elif timer >= 0.22 + self.agent.fakeDeltaTime * 3:
            if self.agent.up.dotProduct(delta_a.normalize()) > 0:
                controls.jump = True

        if timer > 0.22 + self.agent.fakeDeltaTime * 6:
            self.active = False

        return controls


class Wings_Of_Justice:
    def __init__(self, agent, pred, target: Vector, time: float):
        self.active = True
        self.agent = agent
        self.time = clamp(10, 0.0001, time)
        self.airborne = False
        self.launcher = None
        self.pred = predictionStruct(
            convertStructLocationToVector(pred), pred.game_seconds
        )
        self.pred_vel = convertStructVelocityToVector(pred)
        self.target = target
        self.drive_controls = SimpleControllerState()
        self.launch_projection = None
        self.started = self.agent.time
        self.offensive = self.target[1] * sign(self.agent.team) < 0
        self.point_time = 1
        self.accel_cap = self.agent.aerialAccelerationTick
        self.boost_req = self.agent.boost_req
        self.vel_reached = False
        self.goal_down = target[1] * sign(agent.team) < 0 and butterZone(self.pred.location, x=1000)
        self.col_info = None
        self.col_timer = 0

    def launch_window_check(self, time_into_future):
        current_delta_req = calculate_delta_acceleration(
            self.target - self.agent.me.location,
            self.agent.me.velocity,
            self.pred.time - self.agent.time,
            self.agent.gravity,
        )

        projected_location = self.agent.me.location + (
            self.agent.me.velocity.scale(time_into_future)
        )
        projected_delta_req = calculate_delta_acceleration(
            self.target - projected_location,
            self.agent.me.velocity,
            self.pred.time - (self.agent.time + time_into_future),
            self.agent.gravity,
        )
        # print(projected_delta_req[2], current_delta_req[2])

        return projected_delta_req[2] > current_delta_req[2]

    def setup(self):
        launching = False
        self.jumpSim = jumpSimulatorNormalizingJit(
            float32(self.agent.gravity),
            float32(self.agent.physics_tick),
            np.array(self.agent.me.velocity.data, dtype=np.dtype(float)),
            np.array(self.agent.up.data, dtype=np.dtype(float)),
            np.array(self.agent.me.location.data, dtype=np.dtype(float)),
            float32(self.agent.defaultElevation),
            float32(self.agent.takeoff_speed),
            float32(self.target[2]),
            True,
        )
        self.agent.currentHit.jumpSim = self.jumpSim

        destination = self.target
        dt = self.pred.time - self.agent.time
        delta_a = calculate_delta_acceleration(
            self.target - Vector(self.jumpSim[4]),
            Vector(self.jumpSim[5]),
            dt - self.agent.takeoff_speed,
            self.agent.gravity,
        )

        delta_mag = delta_a.magnitude()
        takeoff_dt = dt - self.agent.takeoff_speed
        total_req_delta_a = delta_mag * takeoff_dt

        if delta_mag > self.agent.aerial_accel_limit or takeoff_dt < 0:
            self.active = False

        # print(delta_mag)
        flips_enabled = (
            delta_a.flatten().magnitude()
            - (clamp(2300, 0, self.agent.currentSpd + 500) * 2.1)
            > self.target[2]
        )

        expedite = (
            self.agent.calculate_delta_velocity(takeoff_dt) - 10 > total_req_delta_a
            or self.agent.boostMonster
            or self.agent.aerial_hog
        )

        dist2D = distance2D(self.agent.me.location, self.target)
        distance_multi = 4 if not self.agent.aerial_hog else 8
        if self.agent.onSurface:
            if not self.agent.onWall:
                if dist2D < self.target[2] * distance_multi:
                    accel_req_limit = self.agent.aerial_accel_limit

                    if delta_mag < accel_req_limit:
                        if delta_a.flatten().magnitude() <= 300 or delta_mag <= 600:
                            launching = True

            else:
                if (
                    self.agent.me.velocity[2] > 0
                    or self.target[2] < self.agent.me.location[2]
                ):  # and delta_mag < 950:
                    launching = True



            if launching:
                #if self.agent.time - self.agent.flipTimer > 1.6:
                if self.agent.onSurface and not self.agent.jumped:
                    if self.agent.onWall:
                        self.launcher = speed_takeoff(
                            self.agent, self.target, self.time
                        )
                    else:
                        self.launcher = self.agent.createJumpChain(
                            0.35, 400, jumpSim=None, set_state=False, aim=False
                        )

                    self.agent.flipTimer = self.agent.time

            self.drive_controls = driveController(
                self.agent,
                destination,
                self.pred.time,
                expedite=expedite,
                flippant=False,
                maintainSpeed=False,
                flips_enabled=flips_enabled,
                going_for_aerial=True,
            )
        # else:
        #     self.active = True

    def update(self):
        lazy = False
        controls = SimpleControllerState()
        controls.throttle = 0
        dt = self.pred.time - self.agent.time
        target = self.target
        createBox(self.agent, self.pred.location)
        self.agent.update_action({"type": "BALL", "time": self.pred.time})

        delta_a = calculate_delta_acceleration(
            target - self.agent.me.location,
            self.agent.me.velocity,
            clamp(10, self.agent.fakeDeltaTime, dt),
            self.agent.gravity,
        )

        if self.agent.time - self.started > 0.5:
            if self.launch_projection is not None:
                self.agent.log.append(
                    f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
                )
                self.launch_projection = None

        pred_valid = validateExistingPred(self.agent, self.pred, max_variance=60)
        if not pred_valid:
            self.agent.update_action({"type": "READY", "time": -1})
            if self.launch_projection is not None:
                self.agent.log.append(
                    f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
                )
                self.launch_projection = None
            if self.launcher is None:  # and dt > self.point_time:
                self.active = False
                controls.jump = False
                self.agent.log.append("canceling aerial because ball path changed")

        if self.agent.onSurface and self.launcher is None:
            self.setup()
            if self.launcher is None:
                return self.drive_controls

        if self.launcher is not None:
            #if pred_valid:
            controls = self.launcher.update()
            if not self.launcher.active:
                self.launcher = None
            else:
                return controls

        aligned_threshold = 0.7
        current_alignment = self.agent._forward.dotProduct(delta_a.normalize())
        aligned = current_alignment >= aligned_threshold
        delta_a_mag = delta_a.magnitude()
        total_req_delta_a = delta_a_mag * (clamp(10, self.agent.fakeDeltaTime, dt))

        # print(f"deltatime: {dt} delta magnitude: {delta_a_mag} required total accel change: {total_req_delta_a}")
        boost_req = self.boost_req
        body_pos = self.agent.find_sim_frame(self.pred.time)

        if body_pos is None:
            body_pos = self.agent.me.location
        else:
            body_pos = body_pos[0]


        if self.vel_reached:
            boost_req = self.boost_req * 1.5

        min_dist = 30

        making_contact = findDistance(body_pos, self.pred.location) < self.agent.aerial_reach * 0.9
        if (
            not making_contact or (not self.vel_reached and self.goal_down)
        ):

            if self.vel_reached:
                boost_req = self.boost_req
                self.vel_reached = False
            align_car_to(controls, self.agent.me.avelocity, delta_a, self.agent)

            # controls.boost = aligned and (delta_a.magnitude() > boost_req or abs(delta_a.magnitude() - boost_req) < dt*delta_a.magnitude())
            if making_contact and total_req_delta_a < boost_req:
                self.vel_reached = True
            else:

                if aligned:
                    if not making_contact:
                        controls.boost = True
                    else:
                        if self.goal_down:
                            if total_req_delta_a >= boost_req:
                                controls.boost = True
                            else:
                                self.vel_reached = True
                    if total_req_delta_a > 66.6667 * self.agent.fakeDeltaTime:
                        controls.throttle = 1

        else:
            self.vel_reached = True
            lazy = True

            if self.col_info is None or self.agent.time - self.col_timer > self.agent.fakeDeltaTime * 5:
                self.col_info = self.agent.find_first_aerial_contact(clamp(self.pred.time, self.agent.time, self.pred.time -3), self.pred.time)
                if self.col_info is not None and not self.goal_down:
                    self.pred = predictionStruct(self.col_info[1], self.col_info[2])
                    self.target = self.col_info[1]

            if self.col_info is None:
                target = self.pred.location
                if not pred_valid:
                    target = self.agent.ball.location

            else:
                target = self.col_info[1]
                body_pos = self.col_info[0]




            align_car_to(
                controls,
                self.agent.me.avelocity,
                target - body_pos,
                self.agent,
            )

            if aligned and total_req_delta_a > 66.6667 * self.agent.fakeDeltaTime:
                controls.throttle = 1

        if (
            self.agent.me.velocity[2] < -100
            and self.agent.me.location[2] < self.pred.location[2] - 200
        ):
            self.active = False
            self.agent.log.append("invalidating falling aerial")
            controls.jump = False

        if dt < 0:
            self.active = False
            self.agent.log.append("Aerial timed out")
            controls.jump = False

        if self.agent.onSurface:
            self.agent.log.append("canceling aerial since we're on surface")
            self.active = False
            controls.jump = False

        # if dt > self.point_time and not lazy:
        #     req_vel = self.agent.me.velocity + delta_a
        #     if req_vel.magnitude() > 2300 and self.launcher and delta_a_mag > boost_req:
        #         self.active = False

        return controls


# class Wings_Of_Justice:
#     def __init__(self, agent, pred, target: Vector, time: float):
#         self.active = False
#         self.agent = agent
#         self.time = clamp(10, 0.0001, time)
#         self.airborne = False
#         self.launcher = None
#         self.pred = predictionStruct(
#             convertStructLocationToVector(pred), pred.game_seconds
#         )
#         self.target = target
#         self.drive_controls = SimpleControllerState()
#         self.launch_projection = None
#         self.started = self.agent.time
#         self.powershot = (
#             distance2D(target, Vector([0, 5200 * -sign(agent.team), 0])) > 2000
#         )
#         self.point_time = 1.5
#         self.accel_cap = 1060
#         self.boost_req = self.agent.aerialAccelerationTick*3
#
#     def launch_window_check(self,time_into_future):
#         current_delta_req = calculate_delta_acceleration(
#                 self.target - self.agent.me.location,
#                 self.agent.me.velocity,
#                 self.pred.time - self.agent.time,
#                 self.agent.gravity,
#             )
#
#         projected_location = self.agent.me.location + (self.agent.me.velocity.scale(time_into_future))
#         projected_delta_req = calculate_delta_acceleration(
#             self.target - projected_location,
#             self.agent.me.velocity,
#             self.pred.time - (self.agent.time+time_into_future),
#             self.agent.gravity,
#         )
#         print(projected_delta_req[2] , current_delta_req[2])
#
#         return projected_delta_req[2] > current_delta_req[2]
#
#
#     def setup(self):
#         # print(f"in setup {self.agent.time}")
#         if self.agent.onSurface:
#             if not self.agent.onWall:#self.agent.team == 0:
#                 launching = False
#                 dt = self.pred.time - self.agent.time
#                 accel_req_limit = 1060
#
#                 delta_a = calculate_delta_acceleration(
#                     self.target - Vector(self.agent.currentHit.jumpSim[4]),
#                     Vector(self.agent.currentHit.jumpSim[5]),
#                     dt - self.agent.takeoff_speed,
#                     self.agent.gravity,
#                 )
#                 takeoff_dt = dt - self.agent.takeoff_speed
#                 total_req_delta_a = delta_a.magnitude() * takeoff_dt
#
#                 expedite = (
#                     self.agent.calculate_delta_velocity(takeoff_dt) - 10 > total_req_delta_a
#                 )
#
#                 _direction = direction(self.agent.me.location, self.target)
#                 # _direction = delta_a.flatten().normalize().scale(-1)
#                 offset = clamp(
#                     math.inf, 20, distance2D(self.agent.me.location, self.target)
#                 )
#                 # offset = delta_a.flatten().magnitude()
#
#                 destination = self.agent.me.location + _direction.scale(offset)
#
#                 self.drive_controls = driveController(
#                     self.agent,
#                     destination,
#                     self.pred.time,
#                     expedite=expedite,
#                     flippant=False,
#                     maintainSpeed=False,
#                 )
#
#                 angle_difference = abs(
#                     angleBetweenVectors(
#                         self.agent.me.velocity.flatten().normalize(),
#                         delta_a.flatten().normalize(),
#                     )
#                 )
#
#                 if delta_a.magnitude() < 1050:
#                     if (
#                         (
#                             angle_difference < 10
#                             and self.agent.currentSpd >= 1350
#                             and not expedite
#                         )
#                         or delta_a.flatten().magnitude() <= 600
#                         or (not self.agent.forward and angle_difference < 20)
#                         or abs(
#                             angleBetweenVectors(
#                                 self.agent.me.velocity.flatten().normalize(),
#                                 delta_a.flatten().normalize(),
#                             )
#                         )
#                         <= 5
#                         or (
#                             self.agent.onWall
#                             and (
#                                 self.agent.me.velocity[2] > 0
#                                 or self.target[2] < self.agent.me.location[2]
#                             )
#                         )
#                         or (not self.agent.onWall and self.agent.currentSpd < 600)
#                     ):
#                         launching = True
#                     else:
#                         launching = False
#             else:
#                 launching = True
#
#             # if launching and self.agent.onSurface and not self.agent.onWall:
#             #     launching = self.launch_window_check(self.agent.fakeDeltaTime * 5)
#             #     if not launching:
#             #         print(f"Stalling take off! {self.agent.time}")
#
#             if not launching: #and self.agent.team == 0:
#                 self.active = False
#
#             else:
#                 if distance2D(self.target, self.agent.me.location) <= 5000:
#                     self.launcher = speed_takeoff(self.agent, self.target, self.time)
#                     self.active = True
#                     # print("launching!")
#                 else:
#                     self.active = False
#         else:
#             self.active = True
#
#     def update(self):
#         controls = SimpleControllerState()
#         controls.throttle = 0
#         dt = self.pred.time - self.agent.time
#         target = self.target
#         createBox(self.agent, self.pred.location)
#
#         delta_a = calculate_delta_acceleration(
#             target - self.agent.me.location,
#             self.agent.me.velocity,
#             clamp(10, self.agent.fakeDeltaTime, dt),
#             self.agent.gravity,
#         )
#
#         if self.agent.time - self.started > 0.5:
#             if self.launch_projection != None:
#                 self.agent.log.append(
#                     f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
#                 )
#                 self.launch_projection = None
#
#         pred_valid = validateExistingPred(self.agent, self.pred)
#
#         if self.agent.onSurface and self.launcher == None:
#             self.setup()
#             if self.launcher == None:
#                 return self.drive_controls
#
#         if self.launcher != None:
#             controls = self.launcher.update()
#             if not self.launcher.active:
#                 self.launcher = None
#             return controls
#
#
#
#         aligned_threshold = 0.7
#         current_alignment = self.agent._forward.dotProduct(delta_a.normalize())
#         delta_a_mag = delta_a.magnitude()
#         total_req_delta_a = delta_a_mag * (
#             clamp(10, self.agent.fakeDeltaTime, dt) / self.agent.fakeDeltaTime
#         )
#
#         #if total_req_delta_a >= self.boost_req and (self.agent.me.boostLevel > 0 or dt > self.point_time):
#         if total_req_delta_a >= self.boost_req or (total_req_delta_a > 5 and dt > self.point_time):
#             align_car_to(controls, self.agent.me.avelocity, delta_a, self.agent)
#             aligned = current_alignment > aligned_threshold
#             # controls.boost = aligned and (delta_a.magnitude() > boost_req or abs(delta_a.magnitude() - boost_req) < dt*delta_a.magnitude())
#             controls.boost = aligned and total_req_delta_a >= self.boost_req
#             if aligned:
#                 controls.throttle = 1
#         else:
#             target = self.pred.location  # + offset
#             if not pred_valid:
#                 target = self.agent.ball.location  # + offset
#
#             align_car_to(
#                 controls,
#                 self.agent.me.avelocity,
#                 self.pred.location - self.agent.me.location,
#                 self.agent,
#             )
#
#         # if self.agent.me.location[2] > 500 and (self.agent.me.location[2] > self.pred.location[2] or self.target[2] > self.pred.location[2]) and abs(self.agent._forward[2]) < .4:
#         #     controls.roll = turnController(self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4)
#
#         if not pred_valid:
#             if self.launch_projection != None:
#                 self.agent.log.append(
#                     f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
#                 )
#                 self.launch_projection = None
#             if self.launcher == None and dt > self.point_time:
#                 self.active = False
#
#         if dt < 0:
#             self.active = False
#             self.agent.log.append("Aerial timed out")
#
#         if self.agent.onSurface:
#             self.agent.log.append("canceling aerial since we're on surface")
#             self.active = False
#
#         if dt > self.point_time:
#             req_vel = self.agent.me.velocity + delta_a
#             if (
#                 req_vel.magnitude() > 2300
#                 #and self.launcher
#                 and (req_vel.magnitude() * dt) - (2300*dt) > 50
#                 and self.agent.me.boostLevel > 1
#             ):
#                 self.active = False
#
#             if delta_a_mag > self.accel_cap and (delta_a_mag*dt) - (1057*dt) > 50 and self.agent.me.boostLevel > 1:
#                 self.active = False
#
#         return controls


class Deliverance(baseState):
    def __init__(self, agent, big_jump=True):
        super().__init__(agent)
        if big_jump:
            self.jump_action = LeapOfFaith(agent, 2)
            # print("big carry!")
        else:
            self.jump_action = LeapOfFaith(agent, -1)
            # print("little carry!")
        self.start_time = self.agent.time

    def update(self):
        if self.jump_action.active:
            action = self.jump_action.update()
            updated_time = self.agent.time - self.start_time
            if not action.jump:
                action.pitch = 1
            if not self.agent.onSurface:
                self.throttle = -1
            return action

        controls = SimpleControllerState()
        offset = Vector([0, 50 * sign(self.agent.team), 60])

        (
            controls.steer,
            controls.yaw,
            controls.pitch,
            _roll,
            error,
        ) = point_at_position(self.agent, self.agent.ball.location + offset)

        controls.boost = error < 0.6 and self.agent.ball.location[2] < 780

        if (
            self.agent.me.boostLevel <= 0
            or self.agent.me.location[2] < 55
            or findDistance(self.agent.me.location, self.agent.ball.location) > 500
            or error > 5
            or self.agent.onSurface
        ):
            self.active = False

        # print(f"point error is: {error}")

        return controls


class LeapOfFaith(baseState):
    def __init__(self, agent, targetCode, target=None):
        super().__init__(agent)
        self.targetCode = targetCode  # 0 flip at ball , 1 flip forward, 2 double jump, 3 flip backwards, 4 flip left, 5 flip right, 6 flip at target ,7 left forward diagnal flip, 8 right forward diagnal flip , -1 hold single jump
        self.flip_obj = FlipStatus(agent.time)
        self.target = target
        self.cancelTimerCap = 0.3
        self.cancelStartTime = None
        self.jumped = False
        self.followThrough = 0
        self.start_time = self.agent.time
        self.last_controller = SimpleControllerState()

    def update(self):
        if self.agent.onSurface:
            if self.agent.time - self.start_time > 0.2:
                self.active = False
        controller_state = SimpleControllerState()
        jump = flipHandler(self.agent, self.flip_obj)
        # print(f"code: {self.targetCode}, height: {self.agent.me.location[2]} ")
        if jump:
            if self.targetCode == 1:
                controller_state.pitch = -1
                controller_state.roll = 0
                controller_state.throttle = 1

            elif self.targetCode == 0:
                # ball_local = toLocal(
                #     self.agent.ball.location, self.agent.me
                # ).normalize()
                ball_local = self.agent.ball.local_location
                ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
                controller_state.jump = True
                yaw = math.sin(ball_angle)
                pitch = -math.cos(ball_angle)
                yp = Vector([abs(yaw), abs(pitch)])
                yp = yp.normalize()
                if yaw > 0:
                    yaw = yp[0]
                else:
                    yaw = -yp[0]
                if pitch > 0:
                    pitch = yp[1]
                else:
                    pitch = -yp[1]

                controller_state.yaw = yaw
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
                controller_state.throttle = 1
                # print("in left side flip")

            elif self.targetCode == 5:
                controller_state.pitch = 0
                controller_state.yaw = 1
                controller_state.steer = 1
                controller_state.throttle = 1
                # print("in right side flip")

            elif self.targetCode == 6:
                target_local = toLocal(self.target, self.agent.me).normalize()
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
                # diagnal flip cancel
                controller_state.pitch = -0.2
                controller_state.yaw = -0.8
                # controller_state.steer = -1
                controller_state.throttle = 1

            elif self.targetCode == 10:
                # diagnal flip cancel
                controller_state.pitch = -0.2
                controller_state.yaw = 0.8
                # controller_state.steer = -1
                controller_state.throttle = 1

        controller_state.jump = jump
        controller_state.boost = False
        if self.targetCode == 7 or self.targetCode == 8:
            controller_state.boost = True
        if self.flip_obj.flipDone:
            if self.targetCode != 9 or self.targetCode != 10:
                controller_state = self.last_controller
                if (
                    self.followThrough < 0.33
                    and self.targetCode != 2
                    and self.targetCode != -1
                ):
                    self.followThrough += self.agent.deltaTime
                else:
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

        self.last_controller = controller_state
        return controller_state


class Divine_Mandate:
    # class for performing consecutive inputs over set periods of time. Example: Flipping forward
    def __init__(self, agent, controls_list: list, durations_list: list, target=None, intercept_time=None):
        self.controls = controls_list
        self.durations = durations_list
        self._controls = controls_list
        self._durations = durations_list
        self.complete = False
        self.index = 0
        self.current_duration = 0
        self.agent = agent
        self.touch = self.agent.ball.lastTouch
        self.target = target
        self.intercept_time = intercept_time
        self.remote = None
        self.remote_timer = 0
        # there should be a duration in the durations for every controller given in the list. This inserts 0 for any lacking
        if len(durations_list) < len(controls_list):
            self.durations += [0 * len(controls_list) - len(durations_list)]
        self.active = True

    def create_custom_controls(self, actionCode):
        # perform specialized actions if creating controlers at creation time wasn't feasible
        controller_state = SimpleControllerState()
        if actionCode == 0:
            target = self.agent.ball.location

            if self.agent.ball.lastTouch == self.touch and self.target is not None:
                target = self.target

            target_local = localizeVector(target, self.agent.me)
            ball_angle = math.atan2(target_local.data[1], target_local.data[0])
            controller_state.jump = True

            yaw = math.sin(ball_angle)
            pitch = -math.cos(ball_angle)
            yp = Vector([abs(yaw), abs(pitch)])
            yp = yp.normalize()
            if yaw > 0:
                yaw = yp[0]
            else:
                yaw = -yp[0]
            if pitch > 0:
                pitch = yp[1]
            else:
                pitch = -yp[1]

            controller_state.pitch = pitch
            controller_state.yaw = yaw
            if pitch > 0:
                controller_state.throttle = -1
            else:
                controller_state.throttle = 1

            self.controls[self.index] = controller_state

        if actionCode == 1:
            remote_loc = None
            target = self.agent.ball.location

            if self.agent.ball.lastTouch != self.touch or self.target is None:
                self.intercept_time = None
            else:
                if self.intercept_time and self.agent.time < self.intercept_time:
                    if self.agent.time - self.remote_timer > self.agent.fakeDeltaTime * 5:
                        remote_loc = self.agent.find_sim_frame(self.intercept_time)
                        if remote_loc is not None:
                            remote_loc = remote_loc[0]
                            self.remote = remote_loc
                        self.remote_timer = self.agent.time
                    else:
                        remote_loc = self.remote

                    target = self.target

            if target[1] * sign(self.agent.team) < 0 and butterZone(target, x=1200, y=4000):
                target += Vector([0, 0, 40])

            #target_local = localizeVector(target, self.agent.me, remote_location=remote_loc)
            if remote_loc != None:
                # just a hack so I don't have to update the point function to work remotely
                target += (self.agent.me.location - remote_loc)

            (
                controller_state.steer,
                controller_state.yaw,
                controller_state.pitch,
                controller_state.roll,
                _,
            ) = point_at_position(self.agent, target)

            controller_state.jump = False
            controller_state.throttle = 1
            # print(f"agent height is : {self.agent.me.location[2]}")

        return controller_state

    def update(
        self,
    ):  # call this once per frame with delta time to receive updated controls
        self.current_duration += self.agent.deltaTime
        if self.index >= len(self.controls):
            self.active = False
            return SimpleControllerState()
        if self.current_duration > self.durations[self.index]:
            self.index += 1
            self.current_duration = self.current_duration - self.agent.deltaTime
            # self.current_duration = 0
            if self.index >= len(self.controls):
                self.active = False
                return SimpleControllerState()

        if type(self.controls[self.index]) == SimpleControllerState:
            return self.controls[self.index]

        else:
            return self.create_custom_controls(self.controls[self.index])


class RighteousVolley(baseState):
    def __init__(self, agent, delay, target):
        super().__init__(agent)
        self.smartAngle = False
        self.target = target
        height = target[2]
        boomerDelay = 0.05
        delay = clamp(1.25, 0.3, delay + boomerDelay)
        if delay >= 0.3:
            if height <= 200:
                # print("tiny powershot")
                self.jumpTimerMax = 0.1
                self.angleTimer = clamp(0.15, 0.05, self.jumpTimerMax / 2)
            else:
                # print("normal powershot")
                self.jumpTimerMax = delay - 0.2
                self.angleTimer = clamp(0.15, 0.1, self.jumpTimerMax / 2)
        self.delay = delay
        if self.delay >= 0.5:
            self.smartAngle = True
        self.jumped = False
        self.jumpTimer = 0
        # print("setting action to powershot")

    def update(self):
        controller_state = SimpleControllerState()
        controller_state.throttle = 0
        controller_state.boost = False
        ball_local = toLocal(self.agent.ball.location, self.agent.me).normalize()
        # ball_local = toLocal(self.target, self.agent.me)
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
                    if (
                        self.jumpTimer >= self.delay - 0.2
                        and self.jumpTimer < self.delay - 0.15
                    ):
                        controller_state.jump = False
                    elif (
                        self.jumpTimer >= self.delay - 0.15
                        and self.jumpTimer < self.delay
                    ):
                        controller_state.yaw = math.sin(ball_angle)
                        controller_state.pitch = -math.cos(ball_angle)
                        controller_state.jump = True
                    elif self.jumpTimer < self.delay + 0.1:
                        controller_state.jump = False
                    else:
                        self.active = False
                        controller_state.jump = False
            return controller_state


class Divine_Retribution:
    def __init__(self, agent, grab_boost=True):
        self.agent = agent
        self.active = True
        self.grab_boost = grab_boost

    def update(self,):
        best_target = unpicky_demo_picker(self.agent)
        boostTarget, dist = boostSwipe(self.agent)

        if best_target is not None and (
            (self.agent.me.boostLevel > 12 or self.agent.currentSpd >= 2200)
            or (boostTarget is None or dist > 3000 or not self.grab_boost)
        ):
            return demoTarget(self.agent, best_target)

        else:
            if not self.grab_boost:
                return driveController(self.agent, (self.agent.closestEnemyToBall.location + self.agent.closestEnemyToBall.velocity.scale(self.agent.fakeDeltaTime*20)).flatten(), self.agent.time, expedite=False)
                #return playBack(self.agent)

            if boostTarget is not None and dist < 5000 and self.agent.me.boostLevel < 100:
                return driveController(
                    self.agent,
                    boostTarget.location.flatten(),
                    self.agent.time,
                    expedite=True,
                )

            boost_suggestion = boost_suggester(self.agent, buffer=-20000, mode=0)
            if boost_suggestion is not None and not self.agent.boostMonster:
                target = boost_suggestion.location.scale(1)
                return driveController(self.agent, target.flatten(), 0)
            else:
                return playBack(self.agent)


class DemolitionBot:
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        target = self.agent.closestEnemyToBall
        valid = False
        if target.location[2] <= 90:
            if (
                target.location[1] > self.agent.ball.location[1]
                and target.location[1] < self.agent.me.location[1]
            ) or (
                target.location[1] < self.agent.ball.location[1]
                and target.location[1] > self.agent.me.location[1]
            ):
                valid = True

        if valid:
            return demoTarget(self.agent, target)

        else:
            self.active = False
            return ShellTime(self.agent)


class GroundShot(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        return lineupShot(self.agent, 3)


class GroundAssault(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        return lineupShot(self.agent, 1)


class DivineGuidance(baseState):
    def __init__(self, agent, target):
        super().__init__(agent)
        self.controller = SimpleControllerState()
        self.controller.jump = True
        self.target = Vector([target[0], target[1], 30])
        self.start_time = agent.time
        # self.agent.stubbornessTimer = 2
        # self.agent.stubborness = -50

    def update(self):
        temp_controller = SimpleControllerState(jump=True)

        if self.agent.time - self.start_time < self.agent.fakeDeltaTime * 5:
            temp_controller.jump = True

        elif self.agent.time - self.start_time > 0.1:
            temp_controller.jump = False
        else:
            temp_controller.jump = False
        (
            temp_controller.steer,
            temp_controller.yaw,
            temp_controller.pitch,
            temp_controller.roll,
            _,
        ) = point_at_position(self.agent, self.target.flatten())
        if self.agent.time - self.start_time > 1.2:
            self.active = False

        if self.agent.onSurface:
            if self.agent.time - self.start_time > 0.2:
                self.active = False

        return temp_controller


class HolyGrenade(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        return handleBounceShot(self.agent)


class HolyProtector(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        return ShellTime(self.agent)


class Obstruct(baseState):
    def update(self):
        if not kickOffTest(self.agent):
            return turtle_mode(self.agent)

        else:
            self.active = False
            self.agent.activeState = PreemptiveStrike(self.agent)
            return self.agent.activeState.update()


class Kickoff_Boosties(baseState):
    def __init__(self, agent):
        super().__init__(agent)
        self.setup()

    def setup(self):
        closest_dist = math.inf
        closest_loc = Vector([0, 0, 0])
        for bb in self.agent.bigBoosts:
            dist = distance2D(self.agent.me.location, bb.location)
            if dist < closest_dist:
                closest_dist = dist
                closest_loc = bb.location
        self.boost_target = closest_loc

    def update(self):
        if findDistance(self.agent.me.location, self.boost_target) < 100:
            self.active = False
        return driveController(
            self.agent,
            self.boost_target,
            0.0001,
            expedite=True,
            flippant=True,
            kickoff=True,
        )


class HeavenlyReprieve(baseState):
    def __init__(self, agent, boostloc):
        super().__init__(agent)
        self.boostLoc = boostloc

    def update(self):
        result = inCornerWithBoost(self.agent)
        if result != False:
            self.agent.update_action({"type": "BOOST", "target": result[0].index})
            return refuel(self.agent, result[0].location)
        else:
            self.active = False
            return ShellTime(self.agent)


# class PreemptiveStrike(baseState):
#     def __init__(self, agent):
#         super().__init__(agent)
#         self.fakeDeltaTime = 1 / 120
#         self.started = False
#         self.firstFlip = None
#         self.secondFlip = None
#         self.startTime = agent.time
#         self.kickoff_type = getKickoffPosition(agent.me.location)
#         # 0 == wide diagonal, 1 == short disgonal, 2 == middle
#         agent.stubbornessTimer = 5
#         self.onRight = True
#         self.short_offset = 75
#         self.setup()
#         self.enemyGoal = Vector([0, 5200 * -sign(self.agent.team), 0])
#         self.phase = 1
#         self.KO_option = None
#         self.maintaining_speed = False
#         self.first_recovery = None
#         self.random_offset = None
#
#     def create_speed_flip_cancel(self, left=False):
#         controls = []
#         timers = []
#         # first_controller = SimpleControllerState()
#         # if left:
#         #     first_controller.steer = 1
#         # else:
#         #     first_controller.steer = -1
#         #
#         # first_controller.handbrake = True
#         # first_controller.throttle = 1
#         # first_controller.boost = True
#         # first_controller.jump = False
#         # controls.append(first_controller)
#         # timers.append(self.agent.fakeDeltaTime * 1)
#
#         second_controller = SimpleControllerState()
#
#         # if left:
#         #     second_controller.steer = 1
#         # else:
#         #     second_controller.steer = -1
#         if not left:
#             second_controller.steer = 1
#         else:
#             second_controller.steer = -1
#
#         second_controller.throttle = 1
#         second_controller.boost = True
#         second_controller.jump = True
#         second_controller.pitch = 1
#         second_controller.handbrake = True
#         controls.append(second_controller)
#         timers.append(0.10)
#
#         third_controller = SimpleControllerState()
#         third_controller.jump = False
#         third_controller.boost = True
#         third_controller.throttle = 1
#         third_controller.pitch = 1
#         controls.append(third_controller)
#         timers.append(self.fakeDeltaTime * 1.5)
#
#         fourth_controller = SimpleControllerState()
#         # yaw = 1
#         # if left:
#         #     yaw = -1
#
#         yaw = -1
#         if left:
#             yaw = 1
#
#         fourth_controller.yaw = yaw
#         # fourth_controller.roll = yaw
#         fourth_controller.pitch = -1
#         fourth_controller.jump = True
#         fourth_controller.boost = True
#         fourth_controller.throttle = 1
#         controls.append(fourth_controller)
#         timers.append(0.05)
#
#         fifth_controller = SimpleControllerState()
#         fifth_controller.yaw = -yaw
#         # fifth_controller.roll = -yaw
#         fifth_controller.pitch = 1
#         fifth_controller.throttle = 1
#         fifth_controller.boost = True
#         fifth_controller.handbrake = False
#         fifth_controller.jump = True
#         controls.append(fifth_controller)
#         timers.append(0.75)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def create_diagonal_speed_flip(self, left=False):
#         controls = []
#         timers = []
#         # jump start
#         first_controller = SimpleControllerState()
#         if self.kickoff_type == 0:
#             if self.onRight:
#                 first_controller.yaw = -1
#             else:
#                 first_controller.yaw = 1
#
#         first_controller.jump = True
#         first_controller.boost = True
#         first_controller.throttle = 1
#         first_controller.pitch = -1
#         first_controller.jump = True
#         controls.append(first_controller)
#         timers.append(0.1)
#
#         # jump delay
#         second_controller = SimpleControllerState()
#         second_controller.jump = False
#         second_controller.boost = True
#         second_controller.throttle = 1
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         second_controller.yaw = yaw
#         second_controller.pitch = pitch
#         second_controller.jump = False
#
#         controls.append(second_controller)
#         timers.append(self.fakeDeltaTime * 2)
#
#         # jump flip
#         third_controller = SimpleControllerState()
#         third_controller.jump = True
#         third_controller.boost = True
#         third_controller.throttle = 1
#
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         third_controller.yaw = yaw
#         third_controller.pitch = pitch
#         controls.append(third_controller)
#         timers.append(0.5)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def setup(self):
#         # setup randomness like offsets to either side of the ball. Make sure it's slightly offset from middle so we can flip center
#         # setup flips
#         ball_local = (
#             self.agent.ball.local_location
#         )  # localizeVector(Vector([0, 0, 0]), self.agent.me)
#         if self.kickoff_type == 0:
#             if ball_local[1] > 0:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 # self.firstFlip = LeapOfFaith(self.agent,9)
#                 self.firstFlip = self.create_speed_flip_cancel(left=False)
#                 self.onRight = False
#                 # print("flipping left")
#             else:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 # self.firstFlip = LeapOfFaith(self.agent, 10)
#                 self.firstFlip = self.create_speed_flip_cancel(left=True)
#                 self.onRight = True
#                 # print("flipping right")
#
#         elif self.kickoff_type == 1:
#             if ball_local[1] < 0:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 self.onRight = True
#                 self.short_offset = -50 * sign(self.agent.team)
#             else:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 self.onRight = False
#                 self.short_offset = 50 * sign(self.agent.team)
#                 # print(f"on left and short offset == {self.short_offset}")
#
#         else:
#             # middle kickoff defaulting to right
#             self.firstFlip = self.create_diagonal_speed_flip(left=True)
#             # self.onRight shouldn't matter
#
#     def wide_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > 3150:
#                 # return driveController(self.agent, self.enemyGoal+Vector([0,4000*sign(self.agent.team),0]),
#                 return driveController(
#                     self.agent,
#                     self.agent.ball.location
#                     + Vector([0, sign(self.agent.team) * -100, 0]),
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 3 - first flip
#         if self.phase == 3:
#             # if self.firstFlip == None:
#             #     self.firstFlip = self.create_speed_flip_cancel(left=not self.onRight)
#             if self.firstFlip.active:
#                 # print(f"first flip active: {str(self.firstFlip)} {self.agent.time} {self.firstFlip.targetCode}")
#                 return self.firstFlip.update()
#
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#
#             else:
#                 self.phase = 4
#                 # print(f"switched to stage 4! {self.agent.time}")
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > 450:
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(2, 15)
#                     dummy_location = self.agent.ball.location + Vector(
#                         # [25, 120 * sign(self.agent.team), 0]
#                         [self.random_offset, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal,self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(distance2D(self.agent.me.location,dummy_location)*.5)
#                 else:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(-15, -2)
#                     dummy_location = self.agent.ball.location + Vector(
#                         # [-25, 120 * sign(self.agent.team), 0]
#                         [self.random_offset, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#                 # print(f"switched to stage 5! {self.agent.time}")
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                 ) or (
#                     self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 5
#                 else:
#                     _code = 4
#                 #     _code = 4
#                 # else:
#                 #     _code = 5
#
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def short_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector(
#                 [self.short_offset, sign(self.agent.team) * 2825.0, 0]
#             )
#             if distance2D(self.agent.me.location, drive_target) > 575:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             controls = SimpleControllerState()
#             if not self.agent.onSurface:
#                 (
#                     controls.steer,
#                     controls.yaw,
#                     controls.pitch,
#                     controls.roll,
#                     alignment_error,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 return controls
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 return self.firstFlip.update()
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#             else:
#                 self.phase = 4
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 500
#                 or not self.agent.onSurface
#             ):
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(10, 25)
#                     dummy_location = self.agent.ball.location + Vector(
#                         [self.random_offset, 75 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 else:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(-25, -10)
#                     dummy_location = self.agent.ball.location + Vector(
#                         [self.random_offset, 75 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                 ) or (
#                     self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def middle_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector([0, sign(self.agent.team) * 4000, 0])
#             if distance2D(self.agent.me.location, drive_target) > 75:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 2
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             drive_target = Vector([4500 * sign(self.agent.team), 0, 0])
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 3850
#             ):  # 3875:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 return self.firstFlip.update()
#             else:
#                 if self.agent.onSurface:
#                     self.phase = 4
#                 else:
#                     controls = SimpleControllerState()
#                     (
#                         controls.steer,
#                         controls.yaw,
#                         controls.pitch,
#                         controls.roll,
#                         alignment_error,
#                     ) = point_at_position(
#                         self.agent,
#                         self.agent.me.location
#                         + self.agent.me.velocity.normalize().flatten().scale(1000),
#                     )
#                     return controls
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 500
#                 or not self.agent.onSurface
#             ):
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(10, 25)
#                     dummy_location = self.agent.ball.location + Vector(
#                         [self.random_offset, 75 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 else:
#                     if self.random_offset == None:
#                         self.random_offset = random.randrange(-25, -10)
#                     dummy_location = self.agent.ball.location + Vector(
#                         [self.random_offset, 75 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                 ) or (
#                     self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def retire(self):
#         if self.phase != 5 or self.secondFlip == None or not self.secondFlip.active:
#             self.active = False
#             # self.agent.activeState = None
#             # print(f"retiring on stage {self.phase} {self.agent.time}")
#
#     def update(self):
#         if not self.agent.gameInfo.is_round_active:
#             self.setup()
#
#         if not self.agent.gameInfo.is_kickoff_pause:
#             # print(f"retiring due to kickoff pause")
#             self.retire()
#
#         if self.KO_option != None:
#             if not self.KO_option.active:
#                 self.retire()
#             return self.KO_option.update()
#
#         # 0 == wide diagonal, 1 == short disgonal, 2 == middle
#         if self.kickoff_type == 0:
#             return self.wide_handler()
#         elif self.kickoff_type == 1:
#             return self.short_handler()
#         else:
#             return self.middle_handler()

""


# class PreemptiveStrike(baseState):
#     def __init__(self, agent):
#         super().__init__(agent)
#         self.started = False
#         self.firstFlip = None
#         self.secondFlip = None
#         self.startTime = agent.time
#         self.kickoff_type = getKickoffPosition(agent.me.location)
#         # 0 == wide diagonal, 1 == short disgonal, 2 == middle
#         agent.stubbornessTimer = 5
#         self.onRight = True
#         self.short_offset = 75
#         self.setup()
#         self.enemyGoal = Vector([0, 5200 * -sign(self.agent.team), 0])
#         self.phase = 1
#         # if agent.team == 0:
#         #     self.KO_option = PreemptiveStrike_botpack(agent)
#         # else:
#         self.KO_option = None
#         self.maintaining_speed = False
#         self.first_recovery = None
#         self.greedy = False
#         self.greedy_req = 450
#         self.final_flip_dist = 575
#
#     def create_speed_flip_cancel(self, left=False):
#         controls = []
#         timers = []
#
#         second_controller = SimpleControllerState()
#         if not left:
#             second_controller.steer = 1
#         else:
#             second_controller.steer = -1
#
#         second_controller.throttle = 1
#         second_controller.boost = True
#         second_controller.jump = True
#         second_controller.pitch = 1
#         second_controller.handbrake = True
#         controls.append(second_controller)
#         timers.append(0.10)
#
#         third_controller = SimpleControllerState()
#         third_controller.jump = False
#         third_controller.boost = True
#         third_controller.throttle = 1
#         third_controller.pitch = 1
#         controls.append(third_controller)
#         timers.append(self.agent.fakeDeltaTime * 2)
#
#         fourth_controller = SimpleControllerState()
#         # yaw = 1
#         # if left:
#         #     yaw = -1
#
#         yaw = -1
#         if left:
#             yaw = 1
#
#         fourth_controller.yaw = yaw
#         # fourth_controller.roll = yaw
#         fourth_controller.pitch = -1
#         fourth_controller.jump = True
#         fourth_controller.boost = True
#         fourth_controller.throttle = 1
#         controls.append(fourth_controller)
#         timers.append(0.05)
#
#         fifth_controller = SimpleControllerState()
#         fifth_controller.yaw = -yaw
#         # fifth_controller.roll = -yaw
#         fifth_controller.pitch = 1
#         fifth_controller.throttle = 1
#         fifth_controller.boost = True
#         fifth_controller.handbrake = False
#         fifth_controller.jump = True
#         controls.append(fifth_controller)
#         timers.append(0.75)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def create_diagonal_speed_flip(self, left=False):
#         controls = []
#         timers = []
#         # jump start
#         first_controller = SimpleControllerState()
#         if self.kickoff_type == 0:
#             if self.onRight:
#                 first_controller.yaw = -1
#             else:
#                 first_controller.yaw = 1
#
#         first_controller.jump = True
#         first_controller.boost = True
#         first_controller.throttle = 1
#         first_controller.pitch = -1
#         first_controller.jump = True
#         controls.append(first_controller)
#         timers.append(0.1)
#
#         # jump delay
#         second_controller = SimpleControllerState()
#         second_controller.jump = False
#         second_controller.boost = True
#         second_controller.throttle = 1
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         second_controller.yaw = yaw
#         second_controller.pitch = pitch
#         second_controller.jump = False
#
#         controls.append(second_controller)
#         timers.append(self.agent.fakeDeltaTime * 4)
#
#         # jump flip
#         third_controller = SimpleControllerState()
#         third_controller.jump = True
#         third_controller.boost = True
#         third_controller.throttle = 1
#
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         third_controller.yaw = yaw
#         third_controller.pitch = pitch
#         controls.append(third_controller)
#         timers.append(0.5)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def setup(self):
#         # setup randomness like offsets to either side of the ball. Make sure it's slightly offset from middle so we can flip center
#         # setup flips
#         ball_local = (
#             self.agent.ball.local_location
#         )  # localizeVector(Vector([0, 0, 0]), self.agent.me)
#         if self.kickoff_type == 0:
#             if ball_local[1] > 0:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 # self.firstFlip = LeapOfFaith(self.agent,9)
#                 self.firstFlip = self.create_speed_flip_cancel(left=False)
#                 self.onRight = False
#                 # print("flipping left")
#             else:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 # self.firstFlip = LeapOfFaith(self.agent, 10)
#                 self.firstFlip = self.create_speed_flip_cancel(left=True)
#                 self.onRight = True
#                 # print("flipping right")
#
#         elif self.kickoff_type == 1:
#             if ball_local[1] < 0:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 self.onRight = True
#                 self.short_offset = -50 * sign(self.agent.team)
#             else:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 self.onRight = False
#                 self.short_offset = 50 * sign(self.agent.team)
#                 # print(f"on left and short offset == {self.short_offset}")
#
#         else:
#             # middle kickoff defaulting to right
#             self.firstFlip = self.create_diagonal_speed_flip(left=True)
#             # self.onRight shouldn't matter
#
#     def wide_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > 3155:
#                 # return driveController(self.agent, self.enemyGoal+Vector([0,4000*sign(self.agent.team),0]),
#                 return driveController(
#                     self.agent,
#                     self.agent.ball.location,
#                     #+ Vector([0, sign(self.agent.team) * -50, 0]),
#                     #+ Vector([0, sign(self.agent.team) * -20, 0]),
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 3 - first flip
#         if self.phase == 3:
#             # if self.firstFlip == None:
#             #     self.firstFlip = self.create_speed_flip_cancel(left=not self.onRight)
#             if self.firstFlip.active:
#                 # print(f"first flip active: {str(self.firstFlip)} {self.agent.time} {self.firstFlip.targetCode}")
#                 return self.firstFlip.update()
#
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#
#             else:
#                 self.phase = 4
#                 # print(f"switched to stage 4! {self.agent.time}")
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist:
#                 drive_target = self.agent.ball.location
#                 # if self.agent.me.location[0] > self.agent.ball.location[0]:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [25, 120 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal,self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(distance2D(self.agent.me.location,dummy_location)*.5)
#                 # else:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [-25, 120 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(
#                 #     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#                 # print(f"switched to stage 5! {self.agent.time}")
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip is None and not self.greedy:
#                 self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(self.agent.closestEnemyToBall.location, self.agent.ball.location)
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 5
#                 else:
#                     _code = 4
#                 #     _code = 4
#                 # else:
#                 #     _code = 5
#
#                 self.secondFlip = LeapOfFaith(self.agent, 0, target=None) #_code
#             if not self.greedy:
#                 controls = self.secondFlip.update()
#                 if not self.secondFlip.active:
#                     self.retire()
#             else:
#                 controls = driveController(
#                     self.agent,
#                     self.agent.ball.location,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     kickoff=True,
#                 )
#                 controls.throttle = 0
#             if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
#                 self.retire()
#             return controls
#
#     def short_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector(
#                 [self.short_offset, sign(self.agent.team) * 2900.0, 0]
#             )
#             if distance2D(self.agent.me.location, drive_target) > 525:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             controls = SimpleControllerState()
#             if not self.agent.onSurface:
#                 (
#                     controls.steer,
#                     controls.yaw,
#                     controls.pitch,
#                     controls.roll,
#                     alignment_error,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 return controls
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 return self.firstFlip.update()
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#             else:
#                 self.phase = 4
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist
#                 or not self.agent.onSurface
#             ):
#                 drive_target = self.agent.ball.location
#                 # if self.agent.me.location[0] > self.agent.ball.location[0]:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [65, 75 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(
#                 #     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 # else:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [-65, 75 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(
#                 #     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip is None and not self.greedy:
#                 self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(
#                     self.agent.closestEnemyToBall.location, self.agent.ball.location)
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, 0, target=None)
#
#             if not self.greedy:
#                 controls = self.secondFlip.update()
#                 if not self.secondFlip.active:
#                     self.retire()
#             else:
#                 controls = driveController(
#                     self.agent,
#                     self.agent.ball.location,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     kickoff=True,
#                 )
#                 controls.throttle = 0
#             if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
#                 self.retire()
#             return controls
#
#     def middle_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector([0, sign(self.agent.team) * 4000, 0])
#             if distance2D(self.agent.me.location, drive_target) > 75:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 2
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             drive_target = Vector([4500 * sign(self.agent.team), 0, 0])
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 3850
#             ):  # 3875:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 return self.firstFlip.update()
#             else:
#                 if self.agent.onSurface:
#                     self.phase = 4
#                 else:
#                     controls = SimpleControllerState()
#                     (
#                         controls.steer,
#                         controls.yaw,
#                         controls.pitch,
#                         controls.roll,
#                         alignment_error,
#                     ) = point_at_position(
#                         self.agent,
#                         self.agent.me.location
#                         + self.agent.me.velocity.normalize().flatten().scale(1000),
#                     )
#                     return controls
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist
#                 or not self.agent.onSurface
#             ):
#                 drive_target = self.agent.ball.location
#                 # if self.agent.me.location[0] > self.agent.ball.location[0]:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [55, 75 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(
#                 #     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 # else:
#                 #     dummy_location = self.agent.ball.location + Vector(
#                 #         [-55, 75 * sign(self.agent.team), 0]
#                 #     )
#                 #     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                 #     drive_target = dummy_location  # + _direction.scale(
#                 #     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip is None and not self.greedy:
#                 self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(
#                     self.agent.closestEnemyToBall.location, self.agent.ball.location)
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, 0, target=None)
#             if not self.greedy:
#                 controls = self.secondFlip.update()
#                 if not self.secondFlip.active:
#                     self.retire()
#             else:
#                 controls = driveController(
#                     self.agent,
#                     self.agent.ball.location,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     kickoff=True,
#                 )
#                 controls.throttle = 0
#             if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
#                 self.retire()
#             return controls
#
#     def retire(self):
#         self.active = False
#         if self.secondFlip and self.secondFlip.active:
#             self.agent.activeState = self.secondFlip
#             # self.agent.activeState = None
#             # print(f"retiring on stage {self.phase} {self.agent.time}")
#
#     def update(self):
#         if not self.agent.gameInfo.is_round_active:
#             self.setup()
#
#         if not self.agent.gameInfo.is_kickoff_pause:
#             # print(f"retiring due to kickoff pause")
#             self.retire()
#
#         if self.KO_option is not None:
#             if not self.KO_option.active:
#                 self.retire()
#             return self.KO_option.update()
#
#         # 0 == wide diagonal, 1 == short disgonal, 2 == middle
#         if self.kickoff_type == 0:
#             return self.wide_handler()
#         elif self.kickoff_type == 1:
#             return self.short_handler()
#         else:
#             return self.middle_handler()

class PreemptiveStrike(baseState): #testing 2/25/22
    def __init__(self, agent):
        super().__init__(agent)
        self.started = False
        self.firstFlip = None
        self.secondFlip = None
        self.startTime = agent.time
        self.kickoff_type = getKickoffPosition(agent.me.location)
        # 0 == wide diagonal, 1 == short disgonal, 2 == middle
        agent.stubbornessTimer = 5
        self.onRight = True
        self.short_offset = 75
        self.setup()
        self.enemyGoal = Vector([0, 5200 * -sign(self.agent.team), 0])
        self.phase = 1
        # if agent.team == 0:
        #     self.KO_option = PreemptiveStrike_botpack(agent)
        # else:
        self.KO_option = None
        self.maintaining_speed = False
        self.first_recovery = None
        self.greedy = False
        self.greedy_req = 450
        self.final_flip_dist = 500

    def create_speed_flip_cancel(self, left=False):
        controls = []
        timers = []

        second_controller = SimpleControllerState()
        if not left:
            second_controller.steer = 1
        else:
            second_controller.steer = -1

        second_controller.throttle = 1
        second_controller.boost = True
        second_controller.jump = True
        second_controller.pitch = 1
        second_controller.handbrake = True
        controls.append(second_controller)
        timers.append(0.10)

        third_controller = SimpleControllerState()
        third_controller.jump = False
        third_controller.boost = True
        third_controller.throttle = 1
        third_controller.pitch = 1
        controls.append(third_controller)
        timers.append(self.agent.fakeDeltaTime * 2)

        fourth_controller = SimpleControllerState()
        # yaw = 1
        # if left:
        #     yaw = -1

        yaw = -1
        if left:
            yaw = 1

        fourth_controller.yaw = yaw
        # fourth_controller.roll = yaw
        fourth_controller.pitch = -1
        fourth_controller.jump = True
        fourth_controller.boost = True
        fourth_controller.throttle = 1
        controls.append(fourth_controller)
        timers.append(0.05)

        fifth_controller = SimpleControllerState()
        fifth_controller.yaw = -yaw
        # fifth_controller.roll = -yaw
        fifth_controller.pitch = 1
        fifth_controller.throttle = 1
        fifth_controller.boost = True
        fifth_controller.handbrake = False
        fifth_controller.jump = True
        controls.append(fifth_controller)
        timers.append(0.75)

        action = Divine_Mandate(self.agent, controls, timers)
        # print(type(action))
        return action

    def create_diagonal_speed_flip(self, left=False):
        controls = []
        timers = []
        # jump start
        first_controller = SimpleControllerState()
        if self.kickoff_type == 0:
            if self.onRight:
                first_controller.yaw = -1
            else:
                first_controller.yaw = 1

        first_controller.jump = True
        first_controller.boost = True
        first_controller.throttle = 1
        first_controller.pitch = -1
        first_controller.jump = True
        controls.append(first_controller)
        timers.append(0.1)

        # jump delay
        second_controller = SimpleControllerState()
        second_controller.jump = False
        second_controller.boost = True
        second_controller.throttle = 1
        if left:
            yaw = -0.75
        else:
            yaw = 0.75

        pitch = -0.25

        second_controller.yaw = yaw
        second_controller.pitch = pitch
        second_controller.jump = False

        controls.append(second_controller)
        timers.append(self.agent.fakeDeltaTime * 4)

        # jump flip
        third_controller = SimpleControllerState()
        third_controller.jump = True
        third_controller.boost = True
        third_controller.throttle = 1

        if left:
            yaw = -0.75
        else:
            yaw = 0.75

        pitch = -0.25

        third_controller.yaw = yaw
        third_controller.pitch = pitch
        controls.append(third_controller)
        timers.append(0.5)

        action = Divine_Mandate(self.agent, controls, timers)
        # print(type(action))
        return action

    def setup(self):
        # setup randomness like offsets to either side of the ball. Make sure it's slightly offset from middle so we can flip center
        # setup flips
        ball_local = (
            self.agent.ball.local_location
        )  # localizeVector(Vector([0, 0, 0]), self.agent.me)
        if self.kickoff_type == 0:
            if ball_local[1] > 0:
                # self.firstFlip = self.create_diagonal_speed_flip(left=True)
                # self.firstFlip = LeapOfFaith(self.agent,9)
                self.firstFlip = self.create_speed_flip_cancel(left=False)
                self.onRight = False
                # print("flipping left")
            else:
                # self.firstFlip = self.create_diagonal_speed_flip(left=False)
                # self.firstFlip = LeapOfFaith(self.agent, 10)
                self.firstFlip = self.create_speed_flip_cancel(left=True)
                self.onRight = True
                # print("flipping right")

        elif self.kickoff_type == 1:
            if ball_local[1] < 0:
                self.firstFlip = self.create_diagonal_speed_flip(left=False)
                self.onRight = True
                self.short_offset = -75 * sign(self.agent.team)
            else:
                self.firstFlip = self.create_diagonal_speed_flip(left=True)
                self.onRight = False
                self.short_offset = 75 * sign(self.agent.team)
                # print(f"on left and short offset == {self.short_offset}")

        else:
            # middle kickoff defaulting to right
            self.firstFlip = self.create_diagonal_speed_flip(left=True)
            # self.onRight shouldn't matter

    def wide_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            if distance2D(self.agent.me.location, self.agent.ball.location) > 3110:
                # return driveController(self.agent, self.enemyGoal+Vector([0,4000*sign(self.agent.team),0]),
                x_offset = 250 if self.agent.me.location[0] > self.agent.ball.location[0] else -250
                return driveController(
                    self.agent,
                    self.agent.ball.location + Vector([x_offset,0,0]),
                    #+ Vector([0, sign(self.agent.team) * -50, 0]),
                    #+ Vector([0, sign(self.agent.team) * -20, 0]),
                    0,
                    expedite=True,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 3

        # stage 3 - first flip
        if self.phase == 3:
            # if self.firstFlip == None:
            #     self.firstFlip = self.create_speed_flip_cancel(left=not self.onRight)
            if self.firstFlip.active:
                # print(f"first flip active: {str(self.firstFlip)} {self.agent.time} {self.firstFlip.targetCode}")
                return self.firstFlip.update()

            if not self.agent.onSurface:
                _controller = SimpleControllerState()
                (
                    _controller.steer,
                    _controller.yaw,
                    _controller.pitch,
                    _controller.roll,
                    _err,
                ) = point_at_position(
                    self.agent,
                    self.agent.me.location
                    + self.agent.me.velocity.normalize().flatten().scale(1000),
                )
                _controller.boost = True
                _controller.handbrake = True
                return _controller

            else:
                self.phase = 4
                # print(f"switched to stage 4! {self.agent.time}")

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:
            if distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist:
                #drive_target = self.agent.ball.location
                #if toLocal(self.agent.ball.location, self.agent.me)[0] > 0:
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    dummy_location = [35, 0, 0]
                else:
                    dummy_location = [-35, 0, 0]

                drive_target = self.agent.ball.location + Vector(dummy_location)
                return driveController(
                    self.agent,
                    drive_target,
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 5
                # print(f"switched to stage 5! {self.agent.time}")

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip is None and not self.greedy:
                self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(self.agent.closestEnemyToBall.location, self.agent.ball.location)
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    _code = 5
                else:
                    _code = 4

                self.secondFlip = LeapOfFaith(self.agent, 0, target=None) #_code
            if not self.greedy:
                controls = self.secondFlip.update()
                if not self.secondFlip.active:
                    self.retire()
            else:
                controls = driveController(
                    self.agent,
                    self.agent.ball.location,
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    kickoff=True,
                )
                controls.throttle = 0
            if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
                self.retire()
            return controls

    def short_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector(
                [self.short_offset, sign(self.agent.team) * 2800.0, 0]
            )
            if distance2D(self.agent.me.location, drive_target) > 555:
                return driveController(
                    self.agent,
                    drive_target,
                    0,
                    expedite=True,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 3

        # stage 2 - angle towards outside of ball
        if self.phase == 2:
            controls = SimpleControllerState()
            if not self.agent.onSurface:
                (
                    controls.steer,
                    controls.yaw,
                    controls.pitch,
                    controls.roll,
                    alignment_error,
                ) = point_at_position(
                    self.agent,
                    self.agent.me.location
                    + self.agent.me.velocity.normalize().flatten().scale(1000),
                )
                return controls
            else:
                self.phase = 3
        # stage 3 - first flip
        if self.phase == 3:
            if self.firstFlip.active:
                return self.firstFlip.update()
            if not self.agent.onSurface:
                _controller = SimpleControllerState()
                (
                    _controller.steer,
                    _controller.yaw,
                    _controller.pitch,
                    _controller.roll,
                    _err,
                ) = point_at_position(
                    self.agent,
                    self.agent.me.location
                    + self.agent.me.velocity.normalize().flatten().scale(1000),
                )
                _controller.boost = True
                _controller.handbrake = True
                return _controller
            else:
                self.phase = 4

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:
            if (
                distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist
                or not self.agent.onSurface
            ):
                drive_target = self.agent.ball.location
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    dummy_location = [45, 0, 0]
                else:
                    dummy_location = [-45, 0, 0]

                return driveController(
                    self.agent,
                    drive_target+Vector(dummy_location),
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 5

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip is None and not self.greedy:
                self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(
                    self.agent.closestEnemyToBall.location, self.agent.ball.location)
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    _code = 5
                else:
                    _code = 4
                self.secondFlip = LeapOfFaith(self.agent, 0, target=None)

            if not self.greedy:
                controls = self.secondFlip.update()
                if not self.secondFlip.active:
                    self.retire()
            else:
                controls = driveController(
                    self.agent,
                    self.agent.ball.location,
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    kickoff=True,
                )
                controls.throttle = 0
            if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
                self.retire()
            return controls

    def middle_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector([0, sign(self.agent.team) * 4015, 0])
            if distance2D(self.agent.me.location, drive_target) > 75:
                return driveController(
                    self.agent,
                    drive_target,
                    0,
                    expedite=True,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 2

        # stage 2 - angle towards outside of ball
        if self.phase == 2:
            drive_target = Vector([4500 * sign(self.agent.team), 0, 0])
            if (
                distance2D(self.agent.me.location, self.agent.ball.location) > 3875
            ):  # 3875:
                return driveController(
                    self.agent,
                    drive_target,
                    0,
                    expedite=True,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 3
        # stage 3 - first flip
        if self.phase == 3:
            if self.firstFlip.active:
                return self.firstFlip.update()
            else:
                if self.agent.onSurface:
                    self.phase = 4
                else:
                    controls = SimpleControllerState()
                    (
                        controls.steer,
                        controls.yaw,
                        controls.pitch,
                        controls.roll,
                        alignment_error,
                    ) = point_at_position(
                        self.agent,
                        self.agent.me.location
                        + self.agent.me.velocity.normalize().flatten().scale(1000),
                    )
                    return controls

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:

            if (
                distance2D(self.agent.me.location, self.agent.ball.location) > self.final_flip_dist
                or not self.agent.onSurface
            ):
                drive_target = self.agent.ball.location
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    dummy_location = [25, 0, 0]
                else:
                    dummy_location = [-25, 0, 0]

                return driveController(
                    self.agent,
                    drive_target + Vector(dummy_location),
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    maintainSpeed=self.maintaining_speed,
                    kickoff=True,
                )
            else:
                self.phase = 5

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip is None and not self.greedy:
                self.greedy = distance2D(self.agent.me.location, self.agent.ball.location) + self.greedy_req <= distance2D(
                    self.agent.closestEnemyToBall.location, self.agent.ball.location)
                if (self.agent.me.location - self.agent.ball.location)[0] > 0:
                    _code = 5
                else:
                    _code = 4
                # _code = 0
                self.secondFlip = LeapOfFaith(self.agent, 0, target=None)
            if not self.greedy:
                controls = self.secondFlip.update()
                if not self.secondFlip.active:
                    self.retire()
            else:
                controls = driveController(
                    self.agent,
                    self.agent.ball.location,
                    0,
                    expedite=not self.agent.superSonic,
                    flippant=False,
                    kickoff=True,
                )
                controls.throttle = 0
            if self.agent.ball.location[0] != 0 or self.agent.ball.location[1] != 0:
                self.retire()
            return controls

    def retire(self):
        self.active = False
        if self.secondFlip and self.secondFlip.active:
            self.agent.activeState = self.secondFlip
            # self.agent.activeState = None
            # print(f"retiring on stage {self.phase} {self.agent.time}")

    def update(self):
        if not self.agent.gameInfo.is_round_active:
            self.setup()

        if not self.agent.gameInfo.is_kickoff_pause:
            # print(f"retiring due to kickoff pause")
            self.retire()

        if self.KO_option is not None:
            if not self.KO_option.active:
                self.retire()
            return self.KO_option.update()

        # 0 == wide diagonal, 1 == short disgonal, 2 == middle
        if self.kickoff_type == 0:
            return self.wide_handler()
        elif self.kickoff_type == 1:
            return self.short_handler()
        else:
            return self.middle_handler()

""

# class PreemptiveStrike(baseState):  # real kickoff
#     def __init__(self, agent):
#         self.agent = agent
#         self.fakeDeltaTime = agent.fakeDeltaTime
#         self.started = False
#         self.firstFlip = None
#         self.secondFlip = None
#         self.active = True
#         self.startTime = agent.time
#         self.kickoff_type = getKickoffPosition(agent.me.location)
#         agent.stubbornessTimer = 5
#         self.onRight = True
#         self.short_offset = 75
#         self.setup()
#         self.enemyGoal = Vector([0, 5200 * -sign(self.agent.team), 0])
#         self.phase = 1
#         self.KO_option = None
#         self.maintaining_speed = False
#         self.first_recovery = None
#         self.queued_retire = False
#
#
#     def create_speed_flip_cancel(self, left=False):
#         controls = []
#         timers = []
#
#         second_controller = SimpleControllerState()
#         if not left:
#             second_controller.steer = 1
#         else:
#             second_controller.steer = -1
#
#         second_controller.throttle = 1
#         second_controller.boost = True
#         second_controller.jump = True
#         second_controller.pitch = 1
#         second_controller.handbrake = True
#         controls.append(second_controller)
#         timers.append(0.10)
#
#         third_controller = SimpleControllerState()
#         third_controller.jump = False
#         third_controller.boost = True
#         third_controller.throttle = 1
#         third_controller.pitch = 1
#         controls.append(third_controller)
#         timers.append(self.fakeDeltaTime * 1.5)
#
#         fourth_controller = SimpleControllerState()
#
#         yaw = -1
#         if left:
#             yaw = 1
#
#         fourth_controller.yaw = yaw
#         # fourth_controller.roll = yaw
#         fourth_controller.pitch = -1
#         fourth_controller.jump = True
#         fourth_controller.boost = True
#         fourth_controller.throttle = 1
#         controls.append(fourth_controller)
#         timers.append(0.05)
#
#         fifth_controller = SimpleControllerState()
#         fifth_controller.yaw = -yaw
#         # fifth_controller.roll = -yaw
#         fifth_controller.pitch = 1
#         fifth_controller.throttle = 1
#         fifth_controller.boost = True
#         fifth_controller.handbrake = False
#         fifth_controller.jump = True
#         controls.append(fifth_controller)
#         timers.append(0.75)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def create_diagonal_speed_flip(self, left=False):
#         controls = []
#         timers = []
#         # jump start
#         first_controller = SimpleControllerState()
#         if self.kickoff_type == 0:
#             if self.onRight:
#                 first_controller.yaw = -1
#             else:
#                 first_controller.yaw = 1
#
#         first_controller.jump = True
#         first_controller.boost = True
#         first_controller.throttle = 1
#         first_controller.pitch = -1
#         first_controller.jump = True
#         controls.append(first_controller)
#         timers.append(0.1)
#
#         # jump delay
#         second_controller = SimpleControllerState()
#         second_controller.jump = False
#         second_controller.boost = True
#         second_controller.throttle = 1
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         second_controller.yaw = yaw
#         second_controller.pitch = pitch
#         second_controller.jump = False
#
#         controls.append(second_controller)
#         timers.append(self.fakeDeltaTime * 2)
#
#         # jump flip
#         third_controller = SimpleControllerState()
#         third_controller.jump = True
#         third_controller.boost = True
#         third_controller.throttle = 1
#
#         if left:
#             yaw = -0.75
#         else:
#             yaw = 0.75
#
#         pitch = -0.25
#
#         third_controller.yaw = yaw
#         third_controller.pitch = pitch
#         controls.append(third_controller)
#         timers.append(0.5)
#
#         action = Divine_Mandate(self.agent, controls, timers)
#         # print(type(action))
#         return action
#
#     def setup(self):
#         # setup randomness like offsets to either side of the ball. Make sure it's slightly offset from middle so we can flip center
#         # setup flips
#         ball_local = (
#             self.agent.ball.local_location
#         )  # localizeVector(Vector([0, 0, 0]), self.agent.me)
#         if self.kickoff_type == 0:
#             if ball_local[1] > 0:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 # self.firstFlip = LeapOfFaith(self.agent,9)
#                 self.firstFlip = self.create_speed_flip_cancel(left=False)
#                 self.onRight = False
#                 # print("flipping left")
#             else:
#                 # self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 # self.firstFlip = LeapOfFaith(self.agent, 10)
#                 self.firstFlip = self.create_speed_flip_cancel(left=True)
#                 self.onRight = True
#                 # print("flipping right")
#
#         elif self.kickoff_type == 1:
#             if ball_local[1] < 0:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=False)
#                 self.onRight = True
#                 self.short_offset = -50 * sign(self.agent.team)
#             else:
#                 self.firstFlip = self.create_diagonal_speed_flip(left=True)
#                 self.onRight = False
#                 self.short_offset = 50 * sign(self.agent.team)
#                 # print(f"on left and short offset == {self.short_offset}")
#
#         else:
#             # middle kickoff defaulting to right
#             self.firstFlip = self.create_diagonal_speed_flip(left=True)
#             # self.onRight shouldn't matter
#
#     def wide_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > 3150:
#                 if self.agent.me.location[1] < 0:
#                     y_off = -40
#                 else:
#                     y_off = 40
#
#                 return driveController(
#                     self.agent,
#                     self.agent.ball.location + Vector([0, y_off, 0]),
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 return self.firstFlip.update()
#                 # controls = self.firstFlip.update()
#                 # if self.agent.currentSpd > 2210:
#                 #     controls.boost = False
#                 # return controls
#
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#
#             else:
#                 self.phase = 4
#                 # print(f"switched to stage 4! {self.agent.time}")
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if distance2D(self.agent.me.location, self.agent.ball.location) > 550:
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [35, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal,self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(distance2D(self.agent.me.location,dummy_location)*.5)
#                 else:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [-35, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#                 # print(f"switched to stage 5! {self.agent.time}")
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             # if distance2D(self.agent.closestEnemyToBall.location,self.agent.ball.location) < 600:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 5
#                 else:
#                     _code = 4
#                 #     _code = 4
#                 # else:
#                 #     _code = 5
#
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def short_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector(
#                 [self.short_offset, sign(self.agent.team) * 2850.0, 0]
#             )
#             if distance2D(self.agent.me.location, drive_target) > 575:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             controls = SimpleControllerState()
#             if not self.agent.onSurface:
#                 (
#                     controls.steer,
#                     controls.yaw,
#                     controls.pitch,
#                     controls.roll,
#                     alignment_error,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 return controls
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 controls = self.firstFlip.update()
#                 if self.agent.currentSpd > 2210:
#                     controls.boost = False
#                 return controls
#                 # return self.firstFlip.update()
#             if not self.agent.onSurface:
#                 _controller = SimpleControllerState()
#                 (
#                     _controller.steer,
#                     _controller.yaw,
#                     _controller.pitch,
#                     _controller.roll,
#                     _err,
#                 ) = point_at_position(
#                     self.agent,
#                     self.agent.me.location
#                     + self.agent.me.velocity.normalize().flatten().scale(1000),
#                 )
#                 _controller.boost = True
#                 _controller.handbrake = True
#                 return _controller
#             else:
#                 self.phase = 4
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 550
#                 or not self.agent.onSurface
#             ):
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [60, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 else:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [-60, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def middle_handler(self):
#         # stage 1 - drive to boost pad
#         if self.phase == 1:
#             drive_target = Vector([0, sign(self.agent.team) * 4000, 0])
#             if distance2D(self.agent.me.location, drive_target) > 75:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 2
#
#         # stage 2 - angle towards outside of ball
#         if self.phase == 2:
#             drive_target = Vector([4500 * sign(self.agent.team), 0, 0])
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 3850
#             ):  # 3875:
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=True,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 3
#         # stage 3 - first flip
#         if self.phase == 3:
#             if self.firstFlip.active:
#                 controls = self.firstFlip.update()
#                 if self.agent.currentSpd > 2210:
#                     controls.boost = False
#                 return controls
#                 # return self.firstFlip.update()
#             else:
#                 if self.agent.onSurface:
#                     self.phase = 4
#                 else:
#                     controls = SimpleControllerState()
#                     (
#                         controls.steer,
#                         controls.yaw,
#                         controls.pitch,
#                         controls.roll,
#                         alignment_error,
#                     ) = point_at_position(
#                         self.agent,
#                         self.agent.me.location
#                         + self.agent.me.velocity.normalize().flatten().scale(1000),
#                     )
#                     return controls
#
#         # stage 4 - aim towards just offcenter of ball
#         if self.phase == 4:
#
#             if (
#                 distance2D(self.agent.me.location, self.agent.ball.location) > 550
#                 or not self.agent.onSurface
#             ):
#                 if self.agent.me.location[0] > self.agent.ball.location[0]:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [45, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#                 else:
#                     dummy_location = self.agent.ball.location + Vector(
#                         [-45, 120 * sign(self.agent.team), 0]
#                     )
#                     # _direction = direction(self.enemyGoal, self.agent.ball.location)
#                     drive_target = dummy_location  # + _direction.scale(
#                     # distance2D(self.agent.me.location, dummy_location) * .5)
#
#                 return driveController(
#                     self.agent,
#                     drive_target,
#                     0,
#                     expedite=not self.agent.superSonic,
#                     flippant=False,
#                     maintainSpeed=self.maintaining_speed,
#                     kickoff=True,
#                 )
#             else:
#                 self.phase = 5
#
#         # stage 5 - flip through center and end kickoff
#         # 4 flip left, 5 flip right
#         if self.phase == 5:
#             if self.secondFlip == None:
#                 if (
#                     self.agent.team == 0
#                     and self.agent.me.location[0] < self.agent.ball.location[0]
#                     or self.agent.team == 1
#                     and self.agent.me.location[0] > self.agent.ball.location[0]
#                 ):
#                     _code = 4
#                 else:
#                     _code = 5
#                 # _code = 0
#                 self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
#             controls = self.secondFlip.update()
#             if not self.secondFlip.active:
#                 self.retire()
#             return controls
#
#     def retire(self):
#         if (
#             not self.secondFlip
#             or not self.secondFlip.active
#             or self.agent.time - self.startTime > 3
#         ):
#             self.active = False
#         else:
#             self.queued_retire = True
#
#     def update(self):
#         if not self.agent.gameInfo.is_round_active:
#             self.setup()
#
#         if not self.agent.gameInfo.is_kickoff_pause or self.agent.ball.location.flatten() != Vector(
#             [0, 0, 0]
#         ):
#             # print(f"retiring due to kickoff pause")
#             self.retire()
#
#         if self.queued_retire:
#             self.retire()
#
#         if self.KO_option != None:
#             if not self.KO_option.active:
#                 self.retire()
#             return self.KO_option.update()
#
#         # 0 == wide diagonal, 1 == short disgonal, 2 == middle
#         if self.kickoff_type == 0:
#             return self.wide_handler()
#         elif self.kickoff_type == 1:
#             return self.short_handler()
#         else:
#             return self.middle_handler()


class DivineGrace(baseState):
    def __init__(self, agent):
        super().__init__(agent)
        # self.run_simulation()
        # print(f"default elevation is: {self.agent.defaultElevation}")
        self.x_limit = 4096 - self.agent.defaultElevation
        self.y_limit = 5120 - self.agent.defaultElevation
        self.ground_limit = self.agent.defaultElevation
        self.ceiling_limit = 2044 - self.agent.defaultElevation
        self.ideal_orientation = Vector([0, 0, 0])
        # self.tick_length = 3
        # self.squash_index = 0
        # self.update_count = 0
        # self.collision_timer = 0
        # self.collision_location = Vector([0, 0, 0])
        # self.aim_direction = None
        self.recovery_limit = 1.25

    def get_roll_value(self):
        if self.agent.roll_type == 1:
            return turnController(
                -self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
            )  # will make bot roll top up

        elif self.agent.roll_type == 2:
            return turnController(
                self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
            )  # will make bot roll top down

        elif self.agent.roll_type == 3:
            return turnController(
                -(3.1415 / 2) - self.agent.me.rotation[2],
                self.agent.me.rotational_velocity[0] / 4,
            )  # will make bot roll top left

        elif self.agent.roll_type == 4:
            return turnController(
                3.1415 / 2 - self.agent.me.rotation[2],
                self.agent.me.rotational_velocity[0] / 4,
            )  # will make bot roll top right

    def get_controls(self):
        controller_state = SimpleControllerState()

        aim_vector = self.agent.collision_location - self.agent.me.location
        if self.agent.collision_timer <= self.recovery_limit:
            aim_vector.data[self.agent.squash_index] = 0

        if (
            self.agent.aim_direction is not None
            and self.agent.collision_timer > self.recovery_limit
            and self.agent.me.location[2] > 100
        ):
            aim_vector = (
                self.agent.aim_direction
            )  # (self.aim_direction + aim_vector.normalize()).normalize()

        aim_vector = aim_vector.normalize()

        align_car_to(controller_state, self.agent.me.avelocity, aim_vector, self.agent)

        # print(self.collision_timer)
        if self.agent.collision_timer > self.recovery_limit:
            if self.agent._forward.dotProduct(aim_vector) > 0.7:
                if self.agent.me.velocity[2] > -1700 or self.agent.boostMonster:
                    if self.agent.me.boostLevel > 20:
                        controller_state.boost = True

        else:
            controller_state.roll = self.get_roll_value()

        if self.agent.time - self.agent.flipTimer < 0.5:
            controller_state.roll = 0
            controller_state.pitch = 0
            controller_state.yaw = 0

        controller_state.throttle = 1

        return controller_state

    # def run_simulation(self):
    #     self.update_count = 5
    #     simulated_location = self.agent.me.location.scale(1)
    #     simulated_velocity = self.agent.me.velocity.scale(1)
    #     simulated_time = 0
    #     self.aim_direction = None
    #     while (
    #         simulated_time < 10
    #     ):  # 0 gravity could lead to infinite loop! may want to add hard limiters
    #         simulated_velocity = simulated_velocity + Vector(
    #             [0, 0, self.agent.gravity]
    #         ).scale((self.agent.fakeDeltaTime) * self.tick_length)
    #         if simulated_velocity.magnitude() > 2300:
    #             simulated_velocity = simulated_velocity.normalize().scale(2300)
    #         simulated_location = simulated_location + simulated_velocity.scale(
    #             (self.agent.fakeDeltaTime) * self.tick_length
    #         )
    #         simulated_time += self.agent.fakeDeltaTime * self.tick_length
    #         if simulated_location[2] >= self.ceiling_limit:
    #             self.roll_type = 2
    #             self.squash_index = 2
    #             # print(f"ceiling recovery {self.agent.time}")
    #             self.aim_direction = Vector([0, 0, 1])
    #             break
    #         if simulated_location[2] <= self.ground_limit:
    #             self.roll_type = 1
    #             self.squash_index = 2
    #
    #             # print(f"ground recovery {self.agent.time}")
    #             break
    #
    #         if simulated_location[0] <= -self.x_limit:
    #             # on blue's right wall
    #             # print(f"side wall recovery {self.agent.time}")
    #             self.squash_index = 0
    #             if simulated_velocity[1] < 0:
    #                 # need to keep top right
    #                 self.roll_type = 4
    #
    #             else:
    #                 # need to keep top left
    #                 self.roll_type = 3
    #             break
    #
    #         if simulated_location[0] >= self.x_limit:
    #             # on blue's left wall
    #             self.squash_index = 0
    #             # print(f"side wall recovery {self.agent.time}")
    #             if simulated_velocity[1] < 0:
    #                 # need to keep top left
    #                 self.roll_type = 3
    #
    #             else:
    #                 # need to keep top right
    #                 self.roll_type = 4
    #             break
    #
    #         if simulated_location[1] <= -self.y_limit:
    #             # on blue's backboard
    #             # print(f"back wall recovery {self.agent.time}")
    #             if abs(simulated_location[0]) < 893:
    #                 if simulated_location[2] < 642:
    #                     self.roll_type = 1
    #                     self.squash_index = 2
    #                     break
    #             self.squash_index = 1
    #             if simulated_velocity[0] < 0:
    #                 # need to keep top left
    #                 self.roll_type = 3
    #
    #             else:
    #                 # need to keep top right
    #                 self.roll_type = 4
    #             break
    #
    #         if simulated_location[1] >= self.y_limit:
    #             # on orange's backboard
    #             # print(f"side wall recovery {self.agent.time}")
    #             if abs(simulated_location[0]) < 893:
    #                 if simulated_location[2] < 642:
    #                     self.roll_type = 1
    #                     self.squash_index = 2
    #                     break
    #             self.squash_index = 1
    #             if simulated_velocity[0] < 0:
    #                 # need to keep top right
    #                 self.roll_type = 4
    #
    #             else:
    #                 # need to keep top left
    #                 self.roll_type = 3
    #             break
    #     if simulated_time >= 10:
    #         self.roll_type = 1
    #         self.squash_index = 2
    #
    #     if self.aim_direction == None:
    #         self.aim_direction = Vector([0, 0, -1])
    #
    #     self.collision_timer = simulated_time
    #     self.collision_location = simulated_location

    def update(self):
        # self.update_count -= 1
        # if self.update_count < 0:
        #     self.run_simulation()

        controller_state = self.get_controls()
        if (
            self.agent.onSurface
            or self.agent.me.location[1] <= self.agent.recovery_height
        ):
            self.active = False

        # controller_state = SimpleControllerState()
        controller_state.throttle = 1

        return controller_state


# class DivineGrace(baseState): #mooonbots version
#     def __init__(self, agent):
#         self.agent = agent
#         self.active = True
#         # self.run_simulation()
#         # print(f"default elevation is: {self.agent.defaultElevation}")
#         self.x_limit = 4096 - self.agent.defaultElevation
#         self.y_limit = 5120 - self.agent.defaultElevation
#         self.ground_limit = self.agent.defaultElevation
#         self.ceiling_limit = 2044 - self.agent.defaultElevation
#         self.ideal_orientation = Vector([0, 0, 0])
#         self.tick_length = 5
#         self.squash_index = 0
#         self.update_count = 0
#         self.collision_timer = 0
#         self.collision_location = Vector([0, 0, 0])
#         self.aim_direction = None
#         self.recovery_limit = 1
#
#     def get_roll_value(self):
#         if self.roll_type == 1:
#             return turnController(
#                 -self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
#             )  # will make bot roll top up
#
#         elif self.roll_type == 2:
#             return turnController(
#                 self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
#             )  # will make bot roll top down
#
#         elif self.roll_type == 3:
#             return turnController(
#                 -(3.1415 / 2) - self.agent.me.rotation[2],
#                 self.agent.me.rotational_velocity[0] / 4,
#             )  # will make bot roll top left
#
#         elif self.roll_type == 4:
#             return turnController(
#                 3.1415 / 2 - self.agent.me.rotation[2],
#                 self.agent.me.rotational_velocity[0] / 4,
#             )  # will make bot roll top right
#
#     def get_controls(self):
#         controller_state = SimpleControllerState()
#
#         aim_vector = self.collision_location - self.agent.me.location
#         if self.collision_timer <= self.recovery_limit:
#             aim_vector.data[self.squash_index] = 0
#
#         if self.aim_direction != None:
#             if self.collision_timer > self.recovery_limit:
#                 aim_vector = (self.aim_direction + aim_vector.normalize()).normalize()
#
#         aim_vector = aim_vector.normalize()
#
#         align_car_to(controller_state, self.agent.me.avelocity, aim_vector, self.agent)
#
#         # print(self.collision_timer)
#         if self.collision_timer > self.recovery_limit:
#             if self.agent._forward.dotProduct(aim_vector) > 0.7:
#                 if abs(self.agent.me.velocity[2]) < 1000 or self.agent.boostMonster:
#                     if self.agent.me.boostLevel > 20:
#                         controller_state.boost = True
#
#         controller_state.throttle = 1
#         controller_state.roll = self.get_roll_value()
#         return controller_state
#
#     def run_simulation(self):
#         self.update_count = 5
#         simulated_location = self.agent.me.location.scale(1)
#         simulated_velocity = self.agent.me.velocity.scale(1)
#         simulated_time = 0
#         self.aim_direction = None
#         while (
#                 simulated_time < 10
#         ):  # 0 gravity could lead to infinite loop! may want to add hard limiters
#             simulated_velocity = simulated_velocity + Vector(
#                 [0, 0, self.agent.gravity]
#             ).scale((self.agent.fakeDeltaTime) * self.tick_length)
#             if simulated_velocity.magnitude() > 2300:
#                 simulated_velocity = simulated_velocity.normalize().scale(2300)
#             simulated_location = simulated_location + simulated_velocity.scale(
#                 (self.agent.fakeDeltaTime) * self.tick_length
#             )
#             simulated_time += self.agent.fakeDeltaTime * self.tick_length
#             if simulated_location[2] >= self.ceiling_limit:
#                 self.roll_type = 2
#                 self.squash_index = 2
#                 # print(f"ceiling recovery {self.agent.time}")
#                 self.aim_direction = Vector([0, 0, 1])
#                 break
#             if simulated_location[2] <= self.ground_limit:
#                 self.roll_type = 1
#                 self.squash_index = 2
#
#                 # print(f"ground recovery {self.agent.time}")
#                 break
#
#             if simulated_location[0] <= -self.x_limit:
#                 # on blue's right wall
#                 # print(f"side wall recovery {self.agent.time}")
#                 self.squash_index = 0
#                 if simulated_velocity[1] < 0:
#                     # need to keep top right
#                     self.roll_type = 4
#
#                 else:
#                     # need to keep top left
#                     self.roll_type = 3
#                 break
#
#             if simulated_location[0] >= self.x_limit:
#                 # on blue's left wall
#                 self.squash_index = 0
#                 # print(f"side wall recovery {self.agent.time}")
#                 if simulated_velocity[1] < 0:
#                     # need to keep top left
#                     self.roll_type = 3
#
#                 else:
#                     # need to keep top right
#                     self.roll_type = 4
#                 break
#
#             if simulated_location[1] <= -self.y_limit:
#                 # on blue's backboard
#                 # print(f"back wall recovery {self.agent.time}")
#                 if abs(simulated_location[0]) < 893:
#                     if simulated_location[2] < 642:
#                         self.roll_type = 1
#                         self.squash_index = 2
#                         break
#                 self.squash_index = 1
#                 if simulated_velocity[0] < 0:
#                     # need to keep top left
#                     self.roll_type = 3
#
#                 else:
#                     # need to keep top right
#                     self.roll_type = 4
#                 break
#
#             if simulated_location[1] >= self.y_limit:
#                 # on orange's backboard
#                 # print(f"side wall recovery {self.agent.time}")
#                 if abs(simulated_location[0]) < 893:
#                     if simulated_location[2] < 642:
#                         self.roll_type = 1
#                         self.squash_index = 2
#                         break
#                 self.squash_index = 1
#                 if simulated_velocity[0] < 0:
#                     # need to keep top right
#                     self.roll_type = 4
#
#                 else:
#                     # need to keep top left
#                     self.roll_type = 3
#                 break
#         if simulated_time >= 10:
#             self.roll_type = 1
#             self.squash_index = 2
#
#         if self.aim_direction == None:
#             self.aim_direction = Vector([0, 0, -1])
#
#         self.collision_timer = simulated_time
#         self.collision_location = simulated_location
#
#     def update(self):
#         self.update_count -= 1
#         if self.update_count < 0:
#             self.run_simulation()
#         controller_state = self.get_controls()
#         if (
#             self.agent.onSurface
#             or self.agent.me.location[1] <= self.agent.recovery_height
#         ):
#             self.active = False
#
#         # controller_state = SimpleControllerState()
#
#         return controller_state


# class WardAgainstEvil(baseState):
#     def __init__(self, agent):
#         self.agent = agent
#         self.active = True
#         self.timeCreated = self.agent.time
#
#     def update(self):
#         # print(f"We're too scared! {self.agent.time}")
#         return scaredyCat(self.agent)


class WardAgainstEvil(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        if goalie_shot(self.agent, self.agent.currentHit):
            return ShellTime(self.agent)

        else:
            return gate(self.agent)


class BlessingOfDexterity(baseState):
    def __init__(self, agent):
        super().__init__(agent)
        self.firstJump = False
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
            controller_state.throttle = 1
            if timer < 0.15:
                controller_state.pitch = 1

            else:
                controller_state.pitch = -1
                controller_state.roll = 1

            if timer > 0.8:
                controller_state.roll = 0
            if timer > 1.25:
                self.active = False
            return controller_state

        else:
            self.agent.log.append(
                "halfFlip else conditional called in update. This should not be happening"
            )


class Do_No_Evil(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        if self.agent.scorePred is None:
            self.active = False

        elif (
            self.agent.scorePred.time - self.agent.time
        ) + 0.5 > self.agent.enemyBallInterceptDelay:
            self.active = False
        # print("B)")
        return arrest_movement(self.agent)


class Chase(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        if not kickOffTest(self.agent):
            return efficientMover(self.agent, self.agent.ball, self.agent.maxSpd)
        else:
            self.active = False
            self.agent.activeState = PreemptiveStrike(self.agent)
            return self.agent.activeState.update()


class HeetSeekerDefense(baseState):
    def update(self):
        return goFarPost(self.agent)


class Goalie(baseState):
    def update(self):
        distMin = 2000
        if self.agent.ignore_kickoffs:
            distMin = 3000
        if (
            distance2D(
                Vector([0, 5200 * sign(self.agent.team), 0]), self.agent.ball.location
            )
            < distMin
            or distance2D(
                Vector([0, 5200 * sign(self.agent.team), 0]),
                self.agent.currentHit.pred_vector,
            )
            < distMin
        ):
            self.agent.rotationNumber = 1
            if self.agent.currentHit.hit_type == 5:
                self.agent.activeState = self.agent.currentHit.aerialState
                return self.agent.activeState.update()
            return ShellTime(self.agent)

        offensive = (
            self.agent.offensive
        )  # sign(self.agent.team) * self.agent.ball.location[1] < 0
        if offensive and self.agent.me.boostLevel < self.agent.boostThreshold:
            target_boost = boost_suggester(self.agent, mode=0, buffer=3000)
            if target_boost is not None:
                target = target_boost.location.scale(1)
                self.agent.update_action(
                    {"type": "BOOST", "target": target_boost.index}
                )
                return driveController(
                    self.agent, target.flatten(), 0, flips_enabled=True
                )
        self.agent.rotationNumber = 3
        self.agent.update_action({"type": "DEFEND"})
        return gate(self.agent, hurry=False)


class BlessingOfSafety(baseState):
    def update(self):
        distMin = 1500
        player_goal = Vector([0,5120 * sign(self.agent.team),0])
        dist = distance2D(self.agent.ball.location, player_goal)
        offensive = self.agent.offensive
        if (not offensive and butterZone(self.agent.ball.location)) or (self.agent.goalPred is not None and dist < 3000) or (dist < distMin):
            self.agent.rotationNumber = 1
            createBox(self.agent, self.agent.currentHit.pred_vector)
            if self.agent.currentHit.hit_type == 5:
                self.agent.activeState = self.agent.currentHit.aerialState
                return self.agent.activeState.update()
            return ShellTime(self.agent)

        if self.agent.rotationNumber == 2:
            # if len(self.agent.allies) == 1 and self.agent.team == 0:
            #     return playBack(self.agent, buffer=4500)
            #if len(self.agent.allies) > 0:
            if len(self.agent.allies) > 1:
                # testing
                if self.agent.lastMan != self.agent.me.location:
                    return secondManPositioning(self.agent)
                else:
                    return thirdManPositioning(self.agent)
            # print(f"we here {self.agent.time}")
            return playBack(self.agent)
        else:
            #if len(self.agent.allies) > 0:
            if len(self.agent.allies) > 1:
                return thirdManPositioning(self.agent)
                # return secondManPositioning(self.agent)
            else:
                return playBack(self.agent)
        print(f"getting caught by playback {self.agent.time}")
        return playBack(self.agent)


def halfFlipStateManager(agent):
    if agent.activeState.active == False:
        agent.activeState = BlessingOfDexterity(agent)

    else:
        if type(agent.activeState) != BlessingOfDexterity:
            agent.activeState = BlessingOfDexterity(agent)


class Holding_pattern(baseState):
    def __init__(self, agent):
        super().__init__(agent)

    def update(self):
        if (
            self.agent.me.boostLevel < self.agent.boostThreshold
            and self.agent.goalPred is None
        ):
            return linger(self.agent)

        if self.agent.me.location[1] * sign(self.agent.team) < self.agent.ball.location[
            1
        ] * sign(self.agent.team):
            if abs(self.agent.me.location[1]) < 4000:
                return smart_retreat(self.agent)

        # if self.agent.goalPred != None or self.agent.ballDelay < 1.5:
        action = ShellTime(self.agent)
        # if self.agent.ballDelay > 1.5 and self.agent.me.location[1] * sign(self.agent.team) > \
        #         self.agent.ball.location[1] * sign(self.agent.team):
        if self.agent.goalPred is None:
            action.boost = False
        return action


class soloDefense(baseState):
    def update(self):
        if (
            distance2D(
                Vector([0, 5200 * sign(self.agent.team), 200]),
                convertStructLocationToVector(self.agent.selectedBallPred),
            )
            < 1500
        ):
            return ShellTime(self.agent)
        else:
            return playBack(self.agent)


class ScaleTheWalls(baseState):
    def update(self):
        return handleWallShot(self.agent)


class AngelicEmbrace(baseState):
    def update(self):
        return carry_flick_new(self.agent)


def parseCarInfo(carList, index, _max=False):
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


def state_manager():
    return time()


def aerialStateManager(agent):
    center = Vector([0, 5500 * -sign(agent.team), 200])

    if agent.ball.location[2] < 110:
        car_state = CarState(
            physics=Physics(
                velocity=Vector3(z=0, x=0, y=0), location=Vector3(0, 0, 17.1)
            )
        )
        ball_state = BallState(
            physics=Physics(
                velocity=Vector3(
                    z=1550,
                    x=random.randrange(-1500, 1500),
                    y=random.randrange(-1500, 1500),
                ),
                location=Vector3(0, 0, 350),
            )
        )
        game_state = GameState(cars={agent.index: car_state}, ball=ball_state)
        agent.set_game_state(game_state)
        agent.activeState = None

    if type(agent.activeState) != Wings_Of_Justice or not agent.activeState.active:

        pred = agent.ballPred.slices[0]
        for i in range(0, agent.ballPred.num_slices):
            if i > 60 and i % 3 != 0:
                continue

            pred = agent.ballPred.slices[i]
            tth = pred.game_seconds - agent.gameInfo.seconds_elapsed
            if tth <= 0:
                continue

            if agent.onSurface:
                if pred.physics.location.z < 300:
                    continue

            pred_vec = convertStructLocationToVector(pred)
            if findDistance(agent.me.location, pred_vec) < 2300 * tth:
                _direction = direction(center, pred_vec).flatten()
                positioningOffset = 90
                aim_loc = pred_vec - _direction.scale(90)
                tempAerial = Wings_Of_Justice(agent, pred, aim_loc, tth)
                if tempAerial.active:
                    break
        if tempAerial.active:
            agent.activeState = tempAerial


def demoTest(agent):
    targ = findEnemyClosestToLocation(agent, agent.ball.location)[0]
    return demoEnemyCar(agent, targ)


def air_hog_manager(agent):
    agentType = type(agent.activeState)
    if (
        agentType != PreemptiveStrike
        or agentType == PreemptiveStrike
        and not agent.activeState.active
    ):

        if not kickOffTest(agent):
            if locked_in(agent, agentType):
                return

            if agent.goalPred is not None:
                agent.contested = True
                agent.enemyAttacking = True
            fastesthit = agent.sorted_hits[0]  # find_soonest_hit(agent)
            hit = fastesthit

            if (
                hit.hit_type == 2
                and abs(agent.me.location[1]) > 5000
                and abs(agent.me.location[0]) < 900
                and len(agent.sorted_hits) > 1
            ):
                fastesthit = agent.sorted_hits[1]
                hit = fastesthit

            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                agent.contested = True

            if agent.goalPred is not None:
                agent.contested = True
                agent.enemyAttacking = True

            if hit.hit_type == 5:
                if agentType != Wings_Of_Justice:
                    agent.activeState = hit.aerialState  # .create_copy()
                return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            if agent.dribbling:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if boostOpportunity[1] in agent.my_corners:
                        getBoost = True
                    if getBoost:
                        if agentType != HeavenlyReprieve:
                            agent.activeState = HeavenlyReprieve(
                                agent, boostOpportunity[0]
                            )
                        return

            if agent.activeState != Holding_pattern:
                agent.activeState = Holding_pattern(agent)

        else:
            agent.activeState = PreemptiveStrike(agent)


def newTeamStateManager(agent):
    agentType = type(agent.activeState)
    if (
        agentType != PreemptiveStrike
        or agentType == PreemptiveStrike
        and not agent.activeState.active
    ):

        if not kickOffTest(agent):

            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball.location)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me.location)

            if locked_in(agent, agentType):
                if agent.rotationNumber < 2 and agent.currentHit is not None:
                    createSphere(agent, agent.currentHit.pred_vector)
                return

            fastesthit = agent.sorted_hits[0]  # find_soonest_hit(agent)
            hit = fastesthit

            if agent.dribbler:
                if hit.hit_type != 0:
                    for h in agent.sorted_hits:
                        if h.hit_type == 0:
                            hit = h
                            break

            if (
                hit.hit_type == 2
                and abs(agent.me.location[1]) > 5000
                and abs(agent.me.location[0]) < 900
                and len(agent.sorted_hits) > 1
            ):
                fastesthit = agent.sorted_hits[1]
                hit = fastesthit

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            agent.scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                # if agent.enemyAttacking:
                agent.contested = True

            if agent.goalPred is not None:
                agent.contested = True
                agent.enemyAttacking = True

            # if butterZone(hit.pred_vector):
            #     agent.contested = True
            #     agent.enemyAttacking = True

            if hit.hit_type == 5:
                if (
                    not agent.onSurface or hit.aerialState.launcher is not None
                ) and hit.aerialState.active:
                    if agentType != Wings_Of_Justice:
                        agent.activeState = hit.aerialState  # .create_copy()
                    return

                # if len(agent.sorted_hits) > 1 and not agent.boostMonster:
                #     if (
                #         agent.sorted_hits[1].prediction_time
                #         - agent.sorted_hits[0].prediction_time
                #         < 0.5
                #     ):
                #         fastesthit = agent.sorted_hits[1]
                #         hit = fastesthit
                #         tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            if agent.demo_monster:
                agent.currentHit = hit
                agent.ballDelay = tempDelay
                if agent.activeState != Divine_Retribution:
                    agent.activeState = Divine_Retribution(agent)
                return

            lastMan = agent.lastMan
            catchViable = False
            inclusive_team = []
            _inclusive_team = agent.allies[:]
            # ignore_types = ["DEFEND","DEMO","BOOST"]
            ignore_types = ["DEFEND"]
            removals = []
            for i in range(len(inclusive_team)):
                if _inclusive_team[i].index in agent.ally_actions:
                    if agent.ally_actions["action"]["type"] not in ignore_types:
                        inclusive_team.append(_inclusive_team[i])

            inclusive_team.append(agent.me)
            inclusive_team = sorted(inclusive_team, key=lambda x: x.index)
            offensive = agent.offensive

            if not agent.gameInfo.is_round_active or agent.gameInfo.is_kickoff_pause:
                man = 2
                if agent.me.location == agent.lastMan:
                    man = 3
                agent.rotationNumber = man

                agent.currentHit = fastesthit
                agent.ballDelay = fastesthit.time_difference()
                if man == 2:
                    if agentType != Kickoff_Boosties:
                        agent.activeState = Kickoff_Boosties(agent)
                else:
                    if agentType != BlessingOfSafety:
                        agent.activeState = BlessingOfSafety(agent)
                return
                # if agentType != BlessingOfSafety:
                #     agent.activeState = BlessingOfSafety(agent)
                # return

            else:
                man = 1
                if (
                    (agent.me.location[1] * sign(agent.team)) + 25 * sign(agent.team)
                ) < hit.pred_vector[1] * sign(agent.team):
                    if agent.me.location != agent.lastMan:
                        if hit.pred_vector[1] * sign(agent.team) < 4600 and agent.ball.location[1] * sign(agent.team) < 3000:
                            man = len(agent.allies) + 1

                if agent.me.demolished:
                    man = len(agent.allies) + 1

                if man != len(agent.allies) + 1:
                    if offensive:
                        myDist = weighted_distance_2D(
                            agent.me.location, hit.pred_vector
                        )
                    else:
                        myDist = distance2D(agent.me.location, hit.pred_vector)

                    for ally in agent.allies:
                        if not ally.demolished and not ally.retreating:
                            ally_action = None
                            if ally.index in agent.ally_actions:
                                # testing
                                if agent.ally_actions[ally.index]["action"]["type"] in ["BALL", "READY"]:
                                    if agent.ally_actions[ally.index]["action"]["time"] >= agent.time:
                                        if agent.ally_actions[ally.index]["action"]["time"] < hit.prediction_time:
                                            man+=1
                                            continue
                                        elif agent.ally_actions[ally.index]["action"]["time"] == hit.prediction_time:
                                            if ally.location[1] * sign(agent.team) < agent.me.location[1] * sign(agent.team):
                                                man += 1
                                                continue

                                if (
                                    agent.ally_actions[ally.index]["action"]["type"]
                                    == "BALL"
                                ):
                                    if (
                                        agent.ally_actions[ally.index]["action"]["time"]
                                        > agent.time
                                    ):
                                        if (
                                            agent.ally_actions[ally.index]["action"][
                                                "vector"
                                            ]
                                            is None
                                        ):
                                            ally_pred = find_pred_at_time(
                                                agent,
                                                agent.ally_actions[ally.index][
                                                    "action"
                                                ]["time"],
                                            )
                                            if ally_pred is not None:
                                                agent.ally_actions[ally.index][
                                                    "action"
                                                ][
                                                    "vector"
                                                ] = convertStructLocationToVector(
                                                    ally_pred
                                                )
                                                ally_targ = agent.ally_actions[
                                                    ally.index
                                                ]["action"]["vector"]

                                        if (
                                            agent.ally_actions[ally.index]["action"][
                                                "vector"
                                            ]
                                            is not None
                                        ):
                                            if (
                                                agent.ally_actions[ally.index][
                                                    "action"
                                                ]["vector"][2]
                                                >= 700
                                            ):
                                                if hit.hit_type == 5:
                                                    man += 1
                                                    agent.log.append(
                                                        f"not double commiting {agent.time}"
                                                    )
                                                    continue
                                            man += 1
                                            continue



                                if not (
                                    agent.ally_actions[ally.index]["action"]["type"]
                                    == "BALL"
                                    and agent.ally_actions[ally.index]["action"]["time"]
                                    < agent.time
                                ):
                                    ally_action = agent.ally_actions[ally.index][
                                        "action"
                                    ]
                                    key = "time"
                                    if ally_action["type"] == "READY":
                                        key = "time"

                            ally_targ = agent.ball.location

                            if ally_action is None or (
                                (
                                    ally_action["type"] == "BALL"
                                    or ally_action["type"] == "READY"
                                )
                                #and ally_action[key] >= agent.time
                            ):
                                if ally_action is not None:
                                    # ally_pred = find_pred_at_time(agent,ally_action[key])
                                    # if ally_pred != None:
                                    if (
                                        agent.ally_actions[ally.index]["action"][
                                            "vector"
                                        ]
                                        is not None
                                    ):
                                        # ally_targ = convertStructLocationToVector(ally_pred)
                                        ally_targ = ally_action["vector"]
                                    else:
                                        ally_pred = find_pred_at_time(
                                            agent, ally_action[key]
                                        )
                                        if ally_pred is not None:
                                            agent.ally_actions[ally.index]["action"][
                                                "vector"
                                            ] = convertStructLocationToVector(ally_pred)
                                            ally_targ = agent.ally_actions[ally.index][
                                                "action"
                                            ]["vector"]

                            # else:
                            #     continue

                            if ally.location[1] * sign(agent.team) > ally_targ[
                                1
                            ] * sign(agent.team):
                                if (
                                    ally_action is None
                                ):  # or agent.ally_hit_info[ally.index][0].time < agent.time:
                                    if offensive:
                                        allyDist = weighted_distance_2D(
                                            ally.location, ally_targ
                                        )
                                    else:
                                        allyDist = distance2D(ally.location, ally_targ)
                                    if allyDist < myDist:
                                        man += 1

                                else:
                                    if agent.ally_actions[ally.index]["action"] == "BALL" or agent.ally_actions[ally.index]["action"] == "READY":
                                        if (
                                            agent.ally_actions[ally.index]["action"][key]
                                            < hit.prediction_time  # +0.1
                                        ):
                                            man += 1

                                        elif (
                                            agent.ally_actions[ally.index]["action"][key]
                                            == hit.prediction_time
                                        ):
                                            if distance2D(
                                                agent.me.location, hit.pred_vector
                                            ) > distance2D(ally.location, ally_targ):
                                                man += 1

                                        elif (
                                            agent.currentHit.hit_type == 5
                                            and agent.ally_actions[ally.index]["action"][
                                                "type"
                                            ]
                                            == "BALL"
                                            and agent.ally_actions[ally.index]["action"][
                                                key
                                            ]
                                            < agent.currentHit.prediction_time  # + 1
                                        ):
                                            man += 1

            man = clamp(3, 1, man)
            # if offensive and man != 1:
            if man != 1 and not offensive:
                if agent.lastMan != agent.me.location:
                    man = 2
                else:
                    man = 3

            # if man != 1:
            #     #disregard player furthest advanced
            #
            #     y_dist = 2500
            #     if agent.ball.location[0] > 0:
            #         x_target = -500
            #     else:
            #         x_target = 500
            #
            #     y_target = agent.ball.location[1] + (sign(agent.team) * y_dist)
            #     two_spot = Vector([x_target, y_target, 0])
            #
            #     closest_ally = None
            #     closest_dist = math.inf
            #
            #     most_advanced_position = -math.inf
            #     most_advanced_ally = None
            #
            #     dists = []
            #
            #     for ally in inclusive_team:
            #         ally_dist = distance2D(ally.location, two_spot)
            #         dists.append([ally_dist,ally.index])
            #         pos = ally.location[1] * -(sign(agent.team))
            #         if pos > most_advanced_position:
            #             most_advanced_ally = [ally_dist,ally.index]
            #
            #     #dists.remove(most_advanced_ally)
            #     #dists = sorted(dists, key=lambda x: x[0])
            #     if len(dists) > 1:
            #         dists.remove(most_advanced_ally)
            #         dists = sorted(dists, key=lambda x: x[0])
            #         if dists[0][1] == agent.index:
            #             man = 2
            #         else:
            #             man = 3
            #     else:
            #         man = 2

            # if (
            #     len(agent.enemies) < 4
            #     and not agent.contested
            #     and hit.hit_type not in [5, 0]
            #     and not (
            #         hit.hit_type == 2
            #         and not ballHeadedTowardsMyGoal_testing(agent, hit)
            #     )
            #     and agent.me.boostLevel > 0
            #     and agent.forward
            #     and not ballHeadedTowardsMyGoal_testing(agent, hit)
            #     # and agent.team == 0 or not offensive
            #     and not offensive
            # ):
            #     chrono_hits = agent.sorted_hits
            #     prev_hit = hit
            #     for h in chrono_hits[1:]:
            #         if ballHeadedTowardsMyGoal_testing(agent, h):
            #             break
            #
            #         if distance2D(h.pred_vector, enemyGoalLoc) >= distance2D(
            #             agent.me.location, enemyGoalLoc
            #         ):
            #             break
            #         if h.pred_vel[1] * -sign(agent.team) >= 1 and h.hit_type != 5:
            #             if not butterZone(prev_hit.pred_vector):
            #                 temptime = h.time_difference()
            #                 if (
            #                     temptime
            #                     < agent.enemyBallInterceptDelay
            #                     - agent.contestedTimeLimit
            #                 ):
            #                     hit = h
            #                     if (
            #                         agent.onWall
            #                         and hit.hit_type == 2
            #                         or hit.hit_type == 0
            #                         or butterZone(hit.pred_vector)
            #                     ):
            #                         agent.ballDelay = hit.time_difference()
            #                         break
            #                 else:
            #                     break
            #             else:
            #                 break
            #         prev_hit = h
            #
            #         hit = prev_hit
            #         agent.ballDelay = hit.time_difference()

            agent.rotationNumber = man
            if man == 1:
                createSphere(agent, hit.pred_vector)

            # if man > 1 and len(agent.sorted_hits) > 1:
            #     hit = agent.sorted_hits[1]
            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.time_difference()
            agent.ballGrounded = False

            if hit.hit_type == 2:
                agent.wallShot = True
                agent.ballGrounded = False
            else:
                agent.wallShot = False
                if hit.hit_type == 1:
                    if hit.pred_vector[2] <= agent.groundCutOff:
                        agent.ballGrounded = True
                    else:
                        agent.ballGrounded = False
            if man == 1:
                createBox(agent, hit.pred_vector)

            if agent.dribbling:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            if man !=1:
                boostOpportunity = inCornerWithBoost(agent)
                if boostOpportunity != False:
                    if agent.me.boostLevel <= 50:
                        getBoost = False
                        if boostOpportunity[1] in agent.my_corners:
                            getBoost = True
                        if getBoost:
                            if agentType != HeavenlyReprieve:
                                agent.activeState = HeavenlyReprieve(
                                    agent, boostOpportunity[0]
                                )
                            return

            if agent.ignore_kickoffs:
                if distance2D(hit.pred_vector, myGoalLoc) > 3000:
                    if agent.activeState != HeetSeekerDefense:
                        agent.activeState = HeetSeekerDefense(agent)
                    return

            # if agent.goalie:
            #     if agent.activeState != Goalie:
            #         agent.activeState = Goalie(agent)
            #     return
            if agent.goalie:
                if hit.pred_vector[1] * sign(agent.team) < 0 or man != 1:
                    if agent.activeState != Goalie:
                        agent.activeState = Goalie(agent)
                    return

            if man == 1:

                # if catchViable:
                #     if not agent.dribbling:
                #         # if agent.hits[1].pred_vel[1] * -sign(agent.team) >= 1:
                #         agent.currentHit = agent.hits[1]
                #         agent.ballDelay = agent.currentHit.time_difference()
                #         if agent.activeState != Celestial_Arrest:
                #             agent.activeState = Celestial_Arrest(agent)
                #         return

                if carDistanceFromGoal > ballDistanceFromGoal and hit.hit_type != 5:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                if goalward:
                    if hit.hit_type != 2 and hit.hit_type != 5:
                        if agentType != HolyProtector:
                            agent.activeState = HolyProtector(agent)
                        return
                    elif hit.hit_type == 2:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return
                    else:
                        if hit.hit_type == 5:
                            if agentType != Wings_Of_Justice:
                                agent.activeState = hit.aerialState  # .create_copy()
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

                    elif hit.hit_type == 4:
                        if agentType != HolyGrenade:
                            agent.activeState = HolyGrenade(agent)
                            # print("would have been wallshot before")
                        return

                    elif hit.hit_type == 2:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return

                    elif hit.hit_type == 5:
                        if agentType != Wings_Of_Justice:
                            agent.activeState = hit.aerialState  # .create_copy()
                            # agent.log.append(f"Going for aerial! {agent.time}")
                        return

                    else:
                        agent.log.append(f"condition leaked through! {hit.hit_type}")

            else:

                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

        else:
            agent.activeState = PreemptiveStrike(agent)


""


def TMCP_team_manager(agent):
    agentType = type(agent.activeState)
    if (
        agentType != PreemptiveStrike
        or agentType == PreemptiveStrike
        and not agent.activeState.active
    ):

        if not kickOffTest(agent):

            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball.location)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me.location)

            if locked_in(agent, agentType):
                return

            fastesthit = agent.sorted_hits[0]  # find_soonest_hit(agent)
            hit = fastesthit

            if agent.dribbler:
                if hit.hit_type != 0:
                    for h in agent.sorted_hits:
                        if h.hit_type == 0:
                            hit = h
                            break

            if (
                hit.hit_type == 2
                and abs(agent.me.location[1]) > 5000
                and abs(agent.me.location[0]) < 900
                and len(agent.sorted_hits) > 1
            ):
                fastesthit = agent.sorted_hits[1]
                hit = fastesthit

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                # if agent.enemyAttacking:
                agent.contested = True

            if agent.goalPred is not None:
                agent.contested = True
                agent.enemyAttacking = True

            # if butterZone(hit.pred_vector):
            #     agent.contested = True
            #     agent.enemyAttacking = True

            if hit.hit_type == 5:
                if not agent.onSurface:
                    if agentType != Wings_Of_Justice:
                        agent.activeState = hit.aerialState  # .create_copy()
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            if agent.demo_monster:
                agent.currentHit = hit
                agent.ballDelay = tempDelay
                if agent.activeState != Divine_Retribution:
                    agent.activeState = Divine_Retribution(agent)
                return

            lastMan = agent.lastMan
            catchViable = False
            inclusive_team = []
            _inclusive_team = agent.allies[:]
            # ignore_types = ["DEFEND","DEMO","BOOST"]
            ignore_types = ["DEFEND"]
            removals = []
            for i in range(len(inclusive_team)):
                if _inclusive_team[i].index in agent.ally_actions:
                    if agent.ally_actions["action"]["type"] not in ignore_types:
                        inclusive_team.append(_inclusive_team[i])

            inclusive_team.append(agent.me)
            inclusive_team = sorted(inclusive_team, key=lambda x: x.index)
            offensive = agent.offensive

            if not agent.gameInfo.is_round_active or agent.gameInfo.is_kickoff_pause:
                man = 2
                if agent.me.location == agent.lastMan:
                    man = 3
                agent.rotationNumber = man

                agent.currentHit = fastesthit
                agent.ballDelay = fastesthit.time_difference()
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

            man = 3
            best_action = None
            best_time = -1
            one_slot = None
            closest_dist = 999999
            closest_ally = None

            for ally in inclusive_team:
                ally_dist = findDistance(ally.location, agent.ball.location)
                if ally_dist < closest_dist:
                    closest_dist = ally_dist
                    closest_ally = ally.index
                if ally.index in agent.ally_actions:
                    if best_action is None:
                        if agent.ally_actions[ally.index]["action"]["type"] == "BALL":
                            if (
                                agent.ally_actions[ally.index]["action"]["time"]
                                > agent.time - agent.fakeDeltaTime * 2
                            ):
                                best_action = "BALL"
                                best_time = agent.ally_actions[ally.index]["action"][
                                    "time"
                                ]
                                one_slot = ally.index

                        elif (
                            agent.ally_actions[ally.index]["action"]["type"] == "READY"
                        ):
                            best_action = "READY"
                            best_time = agent.ally_actions[ally.index]["action"]["time"]
                            one_slot = ally.index
                    elif best_action == "READY":
                        if agent.ally_actions[ally.index]["action"]["type"] == "BALL":
                            if (
                                agent.ally_actions[ally.index]["action"]["time"]
                                > agent.time - agent.fakeDeltaTime * 2
                            ):
                                best_action = "BALL"
                                best_time = agent.ally_actions[ally.index]["action"][
                                    "time"
                                ]
                                one_slot = ally.index

                        elif (
                            agent.ally_actions[ally.index]["action"]["type"] == "READY"
                        ):
                            if (
                                agent.ally_actions[ally.index]["action"]["time"]
                                > agent.time - agent.fakeDeltaTime * 2
                            ):
                                if (
                                    agent.ally_actions[ally.index]["action"]["time"]
                                    < best_time
                                ):
                                    best_action = "READY"
                                    best_time = agent.ally_actions[ally.index][
                                        "action"
                                    ]["time"]
                                    one_slot = ally.index

                    elif best_action == "BALL":
                        if agent.ally_actions[ally.index]["action"]["type"] == "BALL":
                            if (
                                agent.ally_actions[ally.index]["action"]["time"]
                                > agent.time
                            ):
                                if (
                                    agent.ally_actions[ally.index]["action"]["time"]
                                    < best_time
                                ):
                                    best_action = "BALL"
                                    best_time = agent.ally_actions[ally.index][
                                        "action"
                                    ]["time"]
                                    one_slot = ally.index

                    else:
                        print(f"{ally.index} not in ally_actions!")

            if one_slot is None:
                one_slot = closest_ally

            # else:
            #     print(f"{best_action} {best_time}")
            print(one_slot == agent.index)
            if one_slot == agent.index:
                man = 1

            else:
                y_dist = 2500
                if agent.ball.location[0] > 0:
                    x_target = -500
                else:
                    x_target = 500

                y_target = agent.ball.location[1] + (sign(agent.team) * y_dist)
                two_spot = Vector([x_target, y_target, 0])

                closest_ally = None
                closest_dist = math.inf

                for index, ally in enumerate(inclusive_team):
                    if index != one_slot.index:
                        ally_dist = distance2D(ally.location, agent.ball.location)
                        if ally_dist < closest_dist:
                            closest_ally = ally.index
                            closest_dist = ally_dist

                if closest_ally == agent.index:
                    man = 2
                else:
                    man = 3

            # print(f"{agent.index}, {man}")

            if (
                len(agent.enemies) < 4
                and not agent.contested
                and hit.hit_type not in [5, 0]
                and not (
                    hit.hit_type == 2
                    and not ballHeadedTowardsMyGoal_testing(agent, hit)
                )
                and agent.me.boostLevel > 0
                and agent.forward
                and not ballHeadedTowardsMyGoal_testing(agent, hit)
                # and agent.team == 0 or not offensive
                and not offensive
                and man == 1
            ):
                chrono_hits = agent.sorted_hits
                prev_hit = hit
                for h in chrono_hits[1:]:
                    if ballHeadedTowardsMyGoal_testing(agent, h):
                        break

                    if distance2D(h.pred_vector, enemyGoalLoc) >= distance2D(
                        agent.me.location, enemyGoalLoc
                    ):
                        break
                    if h.pred_vel[1] * -sign(agent.team) >= 1 and h.hit_type != 5:
                        if not butterZone(prev_hit.pred_vector):
                            temptime = h.time_difference()
                            if (
                                temptime
                                < agent.enemyBallInterceptDelay
                                - agent.contestedTimeLimit
                            ):
                                hit = h
                                if (
                                    agent.onWall
                                    and hit.hit_type == 2
                                    or hit.hit_type == 0
                                    or butterZone(hit.pred_vector)
                                ):
                                    agent.ballDelay = hit.time_difference()
                                    break
                            else:
                                break
                        else:
                            break
                    prev_hit = h

                    hit = prev_hit
                    agent.ballDelay = hit.time_difference()

            agent.rotationNumber = man

            # if man > 1 and len(agent.sorted_hits) > 1:
            #     hit = agent.sorted_hits[1]
            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.time_difference()
            agent.ballGrounded = False

            if hit.hit_type == 2:
                agent.wallShot = True
                agent.ballGrounded = False
            else:
                agent.wallShot = False
                if hit.hit_type == 1:
                    if hit.pred_vector[2] <= agent.groundCutOff:
                        agent.ballGrounded = True
                    else:
                        agent.ballGrounded = False
            if man == 1:
                createBox(agent, hit.pred_vector)

            if agent.dribbling:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if boostOpportunity[1] in agent.my_corners:
                        getBoost = True
                    if getBoost:
                        if agentType != HeavenlyReprieve:
                            agent.activeState = HeavenlyReprieve(
                                agent, boostOpportunity[0]
                            )
                        return

            if agent.ignore_kickoffs:
                if distance2D(hit.pred_vector, myGoalLoc) > 3000:
                    if agent.activeState != HeetSeekerDefense:
                        agent.activeState = HeetSeekerDefense(agent)
                    return

            if agent.goalie:
                if agent.activeState != Goalie:
                    agent.activeState = Goalie(agent)
                return

            if man == 1:

                if catchViable:
                    if not agent.dribbling:
                        # if agent.hits[1].pred_vel[1] * -sign(agent.team) >= 1:
                        agent.currentHit = agent.hits[1]
                        agent.ballDelay = agent.currentHit.time_difference()
                        if agent.activeState != Celestial_Arrest:
                            agent.activeState = Celestial_Arrest(agent)
                        return

                if carDistanceFromGoal > ballDistanceFromGoal and hit.hit_type != 5:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                if goalward:
                    if hit.hit_type != 2 and hit.hit_type != 5:
                        if agentType != HolyProtector:
                            agent.activeState = HolyProtector(agent)
                        return
                    elif hit.hit_type == 2:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return
                    else:
                        if hit.hit_type == 5:
                            if agentType != Wings_Of_Justice:
                                agent.activeState = hit.aerialState  # .create_copy()
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

                    elif hit.hit_type == 4:
                        if agentType != HolyGrenade:
                            agent.activeState = HolyGrenade(agent)
                            # print("would have been wallshot before")
                        return

                    elif hit.hit_type == 2:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return

                    elif hit.hit_type == 5:
                        if agentType != Wings_Of_Justice:
                            agent.activeState = hit.aerialState  # .create_copy()
                            # agent.log.append(f"Going for aerial! {agent.time}")
                        return

                    else:
                        agent.log.append(f"condition leaked through! {hit.hit_type}")

            else:

                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

        else:
            agent.activeState = PreemptiveStrike(agent)


def team_manager(agent):
    agentType = type(agent.activeState)
    if (
        agentType != PreemptiveStrike
        or agentType == PreemptiveStrike
        and not agent.activeState.active
    ):

        if not kickOffTest(agent):

            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball.location)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me.location)

            if locked_in(agent, agentType):
                return

            fastesthit = agent.sorted_hits[0]
            hit = fastesthit
            if hit.hit_type == 5:
                if agent.enemyBallInterceptDelay + 0.5 < hit.time_difference():
                    if agent.onSurface:
                        if len(agent.sorted_hits) > 1:
                            hit = agent.sorted_hits[1]

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed
            # if not agent.dribbling:
            #     agent.enemyAttacking = True

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                # if agent.enemyAttacking or agent.team == 0:
                agent.contested = True
                # agent.enemyAttacking = True

            if agent.goalPred is not None:
                agent.contested = True
                agent.enemyAttacking = True

            if butterZone(hit.pred_vector):
                agent.contested = True
                agent.enemyAttacking = True

            if hit.hit_type == 5:
                # print(f"going for aerial {agent.time}")
                if not agent.onSurface:
                    if agentType != Wings_Of_Justice:
                        agent.activeState = hit.aerialState  # .create_copy()
                        # agent.log.append(f"Going for aerial! {agent.time}")
                    return

            if agentType == DivineGrace:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            lastMan = agent.lastMan
            catchViable = False
            inclusive_team = agent.allies[:]
            inclusive_team.append(agent.me)
            inclusive_team = sorted(inclusive_team, key=lambda x: x.index)
            offensive = agent.offensive

            if not agent.gameInfo.is_round_active or agent.gameInfo.is_kickoff_pause:
                man = 2
            else:
                man = 1

                hit_timers = [
                    [
                        fastesthit.prediction_time,
                        agent.me.retreating
                        or agent.me.location[1] * sign(agent.team)
                        < fastesthit.pred_vector[1] * sign(agent.team),
                    ]
                ]
                if agent.ally_hit_count == 0:
                    ally_hits = []
                    for i in range(len(agent.allies)):
                        agent.allies[i].next_hit = find_ally_hit(agent, agent.allies[i])
                        hit_timers.append(
                            [
                                agent.allies[i].next_hit.time,
                                agent.allies[i].retreating
                                or agent.allies[i].location[1] * sign(agent.team)
                                < agent.allies[i].next_hit.location[1]
                                * sign(agent.team),
                            ]
                        )
                        ally_hits.append(
                            [
                                agent.allies[i].next_hit.time,
                                agent.allies[i].retreating
                                or agent.allies[i].location[1] * sign(agent.team)
                                < agent.allies[i].next_hit.location[1]
                                * sign(agent.team),
                            ]
                        )

                    agent.ally_hit_info = ally_hits

                else:
                    hit_timers = hit_timers + agent.ally_hit_info

                agent.ally_hit_count += 1
                if agent.ally_hit_count > 3:
                    agent.ally_hit_count = 0

                sorted_team_hits = sorted(hit_timers, key=lambda x: x[0])

                for index, th in enumerate(sorted_team_hits[:]):
                    if th[1]:
                        sorted_team_hits.append(th)
                        sorted_team_hits = sorted_team_hits[1:]

                for i in range(len(sorted_team_hits)):
                    if (
                        sorted_team_hits[i][0] < fastesthit.prediction_time
                        or not sorted_team_hits[i][1]
                        and agent.me.retreating
                    ):
                        man += 1
                    # print(sorted_team_hits[i][0],fastesthit.prediction_time)

                man = clamp(3, 1, man)
                agent.boostThreshhold = man * 25

            # if not agent.contested and agent.goalPred == None and len(agent.allies) < 2:
            if False:  # or (agent.team == 1 and not agent.contested):
                # if not agent.contested and agent.lastMan != agent.me.location and man == 1 and hit.hit_type != 0 and agent.goalPred == None and not ballHeadedTowardsMyGoal_testing(agent, hit) and not agent.ignore_kickoffs:# and agent.team == 1:
                chrono_hits = agent.sorted_hits
                prev_hit = hit
                for h in chrono_hits:
                    # if h.time_difference() < 1:
                    #     break

                    if h.hit_type == 5:
                        continue

                    if distance2D(h.pred_vector, enemyGoalLoc) >= distance2D(
                        agent.me.location, enemyGoalLoc
                    ):
                        break
                    if h.pred_vel[1] * -sign(agent.team) >= 1:
                        if not butterZone(prev_hit.pred_vector):
                            temptime = h.time_difference()
                            if (
                                temptime
                                < agent.enemyBallInterceptDelay
                                - agent.contestedTimeLimit
                            ):
                                hit = h
                            else:
                                break
                        else:
                            break
                    prev_hit = h

                    hit = prev_hit
                    agent.ballDelay = hit.time_difference()

            if man == 2:
                if agent.lastMan != agent.me.location:
                    if hit.pred_vector[1] * -sign(agent.team) > 4000 * -sign(
                        agent.team and len(agent.allies) > 1
                    ):
                        if butterZone(hit.pred_vector):
                            if hit.time_difference() < agent.enemyBallInterceptDelay or (
                                hit.time_difference() < 2
                                and agent.lastMan[1] * sign(agent.team) > 0
                            ):
                                man = 1
                                agent.log.append(
                                    f"risking it for the biscuit! {agent.time} {agent.team}"
                                )

            agent.rotationNumber = man

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.time_difference()
            agent.ballGrounded = False

            if hit.hit_type == 2:
                agent.wallShot = True
                agent.ballGrounded = False
            else:
                agent.wallShot = False
                if hit.hit_type == 1:
                    if hit.pred_vector[2] <= agent.groundCutOff:
                        agent.ballGrounded = True
                    else:
                        agent.ballGrounded = False

            createBox(agent, hit.pred_vector)

            if agent.dribbling:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if boostOpportunity[1] in agent.my_corners:
                        getBoost = True
                    if getBoost:
                        if agentType != HeavenlyReprieve:
                            agent.activeState = HeavenlyReprieve(
                                agent, boostOpportunity[0]
                            )
                        return

            if agent.ignore_kickoffs:
                if distance2D(hit.pred_vector, myGoalLoc) > 3000:
                    if agent.activeState != HeetSeekerDefense:
                        agent.activeState = HeetSeekerDefense(agent)
                    return

            if agent.goalie:
                if agent.activeState != Goalie:
                    agent.activeState = Goalie(agent)
                return

            if man == 1:

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

                    elif hit.hit_type == 4:
                        if agentType != HolyGrenade:
                            agent.activeState = HolyGrenade(agent)
                            # print("would have been wallshot before")
                        return

                    elif hit.hit_type == 2:
                        if agentType != ScaleTheWalls:
                            agent.activeState = ScaleTheWalls(agent)
                        return

                    elif hit.hit_type == 5:
                        if agentType != Wings_Of_Justice:
                            agent.activeState = hit.aerialState  # .create_copy()
                            # agent.log.append(f"Going for aerial! {agent.time}")
                        return

                    else:
                        agent.log.append(f"condition leaked through! {hit.hit_type}")

            else:
                # if agent.team == 0:
                # if agent.ball.location[1] * sign(agent.team) >= 0:
                #     if agent.lastMan == agent.me.location:
                #         if agentType != WardAgainstEvil:
                #             agent.activeState = WardAgainstEvil(agent)
                #         return

                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

        else:
            agent.activeState = PreemptiveStrike(agent)


def find_alternative_hit(agent, acceptable_hits):
    for h in agent.sorted_hits:
        if h.hit_type in acceptable_hits:
            return h

    return agent.currentHit

def soloStateManager_testing(agent):
    agentType = type(agent.activeState)

    if (
        agentType != PreemptiveStrike
        or (agentType == PreemptiveStrike and not agent.activeState.active)
    ):

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            # agent.resetTimer += agent.deltaTime
            if locked_in(agent, agentType):
                if agent.currentHit != None:
                    createSphere(agent, agent.currentHit.pred_vector)
                return

            hit = agent.sorted_hits[0]

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.time_difference()
            offensive = agent.offensive
            agent.rotationNumber = 1

            # if tempDelay + agent.contestedTimeLimit > agent.enemyBallInterceptDelay:
            #     if agent.enemyAttacking:
            #         agent.contested = True
            #         if findDistance(
            #             agent.ball.location, agent.me.location
            #         ) > 400:
            #             scared = True
            if not agent.contested and agent.closestEnemyToBall.location[1] * sign(agent.team) <= agent.enemyTargetVec[1] * sign(agent.team):
                if tempDelay - agent.contestedTimeLimit > agent.enemyBallInterceptDelay:
                    if agent.enemyAttacking:
                        agent.contested = True
                        if (
                            distance2D(agent.enemyTargetVec, agent.me.location) > 500
                        ):  # and agent.closestEnemyToBall.location[1] * sign(agent.team) < agent.enemyTargetVec[1] * sign(agent.team):
                            scared = True

                if (
                    distance2D(hit.pred_vector, myGoalLoc) <= 2000
                    or distance2D(agent.enemyTargetVec, myGoalLoc) <= 2000
                    or ballDistanceFromGoal <= 2000
                ):

                    if (
                        agent.enemyAttacking
                    ):  # or agent.me.velocity[1] * sign(agent.team) > 1:
                        agent.contested = True
                        agent.timid = False
                        scared = False

            if agent.goalPred is not None:
                agent.contested = True
                scared = False

            # testing
            if agent.closestEnemyToBall.location[1] * sign(
                agent.team
            ) > agent.enemyTargetVec[1] * sign(agent.team):
                scared = False

            if distance2D(agent.me.location, agent.ball.location) < 500:
                scared = False

            # if agent.team == 1:
            #     scared = False
            scared = False
            agent.scared = scared

            if hit.hit_type == 5:
                if hit.aerialState.active:
                    if not agent.onSurface:
                        if agentType != Wings_Of_Justice:
                                agent.activeState = hit.aerialState
                        return
                else:
                    if agent.enemyBallInterceptDelay < hit.time_difference() and len(agent.sorted_hits) > 1:
                        agent.sorted_hits = agent.sorted_hits[1:]

            # if agent.scorePred is not None:# or (agent.goalPred is None and enemy_carry_check(agent)):
            #     test_state = DemolitionBot(agent)
            #     test_state.update()
            #     if test_state.active:
            #         #print(f"demoing {agent.time}")
            #         agent.activeState = test_state
            #         return


            # testing to see if forcing quick shot with ballward shots is worth it
            if (
                not agent.contested
                and not butterZone(hit.pred_vector)
                and hit.hit_type not in [0, 2]
                and not ballHeadedTowardsMyGoal_testing(agent, hit)
            ) or (hit.hit_type == 4 and agent.scorePred):
                chrono_hits = agent.sorted_hits[1:]
                for h in chrono_hits:
                    if (
                        ballHeadedTowardsMyGoal_testing(agent, h)
                        and cornerDetection(h.pred_vector) not in agent.my_corners
                    ):
                        break
                    if h.hit_type == 5:
                        continue
                    temptime = h.time_difference()
                    if temptime + 0.334 < agent.enemyBallInterceptDelay or not agent.enemyAttacking:
                        # if not offensive or agent.team == 0 or extendToGoal(agent, h.pred_vector, agent.me.location, buffer=agent.ball_size * 3):
                        hit = h
                        if (
                            (agent.onWall and hit.hit_type == 2)
                            or hit.hit_type == 0
                            or butterZone(hit.pred_vector)
                        ):
                            agent.ballDelay = hit.time_difference()
                            break

            if agent.dribbler:
                if hit.hit_type != 0:
                    for h in agent.sorted_hits:
                        if h.hit_type == 0:
                            hit = h
                            break

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.time

            catchViable = False  # ballCatchViable(agent)# and agent.team == 1

            if hit.hit_type == 2:
                agent.wallShot = True
            else:
                agent.wallShot = False

            createSphere(agent, hit.pred_vector)
            #createBox(agent, hit.pred_vector)

            if hit.hit_type == 5:
                if agentType != Wings_Of_Justice:
                    agent.activeState = hit.aerialState
                return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            if agent.dribbling:
                # if not goalward:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            if agent.scorePred is not None:
                # if agent.me.location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team):
                #     if agent.closestEnemyToBall.location[1] * sign(agent.team) > agent.ball.location[1] * sign(agent.team):
                #         if agent.activeState != Divine_Retribution:
                #             agent.activeState = Divine_Retribution(agent,grab_boost=False)
                #         print(f"going for demo! {agent.time}")
                #         return

                if agent.enemyBallInterceptDelay > agent.scorePred.time - agent.time:
                    if agent.activeState != BlessingOfSafety:
                        agent.activeState = BlessingOfSafety(agent)
                    return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if boostOpportunity[1] in agent.my_corners:
                        getBoost = True
                    if getBoost:
                        if agentType != HeavenlyReprieve:
                            agent.activeState = HeavenlyReprieve(
                                agent, boostOpportunity[0]
                            )
                        return

            if agent.goalie:
                if agent.activeState != Goalie:
                    agent.activeState = Goalie(agent)
                return


            if agent.ignore_kickoffs:
                if distance2D(hit.pred_vector, myGoalLoc) > 3000:
                    if agent.activeState != HeetSeekerDefense:
                        agent.activeState = HeetSeekerDefense(agent)
                    return

            if carDistanceFromGoal > ballDistanceFromGoal:
                if agentType != HolyProtector:
                    agent.activeState = HolyProtector(agent)
                return
            #testing
            if goalward or (agent.contested and (not agent.first_hit.scorable or not offensive)):
                if hit.hit_type != 2 and hit.hit_type != 5:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return
                elif hit.hit_type == 2:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                    return
                else:
                    if hit.hit_type == 5:
                        if agentType != Wings_Of_Justice:
                            agent.activeState = hit.aerialState  # .create_copy()
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

                elif hit.hit_type == 4:
                    if agentType != HolyGrenade:
                        agent.activeState = HolyGrenade(agent)
                        # print("would have been wallshot before")
                    return

                elif hit.hit_type == 2:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                    return

                elif hit.hit_type == 5:
                    if agentType != Wings_Of_Justice:
                        agent.activeState = hit.aerialState  # .create_copy()
                        # agent.log.append(f"Going for aerial! {agent.time}")
                    return

                else:
                    agent.log.append(f"condition leaked through! {hit.hit_type}")

        else:
            agent.activeState = PreemptiveStrike(agent)


def orientationStateManager(agent):
    if agent.ball.location[2] < 100:
        car_state = CarState(
            physics=Physics(velocity=Vector3(z=-1, x=0, y=0), location=Vector3(0, 4000, 17))
        )
        ball_state = BallState(physics=Physics(velocity=Vector3(z=-1, x=0, y=15), location=Vector3(150, 3500, 500)))
        game_state = GameState(cars={agent.index: car_state}, ball=ball_state)
        agent.set_game_state(game_state)

    if type(agent.activeState) != AngelicEmbrace:
        agent.activeState = AngelicEmbrace(agent)


def dummyState(agent):
    if type(agent.activeState) != Player_reporter:
        agent.activeState = Player_reporter(agent)
