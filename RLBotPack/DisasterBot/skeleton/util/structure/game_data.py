import ctypes
import numpy as np
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.structures.ball_prediction_struct import BallPrediction
from rlbot.utils.structures.game_data_struct import (
    GameTickPacket,
    PlayerInfo,
    BallInfo,
    GameInfo,
    Physics,
    BoostPadState,
    FieldInfoPacket,
    BoostPad,
    GoalInfo,
    DropShotInfo,
    CollisionShape,
    MAX_BOOSTS,
    MAX_PLAYERS,
    MAX_GOALS,
    Touch,
)
from skeleton.util.structure.dtypes import (
    dtype_PlayerInfo,
    dtype_BoostPadState,
    dtype_BoostPad,
    dtype_GoalInfo,
    dtype_Slice,
    dtype_full_boost,
)
from skeleton.util.conversion import (
    vector3_to_numpy,
    rotator_to_numpy,
    rotator_to_matrix,
    box_shape_to_numpy,
    copy_controls,
)


BUF_READ = 0x100
buf_from_mem = ctypes.pythonapi.PyMemoryView_FromMemory
buf_from_mem.restype = ctypes.py_object
buf_from_mem.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)


class GameData:

    """Internal structure representing data provided by the rlbot framework."""

    def __init__(self, name: str = "skeleton", team: int = 0, index: int = 0):

        self.name = name
        self.index = index
        self.team = team

        # keeping the original packet is sometimes useful
        self.game_tick_packet = GameTickPacket()

        # cars
        self.my_car = Player()

        # other cars as structured numpy arrays
        self.opponents: np.ndarray = np.empty(())
        self.teammates: np.ndarray = np.empty(())

        # ball
        self.ball = Ball()

        # ball prediction structured numpy array
        self.ball_prediction: np.ndarray = np.empty(())

        # boost pads structured numpy array
        self.boost_pads: np.ndarray = np.empty(())

        # goals
        self.opp_goal = Goal()
        self.own_goal = Goal()

        # goals structured numpy arrays
        self.opp_goals: np.ndarray = np.empty(())
        self.own_goals: np.ndarray = np.empty(())

        # other info
        self.counter = 0
        self.time = 0.0
        self.time_remaining = 0.0
        self.overtime = False
        self.round_active = False
        self.kickoff_pause = False
        self.match_ended = False
        self.gravity = -650.0

    def read_game_tick_packet(self, game_tick_packet: GameTickPacket):
        """Reads an instance of GameTickPacket provided by the rlbot framework,
        and converts it's contents into our internal structure."""

        self.game_tick_packet = game_tick_packet
        self.read_game_cars(game_tick_packet.game_cars, game_tick_packet.num_cars)
        self.ball.read_game_ball(game_tick_packet.game_ball)
        self.read_game_boosts(game_tick_packet.game_boosts, game_tick_packet.num_boost)
        self.read_game_info(game_tick_packet.game_info)
        self.update_extra_game_data()

    def read_game_cars(self, game_cars: PlayerInfo * MAX_PLAYERS, num_cars: int):

        self.my_car.read_game_car(game_cars[self.index])

        buf = buf_from_mem(ctypes.addressof(game_cars), dtype_PlayerInfo.itemsize * num_cars, BUF_READ)
        converted_game_cars = np.frombuffer(buf, dtype_PlayerInfo).copy()

        teammates_mask = converted_game_cars["team"] == self.my_car.team
        self.opponents = converted_game_cars[~teammates_mask]
        self.teammates = converted_game_cars[teammates_mask]

    def read_game_boosts(self, game_boosts: BoostPadState * MAX_BOOSTS, num_boosts: int):
        """Reads a list of BoostPadState ctype objects from the game tick packet,
        and updates our structured numpy array based on it's contents."""

        buf = buf_from_mem(ctypes.addressof(game_boosts), dtype_BoostPadState.itemsize * num_boosts, BUF_READ)
        converted_game_boosts = np.frombuffer(buf, dtype_BoostPadState).copy()

        # this fails if we don't call initialize_agent()
        assert set(self.boost_pads.dtype.names) == set(dtype_BoostPad.names) | set(dtype_BoostPadState.names)

        self.boost_pads[list(dtype_BoostPadState.names)] = converted_game_boosts

    def read_game_info(self, game_info: GameInfo):

        self.time = game_info.seconds_elapsed
        self.time_remaining = game_info.game_time_remaining
        self.overtime = game_info.is_overtime
        self.round_active = game_info.is_round_active
        self.kickoff_pause = game_info.is_kickoff_pause
        self.match_ended = game_info.is_match_ended
        self.gravity = game_info.world_gravity_z

    def read_field_info(self, field_info: FieldInfoPacket):
        """Reads an instance of FieldInfoPacket provided by the rlbot framework,
        and converts it's contents into our internal structure."""

        self.read_boost_pads(field_info.boost_pads, field_info.num_boosts)
        self.read_goals(field_info.goals, field_info.num_goals)

    def read_boost_pads(self, boost_pads: BoostPad * MAX_BOOSTS, num_boosts: int):
        """Reads a list of BoostPad ctype objects from the field info,
        and converts it's contents into a structured numpy array.
        Also creates additional fields to be filled with the info from the game tick packet."""

        buf = buf_from_mem(ctypes.addressof(boost_pads), dtype_BoostPad.itemsize * num_boosts, BUF_READ)
        converted_boost_pads = np.frombuffer(buf, dtype_BoostPad).copy()

        self.boost_pads = np.zeros(num_boosts, dtype_full_boost)
        self.boost_pads[list(dtype_BoostPad.names)] = converted_boost_pads

    def read_goals(self, goals: GoalInfo * MAX_GOALS, num_goals: int):

        buf = buf_from_mem(ctypes.addressof(goals), dtype_GoalInfo.itemsize * num_goals, BUF_READ)
        converted_goals = np.frombuffer(buf, dtype_GoalInfo).copy()

        own_goals_mask = converted_goals["team_num"] == self.team
        self.opp_goals = converted_goals[~own_goals_mask]
        self.own_goals = converted_goals[own_goals_mask]

        if len(self.opp_goals) > 0:
            self.opp_goal = Goal(self.opp_goals[0]["location"], self.opp_goals[0]["direction"])

        if len(self.own_goals) > 0:
            self.own_goal = Goal(self.own_goals[0]["location"], self.own_goals[0]["direction"])

    def read_ball_prediction_struct(self, ball_prediction_struct: BallPrediction):
        """Reads an instance of BallPrediction provided by the rlbot framework,
        and parses it's content into a structured numpy array."""

        buf = buf_from_mem(
            ctypes.addressof(ball_prediction_struct.slices),
            dtype_Slice.itemsize * ball_prediction_struct.num_slices,
            BUF_READ,
        )
        self.ball_prediction = np.frombuffer(buf, dtype_Slice).copy()

        self.ball_prediction.flags.writeable = False

    def update_extra_game_data(self):
        """Extracts and updates extra game data."""

        self.my_car.update_extra_game_data(self.time)

    def feedback(self, controls: SimpleControllerState):
        """Called just before the end of a bot's get_output(),
        it saves some useful data to be used in the next ticks."""

        self.my_car.feedback(controls)
        self.counter += 1


class PhysicsObject:
    def __init__(self):

        self.location = np.zeros(3)
        self.rotation = np.zeros(3)
        self.velocity = np.zeros(3)
        self.angular_velocity = np.zeros(3)
        self.rotation_matrix = np.zeros((3, 3))

    def read_physics(self, physics: Physics):

        self.location = vector3_to_numpy(physics.location)
        self.rotation = rotator_to_numpy(physics.rotation)
        self.velocity = vector3_to_numpy(physics.velocity)
        self.angular_velocity = vector3_to_numpy(physics.angular_velocity)
        self.rotation_matrix = rotator_to_matrix(physics.rotation)


class Player(PhysicsObject):
    def __init__(self):

        # physics
        super(Player, self).__init__()

        # game_car info
        self.boost = 0.0
        self.jumped = False
        self.double_jumped = False
        self.on_ground = False
        self.supersonic = False
        self.team = 0
        self.spawn_id = 0

        # hitbox info
        self.hitbox_corner = np.array([59, 42, 18])
        self.hitbox_offset = np.array([13.87566, 0, 20.755])

        # extra info

        # the moment in time the action happened
        self.air_time = 0.0
        self.ground_time = 0.0
        self.jump_start_time = 0.0
        self.jump_end_time = 0.0  # when the first jump forces stop being applied.
        self.dodge_time = 0.0

        # the time between when the action happened and the present
        self.air_timer = 0.0
        self.ground_timer = 0.0
        self.jump_start_timer = 0.0
        self.jump_end_timer = 0.0
        self.dodge_timer = 0.0

        self.jump_count = 2
        self.jump_available = True
        self.first_jump_ended = False

        self.time = 0.0
        self.last_time = 0.0
        self.last_jumped = False
        self.last_on_ground = False
        self.controls_history = [SimpleControllerState(), SimpleControllerState()]

    def read_game_car(self, game_car: PlayerInfo):

        super(Player, self).read_physics(game_car.physics)

        self.boost = game_car.boost
        self.jumped = game_car.jumped
        self.double_jumped = game_car.double_jumped
        self.on_ground = game_car.has_wheel_contact
        self.supersonic = game_car.is_super_sonic
        self.team = game_car.team
        self.spawn_id = game_car.spawn_id

        self.hitbox_corner = box_shape_to_numpy(game_car.hitbox) / 2
        self.hitbox_offset = vector3_to_numpy(game_car.hitbox_offset)

    def update_extra_game_data(self, time: float):

        self.time = time

        # the moment we left the ground
        if not self.on_ground and (self.last_on_ground or self.air_time == 0.0):
            self.air_time = self.time

        # the moment we left the air
        if self.on_ground and (not self.last_on_ground or self.ground_time == 0.0):
            self.ground_time = self.time

        # the moment we start jumping
        if self.jumped and not self.last_jumped:
            self.jump_start_time = self.time
            self.jump_end_time = self.time + 0.2

        # the moment we lose first jump acceleration
        if self.time < self.jump_end_time:
            if not self.last_on_ground:
                if self.controls_history[-2].jump and not self.controls_history[-1].jump:
                    self.jump_end_time = self.last_time

        self.air_timer = self.time - self.air_time
        self.ground_timer = self.time - self.ground_time
        self.jump_start_timer = self.time - self.jump_start_time
        self.jump_end_timer = self.time - self.jump_end_time

        # reset timers
        if self.on_ground and self.last_on_ground:
            self.air_timer = 0.0

        if not self.on_ground and not self.last_on_ground:
            self.ground_timer = 0.0

        # determining how many jumps we have available
        if self.on_ground:
            self.jump_count = 2
        elif self.double_jumped or (self.jump_end_timer > 1.25 and self.jumped):
            self.jump_count = 0
        else:
            self.jump_count = 1

        self.jump_available = self.jump_count > 0
        self.first_jump_ended = self.jump_end_timer >= 0

    def feedback(self, controls: SimpleControllerState):

        self.last_time = self.time
        self.last_jumped = self.jumped
        self.last_on_ground = self.on_ground

        copy_controls(self.controls_history[-2], self.controls_history[-1])
        copy_controls(self.controls_history[-1], controls)


class Ball(PhysicsObject):
    def __init__(self):

        # physics
        super(Ball, self).__init__()

        # latest touch
        self.touch_player_name = "skeleton"
        self.touch_time = 0.0
        self.touch_location = np.zeros(3)
        self.touch_direction = np.zeros(3)

        # drop shot info
        self.absorbed_force = 0.0
        self.damage_index = 0
        self.force_accum_recent = 0.0

        # collision shape
        self.radius = 92

    def read_game_ball(self, game_ball: BallInfo):

        super(Ball, self).read_physics(game_ball.physics)
        self.read_latest_touch(game_ball.latest_touch)
        self.read_drop_shot_info(game_ball.drop_shot_info)

    def read_latest_touch(self, latest_touch: Touch):

        self.touch_player_name = latest_touch.player_name
        self.touch_time = latest_touch.time_seconds
        self.touch_location = latest_touch.hit_location
        self.touch_direction = latest_touch.hit_normal

    def read_drop_shot_info(self, drop_shot_info: DropShotInfo):

        self.absorbed_force = drop_shot_info.absorbed_force
        self.damage_index = drop_shot_info.damage_index
        self.force_accum_recent = drop_shot_info.force_accum_recent

    def read_collision_shape(self, collision_shape: CollisionShape):

        self.radius = collision_shape.sphere.diameter / 2


class Goal:
    def __init__(self, location=np.zeros(3), direction=np.zeros(3)):

        self.location = location
        self.direction = direction
