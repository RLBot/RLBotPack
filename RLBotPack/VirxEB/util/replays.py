from util.routines import recovery


class back_kickoff:
    def __init__(self):
        self.start_time = None

    def run(self, agent):
        if self.start_time is None:
            self.start_time = agent.time

        time_elapsed = round(agent.time - self.start_time, 5)

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
            agent.kickoff_done = True
