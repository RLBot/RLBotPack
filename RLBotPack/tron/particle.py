import random
from dataclasses import dataclass
from typing import List, Tuple

from vec import Vec3


@dataclass
class Particle:
    size: int
    pos: Vec3
    vel: Vec3
    acc: Vec3
    drag: float
    color: Tuple[int, int, int]
    death_time: float

    def update(self):
        self.vel = (1 - self.drag) * self.vel + 0.008333 * self.acc
        self.pos = self.pos + 0.008333 * self.vel

    def render(self, renderer):
        color = renderer.create_color(255, self.color[0], self.color[1], self.color[2])
        renderer.draw_rect_3d(self.pos, self.size, self.size, True, color)
        if random.random() < 0.25:
            spark = self.pos + 6 * Vec3.random()
            renderer.draw_line_3d(self.pos, spark, color)
