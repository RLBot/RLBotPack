import rlutilities.simulation
import typing
__all__  = [
"Ball",
"Car",
"ControlPoint",
"Curve",
"Field",
"Game",
"Goal",
"Input",
"Navigator",
"Pad",
"obb",
"ray",
"sphere",
"tri",
"intersect"
]
class Ball():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: Ball) -> None: ...
    def collide(self, arg0: Car) -> bool: ...
    def getApproachDestination(self, arg0: vec<3>) -> Car: ...
    def hitbox(self) -> sphere: ...
    @typing.overload
    def step(self, arg0: float) -> bool: ...
    @typing.overload
    def step(self, arg0: float, arg1: Car) -> bool: ...
    def updateWithBallPhysics(self, arg0: object) -> None: ...
    @property
    def angular_velocity(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @angular_velocity.setter
    def angular_velocity(self, arg0: vec<3>) -> None:
        pass
    @property
    def position(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @position.setter
    def position(self, arg0: vec<3>) -> None:
        pass
    @property
    def time(self) -> float:
        """
        :type: float
        """
    @time.setter
    def time(self, arg0: float) -> None:
        pass
    @property
    def velocity(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @velocity.setter
    def velocity(self, arg0: vec<3>) -> None:
        pass
    collision_radius = 93.1500015258789
    drag = -0.030500000342726707
    friction = 2.0
    mass = 30.0
    max_omega = 6.0
    max_speed = 6000.0
    moment_of_inertia = 99918.75
    radius = 91.25
    restitution = 0.6000000238418579
    pass
class Car():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: Car) -> None: ...
    def drive_force_forward(self, arg0: Input) -> float: ...
    def drive_force_left(self, arg0: Input) -> float: ...
    def drive_torque_up(self, arg0: Input) -> float: ...
    def driving(self, arg0: Input, arg1: float) -> None: ...
    def extrapolate(self, arg0: float) -> None: ...
    def forward(self) -> vec<3>: ...
    def hitbox(self) -> obb: ...
    def left(self) -> vec<3>: ...
    def nextApproxCollision(self, arg0: vec<3>, arg1: vec<3>, arg2: vec<3>) -> float: ...
    def step(self, arg0: Input, arg1: float) -> None: ...
    def up(self) -> vec<3>: ...
    @property
    def angular_velocity(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @angular_velocity.setter
    def angular_velocity(self, arg0: vec<3>) -> None:
        pass
    @property
    def boost(self) -> int:
        """
        :type: int
        """
    @boost.setter
    def boost(self, arg0: int) -> None:
        pass
    @property
    def controls(self) -> Input:
        """
        :type: Input
        """
    @controls.setter
    def controls(self, arg0: Input) -> None:
        pass
    @property
    def dodge_timer(self) -> float:
        """
        :type: float
        """
    @dodge_timer.setter
    def dodge_timer(self, arg0: float) -> None:
        pass
    @property
    def double_jumped(self) -> bool:
        """
        :type: bool
        """
    @double_jumped.setter
    def double_jumped(self, arg0: bool) -> None:
        pass
    @property
    def id(self) -> int:
        """
        :type: int
        """
    @id.setter
    def id(self, arg0: int) -> None:
        pass
    @property
    def jump_timer(self) -> float:
        """
        :type: float
        """
    @jump_timer.setter
    def jump_timer(self, arg0: float) -> None:
        pass
    @property
    def jumped(self) -> bool:
        """
        :type: bool
        """
    @jumped.setter
    def jumped(self, arg0: bool) -> None:
        pass
    @property
    def on_ground(self) -> bool:
        """
        :type: bool
        """
    @on_ground.setter
    def on_ground(self, arg0: bool) -> None:
        pass
    @property
    def orientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @orientation.setter
    def orientation(self, arg0: mat<3,3>) -> None:
        pass
    @property
    def position(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @position.setter
    def position(self, arg0: vec<3>) -> None:
        pass
    @property
    def rest_height(self) -> float:
        """
        :type: float
        """
    @rest_height.setter
    def rest_height(self, arg0: float) -> None:
        pass
    @property
    def supersonic(self) -> bool:
        """
        :type: bool
        """
    @supersonic.setter
    def supersonic(self, arg0: bool) -> None:
        pass
    @property
    def team(self) -> int:
        """
        :type: int
        """
    @team.setter
    def team(self, arg0: int) -> None:
        pass
    @property
    def time(self) -> float:
        """
        :type: float
        """
    @time.setter
    def time(self, arg0: float) -> None:
        pass
    @property
    def velocity(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @velocity.setter
    def velocity(self, arg0: vec<3>) -> None:
        pass
    angular_velocity_max = 5.5
    mass = 180.0
    velocity_max = 2300.0
    pass
class ControlPoint():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: vec<3>, arg1: vec<3>, arg2: vec<3>) -> None: ...
    @property
    def n(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @n.setter
    def n(self, arg0: vec<3>) -> None:
        pass
    @property
    def p(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @p.setter
    def p(self, arg0: vec<3>) -> None:
        pass
    @property
    def t(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @t.setter
    def t(self, arg0: vec<3>) -> None:
        pass
    pass
class Curve():
    @typing.overload
    def __init__(self, arg0: typing.List[ControlPoint]) -> None: ...
    @typing.overload
    def __init__(self, arg0: typing.List[vec<3>]) -> None: ...
    def calculate_distances(self) -> None: ...
    def calculate_max_speeds(self, arg0: float, arg1: float) -> float: ...
    def calculate_tangents(self) -> None: ...
    def curvature_at(self, arg0: float) -> float: ...
    def find_nearest(self, arg0: vec<3>) -> float: ...
    def max_speed_at(self, arg0: float) -> float: ...
    def point_at(self, arg0: float) -> vec<3>: ...
    def pop_front(self) -> None: ...
    def tangent_at(self, arg0: float) -> vec<3>: ...
    def write_to_file(self, arg0: str) -> None: ...
    @property
    def length(self) -> float:
        """
        :type: float
        """
    @property
    def points(self) -> typing.List[vec<3>]:
        """
        :type: typing.List[vec<3>]
        """
    @points.setter
    def points(self, arg0: typing.List[vec<3>]) -> None:
        pass
    pass
class Field():
    @staticmethod
    @typing.overload
    def collide(arg0: obb) -> ray: ...
    @staticmethod
    @typing.overload
    def collide(arg0: sphere) -> ray: ...
    @staticmethod
    def raycast_any(arg0: ray) -> ray: ...
    @staticmethod
    def snap(arg0: vec<3>) -> ray: ...
    mode = 'Uninitialized'
    triangles = []
    walls = []
    pass
class Game():
    def __init__(self) -> None: ...
    def read_game_information(self, arg0: object, arg1: object) -> None: ...
    @staticmethod
    def set_mode(arg0: str) -> None: ...
    @property
    def ball(self) -> Ball:
        """
        :type: Ball
        """
    @ball.setter
    def ball(self, arg0: Ball) -> None:
        pass
    @property
    def cars(self) -> typing.List[Car[64]]:
        """
        :type: typing.List[Car[64]]
        """
    @cars.setter
    def cars(self, arg0: typing.List[Car[64]]) -> None:
        pass
    @property
    def kickoff_pause(self) -> bool:
        """
        :type: bool
        """
    @kickoff_pause.setter
    def kickoff_pause(self, arg0: bool) -> None:
        pass
    @property
    def match_ended(self) -> bool:
        """
        :type: bool
        """
    @match_ended.setter
    def match_ended(self, arg0: bool) -> None:
        pass
    @property
    def num_cars(self) -> int:
        """
        :type: int
        """
    @num_cars.setter
    def num_cars(self, arg0: int) -> None:
        pass
    @property
    def overtime(self) -> bool:
        """
        :type: bool
        """
    @overtime.setter
    def overtime(self, arg0: bool) -> None:
        pass
    @property
    def pads(self) -> typing.List[Pad]:
        """
        :type: typing.List[Pad]
        """
    @property
    def round_active(self) -> bool:
        """
        :type: bool
        """
    @round_active.setter
    def round_active(self, arg0: bool) -> None:
        pass
    @property
    def time(self) -> float:
        """
        :type: float
        """
    @time.setter
    def time(self, arg0: float) -> None:
        pass
    @property
    def time_delta(self) -> float:
        """
        :type: float
        """
    @time_delta.setter
    def time_delta(self, arg0: float) -> None:
        pass
    @property
    def time_remaining(self) -> float:
        """
        :type: float
        """
    @time_remaining.setter
    def time_remaining(self, arg0: float) -> None:
        pass
    frametime = 0.008333333767950535
    gravity = -650.0
    map = 'map_not_set'
    pass
class Goal():
    def __init__(self) -> None: ...
    @property
    def direction(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @direction.setter
    def direction(self, arg0: vec<3>) -> None:
        pass
    @property
    def location(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @location.setter
    def location(self, arg0: vec<3>) -> None:
        pass
    @property
    def team(self) -> int:
        """
        :type: int
        """
    @team.setter
    def team(self, arg0: int) -> None:
        pass
    pass
class Input():
    def __init__(self) -> None: ...
    @property
    def boost(self) -> bool:
        """
        :type: bool
        """
    @boost.setter
    def boost(self, arg0: bool) -> None:
        pass
    @property
    def handbrake(self) -> bool:
        """
        :type: bool
        """
    @handbrake.setter
    def handbrake(self, arg0: bool) -> None:
        pass
    @property
    def jump(self) -> bool:
        """
        :type: bool
        """
    @jump.setter
    def jump(self, arg0: bool) -> None:
        pass
    @property
    def pitch(self) -> float:
        """
        :type: float
        """
    @pitch.setter
    def pitch(self, arg0: float) -> None:
        pass
    @property
    def roll(self) -> float:
        """
        :type: float
        """
    @roll.setter
    def roll(self, arg0: float) -> None:
        pass
    @property
    def steer(self) -> float:
        """
        :type: float
        """
    @steer.setter
    def steer(self, arg0: float) -> None:
        pass
    @property
    def throttle(self) -> float:
        """
        :type: float
        """
    @throttle.setter
    def throttle(self, arg0: float) -> None:
        pass
    @property
    def useItem(self) -> bool:
        """
        :type: bool
        """
    @useItem.setter
    def useItem(self, arg0: bool) -> None:
        pass
    @property
    def yaw(self) -> float:
        """
        :type: float
        """
    @yaw.setter
    def yaw(self, arg0: float) -> None:
        pass
    pass
class Navigator():
    def __init__(self, arg0: Car) -> None: ...
    def analyze_surroundings(self, arg0: float) -> None: ...
    def path_to(self, arg0: vec<3>, arg1: vec<3>, arg2: float) -> Curve: ...
    nodes = []
    pass
class Pad():
    def __init__(self) -> None: ...
    @property
    def is_active(self) -> bool:
        """
        :type: bool
        """
    @is_active.setter
    def is_active(self, arg0: bool) -> None:
        pass
    @property
    def is_full_boost(self) -> bool:
        """
        :type: bool
        """
    @is_full_boost.setter
    def is_full_boost(self, arg0: bool) -> None:
        pass
    @property
    def position(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @position.setter
    def position(self, arg0: vec<3>) -> None:
        pass
    @property
    def timer(self) -> float:
        """
        :type: float
        """
    @timer.setter
    def timer(self, arg0: float) -> None:
        pass
    pass
class obb():
    def __init__(self) -> None: ...
    @property
    def center(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @center.setter
    def center(self, arg0: vec<3>) -> None:
        pass
    @property
    def half_width(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @half_width.setter
    def half_width(self, arg0: vec<3>) -> None:
        pass
    @property
    def orientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @orientation.setter
    def orientation(self, arg0: mat<3,3>) -> None:
        pass
    pass
class ray():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: vec<3>, arg1: vec<3>) -> None: ...
    @property
    def direction(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @direction.setter
    def direction(self, arg0: vec<3>) -> None:
        pass
    @property
    def start(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @start.setter
    def start(self, arg0: vec<3>) -> None:
        pass
    pass
class sphere():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: vec<3>, arg1: float) -> None: ...
    @property
    def center(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @center.setter
    def center(self, arg0: vec<3>) -> None:
        pass
    @property
    def radius(self) -> float:
        """
        :type: float
        """
    @radius.setter
    def radius(self, arg0: float) -> None:
        pass
    pass
class tri():
    def __getitem__(self, arg0: int) -> vec<3>: ...
    def __init__(self) -> None: ...
    def __setitem__(self, arg0: int, arg1: vec<3>) -> None: ...
    pass
@typing.overload
def intersect(arg0: obb, arg1: sphere) -> bool:
    pass
@typing.overload
def intersect(arg0: sphere, arg1: obb) -> bool:
    pass
