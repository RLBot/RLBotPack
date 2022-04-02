from typing import *

_Shape = Tuple[int, ...]
import rlutilities.linear_algebra

__all__ = [
    "Ball",
    "BoostPad",
    "BoostPadState",
    "BoostPadType",
    "Car",
    "ControlPoint",
    "Curve",
    "Field",
    "Game",
    "GameState",
    "Goal",
    "Input",
    "Navigator",
    "obb",
    "ray",
    "sphere",
    "tri",
    "intersect"
]


class Ball():
    collision_radius: float
    drag: float
    friction: float
    mass: float
    max_omega: float
    max_speed: float
    moment_of_inertia: float
    radius: float
    restitution: float

    @overload
    def __init__(self, arg0: Ball) -> None:
        pass

    @overload
    def __init__(self) -> None: ...

    def hitbox(self) -> sphere: ...

    @overload
    def step(self, dt: float, car: Car) -> None:
        pass

    @overload
    def step(self, dt: float) -> None: ...

    angular_velocity: rlutilities.linear_algebra.vec3
    position: rlutilities.linear_algebra.vec3
    time: float
    velocity: rlutilities.linear_algebra.vec3
    pass


class BoostPad():

    def __init__(self) -> None: ...

    position: rlutilities.linear_algebra.vec3
    state: BoostPadState
    timer: float
    type: BoostPadType
    pass


class BoostPadState():
    Available: rlutilities.simulation.BoostPadState
    Unavailable: rlutilities.simulation.BoostPadState
    __entries: dict
    __members__: dict

    def __eq__(self, arg0: object) -> bool: ...

    def __getstate__(self) -> int: ...

    def __hash__(self) -> int: ...

    def __init__(self, arg0: int) -> None: ...

    def __int__(self) -> int: ...

    def __ne__(self, arg0: object) -> bool: ...

    def __repr__(self) -> str: ...

    def __setstate__(self, arg0: int) -> None: ...

    name: None
    pass


class BoostPadType():
    Full: rlutilities.simulation.BoostPadType
    Partial: rlutilities.simulation.BoostPadType
    __entries: dict
    __members__: dict

    def __eq__(self, arg0: object) -> bool: ...

    def __getstate__(self) -> int: ...

    def __hash__(self) -> int: ...

    def __init__(self, arg0: int) -> None: ...

    def __int__(self) -> int: ...

    def __ne__(self, arg0: object) -> bool: ...

    def __repr__(self) -> str: ...

    def __setstate__(self, arg0: int) -> None: ...

    name: None
    pass


class Car():

    @overload
    def __init__(self) -> None:
        pass

    @overload
    def __init__(self, arg0: Car) -> None: ...

    def extrapolate(self, arg0: float) -> None: ...

    def forward(self) -> rlutilities.linear_algebra.vec3: ...

    def hitbox(self) -> obb: ...

    def left(self) -> rlutilities.linear_algebra.vec3: ...

    def step(self, controls: Input, dt: float) -> None: ...

    def up(self) -> rlutilities.linear_algebra.vec3: ...

    angular_velocity: rlutilities.linear_algebra.vec3
    boost: int
    controls: Input
    demolished: bool
    dodge_timer: float
    double_jumped: bool
    hitbox_offset: rlutilities.linear_algebra.vec3
    hitbox_widths: rlutilities.linear_algebra.vec3
    id: int
    jump_timer: float
    jumped: bool
    on_ground: bool
    orientation: rlutilities.linear_algebra.mat3
    position: rlutilities.linear_algebra.vec3
    supersonic: bool
    team: int
    time: float
    velocity: rlutilities.linear_algebra.vec3
    pass


class ControlPoint():

    @overload
    def __init__(self) -> None:
        pass

    @overload
    def __init__(self, arg0: rlutilities.linear_algebra.vec3, arg1: rlutilities.linear_algebra.vec3,
                 arg2: rlutilities.linear_algebra.vec3) -> None: ...

    n: rlutilities.linear_algebra.vec3
    p: rlutilities.linear_algebra.vec3
    t: rlutilities.linear_algebra.vec3
    pass


class Curve():

    @overload
    def __init__(self, arg0: List[rlutilities.linear_algebra.vec3]) -> None:
        pass

    @overload
    def __init__(self, arg0: List[ControlPoint]) -> None: ...

    def calculate_distances(self) -> None: ...

    def calculate_max_speeds(self, v0: float, vf: float) -> float: ...

    def calculate_tangents(self) -> None: ...

    def curvature_at(self, arg0: float) -> float: ...

    def find_nearest(self, arg0: rlutilities.linear_algebra.vec3) -> float: ...

    def max_speed_at(self, arg0: float) -> float: ...

    def point_at(self, arg0: float) -> rlutilities.linear_algebra.vec3: ...

    def pop_front(self) -> None: ...

    def tangent_at(self, arg0: float) -> rlutilities.linear_algebra.vec3: ...

    def write_to_file(self, arg0: str) -> None: ...

    length: float
    points: List[rlutilities.linear_algebra.vec3]
    pass


class Field():
    mode: str
    triangles: list

    @staticmethod
    @overload
    def collide(arg0: obb) -> ray:
        pass

    @staticmethod
    @overload
    def collide(arg0: sphere) -> ray: ...

    @staticmethod
    def raycast_any(arg0: ray) -> ray: ...

    @staticmethod
    def raycast_nearest(arg0: ray) -> ray: ...

    pass


class Game():
    gravity: rlutilities.linear_algebra.vec3
    map: str

    def __init__(self) -> None: ...

    def read_field_info(self, field_info: object) -> None: ...

    def read_packet(self, packet: object) -> None: ...

    @staticmethod
    def set_mode(mode: str) -> None: ...

    ball: Ball
    cars: List[Car]
    frame: int
    goals: List[Goal]
    pads: List[BoostPad]
    state: GameState
    time: float
    time_delta: float
    time_remaining: float
    pass


class GameState():
    Active: rlutilities.simulation.GameState
    Countdown: rlutilities.simulation.GameState
    Ended: rlutilities.simulation.GameState
    GoalScored: rlutilities.simulation.GameState
    Inactive: rlutilities.simulation.GameState
    Kickoff: rlutilities.simulation.GameState
    Paused: rlutilities.simulation.GameState
    Replay: rlutilities.simulation.GameState
    __entries: dict
    __members__: dict

    def __eq__(self, arg0: object) -> bool: ...

    def __getstate__(self) -> int: ...

    def __hash__(self) -> int: ...

    def __init__(self, arg0: int) -> None: ...

    def __int__(self) -> int: ...

    def __ne__(self, arg0: object) -> bool: ...

    def __repr__(self) -> str: ...

    def __setstate__(self, arg0: int) -> None: ...

    name: None
    pass


class Goal():

    def __init__(self) -> None: ...

    direction: rlutilities.linear_algebra.vec3
    height: float
    position: rlutilities.linear_algebra.vec3
    team: int
    width: float
    pass


class Input():

    def __init__(self) -> None: ...

    boost: bool
    handbrake: bool
    jump: bool
    pitch: float
    roll: float
    steer: float
    throttle: float
    use_item: bool
    yaw: float
    pass


class Navigator():
    nodes: list

    def __init__(self, arg0: Car) -> None: ...

    def analyze_surroundings(self, time_budget: float) -> None: ...

    def path_to(self, destination: rlutilities.linear_algebra.vec3, tangent: rlutilities.linear_algebra.vec3,
                offset: float) -> Curve: ...

    pass


class obb():

    def __init__(self) -> None: ...

    center: rlutilities.linear_algebra.vec3
    half_width: rlutilities.linear_algebra.vec3
    orientation: rlutilities.linear_algebra.mat3
    pass


class ray():

    @overload
    def __init__(self, start: rlutilities.linear_algebra.vec3, direction: rlutilities.linear_algebra.vec3) -> None:
        pass

    @overload
    def __init__(self) -> None: ...

    direction: rlutilities.linear_algebra.vec3
    start: rlutilities.linear_algebra.vec3
    pass


class sphere():

    @overload
    def __init__(self, center: rlutilities.linear_algebra.vec3, radius: float) -> None:
        pass

    @overload
    def __init__(self) -> None: ...

    center: rlutilities.linear_algebra.vec3
    radius: float
    pass


class tri():

    def __getitem__(self, arg0: int) -> rlutilities.linear_algebra.vec3: ...

    def __init__(self) -> None: ...

    def __setitem__(self, arg0: int, arg1: rlutilities.linear_algebra.vec3) -> None: ...

    pass


@overload
def intersect(arg0: sphere, arg1: obb) -> bool:
    pass


@overload
def intersect(arg0: obb, arg1: sphere) -> bool:
    pass
