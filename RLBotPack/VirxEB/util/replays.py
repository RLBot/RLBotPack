from .routines import recovery


class back_right_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time == None:
            self.start_time = agent.time

        time_elapsed = round((agent.time - self.start_time) * 10000) / 10000

        if (0 <= time_elapsed and time_elapsed <= 0.2583) or (1.15 <= time_elapsed and time_elapsed <= 2.5833):
            agent.controller.throttle = 1
            agent.controller.pitch = -1

        if (0 <= time_elapsed and time_elapsed <= 0.2417) or (2.1417 <= time_elapsed and time_elapsed <= 2.3):
            agent.controller.steer = agent.controller.yaw = -1

        if (0.2417 <= time_elapsed and time_elapsed <= 0.3417) or (0.3917 <= time_elapsed and time_elapsed <= 0.6083) or (2.125 <= time_elapsed and time_elapsed <= 2.2333) or (2.2917 <= time_elapsed and time_elapsed <= 2.425):
            agent.controller.jump = True

        if (1.1 <= time_elapsed and time_elapsed <= 1.5):
            agent.controller.steer = agent.controller.yaw = 1

        if (0 <= time_elapsed and time_elapsed <= 1.1583) or (1.6083 <= time_elapsed and time_elapsed <= 2.5667):
            agent.controller.boost = True

        if (0.3333 <= time_elapsed and time_elapsed <= 0.7667):
            agent.controller.roll = 1

        if (1.8083 <= time_elapsed and time_elapsed <= 1.9417):
            agent.controller.roll = -1

        if time_elapsed > 2.5833:
            agent.pop()
            agent.push(recovery())


class back_left_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time == None:
            self.start_time = agent.time

        time_elapsed = agent.time - self.start_time

        if (0 <= time_elapsed and time_elapsed <= 0.352) or (0.9573 <= time_elapsed and time_elapsed <= 2.6127):
            agent.controller.throttle = 1
            agent.controller.pitch = -1

        if (0.002 <= time_elapsed and time_elapsed <= 0.3421) or (1.9217 <= time_elapsed and time_elapsed <= 2.0174):
            agent.controller.steer = agent.controller.yaw = 1

        if (0.3022 <= time_elapsed and time_elapsed <= 0.347) or (0.4324 <= time_elapsed and time_elapsed <= 0.5888) or (2.2474 <= time_elapsed and time_elapsed <= 2.3022) or (2.3691 <= time_elapsed and time_elapsed <= 2.5091):
            agent.controller.jump = True

        if (0.3291 <= time_elapsed and time_elapsed <= 0.7753):
            agent.controller.steer = agent.controller.roll = -1

        if (0.3151 <= time_elapsed and time_elapsed <= 0.3291) or (0.7753 <= time_elapsed and time_elapsed <= 0.7893) or (0.89 <= time_elapsed and time_elapsed <= 1.3092) or (1.5222 <= time_elapsed and time_elapsed <= 1.6424) or (2.2224 <= time_elapsed and time_elapsed <= 2.3092):
            agent.controller.steer = agent.controller.yaw = -1

        if (0.3291 <= time_elapsed and time_elapsed <= 0.7753):
            agent.controller.handbrake = True

        if (0.3291 <= time_elapsed and time_elapsed <= 0.3421):
            agent.controller.steer = agent.controller.roll = 1

        if (0 <= time_elapsed and time_elapsed <= 0.9673) or (1.588 <= time_elapsed and time_elapsed <= 2.5665):
            agent.controller.boost = True

        if time_elapsed > 2.6127:
            agent.pop()
            agent.push(recovery())


class back_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time == None:
            self.start_time = agent.time

        time_elapsed = round((agent.time - self.start_time) * 10000) / 10000

        if (0 <= time_elapsed and time_elapsed <= 0.775) or (1.7 <= time_elapsed and time_elapsed <= 2.9333):
            agent.controller.throttle = 1
            agent.controller.pitch = -1

        if (0.55 <= time_elapsed and time_elapsed <= 0.7417) or (1.7917 <= time_elapsed and time_elapsed <= 1.925) or (2.45 <= time_elapsed and time_elapsed <= 2.5333) or (2.5917 <= time_elapsed and time_elapsed <= 2.7583):
            agent.controller.jump = True

        if (0.9583 <= time_elapsed and time_elapsed <= 1.3):
            agent.controller.throttle = -1
            agent.controller.pitch = 1

        if (0 <= time_elapsed and time_elapsed <= 1.1167) or (2.025 <= time_elapsed and time_elapsed <= 2.125) or (2.1833 <= time_elapsed and time_elapsed <= 2.2917) or (2.35 <= time_elapsed and time_elapsed <= 2.4417):
            agent.controller.boost = True

        if time_elapsed > 2.9333:
            agent.pop()
            agent.push(recovery())


class left_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time == None:
            self.start_time = agent.time

        time_elapsed = agent.time - self.start_time

        if (0 <= time_elapsed and time_elapsed <= 0.0459):
            agent.controller.steer = agent.controller.yaw = -1

        if (0.011 <= time_elapsed and time_elapsed <= 0.0519) or (0.1172 <= time_elapsed and time_elapsed <= 0.3054) or (1.9766 <= time_elapsed and time_elapsed <= 2.0424) or (2.1063 <= time_elapsed and time_elapsed <= 2.3028):
            agent.controller.jump = True

        if (0 <= time_elapsed and time_elapsed <= 0.015) or (1.1298 <= time_elapsed and time_elapsed <= 1.1877) or (1.9906 <= time_elapsed and time_elapsed <= 2.4224):
            agent.controller.steer = agent.controller.yaw = 1

        if (0 <= time_elapsed and time_elapsed <= 0.0259) or (1.0978 <= time_elapsed and time_elapsed <= 2.4005):
            agent.controller.throttle = 1
            agent.controller.pitch = -1

        if (0.0459 <= time_elapsed and time_elapsed <= 0.3304):
            agent.controller.handbrake = True

        if (0.0459 <= time_elapsed and time_elapsed <= 0.3084):
            agent.controller.steer = agent.controller.roll = -1

        if (0 <= time_elapsed and time_elapsed <= 1.2515):
            agent.controller.boost = True

        if time_elapsed > 2.4224:
            agent.pop()
            agent.push(recovery())


class right_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time == None:
            self.start_time = agent.time

        time_elapsed = agent.time - self.start_time

        if (1.5287 <= time_elapsed and time_elapsed <= 2.2398):
            agent.controller.throttle = 1
            agent.controller.pitch = -1

        if (0.1751 <= time_elapsed and time_elapsed <= 0.2808):
            agent.controller.steer = agent.controller.yaw = 1

        if (0.2688 <= time_elapsed and time_elapsed <= 0.2808):
            agent.controller.steer = agent.controller.yaw = -1

        if (0.2788 <= time_elapsed and time_elapsed <= 0.3481) or (0.4429 <= time_elapsed and time_elapsed <= 0.6354) or (2.0164 <= time_elapsed and time_elapsed <= 2.0892) or (2.148 <= time_elapsed and time_elapsed <= 2.3325):
            agent.controller.jump = True

        if (0.2808 <= time_elapsed and time_elapsed <= 2.691):
            agent.controller.handbrake = True

        if (0 <= time_elapsed and time_elapsed <= 1.4095):
            agent.controller.boost = True

        if (0.2808 <= time_elapsed and time_elapsed <= 1.7671):
            agent.controller.steer = agent.controller.roll = 1

        if (0.2808 <= time_elapsed and time_elapsed <= 0.6363):
            agent.controller.steer = agent.controller.roll = -1

        if time_elapsed > 2.691:
            agent.pop()
            agent.push(recovery())
