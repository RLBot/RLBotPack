"""
Invisibot is a rocket league bot based on RLBot framework.
It uses an internals of a different bot and adds
hiding/unhiding as appropriate.
"""

from os import path

from rlbot.utils.class_importer import import_agent

botlib = import_agent(path.abspath('../Necto/Nexto/bot.py'))
BaseBot = botlib.get_loaded_class()

from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, CarState, Physics, Vector3, Rotator

from car_simulation_by_controls import SimPhysics, CarSimmer, Vec3

DEBUG = False
PROXIMITY = 1000

# To implement list:
# - Reset between goals
# - If simulation stuck in same location for multiple ticks, unhide
# - Boost tracking

# Import appropriate bot as BaseBot
class InvisibotWrapper(BaseBot):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        # prefix with __ to avoid accidental collision
        self.__hidden = False
        self.__teleporting = 0

        self.__car_sim: CarSimmer = CarSimmer(SimPhysics.empty())

        self.__timestamp = 0
        self.__count = 0
        self.__visible_timestamp = self.__timestamp

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        Core logic. Hide/unhide bot based on distance.
        Depending on hidden state, either sim resulting controls
        or forward the bot controls
        """
        if DEBUG:
            if self.__car_sim.renderer is None:
                self.__car_sim.renderer = self.renderer
            self.__car_sim.mark_location()
    
        cur_time = packet.game_info.seconds_elapsed
        dt = cur_time - self.__timestamp
        self.__timestamp = cur_time

        self.__count += 1
        # hide/unhide at the end of the frame
        emptry_controls = SimpleControllerState()

        if not packet.game_info.is_round_active:
            self.__hidden = False
            self.__count = 0

            self.__visible_timestamp = self.__timestamp # let kickoffs be in cooldown
            return emptry_controls

        packet_car = packet.game_cars[self.index]
        # if we are in the middle of teleporting, bail
        if self.__teleporting and (self.__count - self.__teleporting) < 15:
            # wait max of 15 ticks
            cur_location = Vec3(packet_car.physics.location)
            target = self.__car_sim.physics.location
            if (cur_location - target).length() > 100:
                return emptry_controls
            else:
                self.__teleporting = 0
        else:
            self.__teleporting = 0

        pre_location: Vec3 = None
        if not self.__hidden:
            pre_location = Vec3(packet_car.physics.location)
        else:
            # manipulate the packet
            sim = self.__car_sim
            self.__load_physics(packet_car.physics)

            packet_car.boost = sim.boost
            packet_car.is_super_sonic = sim.is_supersonic()
            packet_car.has_wheel_contact = sim.is_on_ground()
            packet_car.double_jumped = sim.is_double_jumped()
            packet_car.jumped = sim.is_jumped()

            pre_location = sim.physics.location

        controls: SimpleControllerState = super().get_output(packet)

        ball = Vec3(packet.game_ball.physics.location)
        is_ball_near = (ball - pre_location).length() < PROXIMITY
        is_enemy_near = self.__min_enemy_dist(packet, pre_location) < PROXIMITY

        anything_near = is_ball_near or is_enemy_near

        if self.__hidden and anything_near:
            # we are hidden but something is near
            self.__unhide()
        elif not (self.__hidden or anything_near or self.__in_cooldown()):
            # hide if hidden and nothing close and not in cooldown
            self.__hide(packet_car)

        if self.__count % 30 == 0:
            # print(f"{is_ball_near} {is_enemy_near} {anything_near} {self.__in_cooldown()}")
            pass

        if self.__hidden:
            self.__car_sim.tick(controls, dt)
            return emptry_controls
        elif self.__teleporting:
            return emptry_controls
        else:
            return controls

    def __min_enemy_dist(self, packet: GameTickPacket, position: Vec3):
        min_enemy_distance = 1e5
        for i in range(packet.num_cars):
            car = packet.game_cars[i]
            if car.team != self.team:
                dist = (Vec3(car.physics.location) - position).length()
                min_enemy_distance = min(min_enemy_distance, dist)

        return min_enemy_distance

    def __load_vector(self, target, source):
        target.x = source.x
        target.y = source.y
        target.z = source.z
    def __load_physics(self, p: Physics):
        sim = self.__car_sim.physics
        self.__load_vector(p.location, sim.location)
        self.__load_vector(p.velocity, sim.velocity)
        self.__load_vector(p.angular_velocity, sim.angular_velocity)
        p.rotation.pitch = sim.rotation.pitch
        p.rotation.yaw = sim.rotation.yaw
        p.rotation.roll = sim.rotation.roll

    def __unhide(self):
        print("Here I am!")
        p = Physics(Vector3(), Rotator(), Vector3(), Vector3())
        self.__load_physics(p)
        sim = self.__car_sim
        state = GameState(
            cars={
                self.index: CarState(
                    physics=p,
                    boost_amount=sim.boost)
                    # jumped=sim.is_jumped(),
                    # double_jumped=sim.is_double_jumped())
            }
        )
        self.set_game_state(state)
        self.__hidden = False
        self.__teleporting = self.__count
        self.__visible_timestamp = self.__timestamp

    def __in_cooldown(self):
        # no rehiding for some amount of time since the last
        # unhiding. This is to avoid hide/unhide loops
        return (self.__timestamp - self.__visible_timestamp) <= 3

    def __hide(self, packet_car):
        print("There I go!")
        self.__car_sim.reset(SimPhysics.p(packet_car.physics))
        p = Physics(location=Vector3(3520, 5100, 0), velocity=Vector3(0, 0, 0))
        self.set_game_state(GameState(cars={self.index: CarState(physics=p)}))

        self.__hidden = True
        self.__teleporting = 0

