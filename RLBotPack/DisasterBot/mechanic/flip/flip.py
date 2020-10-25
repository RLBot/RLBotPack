import numpy as np

from rlbot.agents.base_agent import SimpleControllerState

from mechanic.base_mechanic import BaseMechanic
from skeleton.util.structure import Player
from util.generator_utils import initialize_generator
from util.linear_algebra import cross, dot, normalize


class Flip(BaseMechanic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flip = self.flip_generator()

    def get_controls(self, car: Player, target_dir) -> SimpleControllerState:
        return self.flip.send((car, target_dir))

    @initialize_generator
    def flip_generator(self):
        car, target_dir = yield
        car: Player

        while not car.on_ground:
            car, target_dir = yield SimpleControllerState(throttle=1)

        front = car.rotation_matrix[:, 0]
        world_left = cross(np.array([0, 0, 1]), front)
        target_dir = normalize(target_dir)
        pitch = -dot(front, target_dir)
        roll = dot(world_left, target_dir)

        for _ in range(5):
            car, target_dir = yield SimpleControllerState(jump=True, handbrake=True)
        for _ in range(1):
            car, target_dir = yield SimpleControllerState(jump=False, handbrake=True)

        car, target_dir = yield SimpleControllerState(jump=True, pitch=pitch, roll=roll, handbrake=True)

        while not car.on_ground:
            car, target_dir = yield SimpleControllerState(throttle=1, handbrake=True)

        self.finished = True

        yield SimpleControllerState()
        return
