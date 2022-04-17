from typing import *

_Shape = Tuple[int, ...]
import rlutilities.simulation
import rlutilities.linear_algebra

__all__ = [
    "Aerial",
    "Boostdash",
    "Dodge",
    "Drive",
    "FollowPath",
    "Jump",
    "Reorient",
    "ReorientML",
    "Wavedash"
]


class Aerial():
    boost_accel: float
    boost_per_second: float
    max_speed: float
    throttle_accel: float

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def is_viable(self) -> bool: ...

    def simulate(self) -> rlutilities.simulation.Car: ...

    def step(self, arg0: float) -> None: ...

    angle_threshold: float
    arrival_time: float
    controls: rlutilities.simulation.Input
    double_jump: bool
    finished: bool
    reorient_distance: float
    target_orientation: rlutilities.linear_algebra.mat3
    target_position: rlutilities.linear_algebra.vec3
    up: rlutilities.linear_algebra.vec3
    pass


class Boostdash():

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def step(self, arg0: float) -> None: ...

    controls: rlutilities.simulation.Input
    finished: bool
    pass


class Dodge():
    forward_torque: float
    input_threshold: float
    side_torque: float
    timeout: float
    torque_time: float
    z_damping: float
    z_damping_end: float
    z_damping_start: float

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def simulate(self) -> rlutilities.simulation.Car: ...

    def step(self, arg0: float) -> None: ...

    controls: rlutilities.simulation.Input
    delay: float
    direction: rlutilities.linear_algebra.vec2
    finished: bool
    jump_duration: float
    preorientation: rlutilities.linear_algebra.mat3
    timer: float
    pass


class Drive():
    boost_accel: float
    brake_accel: float
    coasting_accel: float
    max_speed: float
    max_throttle_speed: float

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    @staticmethod
    def max_turning_curvature(speed: float) -> float: ...

    @staticmethod
    def max_turning_speed(curvature: float) -> float: ...

    def step(self, arg0: float) -> None: ...

    @staticmethod
    def throttle_accel(speed: float) -> float: ...

    controls: rlutilities.simulation.Input
    finished: bool
    reaction_time: float
    speed: float
    target: rlutilities.linear_algebra.vec3
    pass


class FollowPath():

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def calculate_plan(self, path: rlutilities.simulation.Curve, arrival_time: float, arrival_speed: float) -> None: ...

    def step(self, arg0: float) -> None: ...

    arrival_speed: float
    arrival_time: float
    controls: rlutilities.simulation.Input
    finished: bool
    path: rlutilities.simulation.Curve
    pass


class Jump():
    acceleration: float
    max_duration: float
    min_duration: float
    speed: float

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def simulate(self) -> rlutilities.simulation.Car: ...

    def step(self, arg0: float) -> None: ...

    controls: rlutilities.simulation.Input
    duration: float
    finished: bool
    pass


class Reorient():

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def simulate(self) -> rlutilities.simulation.Car: ...

    def step(self, arg0: float) -> None: ...

    alpha: rlutilities.linear_algebra.vec3
    controls: rlutilities.simulation.Input
    eps_omega: float
    eps_phi: float
    finished: bool
    horizon_time: float
    target_orientation: rlutilities.linear_algebra.mat3
    pass


class ReorientML():

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def simulate(self) -> rlutilities.simulation.Car: ...

    def step(self, arg0: float) -> None: ...

    controls: rlutilities.simulation.Input
    eps_phi: float
    finished: bool
    target_orientation: rlutilities.linear_algebra.mat3
    pass


class Wavedash():

    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...

    def step(self, arg0: float) -> None: ...

    controls: rlutilities.simulation.Input
    direction: rlutilities.linear_algebra.vec2
    finished: bool
    pass
