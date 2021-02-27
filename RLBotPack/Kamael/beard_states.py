from beard_utilities import *
import math
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

    if agentType == Special_Delivery:
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


class State:
    RESET = 0
    WAIT = 1
    INITIALIZE = 2
    RUNNING = 3


class Kickoff_boosties(baseState):
    def __init__(self,agent):
        super().__init__(agent)

    def update(self):
        self.active = self.agent.gameInfo.is_kickoff_pause or not self.agent.gameInfo.is_round_active
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


class Wings_Of_Justice:
    def __init__(self, agent, pred, target: Vector, time: float):
        self.active = False
        self.agent = agent
        self.time = clamp(10, 0.0001, time)
        self.airborne = False
        self.launcher = None
        self.pred = predictionStruct(
            convertStructLocationToVector(pred), pred.game_seconds
        )
        self.target = target
        self.drive_controls = SimpleControllerState()
        self.launch_projection = None
        self.started = self.agent.time
        self.powershot = (
            distance2D(target, Vector([0, 5200 * -sign(agent.team), 0])) > 2000
        )
        self.point_time = 1

    def setup(self):
        # print(f"in setup {self.agent.time}")
        if self.agent.onSurface:
            launching = False
            dt = self.pred.time - self.agent.time
            delta_a = calculate_delta_acceleration(
                self.target - self.agent.me.location,
                self.agent.jumpPhysics.velocity,
                dt,
                self.agent.gravity,
            )
            expedite = (
                1058 * (self.agent.me.boostLevel - 10 / 33.333)
                > delta_a.scale(dt).magnitude()
            )

            _direction = direction(self.agent.me.location, self.target)
            destination = self.target + _direction.scale(150)

            self.drive_controls = driveController(
                self.agent,
                destination,
                self.pred.time,
                expedite=expedite,
                flippant=False,
                maintainSpeed=False,
            )

            # zoneInfo= takeoff_goldielox_zone(self.agent,self.target)

            if delta_a.magnitude() < 1050:
                if (
                    abs(self.drive_controls.steer) <= 0.1
                ):  # or self.agent.team == 1 and self.agent.currentSpd < 300: #self.agent.currentSpd < 300 or
                    if not self.agent.onWall:
                        projection = (
                            self.agent.me.location
                            + self.agent.jumpPhysics.velocity.scale(1.5)
                        )
                        projected_delta_a = calculate_delta_acceleration(
                            self.target - projection,
                            self.agent.jumpPhysics.velocity,
                            dt,
                            self.agent.gravity,
                        )
                        launching = True
                else:
                    launching = True

            if not launching:
                self.active = False

            else:
                if distance2D(self.target, self.agent.me.location) <= 5000:
                    if not self.agent.onWall:
                        self.launcher = self.agent.createJumpChain(
                            2, 400, jumpSim=None, set_state=False, aim=False
                        )
                    else:
                        # self.launcher = Aerial_Charge(self.agent, self.target)
                        self.launcher = Divine_Mandate(
                            self.agent, [SimpleControllerState(jump=True)], [0.10]
                        )
                    self.active = True
                else:
                    self.active = False
        else:
            self.active = True

    def update(self):
        controls = SimpleControllerState()
        controls.throttle = 0
        dt = self.pred.time - self.agent.time
        target = self.target
        createBox(self.agent, self.pred.location)

        delta_a = calculate_delta_acceleration(
            target - self.agent.me.location,
            self.agent.me.velocity,
            dt,
            self.agent.gravity,
        )

        if self.agent.time - self.started > 0.5:
            if self.launch_projection != None:
                self.agent.log.append(
                    f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
                )
                self.launch_projection = None

        pred_valid = validateExistingPred(self.agent, self.pred)

        if self.agent.onSurface and self.launcher == None:
            self.setup()
            if self.launcher == None:
                return self.drive_controls

        if self.launcher != None:
            controls = self.launcher.update()
            if not self.launcher.active:
                self.launcher = None
            return controls

        boost_req = (
            clamp(
                self.agent.boost_duration_min,
                1,
                abs(
                    self.agent.boost_duration_min
                    - clamp(self.agent.boost_duration_min, 0, self.agent.boost_counter)
                ),
            )
            * self.agent.aerialAccelerationTick
        )
        # if dt <= self.point_time:
        #     boost_req= 8*self.agent.aerialAccelerationTick

        aligned_threshold = 0.7
        current_alignment = self.agent._forward.dotProduct(delta_a.normalize())

        if dt > self.point_time or (delta_a.magnitude() > self.agent.aerialAccelerationTick*8):
            align_car_to(controls, self.agent.me.avelocity, delta_a, self.agent)
            aligned = current_alignment > aligned_threshold
            controls.boost = aligned and delta_a.magnitude() > boost_req
            if delta_a.magnitude() > 66 * self.agent.fakeDeltaTime and aligned:
                controls.throttle = 1
            if delta_a.magnitude() > 1058 and dt > 1 and not self.launcher:
                self.active = False
                self.agent.log.append(
                    f"required acceleration too high {delta_a.magnitude()}"
                )
        else:
            target = self.pred.location #+ offset
            if not pred_valid:
                target = self.agent.ball.location # + offset

            (
                controls.steer,
                controls.yaw,
                controls.pitch,
                _roll,
                error,
            ) = point_at_position(self.agent, target)

            #controls.boost = error <= aligned_threshold


        if not pred_valid:
            if self.launch_projection != None:
                self.agent.log.append(
                    f"Projected delta_a after launcher: {str(self.launch_projection)[:6]}, in reality: {str(delta_a.magnitude())[:6]}"
                )
                self.launch_projection = None
            if self.launcher == None:
                self.active = False

        if dt <= 0:
            self.active = False
            self.agent.log.append("Aerial timed out")

        if self.agent.onSurface:
            self.agent.log.append("canceling aerial since we're on surface")
            self.active = False

        if dt > self.point_time:
            req_vel = self.agent.me.velocity + delta_a
            if req_vel.magnitude() > 2300 and self.launcher:
                self.active = False

        return controls


class Celestial_Arrest(baseState):
    def update(self):
        return catch_ball(self.agent)


class Special_Delivery(baseState):
    def __init__(self, agent):
        super().__init__(agent)
        self.jump_action = LeapOfFaith(agent, 2)

    def update(self):
        if self.jump_action.active:
            return self.jump_action.update()

        controls = SimpleControllerState()
        offset = Vector([0, 60 * sign(self.agent.team), 50])

        (
            controls.steer,
            controls.yaw,
            controls.pitch,
            _roll,
            error,
        ) = point_at_position(self.agent, self.agent.ball.location + offset)

        controls.boost = error < 0.7

        if (
            self.agent.me.boostLevel <= 0
            or self.agent.me.location[2] < 55
            or findDistance(self.agent.me.location, self.agent.ball.location) > 375
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
        controller_state = SimpleControllerState()
        jump = flipHandler(self.agent, self.flip_obj)
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
                    self.followThrough < 0.4
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

        # if self.agent.forward:
        #     controller_state.throttle = 1
        # else:
        #     controller_state.throttle = -1
        if self.agent.onSurface:
            if self.agent.time - self.start_time > 0.2:
                self.active = False
        self.last_controller = controller_state
        return controller_state


class Divine_Mandate:
    # class for performing consecutive inputs over set periods of time. Example: Flipping forward
    def __init__(self, agent, controls_list: list, durations_list: list):
        self.controls = controls_list
        self.durations = durations_list
        self.complete = False
        self.index = 0
        self.current_duration = 0
        self.agent = agent
        # there should be a duration in the durations for every controller given in the list. This inserts 0 for any lacking
        if len(durations_list) < len(controls_list):
            self.durations += [0 * len(controls_list) - len(durations_list)]
        self.active = True

    def create_custom_controls(self, actionCode):
        # perform specialized actions if creating controlers at creation time wasn't feasible
        controller_state = SimpleControllerState()
        if actionCode == 0:
            ball_local = localizeVector(
                self.agent.ball.location + Vector([0, 0, 40]), self.agent.me
            )
            ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
            controller_state.jump = True
            # controller_state.yaw = math.sin(ball_angle)
            # pitch = -math.cos(ball_angle)

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
            (
                controller_state.steer,
                controller_state.yaw,
                controller_state.pitch,
                controller_state.roll,
                _,
            ) = point_at_position(
                self.agent, self.agent.ball.location + Vector([0, 0, 65])
            )
            controller_state.jump = False
            controller_state.throttle = 1
            # print(f"agent height is : {self.agent.me.location[2]}")

        return controller_state

    def update(
        self,
    ):  # call this once per frame with delta time to recieve updated controls
        self.current_duration += self.agent.deltaTime
        if self.current_duration > self.durations[self.index]:
            self.index += 1
            self.current_duration = self.current_duration - self.agent.deltaTime
            # self.current_duration = 0
            if self.index == len(self.controls):
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
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self,):
        best_target = unpicky_demo_picker(self.agent)
        boostTarget, dist = boostSwipe(self.agent)

        if best_target != None and ((self.agent.me.boostLevel > 12 or self.agent.currentSpd >= 2200) or (boostTarget == None or dist > 3000)):
            return demoTarget(self.agent, best_target)

        else:

            if (
                boostTarget != None and dist < 5000 and self.agent.me.boostLevel < 100
            ):
                return driveController(self.agent, boostTarget.flatten(), self.agent.time, expedite=True)

            boost_suggestion = boost_suggester(self.agent, buffer=-20000, mode=0)
            if boost_suggestion != None and not self.agent.boostMonster:
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
            return demoEnemyCar(self.agent, target)

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

    def update(self):
        temp_controller = SimpleControllerState(jump=True)

        if self.agent.time - self.start_time < self.agent.fakeDeltaTime * 10:
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
    def __init__(self,agent):
        super().__init__(agent)

    def update(self):
        return ShellTime(self.agent)


class AerialDefend(baseState):
    pass


class TurnTowardsPosition(baseState):
    def __init__(self, agent, target, targetCode):  # 0 = ball.location
        super().__init__(agent)
        self.target = target
        self.threshold = 1
        self.targetCode = targetCode

    def update(self):
        if self.targetCode == 0:
            self.target = self.agent.ball.location
        localTarg = toLocal(self.target, self.agent.me)
        localAngle = correctAngle(math.degrees(math.atan2(localTarg[1], localTarg[0])))
        controls = SimpleControllerState()

        if abs(localAngle) > self.threshold:
            if self.agent.forward:
                if localAngle > 0:
                    controls.steer = 1
                else:
                    controls.steer = -1

                controls.handbrake = True
                if self.agent.currentSpd < 300:
                    controls.throttle = 0.5
            else:
                if localAngle > 0:
                    controls.steer = -0.5
                else:
                    controls.steer = 1
                controls.handbrake = True
                if self.agent.currentSpd < 300:
                    controls.throttle = -0.5
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
    def __init__(self, agent):
        super().__init__(agent)
        self.started = False
        self.firstFlip = False
        self.secondFlip = False
        # if agent.team == 1:
        #         #     self.finalFlipDistance = 500
        #         # else:
        self.finalFlipDistance = 750
        self.startTime = agent.time
        self.flipState = None

    def fakeKickOffChecker(self):
        closestToBall, bDist = findEnemyClosestToLocation(
            self.agent, self.agent.ball.location
        )
        myDist = findDistance(self.agent.me.location, self.agent.ball.location)

        if bDist:
            if bDist <= myDist * 0.75:
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
                    if spd < maxPossibleSpeed:
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
                self.flipState = LeapOfFaith(
                    self.agent, 0, target=self.agent.ball.location
                )
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
            # if self.agent.onSurface:
            # if self.agent.team == 0:
            self.flipState = LeapOfFaith(self.agent, 0)
            self.secondFlip = True
            return self.flipState.update()
            # else:
            #     ball_local = self.agent.ball.local_location
            #     # 4 flip left, 5 flip right,
            #     if ball_local[0] > 10:
            #         self.flipState = LeapOfFaith(self.agent, 4)
            #         print("flipping left")
            #
            #     elif ball_local[0] < -10:
            #         self.flipState = LeapOfFaith(self.agent, 5)
            #         print("flipping right")
            #     else:
            #         self.flipState = LeapOfFaith(self.agent, 0)
            #         print("flipping at ball")
            #
            #     self.secondFlip = True
            #     return self.flipState.update()
            # self.flipState = LeapOfFaith(self.agent, 0, self.agent.ball.location)
            # self.secondFlip = True
            # return self.flipState.update()


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
            return refuel(self.agent, result[0])
        else:
            self.active = False
            return ShellTime(self.agent)

class PreemptiveStrike(baseState):
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

    def create_speed_flip_cancel(self, left=False):
        controls = []
        timers = []
        # first_controller = SimpleControllerState()
        # if left:
        #     first_controller.steer = 1
        # else:
        #     first_controller.steer = -1
        #
        # first_controller.handbrake = True
        # first_controller.throttle = 1
        # first_controller.boost = True
        # first_controller.jump = False
        # controls.append(first_controller)
        # timers.append(self.agent.fakeDeltaTime * 1)

        second_controller = SimpleControllerState()

        # if left:
        #     second_controller.steer = 1
        # else:
        #     second_controller.steer = -1
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
                self.short_offset = -50 * sign(self.agent.team)
            else:
                self.firstFlip = self.create_diagonal_speed_flip(left=True)
                self.onRight = False
                self.short_offset = 50 * sign(self.agent.team)
                # print(f"on left and short offset == {self.short_offset}")

        else:
            # middle kickoff defaulting to right
            self.firstFlip = self.create_diagonal_speed_flip(left=True)
            # self.onRight shouldn't matter

    def wide_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            if distance2D(self.agent.me.location, self.agent.ball.location) > 3150:
                # return driveController(self.agent, self.enemyGoal+Vector([0,4000*sign(self.agent.team),0]),
                return driveController(
                    self.agent,
                    self.agent.ball.location
                    + Vector([0, sign(self.agent.team) * -100, 0]),
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
                ) = point_at_position(self.agent, self.agent.me.location+ self.agent.me.velocity.normalize().flatten().scale(1000))
                _controller.boost = True
                _controller.handbrake = True
                return _controller

            else:
                self.phase = 4
                # print(f"switched to stage 4! {self.agent.time}")

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:
            if distance2D(self.agent.me.location, self.agent.ball.location) > 450:
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [25, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal,self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(distance2D(self.agent.me.location,dummy_location)*.5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-25, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 5
                else:
                    _code = 4
                #     _code = 4
                # else:
                #     _code = 5

                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def short_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector(
                [self.short_offset, sign(self.agent.team) * 2825.0, 0]
            )
            if distance2D(self.agent.me.location, drive_target) > 575:
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
                ) = point_at_position(self.agent, self.agent.me.location+ self.agent.me.velocity.normalize().flatten().scale(1000))
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
                ) = point_at_position(self.agent,
                                      self.agent.me.location + self.agent.me.velocity.normalize().flatten().scale(
                                          1000))
                _controller.boost = True
                _controller.handbrake = True
                return _controller
            else:
                self.phase = 4

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:
            if (
                distance2D(self.agent.me.location, self.agent.ball.location) > 500
                or not self.agent.onSurface
            ):
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [65, 75 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-65, 75 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 4
                else:
                    _code = 5
                #_code = 0
                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def middle_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector([0, sign(self.agent.team) * 4000, 0])
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
            if distance2D(self.agent.me.location, self.agent.ball.location) > 3850:#3875:
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
                    ) = point_at_position(self.agent, self.agent.me.location+ self.agent.me.velocity.normalize().flatten().scale(1000))
                    return controls

        # stage 4 - aim towards just offcenter of ball
        if self.phase == 4:

            if (
                distance2D(self.agent.me.location, self.agent.ball.location) > 500
                or not self.agent.onSurface
            ):
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [55, 75 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-55, 75 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 4
                else:
                    _code = 5
                #_code = 0
                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def retire(self):
        if self.phase != 5 or self.secondFlip == None or not self.secondFlip.active:
            self.active = False
            #self.agent.activeState = None
            # print(f"retiring on stage {self.phase} {self.agent.time}")

    def update(self):
        if not self.agent.gameInfo.is_round_active:
            self.setup()

        if not self.agent.gameInfo.is_kickoff_pause:
            # print(f"retiring due to kickoff pause")
            self.retire()

        if self.KO_option != None:
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

class PreemptiveStrike_BAK(baseState):  # real kickoff
    def __init__(self, agent):
        self.agent = agent
        self.started = False
        self.firstFlip = None
        self.secondFlip = None
        self.active = True
        self.startTime = agent.time
        self.kickoff_type = getKickoffPosition(agent.me.location)
        agent.stubbornessTimer = 5
        self.onRight = True
        self.short_offset = 75
        self.setup()
        self.enemyGoal = Vector([0, 5200 * -sign(self.agent.team), 0])
        self.phase = 1
        self.KO_option = None
        self.maintaining_speed = False
        self.first_recovery = None
        self.queued_retire = False

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
                self.short_offset = -50 * sign(self.agent.team)
            else:
                self.firstFlip = self.create_diagonal_speed_flip(left=True)
                self.onRight = False
                self.short_offset = 50 * sign(self.agent.team)
                # print(f"on left and short offset == {self.short_offset}")

        else:
            # middle kickoff defaulting to right
            self.firstFlip = self.create_diagonal_speed_flip(left=True)
            # self.onRight shouldn't matter

    def wide_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            if distance2D(self.agent.me.location, self.agent.ball.location) > 3150:
                if self.agent.me.location[1] < 0:
                    y_off = -40
                else:
                    y_off = 40

                return driveController(
                    self.agent,
                    self.agent.ball.location + Vector([0, y_off, 0]),
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
                # controls = self.firstFlip.update()
                # if self.agent.currentSpd > 2210:
                #     controls.boost = False
                # return controls

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
            if distance2D(self.agent.me.location, self.agent.ball.location) > 550:
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [35, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal,self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(distance2D(self.agent.me.location,dummy_location)*.5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-35, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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
            # if distance2D(self.agent.closestEnemyToBall.location,self.agent.ball.location) < 600:
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 5
                else:
                    _code = 4
                #     _code = 4
                # else:
                #     _code = 5

                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def short_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector(
                [self.short_offset, sign(self.agent.team) * 2850.0, 0]
            )
            if distance2D(self.agent.me.location, drive_target) > 575:
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
                controls = self.firstFlip.update()
                if self.agent.currentSpd > 2210:
                    controls.boost = False
                return controls
                # return self.firstFlip.update()
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
                distance2D(self.agent.me.location, self.agent.ball.location) > 550
                or not self.agent.onSurface
            ):
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [60, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-60, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 4
                else:
                    _code = 5
                # _code = 0
                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def middle_handler(self):
        # stage 1 - drive to boost pad
        if self.phase == 1:
            drive_target = Vector([0, sign(self.agent.team) * 4000, 0])
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
                distance2D(self.agent.me.location, self.agent.ball.location) > 3850
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
                controls = self.firstFlip.update()
                if self.agent.currentSpd > 2210:
                    controls.boost = False
                return controls
                # return self.firstFlip.update()
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
                distance2D(self.agent.me.location, self.agent.ball.location) > 550
                or not self.agent.onSurface
            ):
                if self.agent.me.location[0] > self.agent.ball.location[0]:
                    dummy_location = self.agent.ball.location + Vector(
                        [45, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)
                else:
                    dummy_location = self.agent.ball.location + Vector(
                        [-45, 120 * sign(self.agent.team), 0]
                    )
                    # _direction = direction(self.enemyGoal, self.agent.ball.location)
                    drive_target = dummy_location  # + _direction.scale(
                    # distance2D(self.agent.me.location, dummy_location) * .5)

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

        # stage 5 - flip through center and end kickoff
        # 4 flip left, 5 flip right
        if self.phase == 5:
            if self.secondFlip == None:
                if (
                    self.agent.team == 0
                    and self.agent.me.location[0] < self.agent.ball.location[0]
                    or self.agent.team == 1
                    and self.agent.me.location[0] > self.agent.ball.location[0]
                ):
                    _code = 4
                else:
                    _code = 5
                # _code = 0
                self.secondFlip = LeapOfFaith(self.agent, _code, target=None)
            controls = self.secondFlip.update()
            if not self.secondFlip.active:
                self.retire()
            return controls

    def retire(self):
        if (
            not self.secondFlip
            or not self.secondFlip.active
            or self.agent.time - self.startTime > 3
        ):
            self.active = False
        else:
            self.queued_retire = True

    def update(self):
        if not self.agent.gameInfo.is_round_active:
            self.setup()

        if not self.agent.gameInfo.is_kickoff_pause or self.agent.ball.location.flatten() != Vector(
            [0, 0, 0]
        ):
            # print(f"retiring due to kickoff pause")
            self.retire()

        if self.queued_retire:
            self.retire()

        if self.KO_option != None:
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
        self.tick_length = 5
        self.squash_index = 0
        self.update_count = 0
        self.collision_timer = 0
        self.collision_location = Vector([0, 0, 0])
        self.aim_direction = None
        self.recovery_limit = 1.5

    def get_roll_value(self):
        if self.roll_type == 1:
            return turnController(
                -self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
            )  # will make bot roll top up

        elif self.roll_type == 2:
            return turnController(
                self.agent.me.rotation[2], self.agent.me.rotational_velocity[0] / 4
            )  # will make bot roll top down

        elif self.roll_type == 3:
            return turnController(
                -(3.1415 / 2) - self.agent.me.rotation[2],
                self.agent.me.rotational_velocity[0] / 4,
            )  # will make bot roll top left

        elif self.roll_type == 4:
            return turnController(
                3.1415 / 2 - self.agent.me.rotation[2],
                self.agent.me.rotational_velocity[0] / 4,
            )  # will make bot roll top right

    def get_controls(self):
        controller_state = SimpleControllerState()

        aim_vector = self.collision_location - self.agent.me.location
        if self.collision_timer <= self.recovery_limit:
            aim_vector.data[self.squash_index] = 0

        if (
            self.aim_direction != None
            and self.collision_timer > self.recovery_limit
            and self.agent.me.location[2] > 100
        ):
            aim_vector = (
                self.aim_direction
            )  # (self.aim_direction + aim_vector.normalize()).normalize()

        aim_vector = aim_vector.normalize()

        align_car_to(controller_state, self.agent.me.avelocity, aim_vector, self.agent)

        # print(self.collision_timer)
        if self.collision_timer > self.recovery_limit:
            if self.agent._forward.dotProduct(aim_vector) > 0.7:
                if abs(self.agent.me.velocity[2]) < 1500 or self.agent.boostMonster:
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

    def run_simulation(self):
        self.update_count = 5
        simulated_location = self.agent.me.location.scale(1)
        simulated_velocity = self.agent.me.velocity.scale(1)
        simulated_time = 0
        self.aim_direction = None
        while (
            simulated_time < 10
        ):  # 0 gravity could lead to infinite loop! may want to add hard limiters
            simulated_velocity = simulated_velocity + Vector(
                [0, 0, self.agent.gravity]
            ).scale((self.agent.fakeDeltaTime) * self.tick_length)
            if simulated_velocity.magnitude() > 2300:
                simulated_velocity = simulated_velocity.normalize().scale(2300)
            simulated_location = simulated_location + simulated_velocity.scale(
                (self.agent.fakeDeltaTime) * self.tick_length
            )
            simulated_time += self.agent.fakeDeltaTime * self.tick_length
            if simulated_location[2] >= self.ceiling_limit:
                self.roll_type = 2
                self.squash_index = 2
                # print(f"ceiling recovery {self.agent.time}")
                self.aim_direction = Vector([0, 0, 1])
                break
            if simulated_location[2] <= self.ground_limit:
                self.roll_type = 1
                self.squash_index = 2

                # print(f"ground recovery {self.agent.time}")
                break

            if simulated_location[0] <= -self.x_limit:
                # on blue's right wall
                # print(f"side wall recovery {self.agent.time}")
                self.squash_index = 0
                if simulated_velocity[1] < 0:
                    # need to keep top right
                    self.roll_type = 4

                else:
                    # need to keep top left
                    self.roll_type = 3
                break

            if simulated_location[0] >= self.x_limit:
                # on blue's left wall
                self.squash_index = 0
                # print(f"side wall recovery {self.agent.time}")
                if simulated_velocity[1] < 0:
                    # need to keep top left
                    self.roll_type = 3

                else:
                    # need to keep top right
                    self.roll_type = 4
                break

            if simulated_location[1] <= -self.y_limit:
                # on blue's backboard
                # print(f"back wall recovery {self.agent.time}")
                if abs(simulated_location[0]) < 893:
                    if simulated_location[2] < 642:
                        self.roll_type = 1
                        self.squash_index = 2
                        break
                self.squash_index = 1
                if simulated_velocity[0] < 0:
                    # need to keep top left
                    self.roll_type = 3

                else:
                    # need to keep top right
                    self.roll_type = 4
                break

            if simulated_location[1] >= self.y_limit:
                # on orange's backboard
                # print(f"side wall recovery {self.agent.time}")
                if abs(simulated_location[0]) < 893:
                    if simulated_location[2] < 642:
                        self.roll_type = 1
                        self.squash_index = 2
                        break
                self.squash_index = 1
                if simulated_velocity[0] < 0:
                    # need to keep top right
                    self.roll_type = 4

                else:
                    # need to keep top left
                    self.roll_type = 3
                break
        if simulated_time >= 10:
            self.roll_type = 1
            self.squash_index = 2

        if self.aim_direction == None:
            self.aim_direction = Vector([0, 0, -1])

        self.collision_timer = simulated_time
        self.collision_location = simulated_location

    def update(self):
        self.update_count -= 1
        if self.update_count < 0:
            self.run_simulation()
        controller_state = self.get_controls()
        if (
            self.agent.onSurface
            or self.agent.me.location[1] <= self.agent.recovery_height
        ):
            self.active = False

        # controller_state = SimpleControllerState()

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


class catchTesting(baseState):
    def update(self):
        return catch_ball(self.agent)


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
        if self.agent.scorePred == None:
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
            return ShellTime(self.agent)

        offensive = sign(self.agent.team) * self.agent.ball.location[1] < 0
        if offensive and self.agent.me.boostLevel < self.agent.boostThreshold:
            return backmanBoostGrabber(self.agent)

        return gate(self.agent, hurry=False)


class BlessingOfSafety(baseState):
    def update(self):
        distMin = 1500

        offensive = sign(self.agent.team) * self.agent.ball.location[1] < 0

        if self.agent.rotationNumber == 1:
            return ShellTime(self.agent)

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
            # return ShellTime(self.agent,retreat_enabled=self.agent.me.location == self.agent.lastMan) #retreat_enabled=self.agent.me.location != self.agent.lastMan
            return ShellTime(self.agent)
        else:
            if self.agent.rotationNumber == 2:
                # if len(self.agent.allies) == 1 and self.agent.team == 0:
                #     return playBack(self.agent, buffer=4500)
                if len(self.agent.allies) > 0:
                    # if self.agent.team !=0 or self.agent.lastMan != self.agent.me.location:
                    if self.agent.lastMan != self.agent.me.location:
                        return secondManPositioning(self.agent)
                    else:
                        return thirdManPositioning(self.agent)
                return playBack(self.agent)
            else:
                if len(self.agent.allies) > 0:
                    return thirdManPositioning(self.agent)
                    # return secondManPositioning(self.agent)
                else:
                    return playBack(self.agent)

        # catch case
        return playBack(self.agent)

    # def update(self):
    #     distMin = 1500
    #
    #     offensive = sign(self.agent.team) * self.agent.ball.location[1] < 0
    #
    #     if self.agent.rotationNumber == 1:
    #         return ShellTime(self.agent)
    #
    #     if (
    #             (distance2D(
    #             Vector([0, 5200 * sign(self.agent.team), 0]), self.agent.ball.location
    #         )
    #         < distMin) or (distance2D(
    #             Vector([0, 5200 * sign(self.agent.team), 0]), self.agent.currentHit.pred_vector
    #         )
    #         < distMin)
    #     ):
    #         #return ShellTime(self.agent,retreat_enabled=self.agent.me.location == self.agent.lastMan) #retreat_enabled=self.agent.me.location != self.agent.lastMan
    #         return ShellTime(self.agent)
    #     else:
    #         if True:
    #             self.agent.wallShot = False
    #             if (self.agent.rotationNumber == 2):
    #                 if len(self.agent.allies) > 0:
    #                     #if self.agent.team !=0 or self.agent.lastMan != self.agent.me.location:
    #                     if self.agent.lastMan != self.agent.me.location:
    #                         return secondManPositioning(self.agent)
    #                     else:
    #                         return thirdManPositioning(self.agent)
    #                 return playBack(self.agent,buffer = 4500)
    #             else:
    #                 return thirdManPositioning(self.agent)

    # def update(self):
    #     if self.agent.team == 0:
    #         return self.update_old()
    #
    #     distMin = 2000
    #
    #     offensive = self.agent.ball.location[1] * -sign(self.agent.team) > 1000
    #
    #     if offensive:
    #         if self.agent.rotationNumber == 2:
    #             if self.agent.me.location[1] != self.agent.lastManY:
    #                 return secondManPositioning(self.agent)
    #             else:
    #                 if len(self.agent.allies) >= 2:
    #                     return thirdManPositioning(self.agent)
    #     else:
    #         if self.agent.rotationNumber == 2:
    #             if self.agent.me.location[1] != self.agent.lastManY:
    #                 return playBack(self.agent,buffer=2000)
    #             else:
    #                 return playBack(self.agent, buffer=3500)
    #
    #     return playBack(self.agent, buffer=3000)


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
        # return carry_flick(self.agent,cradled = True)
        return carry_flick_new(self.agent, cradled=True)
        # return newCarry(self.agent)


class Holy_Shield(baseState):
    def update(self):
        return defensive_posture(self.agent)


class emergencyDefend(baseState):
    def update(self):
        penetrationPosition = convertStructLocationToVector(self.agent.goalPred)
        penetrationPosition.data[1] = 5350 * sign(self.agent.team)
        if self.agent.goalPred.game_seconds - self.agent.gameInfo.seconds_elapsed > 0.1:
            if distance2D(self.agent.me.location, penetrationPosition) > 100:
                return testMover(self.agent, penetrationPosition, 2300)
        else:
            if penetrationPosition[2] > 300:
                self.activeState = LeapOfFaith(self.agent, -1)
                return self.activeState.update()

            else:
                self.activeState = LeapOfFaith(self.agent, 0)
                return self.activeState.update()


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


def twos_manager(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            if agentType == LeapOfFaith:
                if agent.activeState.active != False:
                    return
            if agentType == Divine_Mandate:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == BlessingOfDexterity:
                if agent.activeState.active != False:
                    return

            if agentType == Wings_Of_Justice:
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

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                if agent.enemyAttacking:
                    agent.contested = True

            if (
                distance2D(hit.pred_vector, myGoalLoc) <= 2000
                or distance2D(agent.enemyTargetVec, myGoalLoc) <= 2000
                or ballDistanceFromGoal <= 2000
            ):
                if agent.enemyAttacking:
                    agent.contested = True
                    agent.timid = False
                    scared = False

            if hit.hit_type == 5:
                if agentType != Wings_Of_Justice:
                    agent.activeState = hit.aerialState
                return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

        else:
            agent.activeState = PreemptiveStrike(agent)


def team_synergy(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            if locked_in(agent, agentType):
                return

            my_goal = Vector([0, 5200 * sign(agent.team), 200])
            inclusive_team = agent.allies[:]
            inclusive_team.append(agent.me)
            inclusive_team = sorted(inclusive_team, key=lambda x: x.index)

            ballDistanceFromGoal = distance2D(my_goal, agent.ball.location)
            carDistanceFromGoal = distance2D(my_goal, agent.me.location)
            current_ball_position = agent.ball.location
            offensive = current_ball_position[1] * sign(agent.team) > 0

            team_info = []

            if agent.dribbling:
                if agentType != AngelicEmbrace:
                    agent.activeState = AngelicEmbrace(agent)
                return

            for tm in inclusive_team:
                # if agent.team == 1:
                if tm.location[1] * sign(agent.team) > current_ball_position[1] * sign(
                    agent.team
                ):
                    dist = distance2D(tm.location, current_ball_position)
                    # if offensive:
                    #     if player_retreat_status(tm,agent.team):
                    #         dist+=1500

                    # if agent.ball.location[0] > 1000:
                    #     if tm.location[0] >= agent.ball.location[0]:
                    #         dist = clamp(dist, 0, dist - 1000)
                    # elif agent.ball.location[0] < -1000:
                    #     if tm.location[0] <= agent.ball.location[0]:
                    #         dist = clamp(dist, 0, dist - 1000)

                else:
                    dist = distance2D(tm.location, my_goal) * 2

                team_info.append((tm, dist))

            rotations = sorted(team_info, key=lambda x: x[1])

            if agent.me.location == rotations[0][0].location:
                agent.rotationNumber = 1
            elif agent.me.location == rotations[1][0].location:
                agent.rotationNumber = 2
            else:
                agent.rotationNumber = 3

            # if agent.hits[4] != None:
            #     print(f"agent {agent.index} found an aerial target! {agent.time}")

            if agent.rotationNumber != 1 and agent.rotationNumber != 2:
                if agent.hits[4] != None:
                    agent.currentHit = agent.hits[4]
                    agent.ballDelay = agent.currentHit.time_difference()
                    if agentType != Wings_Of_Justice:
                        agent.activeState = agent.hits[4].aerialState  # .create_copy()
                        # agent.log.append(f"Going for aerial! {agent.time}")
                    return
                agent.currentHit = find_soonest_hit(agent)
                agent.ballDelay = agent.currentHit.time_difference()
                if agentType == DivineGrace:
                    if agent.activeState.active != False:
                        return

                if not agent.onSurface:
                    if agent.me.location[2] > agent.recovery_height:
                        if agentType != DivineGrace:
                            agent.activeState = DivineGrace(agent)
                        return
                if agentType != BlessingOfSafety:
                    agent.activeState = BlessingOfSafety(agent)
                return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if agent.team == 0:
                        if boostOpportunity[1] == 0 or boostOpportunity[1] == 1:
                            getBoost = True
                    else:
                        if boostOpportunity[1] == 2 or boostOpportunity[1] == 3:
                            getBoost = True
                    if getBoost:
                        if agentType != HeavenlyReprieve:
                            agent.activeState = HeavenlyReprieve(
                                agent, boostOpportunity[0]
                            )
                        return

            if agent.rotationNumber == 2:
                if agent.hits[4] != None:
                    agent.currentHit = agent.hits[4]
                    agent.ballDelay = agent.currentHit.time_difference()
                    if agentType != Wings_Of_Justice:
                        agent.activeState = agent.hits[4].aerialState  # .create_copy()
                        # agent.log.append(f"Going for aerial! {agent.time}")
                    return
                else:
                    agent.currentHit = find_soonest_hit(agent)
                    agent.ballDelay = agent.currentHit.time_difference()
                    if agentType == DivineGrace:
                        if agent.activeState.active != False:
                            return

                    if not agent.onSurface:
                        if agent.me.location[2] > agent.recovery_height:
                            if agentType != DivineGrace:
                                agent.activeState = DivineGrace(agent)
                            return
                    if agentType != BlessingOfSafety:
                        agent.activeState = BlessingOfSafety(agent)
                    return

            fastesthit = find_soonest_hit(agent)
            hit = fastesthit
            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            tempDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                if agent.enemyAttacking:
                    agent.contested = True

            if hit.hit_type == 5:
                # print(f"going for aerial {agent.time}")
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

            if butterZone(hit.pred_vector):
                agent.contested = True
                agent.enemyAttacking = True

            if agent.goalPred != None:
                agent.contested = True
                agent.enemyAttacking = True

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward

            # if not agent.contested and not goalward:
            #     if hit.hit_type == 4:
            #         if agent.hits[1] != None:
            #             if not butterZone(hit.pred_vector):
            #                 temptime = agent.hits[1].prediction_time - agent.time
            #                 if (
            #                     temptime
            #                     < agent.enemyBallInterceptDelay
            #                     - agent.contestedTimeLimit
            #                 ):
            #                     hit = agent.hits[1]
            #
            #     elif hit.hit_type == 1:
            #         if agent.hits[0] != None:
            #             if not butterZone(hit.pred_vector):
            #                 if agent.me.boostLevel > 30:
            #                     temptime = agent.hits[0].prediction_time - agent.time
            #                     if (
            #                         temptime
            #                         < agent.enemyBallInterceptDelay
            #                         - agent.contestedTimeLimit
            #                     ):
            #                         hit = agent.hits[0]

            if not agent.contested:
                if hit.hit_type == 4:
                    if agent.hits[1] != None:
                        if hit.pred_vel[1] * -sign(agent.team) >= 1:
                            if not butterZone(hit.pred_vector):
                                temptime = agent.hits[1].prediction_time - agent.time
                                if (
                                    temptime
                                    < agent.enemyBallInterceptDelay
                                    - agent.contestedTimeLimit
                                ):
                                    hit = agent.hits[1]

                if hit.hit_type == 1:
                    if agent.hits[0] != None:
                        if agent.hits[0].pred_vel[1] * -sign(agent.team) >= 1:
                            if not butterZone(hit.pred_vector):
                                if agent.me.boostLevel > 30:
                                    temptime = (
                                        agent.hits[0].prediction_time - agent.time
                                    )
                                    if (
                                        temptime
                                        < agent.enemyBallInterceptDelay
                                        - agent.contestedTimeLimit
                                    ):
                                        hit = agent.hits[0]

            if hit.hit_type == 5:
                # print(f"going for aerial {agent.time}")
                if agentType != Wings_Of_Justice:
                    agent.activeState = hit.aerialState  # .create_copy()
                    # agent.log.append(f"Going for aerial! {agent.time}")
                return

            if carDistanceFromGoal > ballDistanceFromGoal:
                if agentType != HolyProtector:
                    agent.activeState = HolyProtector(agent)
                return

            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.gameInfo.seconds_elapsed
            # if agent.team == 1:
            #     catchViable = ballCatchViable(agent)
            # else:
            catchViable = False

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
                if catchViable:
                    if not agent.dribbling:
                        agent.currentHit = agent.hits[1]
                        agent.ballDelay = agent.currentHit.time_difference()
                        if agent.activeState != Celestial_Arrest:
                            agent.activeState = Celestial_Arrest(agent)
                        return
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

                else:
                    agent.log.append(f"condition leaked through! {hit.hit_type}")

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
                return


            fastesthit = agent.sorted_hits[0]  # find_soonest_hit(agent)
            hit = fastesthit

            if (
                hit.hit_type == 2
                and abs(agent.me.location[1]) > 5100
                and len(agent.sorted_hits) > 1
            ):
                fastesthit = agent.sorted_hits[1]
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

            if tempDelay >= agent.enemyBallInterceptDelay - agent.contestedTimeLimit:
                if agent.enemyAttacking:
                    agent.contested = True

            if agent.goalPred != None:
                agent.contested = True
                agent.enemyAttacking = True

            if butterZone(hit.pred_vector):
                agent.contested = True
                agent.enemyAttacking = True

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
            inclusive_team = agent.allies[:]
            inclusive_team.append(agent.me)
            inclusive_team = sorted(inclusive_team, key=lambda x: x.index)
            offensive = agent.ball.location[1] * -sign(agent.team) > 0

            if agent.team == 5:
                if (
                    not agent.gameInfo.is_round_active
                    or agent.gameInfo.is_kickoff_pause
                ):
                    man = 2
                else:
                    rotations = prototype_rotations(agent)
                    man = clamp(3, 1, rotations.index(agent.index) + 1)

                agent.rotationNumber = man
                agent.boostThreshhold = man * 25

            else:
                if (
                    not agent.gameInfo.is_round_active
                    or agent.gameInfo.is_kickoff_pause
                ):
                    man = 2
                    if agent.me.location == agent.lastMan:
                        man = 3
                    agent.rotationNumber = man

                    agent.currentHit = fastesthit
                    agent.ballDelay = fastesthit.time_difference()
                    # if agentType != Kickoff_Boosties and agent.team == 0:
                    #     agent.activeState = Kickoff_Boosties(agent)
                    #     return
                    # else:
                    #     #print("not locked in?")
                    if agentType != BlessingOfSafety:
                        agent.activeState = BlessingOfSafety(agent)
                    return
                else:
                    man = 1
                    if agent.me.location[1] * sign(agent.team) < hit.pred_vector[
                        1
                    ] * sign(agent.team):
                        if agent.me.location != lastMan:
                            # if hit.pred_vector[1] * sign(agent.time) < 4000:
                            man = len(agent.allies) + 1

                    if offensive:
                        if retreating_tally(agent.allies) != len(agent.allies):
                            if agent.me.retreating:
                                if agent.me.location != lastMan:
                                    if distance2D(hit.pred_vector, myGoalLoc) > 2000:
                                        man = len(agent.allies) + 1

                    if man != len(agent.allies) + 1:
                        myDist = weighted_distance_2D(
                            agent.me.location, agent.ball.location
                        )
                        for ally in agent.allies:
                            if not ally.demolished:
                                if ally.location[1] * sign(
                                    agent.team
                                ) > agent.ball.location[1] * sign(agent.team):
                                    allyDist = weighted_distance_2D(
                                        ally.location, agent.ball.location
                                    )
                                    if allyDist < myDist:
                                        if not ally.retreating:
                                            man += 1

            man = clamp(3, 1, man)

            if len(agent.enemies) < 4 and not agent.contested and hit.hit_type != 5:
                # if not agent.contested and agent.lastMan != agent.me.location and man == 1 and hit.hit_type != 0 and agent.goalPred == None and not ballHeadedTowardsMyGoal_testing(agent, hit) and not agent.ignore_kickoffs:# and agent.team == 1:
                chrono_hits = agent.sorted_hits
                prev_hit = hit
                for h in chrono_hits:
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
                    if agent.team == 0:
                        if boostOpportunity[1] == 0 or boostOpportunity[1] == 1:
                            getBoost = True
                    else:
                        if boostOpportunity[1] == 2 or boostOpportunity[1] == 3:
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

                if carDistanceFromGoal > ballDistanceFromGoal:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                # if agent.contested and agent.enemyBallInterceptDelay +.2 < hit.time_difference() and agent.goalPred == None:
                #     if agent.team == 1:
                #         if agentType != Holy_Shield:
                #             agent.activeState = Holy_Shield(agent)
                #         return

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

            fastesthit = agent.sorted_hits[0]  # find_soonest_hit(agent)
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

            if agent.goalPred != None:
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
            offensive = agent.ball.location[1] * -sign(agent.team) > 0

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
                    if agent.team == 0:
                        if boostOpportunity[1] == 0 or boostOpportunity[1] == 1:
                            getBoost = True
                    else:
                        if boostOpportunity[1] == 2 or boostOpportunity[1] == 3:
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

                if carDistanceFromGoal > ballDistanceFromGoal:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return

                # if agent.contested and agent.enemyBallInterceptDelay +.2 < hit.time_difference() and agent.goalPred == None:
                #     if agent.team == 1:
                #         if agentType != Holy_Shield:
                #             agent.activeState = Holy_Shield(agent)
                #         return

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


def soloStateManager(agent):
    agentType = type(agent.activeState)
    if agentType != PreemptiveStrike:

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            # agent.resetTimer += agent.deltaTime

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
            # print(tempDelay)

            if tempDelay >= agent.enemyBallInterceptDelay - 0.5:
                if agent.enemyAttacking:
                    agent.contested = True

            if tempDelay >= agent.enemyBallInterceptDelay + 1:
                if not butterZone(hit.pred_vector):
                    if ballDistanceFromGoal <= 5000:
                        agent.timid = True
                    else:
                        scared = True
                    # print(tempDelay,agent.enemyBallInterceptDelay)
                    # pass

            if (
                distance2D(hit.pred_vector, myGoalLoc) <= 2000
                or distance2D(agent.enemyTargetVec, myGoalLoc) <= 2000
            ):
                agent.contested = True
                agent.timid = False
                scared = False

            # if not agent.contested or not agent.enemyAttacking:
            #     if agent.hits[0] != None:
            #         temptime = (
            #             agent.hits[0].prediction_time - agent.gameInfo.seconds_elapsed
            #         )
            #         # if temptime >=1:
            #         if hit.hit_type != 2:
            #             # if temptime < agent.enemyBallInterceptDelay - .5:
            #             hit = agent.hits[0]

            # if False:
            if not agent.contested:
                chrono_hits = agent.sorted_hits
                prev_hit = hit
                for h in chrono_hits:
                    if h.time_difference() < 1:
                        break

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

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.time
            agent.ballGrounded = False

            # print(agent.ballDelay, agent.enemyBallInterceptDelay,agent.contested,agent.timid)

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

            if agentType == Wings_Of_Justice:
                if agent.activeState.active != False:
                    return

            if not agent.onSurface:
                if agent.me.location[2] > agent.recovery_height:
                    if agentType != DivineGrace:
                        agent.activeState = DivineGrace(agent)
                    return

            if agent.dribbling:
                if not goalward:
                    if agentType != AngelicEmbrace:
                        agent.activeState = AngelicEmbrace(agent)
                    return
            # else:
            #     agent.resetTimer += agent.deltaTime
            #     if agent.resetTimer >= 5:
            #         agent.resetTimer = 0
            #         print("setting up dribble training")
            #         #game_state = GameState()
            #         #self.set_game_state(game_state)
            #         ball_state = BallState(Physics(location=Vector3(agent.me.location[0], agent.me.location[1], agent.me.location[2]+160),velocity=Vector3(agent.me.velocity[0],agent.me.velocity[1],agent.me.velocity[2])))
            #         game_state = GameState(ball=ball_state)
            #         agent.set_game_state(game_state)
            #         if agentType != AngelicEmbrace:
            #             agent.activeState = AngelicEmbrace(agent)
            #         return

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
                if hit.hit_type != 2:
                    if agentType != HolyProtector:
                        agent.activeState = HolyProtector(agent)
                    return
                else:
                    if agentType != ScaleTheWalls:
                        agent.activeState = ScaleTheWalls(agent)
                        # print("scaling walls")
                    # print(f"scale the walls defensive {agent.time}")
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
                    agent.log.append("we got an eroneous hit_type somehow")
            agent.log.append("rawr")

        else:
            agent.activeState = PreemptiveStrike(agent)


def soloStateManager_testing(agent):
    agentType = type(agent.activeState)

    if (
        agentType != PreemptiveStrike
        or agentType == PreemptiveStrike
        and not agent.activeState.active
    ):

        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5200 * sign(agent.team), 200])
            enemyGoalLoc = Vector([0, 5200 * -sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            # agent.resetTimer += agent.deltaTime
            if locked_in(agent, agentType):
                return

            hit = agent.sorted_hits[0]  # find_soonest_hit(agent)

            openNet = openGoalOpportunity(agent)
            agent.openGoal = openNet
            agent.timid = False
            scared = False
            tempDelay = hit.time_difference()
            offensive = hit.pred_vector[1] * sign(agent.team) < 0

            if tempDelay >= agent.enemyBallInterceptDelay:
                if agent.enemyAttacking:
                    agent.contested = True
                    if (
                        tempDelay > agent.enemyBallInterceptDelay and offensive
                    ):  # and agent.me.boostLevel < agent.boostThreshold:
                        if (
                            findDistance(agent.ball.location, agent.me.location) > 600
                        ):  # and not extendToGoal(agent,hit.pred_vector,agent.me.location):
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

            if agent.goalPred != None:
                agent.contested = True
                scared = False

            if hit.hit_type == 5:
                if not agent.onSurface:
                    if agentType != Wings_Of_Justice:
                        agent.activeState = hit.aerialState  # .create_copy()
                    print(f" aerial is accepted... {agent.time}")
                    return
                else:
                    if agent.sorted_hits[1] != None:
                        hit = agent.sorted_hits[1]

            if agentType == Do_No_Evil:
                if agent.activeState.active:
                    return

            if (
                not agent.contested
                and not butterZone(hit.pred_vector)
                and not ballHeadedTowardsMyGoal_testing(agent, hit)
            ):
                chrono_hits = agent.sorted_hits
                prev_hit = hit
                for h in chrono_hits:
                    if ballHeadedTowardsMyGoal_testing(agent, h):
                        break

                    if h.hit_type == 5:
                        continue

                    if h.pred_vel[1] * -sign(agent.team) >= 1:
                        # current_butter = butterZone(h.pred_vector) and h.pred_vector[1] * sign(agent.team) < 0
                        temptime = h.time_difference()
                        if (
                            temptime
                            < agent.enemyBallInterceptDelay - agent.contestedTimeLimit
                        ) or not agent.enemyAttacking:
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
                        prev_hit = h

            goalward = ballHeadedTowardsMyGoal_testing(agent, hit)
            agent.goalward = goalward
            agent.currentHit = hit
            agent.ballDelay = hit.prediction_time - agent.time

            catchViable = False  # ballCatchViable(agent)# and agent.team == 1

            if hit.hit_type == 2:
                agent.wallShot = True
            else:
                agent.wallShot = False

            createBox(agent, hit.pred_vector)

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

            # if scared and agent.team == 0:
            # if scared:
            #     if agent.activeState != BlessingOfSafety:
            #         agent.activeState = BlessingOfSafety(agent)
            #     # print(f"We scared! {agent.time}")
            #     return

            if agent.scorePred != None:
                if (
                    clamp(
                        15000,
                        0.0001,
                        findDistance(
                            agent.closestEnemyToBall.location, agent.scorePred.location
                        )
                        - 150,
                    )
                    / 2300
                    > agent.scorePred.time - agent.time
                ):
                    if (
                        (agent.scorePred.time - agent.time) + 0.5
                        < agent.enemyBallInterceptDelay
                        and (agent.scorePred.time - agent.time) < 4.5
                        and not agent.dribbling
                        and not agent.closestEnemyToBall.demolished
                    ):
                        # if agent.team == 1:
                        agent.activeState = Do_No_Evil(agent)
                        return

                if agent.enemyBallInterceptDelay > agent.scorePred.time - agent.time:
                    if agent.activeState != BlessingOfSafety:
                        agent.activeState = BlessingOfSafety(agent)
                    return

            boostOpportunity = inCornerWithBoost(agent)
            if boostOpportunity != False:
                if agent.me.boostLevel <= 50:
                    getBoost = False
                    if agent.team == 0:
                        if boostOpportunity[1] == 0 or boostOpportunity[1] == 1:
                            getBoost = True
                    else:
                        if boostOpportunity[1] == 2 or boostOpportunity[1] == 3:
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
                # if hit.hit_type == 0:  #hit.pred_vector[2] <= agent.groundCutOff:
                #     if agentType != GroundAssault:
                #         agent.activeState = GroundAssault(agent)
                #     return
                #
                # elif hit.hit_type == 1 or hit.hit_type == 4:
                #     if agentType != HolyGrenade:
                #         agent.activeState = HolyGrenade(agent)
                #     return
                #
                # else:
                #     if agentType != ScaleTheWalls:
                #         agent.activeState = ScaleTheWalls(agent)
                #     return

                if catchViable:
                    # if agent.team == 1:
                    hit = agent.hits[1]
                    goalward = False
                    agent.goalward = False
                    agent.currentHit = hit
                    agent.ballDelay = hit.prediction_time - agent.time
                    agent.ballGrounded = False
                    if agent.activeState != Celestial_Arrest:
                        agent.activeState = Celestial_Arrest(agent)

                    print(f"catching? {agent.time}")
                    agent.log.append(f"catching? {agent.time}")
                    return

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

                else:
                    agent.log.append(f"condition leaked through! {hit.hit_type}")

        else:
            agent.activeState = PreemptiveStrike(agent)


def guidanceTesting(agent):
    # print("in guidance testing")
    if type(agent.activeState) != DivineGuidance:
        agent.activeState = DivineGuidance(agent, agent.ball.location)
    if agent.onSurface:
        if not agent.activeState.active:
            agent.activeState = DivineGuidance(agent, agent.ball.location)


# def aerialTesting(agent):
#     if agent.activeState == None or not agent.activeState.active:
#         center = Vector([0, 5200 * -sign(agent.team), 0])
#         _offset = agent.reachLength
#
#         picked = agent.ballPred.slices[agent.ballPred.num_slices-1]
#         pred = agent.ballPred.slices[0]
#         selected = False
#         for i in range(0, agent.ballPred.num_slices):
#             if i > 60 and i % 3 != 0:
#                 continue
#
#             pred = agent.ballPred.slices[i]
#             tth = pred.game_seconds - agent.gameInfo.seconds_elapsed
#
#             if tth <= 0:
#                 continue
#             pred_vec = convertStructLocationToVector(pred)
#             pred_vel = convertStructVelocityToVector(pred)
#
#             _direction = direction(
#                 pred_vec, center.flatten()
#             )
#
#             target = pred_vec + _direction.scale(agent.reachLength * 0.9)
#             req_delta_a = calculate_delta_acceleration(target-agent.me.location, agent.me.velocity,
#                                             tth, agent.gravity)
#             req_delta_v = req_delta_a.magnitude()*tth
#             if req_delta_v < agent.available_delta_v and req_delta_a.magnitude() < 1060:
#                 agent.activeState = Wings_Of_Justice(agent,pred, target, tth)
#                 selected = True
#                 break
#         if not selected:
#             agent.activeState = Wings_Of_Justice(agent, picked, convertStructLocationToVector(picked), 6)


def reset_aerial_test(agent):
    ball_state = BallState(
        physics=Physics(
            velocity=Vector3(
                z=random.randrange(500, 1000),
                x=random.randrange(-100, 100),
                y=random.randrange(-100, 100),
            ),
            location=Vector3(
                random.randrange(-100, 100),
                random.randrange(-100, 100),
                random.randrange(1200, 1750),
            ),
        )
    )
    car_state = CarState(
        physics=Physics(
            velocity=Vector3(z=1000, x=0, y=0),
            location=Vector3(
                random.randrange(-1500, 1500),
                sign(agent.team) * random.randrange(1500, 2500),
                100,
            ),
            rotation=agent.defaultRotation,
        )
    )

    game_state = GameState(ball=ball_state, cars={agent.index: car_state})
    agent.set_game_state(game_state)
    agent.activeState = None


def aerialTesting(agent):
    if agent.ball.location[2] < 110:
        reset_aerial_test(agent)

    if agent.activeState == None or not agent.activeState.active:
        center = Vector([0, 5200 * -sign(agent.team), 0])
        _offset = agent.reachLength

        picked = agent.ballPred.slices[agent.ballPred.num_slices - 1]
        pred = agent.ballPred.slices[0]
        selected = False
        for i in range(0, agent.ballPred.num_slices):
            if i > 60 and i % 3 != 0:
                continue

            pred = agent.ballPred.slices[i]
            tth = pred.game_seconds - agent.gameInfo.seconds_elapsed

            if tth <= 0:
                continue

            pred_vec = convertStructLocationToVector(pred)
            pred_vel = convertStructVelocityToVector(pred)

            if pred_vec[2] < 600:
                break

            _direction = direction(pred_vec, center.flatten())

            target = pred_vec + _direction.scale(agent.reachLength * 0.25)

            aerial_accepted = False
            if agent.onSurface:
                # if (inaccurateArrivalEstimator(agent, pred_vec, False, offset=_offset) + 1 < tth):
                delta_a = calculate_delta_acceleration(
                    target - agent.me.location,
                    agent.me.velocity + agent.up.scale(600),
                    tth,
                    agent.gravity,
                )
                if delta_a.magnitude() <= 900:
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
                        approach_direction.scale(1800) + agent.up.scale(500),
                        tth,
                        agent.gravity,
                    )
                    req_delta_v = req_delta_a.magnitude() * tth
                    if (
                        req_delta_v < agent.available_delta_v - 50
                        and req_delta_a.magnitude() < 1000
                    ):
                        aerial_accepted = True
            else:

                delta_a = calculate_delta_acceleration(
                    target - agent.me.location, agent.me.velocity, tth, agent.gravity
                )
                if delta_a.magnitude() < 950:
                    req_delta_v = delta_a.magnitude() * tth
                    if req_delta_v < agent.available_delta_v - 50:
                        aerial_accepted = True

            if aerial_accepted:
                agent.activeState = Wings_Of_Justice(agent, pred, target, tth)
                selected = True
                break

        if not selected:
            # agent.activeState = Wings_Of_Justice(agent, picked, convertStructLocationToVector(picked), 6)
            agent.activeState = DivineGrace(agent)


def dribbleTesting(agent):
    agent.activeState = AngelicEmbrace(agent)
    if agent.dribbling:
        return

    else:
        agent.resetTimer += agent.deltaTime
        if agent.resetTimer >= 5:
            agent.resetTimer = 0
            agent.log.append("setting up dribble training")
            # game_state = GameState()
            # self.set_game_state(game_state)
            ball_state = BallState(
                Physics(
                    location=Vector3(
                        agent.me.location[0],
                        agent.me.location[1],
                        agent.me.location[2] + 160,
                    ),
                    velocity=Vector3(
                        agent.me.velocity[0] * 0.95,
                        agent.me.velocity[1] * 0.95,
                        agent.me.velocity[2],
                    ),
                )
            )
            game_state = GameState(ball=ball_state)
            agent.set_game_state(game_state)
            # if agentType != AngelicEmbrace:
            #     agent.activeState = AngelicEmbrace(agent)
            return


def orientationStateManager(agent):
    if agent.ball.location < 110:
        agent.log.append("resetting orientations")
        car_state = CarState(
            physics=Physics(velocity=Vector3(z=0, x=0, y=0), location=Vector3(0, 0, 20))
        )
        game_state = GameState(cars={agent.index: car_state})
        agent.set_game_state(game_state)

    if agent.dribbling:
        if type(agent.activeState) != AngelicEmbrace:
            agent.activeState = AngelicEmbrace(agent)
        return
    else:
        agent.activeState

    # return agent.activeState


def dummyState(agent):
    if type(agent.activeState) != Player_reporter:
        agent.activeState = Player_reporter(agent)
