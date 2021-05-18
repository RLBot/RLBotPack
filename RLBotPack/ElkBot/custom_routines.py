from util.agent import VirxERLU
from util.routines import *
from util.utils import (Vector, almost_equals, cap, cap_in_field, defaultDrive,
                        defaultPD, dodge_impulse, lerp, math, peek_generator,
                        side, sign)

class speed_flip:
    def __init__(self):
        self.start_time = -1
        self.have_jumped = False
        self.have_flipped = False
    
    def run(self, agent: VirxERLU):
        if self.start_time == -1:
            self.start_time = agent.time
        T = agent.time - self.start_time

        agent.controller.boost = True
        agent.controller.throttle = 1
        agent.controller.roll = -1

        if T > 1.295 and not agent.me.airborne:
            agent.pop()
            return

        if T < .11:
            agent.controller.steer = 1
            agent.controller.yaw = 1

        if T >= .1 and not self.have_jumped:
            agent.controller.jump = True
            self.have_jumped = True

        if T > .175 and not self.have_flipped:
            agent.controller.jump = True
            agent.controller.pitch = -1
            self.have_flipped = True

        if .195 < T < .845:
            agent.controller.pitch = 1

        if .795 < T < 1.295:
            agent.controller.yaw = -1

class speed_flip_kickoff:
    def __init__(self):
        self.old_boost = 34
        self.stage = 0
        print("Speedflipping!")

    def run(self, agent: VirxERLU):
        print("running speedflip routine")
        if self.stage == 0:
            agent.controller.boost = True
            if agent.me.boost > self.old_boost:
                self.stage = 1
                agent.print(f"Next stage: {self.stage}")
            else:
                self.old_boost = agent.me.boost
        elif self.stage == 1:
            angles = defaultPD(agent, agent.me.local_location(Vector(110*sign(agent.me.location.x))))
            if abs(angles[1]) < 0.1:
                self.stage = 2
                agent.print(f"Next stage: {self.stage}")
        elif self.stage == 2:
            agent.push(speed_flip())
            self.stage = 3
            agent.print(f"Next stage: {self.stage}")
        elif self.stage == 3:
            # TODO do a second flip is the opponent is speedflipping as well
            if False:
                agent.push(flip(agent.me.local_location(Vector(120*sign(agent.me.location.x)))))
            self.stage = 4
            agent.print(f"Next stage: {self.stage}")
        elif self.stage == 4:
            agent.pop()
            