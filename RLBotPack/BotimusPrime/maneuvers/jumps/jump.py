from rlutilities.simulation import Input

class Jump:

    def __init__(self, duration):

        self.duration = duration
        self.controls = Input()

        self.timer = 0
        self.counter = 0

        self.finished = False

    def step(self, dt):

        self.controls.jump = 1 if self.timer < self.duration else 0

        if self.controls.jump == 0:
            self.counter += 1

        self.timer += dt

        if self.counter >= 2:
            self.finished = True

        return self.finished