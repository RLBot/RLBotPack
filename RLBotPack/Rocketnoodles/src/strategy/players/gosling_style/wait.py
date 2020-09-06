from typing import Optional
from gosling.objects import *
from gosling.utils import defaultPD, defaultThrottle


class State:
    INITIALIZE = 0
    WAIT = 1


class Wait:
    """ A wait function to make a drone stay at its current position.

    :param seconds: How long to wait. If it is None waits forever
    :type seconds: float
    :param face_ball: Whether to keeper correcting the angle to face the ball while waiting.
    :type face_ball: bool
    """

    ANGLE_CORRECTION_DRIVE_DURATION = 0.5
    ANGLE_CORRECTION_SPEED = 250
    ANGLE_CORRECTION_ALLOWED_DIFF = 15

    def __init__(self, seconds: float = None, face_ball: bool = False):
        # Starting state
        self.state = State.INITIALIZE

        # Settings for this instance
        self.seconds: float = seconds
        self.finish_timer: Optional[float] = None
        self.agent: Optional[GoslingAgent] = None
        self.face_ball = face_ball

        # Correcting facing direction if enabled
        self.start_time = 0.0
        self.toggle = 1  # Switches between 1 and -1

    def run(self, agent: GoslingAgent):
        """Wait forever

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        if self.state == State.INITIALIZE:
            self._initialize_wait()
        if self._waiting_done():
            agent.pop()

        defaultThrottle(agent, 0)
        if self.face_ball:
            self._face_ball()

    def _waiting_done(self) -> bool:
        return self.finish_timer is not None and self.agent.time > self.finish_timer

    def _initialize_wait(self):
        if self.seconds is not None:
            self.finish_timer = self.agent.time + self.seconds
        self.state = State.WAIT

    def _face_ball(self):
        vec_to_ball = self.agent.ball.location - self.agent.me.location
        angle = self.agent.me.local(vec_to_ball).angle(Vector3(1, 0, 0))
        if angle > math.radians(self.ANGLE_CORRECTION_ALLOWED_DIFF):
            if self.agent.time - self.start_time > self.ANGLE_CORRECTION_DRIVE_DURATION:
                self.toggle *= -1
                self.start_time = self.agent.time
            defaultPD(self.agent, self.toggle * self.agent.me.local(vec_to_ball), self.toggle)
            defaultThrottle(self.agent, self.ANGLE_CORRECTION_SPEED, self.toggle)
