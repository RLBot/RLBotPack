from typing import List, Optional

from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, dot, norm, angle_between, normalize, cross, look_at
from rlutilities.mechanics import Reorient
from rlutilities.simulation import Car, sphere, Field
from tools.drawing import DrawingTool
from tools.vector_math import forward, three_vec3_to_mat3


class Recovery(Maneuver):
    """Boost down and try to land smoothly"""

    def __init__(self, car: Car, jump_when_upside_down=True):
        super().__init__(car)

        self.jump_when_upside_down = jump_when_upside_down
        self.landing = False
        self.reorient = Reorient(self.car)

        self.trajectory: List[vec3] = []
        self.landing_pos: Optional[vec3] = None

    def interruptible(self) -> bool:
        return False

    def step(self, dt):
        self.simulate_landing()

        self.reorient.step(dt)
        self.controls = self.reorient.controls

        self.controls.boost = angle_between(self.car.forward(), vec3(0, 0, -1)) < 1.5 and not self.landing
        self.controls.throttle = 1  # in case we're turtling

        # jump if the car is upside down and has wheel contact
        if (
            self.jump_when_upside_down
            and self.car.on_ground
            and dot(self.car.up(), vec3(0, 0, 1)) < -0.95
        ):
            self.controls.jump = True
            self.landing = False
            
        else:
            self.finished = self.car.on_ground

    def simulate_landing(self):
        pos = vec3(self.car.position)
        vel = vec3(self.car.velocity)
        grav = vec3(0, 0, -650)
        self.trajectory = [vec3(pos)]
        self.landing = False
        collision_normal: Optional[vec3] = None

        dt = 1/60
        simulation_duration = 0.8
        for i in range(int(simulation_duration / dt)):
            pos += vel * dt
            vel += grav * dt
            if norm(vel) > 2300: vel = normalize(vel) * 2300
            self.trajectory.append(vec3(pos))

            collision_sphere = sphere(pos, 50)
            collision_ray = Field.collide(collision_sphere)
            collision_normal = collision_ray.direction

            if (norm(collision_normal) > 0.0 or pos[2] < 0) and i > 20:
                self.landing = True
                self.landing_pos = pos
                break

        if self.landing:
            u = collision_normal
            f = normalize(vel - dot(vel, u) * u)
            l = normalize(cross(u, f))
            self.reorient.target_orientation = three_vec3_to_mat3(f, l, u)
        else:
            target_direction = normalize(normalize(self.car.velocity) - vec3(0, 0, 3))
            self.reorient.target_orientation = look_at(target_direction, vec3(0, 0, 1))

    def render(self, draw: DrawingTool):
        if self.landing:
            draw.color(draw.cyan)
            draw.polyline(self.trajectory)

            if self.landing_pos:
                draw.crosshair(self.landing_pos)

        draw.color(draw.green)
        draw.vector(self.car.position, forward(self.reorient.target_orientation) * 200)

        draw.color(draw.red)
        draw.vector(self.car.position, self.car.forward() * 200)
