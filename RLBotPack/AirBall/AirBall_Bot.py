from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from utils.LinAlg import Vector3, Matrix3
from utils.Functions import sign, side, orient_pd, throttle_p, cap, time_to_fall
from random import uniform, randint

# Absolute value of the spawn locations
DEFENDER_SPAWNS = [
    Vector3(2300, 500, 18),
    Vector3(0, 500, 18)
]

ATTACKER_SPAWNS = [
    Vector3(600, 5350, 18),
    Vector3(0, 5300, 18)
]


class BallObject:
    def __init__(self):
        self.location = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.latest_touched_time = 0
        self.latest_touched_team = 0

    def update(self, packet):
        ball = packet.game_ball
        self.location.data = [ball.physics.location.x, ball.physics.location.y, ball.physics.location.z]
        self.velocity.data = [ball.physics.velocity.x, ball.physics.velocity.y, ball.physics.velocity.z]
        self.latest_touched_time = ball.latest_touch.time_seconds
        self.latest_touched_team = ball.latest_touch.team


class CarObject:
    def __init__(self, index, packet=None):
        self.location = Vector3(0, 0, 0)
        self.velocity = Vector3(0, 0, 0)
        self.angular_velocity = Vector3(0, 0, 0)
        self.orientation = Matrix3()
        self.airborne = False
        self.supersonic = False
        self.double_jumped = False
        self.boost = 0
        self.index = index
        self.team = 0
        self.time_hit_ground = 0.0
        self.jump_ready = False
        if packet is not None:
            self.update(packet)

    def local(self, value):
        # Shorthand for self.orientation.local(value)
        return self.orientation.local(value)

    def update(self, packet):
        car = packet.game_cars[self.index]
        # We update the raw data inside the Vector3's instead of creating new Vector3's
        self.location.data = [car.physics.location.x, car.physics.location.y, car.physics.location.z]
        self.velocity.data = [car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z]
        self.orientation.convert_euler(car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll)
        temp = (car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z)
        self.angular_velocity = self.orientation.local(temp)
        self.airborne = not car.has_wheel_contact
        self.supersonic = car.is_super_sonic
        self.double_jumped = car.double_jumped
        self.boost = car.boost
        self.team = car.team
        if self.airborne:
            self.time_hit_ground = 0.0
            self.jump_ready = False
        elif self.time_hit_ground == 0.0:
            self.time_hit_ground = packet.game_info.seconds_elapsed
        else:
            self.jump_ready = packet.game_info.seconds_elapsed > self.time_hit_ground + 0.1

    @property
    def forward(self):
        # A vector pointing forwards relative to the cars orientation. Its magnitude is 1
        return self.orientation.forward

    @property
    def left(self):
        # A vector pointing left relative to the cars orientation. Its magnitude is 1
        return self.orientation.left

    @property
    def up(self):
        # A vector pointing up relative to the cars orientation. Its magnitude is 1
        return self.orientation.up


class ControlStep:
    def __init__(self, frames, **kwargs):
        assert frames > 0
        self.frames = frames
        self.state = SimpleControllerState()
        self.state.steer = kwargs.get("steer", 0)
        self.state.throttle = kwargs.get("throttle", 0)
        self.state.pitch = kwargs.get("pitch", 0)
        self.state.yaw = kwargs.get("yaw", 0)
        self.state.roll = kwargs.get("roll", 0)
        self.state.jump = kwargs.get("jump", 0)
        self.state.boost = kwargs.get("boost", 0)
        self.state.handbrake = kwargs.get("handbrake", 0)
        self.state.use_item = kwargs.get("use_item", 0)


class Cube:
    def __init__(self, location):
        self.location = Vector3(location.x, location.y, location.z)
        self.collected = False

    def reset(self):
        self.collected = False


class AirBallBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller = SimpleControllerState()
        self.ball = BallObject()
        self.car = CarObject(index)
        self.friends = []
        self.foes = []
        self.output = []
        self.cubes = []
        self.ready = False

        self.side = 0
        self.state = "grab_cubes"
        self.kickoff_offset = 0
        self.kickoff_frames = 6
        self.second_closest = 0
        self.cube_target = None

    def initialize_agent(self):
        info = self.get_field_info()

        for i in range(info.num_boosts):
            boost = info.boost_pads[i]
            on_side = abs(boost.location.y) > 100 and sign(boost.location.y) != side(self.team)
            if boost.is_full_boost and on_side:
                self.cubes.append(Cube(boost.location))

    def get_ready(self, packet: GameTickPacket):
        self.refresh_player_lists(packet)
        self.ball.update(packet)
        self.ready = True

    def refresh_player_lists(self, packet):
        self.friends = [CarObject(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team == self.team and i != self.index]
        self.foes = [CarObject(i, packet) for i in range(packet.num_cars) if packet.game_cars[i].team != self.team]

    def preprocess(self, packet):
        if packet.num_cars != len(self.friends) + len(self.foes) + 1:
            self.refresh_player_lists(packet)
        for car in self.friends + self.foes:
            car.update(packet)
        self.ball.update(packet)
        self.car.update(packet)

    def return_step(self):
        if len(self.output) > 0:
            state = self.output[0].state
            if self.output[0].frames - 1 == 0:
                self.output.pop(0)
            else:
                self.output[0].frames -= 1
            return state
        else:
            return SimpleControllerState()

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        if not self.ready:
            self.get_ready(packet)
        else:
            self.preprocess(packet)
        self.run()
        return self.return_step()

    def reset_cubes(self):
        for cube in self.cubes:
            cube.reset()

    def randomize(self):
        self.kickoff_offset = (uniform(0, 1) * 250) - 125
        self.second_closest = uniform(0, 1) > 0.75
        self.kickoff_frames = randint(4, 10)

    def run(self):
        # Determine if we are at any of the attacker spawns. We check by a distance threshold because state-setting
        # is dumb sometimes
        if any([(abs(self.car.location) - spawn).magnitude() < 1 for spawn in ATTACKER_SPAWNS]):
            # If we are at any of these spawns, we know a new play is beginning and can use this time to reset ourselves
            self.side = 0  # attacking
            self.reset_cubes()
            self.randomize()
            # Decide what to do based on whether we are at the center spawn or not
            if abs(self.car.location.x) > 1:
                self.cube_target = None
                self.state = "grab_cubes"
            else:
                self.state = "kickoff"
        # Determine if we are at any of the defender spawns.
        elif any([(abs(self.car.location) - spawn).magnitude() < 1 for spawn in DEFENDER_SPAWNS]):
            self.side = 1  # defending
            self.reset_cubes()
            self.randomize()
            self.state = "defend_cubes"

        # If we are attacking we need to keep track of which cubes have been collected
        if self.side == 0:
            for cube in self.cubes:
                for friend in self.friends + [self.car]:
                    if (friend.location - cube.location).magnitude() < 165:
                        cube.collected = True

        # State logic
        if self.state == "kickoff":
            # annoying way to handle controls, this was partially an experiment for a new [redacted]
            pitch, yaw, steer, roll = orient_pd(self, self.ball.location + Vector3(self.kickoff_offset, 0, -50))
            throttle, boost, dodge = throttle_p(self, 2300)

            # silly way of calculating when to jump. I made it in an hour don't hate
            relative = self.car.location - self.ball.location
            direction, distance = relative.flatten().normalize(True)
            relative_velocity = cap(abs((self.car.velocity - self.ball.velocity).dot(direction)), 0, 9999, False)
            time_till_intercept = distance / relative_velocity

            need_jump = abs(relative.z) > time_till_intercept * 300

            if len(self.output) == 0:
                if need_jump:
                    self.output.append(ControlStep(self.kickoff_frames, jump=True, boost=True))
                    self.output.append(ControlStep(1, jump=False, boost=True))
                else:
                    self.output.append(
                        ControlStep(1, pitch=pitch, yaw=yaw, roll=roll, steer=steer, throttle=throttle, boost=boost)
                    )
            # once we hit the ball we change states and try to keep it in the air
            if distance < 200:
                self.state = "dribble"

        elif self.state == "dribble":
            # figure out where the ball will land and then drive to that point
            target = self.ball.location + (self.ball.velocity * time_to_fall(self.ball.location.z - 30, self.ball.velocity.z))
            relative = (target - self.car.location).flatten()
            distance = relative.magnitude()
            max_speed = 2300
            if distance < 1000 and relative.dot(self.car.forward) < 0:
                distance *= -1
            elif relative.dot(self.car.forward) < 0:
                max_speed = 1000

            if not self.car.airborne:
                pitch, yaw, steer, roll = orient_pd(self, target)
            else:
                pitch, yaw, steer, roll = orient_pd(self, self.car.location + (self.car.velocity.flatten() * 100))

            throttle, boost, dodge = throttle_p(self, cap(distance * 3, -max_speed, max_speed))

            if len(self.output) == 0:
                if distance < 50 and self.ball.location.z < 200 and not self.car.airborne:
                    self.output.append(ControlStep(5, jump=True, boost=True))
                else:
                    self.output.append(
                        ControlStep(1, pitch=pitch, yaw=yaw, roll=roll, steer=steer, throttle=throttle, boost=boost)
                    )

        elif self.state == "grab_cubes":
            # drive toward cubes, do wacky stuff if about to be demo'd
            evasive = False

            # we find the closest cubes and sometimes target the second-closest to mix things up
            if self.cube_target is None:
                sorted_cubes = sorted(self.cubes, key=lambda x: (x.location - self.car.location).magnitude())
                closest = sorted_cubes[0]
                second_closest = sorted_cubes[1]
                if self.second_closest:
                    self.cube_target = second_closest
                    self.second_closest = 0
                else:
                    self.cube_target = closest
            # if our cube was collected we look for another
            if self.cube_target.collected:
                uncollected = [cube for cube in self.cubes if not cube.collected]
                if len(uncollected) > 0:
                    sorted_cubes = sorted(uncollected, key=lambda x: (x.location - self.car.location).magnitude())
                    self.cube_target = sorted_cubes[0]

            pitch, yaw, steer, roll = orient_pd(self, self.cube_target.location)

            # are we being attacked?
            for foe in self.foes:
                if (foe.location - self.car.location).magnitude() < 1000 and foe.velocity.magnitude() > 2000:
                    direction = (self.car.location - foe.location).normalize()
                    if foe.velocity.dot(direction) > 0.8:
                        evasive = True

            throttle, boost, dodge = throttle_p(self, 2300)
            if len(self.output) == 0:
                if evasive:
                    mode = randint(0, 2)
                    if mode == 0:
                        self.output.append(ControlStep(3, jump=1, boost=boost))
                    elif mode == 1:
                        self.output.append(ControlStep(3, jump=1, boost=boost))
                        self.output.append(ControlStep(3, jump=0, boost=boost, yaw=-1.0))
                        self.output.append(ControlStep(10, jump=1, boost=boost, yaw=-1.0))
                    else:
                        self.output.append(ControlStep(3, jump=1, boost=boost))
                        self.output.append(ControlStep(3, jump=0, boost=boost, yaw=1.0))
                        self.output.append(ControlStep(10, jump=1, boost=boost, yaw=1.0))
                else:
                    self.output.append(
                        ControlStep(1, pitch=pitch, yaw=yaw, roll=roll, steer=steer, throttle=throttle, boost=boost)
                    )

        elif self.state == "defend_cubes":
            # try to demo the closest opponent
            jump_ready = False
            closest = self.foes[0]
            distance = -1
            for foe in self.foes:
                temp_distance = (foe.location - self.car.location).magnitude()
                if temp_distance < distance or distance == -1:
                    closest = foe
                    distance = temp_distance

            relative = closest.location - self.car.location
            direction = relative.normalize()
            relative_velocity = -(closest.velocity - self.car.velocity).dot(direction)
            time = distance / cap(relative_velocity, 1000, 5000, False)

            # lead target by a bit
            target = closest.location + (closest.velocity * time)
            pitch, yaw, steer, roll = orient_pd(self, target)
            max_speed = 2300
            if direction.dot(self.car.forward) < 0:
                max_speed = 1000
            elif direction.flatten().dot(self.car.forward.flatten()) > 0.8:
                jump_ready = True

            need_jump = abs(relative.z) > time * 300
            throttle, boost, dodge = throttle_p(self, max_speed)

            # we will use dodges to try and stay on target
            horizontal_error = self.car.left.dot(target - self.car.location)

            if len(self.output) == 0:
                if need_jump and jump_ready:
                    self.output.append(ControlStep(4, jump=True, boost=boost))
                    self.output.append(ControlStep(1, jump=False, boost=boost))
                elif jump_ready and 0.45 > time > 0.25 and abs(horizontal_error) > 500 * time:
                    if not self.car.airborne:
                        self.output.append(ControlStep(2, jump=True, boost=boost))
                        self.output.append(ControlStep(1, jump=False, boost=boost))
                    self.output.append(ControlStep(10, jump=True, boost=boost, yaw=-sign(horizontal_error)))
                else:
                    self.output.append(
                        ControlStep(1, pitch=pitch, yaw=yaw, roll=roll, steer=steer, throttle=throttle, boost=boost)
                    )
        else:
            print("no state!")

