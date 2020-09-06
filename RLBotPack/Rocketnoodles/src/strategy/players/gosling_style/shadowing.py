from gosling.routines import *
from gosling.utils import defaultPD, defaultThrottle
from rlbot.agents.base_agent import SimpleControllerState
from gosling.objects import *
from physics.math import Vec3
import math


class State:
    INITIALIZE = 0
    GOTO = 1
    CORRECT_ANGLE = 2


class GameConstants:
    MAX_SPEED_BOOST = 2300
    FIELD_LENGTH = 5150
    CAP_X_IN_GOAL_LENGTH = 750


class Shadowing:
    """ Drive back to the goalpost of your team."""

    ANGLE_CORRECTION_DRIVE_DURATION = 0.5
    ANGLE_CORRECTION_SPEED = 500
    ANGLE_CORRECTION_ALLOWED_DIFF = 15

    TARGET_RADIUS = 350
    TARGET_Y = 5115

    def __init__(self):
        self.scenario = None
        self.goto_routine = None
        self.target = None
        self.dir_to_goal = None
        self.agent: Optional[GoslingAgent] = None

        self.state = State.INITIALIZE

        # Correcting facing direction when we reached the target
        self.start_time = 0.0
        self.toggle = 1  # Switches between 1 and -1

    def run(self, agent: GoslingAgent):
        """ Updates the controls for this Player.

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        if self.state == State.INITIALIZE:
            self._initialize_shadowing()
        if self.state == State.GOTO:
            self._go_to_target()
        if self.state == State.CORRECT_ANGLE:
            self._correct_car_angle()

    def _initialize_shadowing(self):
        self.target = Vector3(0, self.TARGET_Y * side(self.agent.team), 0)
        self.dir_to_goal = Vector3(0, -side(self.agent.team), 0).normalize()
        self.state = State.GOTO

    def _go_to_target(self):
        self._drive_to_post()
        if self.agent.me.local(self.target - self.agent.me.location).magnitude() <= self.TARGET_RADIUS:
            self.state = State.CORRECT_ANGLE
            self.start_time = self.agent.time

    def _correct_car_angle(self):
        angle = self.agent.me.local(self.dir_to_goal).angle(Vector3(1, 0, 0))
        if angle < math.radians(self.ANGLE_CORRECTION_ALLOWED_DIFF):
            self.agent.pop()

        if self.agent.time - self.start_time > self.ANGLE_CORRECTION_DRIVE_DURATION:
            self.toggle *= -1
            self.start_time = self.agent.time

        defaultPD(self.agent, self.toggle * self.agent.me.local(self.dir_to_goal), self.toggle)
        defaultThrottle(self.agent, self.ANGLE_CORRECTION_SPEED, self.toggle)

    def _drive_to_post(self):
        car_to_target = self.target - self.agent.me.location
        distance_remaining = car_to_target.flatten().magnitude()

        # See commends for adjustment in jump_shot or aerial for explanation
        side_of_vector = sign(self.dir_to_goal.cross((0, 0, 1)).dot(car_to_target))
        car_to_target_perp = car_to_target.cross((0, 0, side_of_vector)).normalize()
        adjustment = car_to_target.angle(self.dir_to_goal) * distance_remaining / 3.14
        final_target = self.target + (car_to_target_perp * adjustment)

        # Some adjustment to the final target to ensure it's inside the field and we dont try to drive through
        # any goalposts to reach it
        if abs(self.agent.me.location[1]) > GameConstants.FIELD_LENGTH:
            final_target[0] = cap(final_target[0], -GameConstants.CAP_X_IN_GOAL_LENGTH,
                                  GameConstants.CAP_X_IN_GOAL_LENGTH)

        local_target = self.agent.me.local(final_target - self.agent.me.location)
        angles = defaultPD(self.agent, local_target)
        defaultThrottle(self.agent, GameConstants.MAX_SPEED_BOOST)

        self.agent.controller.boost = False
        self.agent.controller.handbrake = True if abs(angles[1]) > 2.3 else self.agent.controller.handbrake
