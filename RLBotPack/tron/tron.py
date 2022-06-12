import random

from rlbot.agents.base_script import BaseScript

from particle import Particle
from sounds import SoundPlayer
from trail import Trail
from vec import Vec3


class Tron(BaseScript):
    def __init__(self):
        super().__init__("Tron")
        self.trails = []
        self.particles = []
        self.is_kickoff = False
        self.sounds = SoundPlayer()

    def run(self):
        while True:
            packet = self.wait_game_tick_packet()
            time = packet.game_info.seconds_elapsed

            ball_pos = Vec3(packet.game_ball.physics.location)

            if ball_pos.x == 0 and ball_pos.y == 0 and packet.game_info.is_kickoff_pause:
                # Kickoff
                if not self.is_kickoff:
                    # It was not kickoff previous frame
                    for trail in self.trails:
                        trail.clear(self.game_interface.renderer)

                self.is_kickoff = True
            else:
                self.is_kickoff = False

            # Update and render trails
            for index in range(packet.num_cars):
                car = packet.game_cars[index]

                if index >= len(self.trails):
                    self.trails.append(Trail(index, car.team))

                trail = self.trails[index]
                trail.update(car, time)
                trail.do_collisions(self, packet)
                trail.render(self.game_interface.renderer)

            # Particles
            self.game_interface.renderer.begin_rendering("particles")
            for particle in self.particles:
                particle.update()
                particle.render(self.game_interface.renderer)
            self.game_interface.renderer.end_rendering()
            self.particles = [particle for particle in self.particles if time < particle.death_time]

    def particle_burst(self, time: float, pos: Vec3, normal: Vec3, count: int, team: int):
        color = (50, 180, 255) if team == 0 else (255, 168, 50)
        self.particles.extend([Particle(
            int(4 + 4 * random.random()),
            pos,
            600 * (normal + 0.7 * Vec3.random()),
            Vec3(z=-500),
            0.02,
            color if random.random() < 0.55 else (255, 255, 255),  # Some chance for white instead
            time + 0.3 + 0.8 * random.random()
        ) for _ in range(count)])


if __name__ == "__main__":
    script = Tron()
    script.run()
