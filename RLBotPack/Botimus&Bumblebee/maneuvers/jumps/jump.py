from rlutilities.simulation import Input

# Most of this class is from the old RLUtilities, made by chip


class Jump:
    def __init__(self, duration):

        self.duration = duration
        self.controls = Input()

        self.timer = 0
        self.counter = 0

        self.finished = False

    def interruptible(self) -> bool:
        return False

    def step(self, dt):

        self.controls.jump = 1 if self.timer < self.duration else 0

        if self.controls.jump == 0:
            self.counter += 1

        self.timer += dt

        if self.counter >= 2:
            self.finished = True

        return self.finished
