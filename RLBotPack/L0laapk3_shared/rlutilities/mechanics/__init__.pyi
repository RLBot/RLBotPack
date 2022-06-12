import rlutilities.mechanics
import typing
import rlutilities.simulation
__all__  = [
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
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def is_viable(self) -> bool: ...
    def simulate(self) -> rlutilities.simulation.Car: ...
    def step(self, arg0: float) -> None: ...
    @property
    def angle_threshold(self) -> float:
        """
        :type: float
        """
    @angle_threshold.setter
    def angle_threshold(self, arg0: float) -> None:
        pass
    @property
    def arrival_time(self) -> float:
        """
        :type: float
        """
    @arrival_time.setter
    def arrival_time(self, arg0: float) -> None:
        pass
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @property
    def reorient_distance(self) -> float:
        """
        :type: float
        """
    @reorient_distance.setter
    def reorient_distance(self, arg0: float) -> None:
        pass
    @property
    def target_orientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @target_orientation.setter
    def target_orientation(self, arg0: mat<3,3>) -> None:
        pass
    @property
    def target_position(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @target_position.setter
    def target_position(self, arg0: vec<3>) -> None:
        pass
    @property
    def throttle_distance(self) -> float:
        """
        :type: float
        """
    @throttle_distance.setter
    def throttle_distance(self, arg0: float) -> None:
        pass
    @property
    def up(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @up.setter
    def up(self, arg0: vec<3>) -> None:
        pass
    boost_accel = 1060.0
    boost_per_second = 30.0
    max_speed = 2300.0
    throttle_accel = 66.66667175292969
    pass
class Boostdash():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def step(self, arg0: float) -> None: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    pass
class Dodge():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def simulate(self) -> rlutilities.simulation.Car: ...
    def step(self, arg0: float) -> None: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @property
    def delay(self) -> float:
        """
        :type: float
        """
    @delay.setter
    def delay(self, arg0: float) -> None:
        pass
    @property
    def direction(self) -> vec<2>:
        """
        :type: vec<2>
        """
    @direction.setter
    def direction(self, arg0: vec<2>) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @property
    def jump_duration(self) -> float:
        """
        :type: float
        """
    @jump_duration.setter
    def jump_duration(self, arg0: float) -> None:
        pass
    @property
    def preorientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @preorientation.setter
    def preorientation(self, arg0: mat<3,3>) -> None:
        pass
    @property
    def timer(self) -> float:
        """
        :type: float
        """
    forward_torque = 224.0
    input_threshold = 0.5
    side_torque = 260.0
    timeout = 1.25
    torque_time = 0.6499999761581421
    z_damping = 0.3499999940395355
    z_damping_end = 0.20999999344348907
    z_damping_start = 0.15000000596046448
    pass
class Drive():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    @staticmethod
    def max_turning_curvature(arg0: float) -> float: ...
    @staticmethod
    def max_turning_speed(arg0: float) -> float: ...
    def step(self, arg0: float) -> None: ...
    @staticmethod
    def throttle_accel(arg0: float) -> float: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @controls.setter
    def controls(self, arg0: rlutilities.simulation.Input) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @finished.setter
    def finished(self, arg0: bool) -> None:
        pass
    @property
    def reaction_time(self) -> float:
        """
        :type: float
        """
    @reaction_time.setter
    def reaction_time(self, arg0: float) -> None:
        pass
    @property
    def speed(self) -> float:
        """
        :type: float
        """
    @speed.setter
    def speed(self, arg0: float) -> None:
        pass
    @property
    def target(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @target.setter
    def target(self, arg0: vec<3>) -> None:
        pass
    boost_accel = 991.6669921875
    brake_accel = 3500.0
    coasting_accel = 525.0
    max_speed = 2300.0
    max_throttle_speed = 1410.0
    pass
class FollowPath():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def step(self, arg0: float) -> None: ...
    @property
    def arrival_speed(self) -> float:
        """
        :type: float
        """
    @arrival_speed.setter
    def arrival_speed(self, arg0: float) -> None:
        pass
    @property
    def arrival_time(self) -> float:
        """
        :type: float
        """
    @arrival_time.setter
    def arrival_time(self, arg0: float) -> None:
        pass
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @property
    def path(self) -> rlutilities.simulation.Curve:
        """
        :type: rlutilities.simulation.Curve
        """
    @path.setter
    def path(self, arg0: rlutilities.simulation.Curve) -> None:
        pass
    pass
class Jump():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def simulate(self) -> rlutilities.simulation.Car: ...
    def step(self, arg0: float) -> None: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @controls.setter
    def controls(self, arg0: rlutilities.simulation.Input) -> None:
        pass
    @property
    def duration(self) -> float:
        """
        :type: float
        """
    @duration.setter
    def duration(self, arg0: float) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @finished.setter
    def finished(self, arg0: bool) -> None:
        pass
    acceleration = 1458.333251953125
    max_duration = 0.20000000298023224
    min_duration = 0.02500000037252903
    speed = 291.6669921875
    pass
class Reorient():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def simulate(self) -> rlutilities.simulation.Car: ...
    def step(self, arg0: float) -> None: ...
    @property
    def alpha(self) -> vec<3>:
        """
        :type: vec<3>
        """
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @controls.setter
    def controls(self, arg0: rlutilities.simulation.Input) -> None:
        pass
    @property
    def eps_omega(self) -> float:
        """
        :type: float
        """
    @eps_omega.setter
    def eps_omega(self, arg0: float) -> None:
        pass
    @property
    def eps_phi(self) -> float:
        """
        :type: float
        """
    @eps_phi.setter
    def eps_phi(self, arg0: float) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @finished.setter
    def finished(self, arg0: bool) -> None:
        pass
    @property
    def horizon_time(self) -> float:
        """
        :type: float
        """
    @horizon_time.setter
    def horizon_time(self, arg0: float) -> None:
        pass
    @property
    def target_orientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @target_orientation.setter
    def target_orientation(self, arg0: mat<3,3>) -> None:
        pass
    pass
class ReorientML():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def simulate(self) -> rlutilities.simulation.Car: ...
    def step(self, arg0: float) -> None: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @controls.setter
    def controls(self, arg0: rlutilities.simulation.Input) -> None:
        pass
    @property
    def eps_phi(self) -> float:
        """
        :type: float
        """
    @eps_phi.setter
    def eps_phi(self, arg0: float) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    @finished.setter
    def finished(self, arg0: bool) -> None:
        pass
    @property
    def target_orientation(self) -> mat<3,3>:
        """
        :type: mat<3,3>
        """
    @target_orientation.setter
    def target_orientation(self, arg0: mat<3,3>) -> None:
        pass
    pass
class Wavedash():
    def __init__(self, arg0: rlutilities.simulation.Car) -> None: ...
    def step(self, arg0: float) -> None: ...
    @property
    def controls(self) -> rlutilities.simulation.Input:
        """
        :type: rlutilities.simulation.Input
        """
    @property
    def direction(self) -> vec<2>:
        """
        :type: vec<2>
        """
    @direction.setter
    def direction(self, arg0: vec<2>) -> None:
        pass
    @property
    def finished(self) -> bool:
        """
        :type: bool
        """
    pass
