from maneuvers.driving.travel import Travel
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, norm
from rlutilities.simulation import Car, BoostPad, BoostPadState
from tools.drawing import DrawingTool
from tools.vector_math import distance


class PickupBoostPad(Maneuver):
    """Pickup a boostpad. Abort when picked up by someone else."""

    def __init__(self, car: Car, pad: BoostPad):
        super().__init__(car)
        self.pad = pad
        self.pad_was_active = self.pad.state == BoostPadState.Available

        self.travel = Travel(car, self.pad.position, waste_boost=True)

    def interruptible(self) -> bool:
        return self.travel.interruptible()

    def step(self, dt):
        # slow down when we're about to pick up the boost, so we can turn faster afterwards
        if distance(self.car, self.pad) < norm(self.car.velocity) * 0.2:
            self.travel.drive.target_speed = 1400

        self.travel.step(dt)
        self.controls = self.travel.controls

        # finish when someone picks up the pad
        if self.pad_was_active and self.pad.state == BoostPadState.Unavailable:
            self.finished = True
        self.pad_was_active = self.pad.state == BoostPadState.Available

        # finish when we picked the boost up but the previous condition somehow wasn't true
        if self.car.boost > 99 or distance(self.car, self.pad) < 100:
            self.finished = True

    def render(self, draw: DrawingTool):
        self.travel.render(draw)

        # draw timer if boost isn't available yet
        if self.pad and not self.pad.state == BoostPadState.Available:
            draw.color(draw.yellow)
            draw.string(self.pad.position + vec3(0, 0, 100), f"spawns in: {self.pad.timer:.1f}s")
