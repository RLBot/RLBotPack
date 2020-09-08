from strategy.base_ccp import BaseCaptain, BaseCCP
from gosling.utils import *
from physics.math import Vec3
from strategy.drone import Drone
from strategy.players import *


class InterceptorState:
    """"
    The interceptor drone drives back to collect a big boost on it's own
    side, then it drives in front of the goal and finally drives towards the 
    ball to intercept it.
    """
    COVER = 1
    INTERCEPT = 2


class KeeperState:
    """"
    In shadowing, the keeper goes to the goal and focuses on strategic positioning.
    Once the correct position is reached we wait for a shot at goal
    In keeping, the keeper attempts to prevent a goal
    """
    SHADOWING = 0
    WAIT = 1
    KEEPING = 2


class Defense(BaseCaptain):
    """"
    This class assigns the roles (tactics) to the bots in the current team when defending
    We have one bot who is the assigned keeper and two other bots who fetch boost
    """
    LENGTH_MAP_ONE_SIDE = 5250  # Length of map in Y direction
    BOOST_THRESHOLD = 10  # Minimal boost before getting boost
    START_KEEPER_CIRCLE_RANGE = 1800  # Circular area centered on goal in which the keeper starts keeping
    START_KEEPER_SIDE_RANGE = 3000  # Rectangular area in the opposite corner of the keeper in which it starts keeping
    KEEPER_SWITCH_TRESHOLD = 1000  # Minimal absolute X of the ball for the keeper to shadow in the other corner

    INTERCEPTOR_COVER_RATIO = 0.3
    INTERCEPTOR_CANCEL_CHECK_RANGE = 900

    MAX_GOAL_TIME = 3  # We call keeper if they score in less than this seconds
    MINIMUM_DIRECTION_RATIO = 0.4  # If lower than this we have a high change to have a chance to shoot backwards
    JUMP_THRESHOLD = 300  # Higher than this we can't shoot the ball as the keepre

    def __init__(self):
        # print("Captain Defense: Started")
        self.team = self.drones[0].team
        self.own_goal_location = Vec3(0, self.LENGTH_MAP_ONE_SIDE * side(self.team), 0)

        # Clear the stacks
        for drone in self.drones:
            drone.flush_actions()

        # Closest car to the goal becomes the keeper
        goal_dist = {(Vec3.from_other_vec(car.physics.location) - self.own_goal_location).magnitude(): drone
                     for car, drone in zip(self.world.teams[self.team].cars, self.drones)}
        self.keeper_drone = goal_dist[min(goal_dist.keys())]
        self.keeper_state = KeeperState.SHADOWING
        self.keeper_drone.assign(Shadowing())

        # Other drones become interceptors
        self.interceptor_drones = [drone for drone in self.drones if (drone != self.keeper_drone)]
        self.interceptor_states = {drone: InterceptorState.COVER for drone in self.interceptor_drones}
        [drone.assign(Cover(distance_ratio=self.INTERCEPTOR_COVER_RATIO)) for drone in self.interceptor_drones]

    def step(self) -> bool:
        """
        Checks for each drone if it needs to get boost or can go intercept.
        The keeper drone will go to the goal and wait.

        :return: Done flag, true if finished
        :rtype: bool
        """
        self._control_interceptors()
        self._control_keeper()
        return False

    def _control_interceptors(self):
        """Updates the controls for all other drones"""

        for drone in self.interceptor_drones:
            drone_state = self.interceptor_states[drone]
            done = drone.step()

            if done:
                self._select_state_interceptor(drone, drone_state)
            else:
                self._check_and_adjust_current_state_interceptor(drone, drone_state)

    def _select_state_interceptor(self, drone: Drone, drone_state: int):
        """Switch to different state upon completion. Assumes that the current state is done"""
        # COVER done -> INTERCEPT
        if drone_state == InterceptorState.COVER:
            if self._allow_intercept_state():
                self.interceptor_states[drone] = InterceptorState.INTERCEPT
                drone.assign(Intercept())
            else:
                self.interceptor_states[drone] = InterceptorState.COVER
                drone.assign(Cover(distance_ratio=self.INTERCEPTOR_COVER_RATIO))

        # INTERCEPT done -> COVER
        if drone_state == InterceptorState.INTERCEPT:
            self.interceptor_states[drone] = InterceptorState.COVER
            drone.assign(Cover(distance_ratio=self.INTERCEPTOR_COVER_RATIO))

    def _check_and_adjust_current_state_interceptor(self, drone: Drone, drone_state: int):
        """If the interceptor can only make a bad shot, we give the interception a new state: cover"""
        if drone_state == InterceptorState.INTERCEPT:
            if self._detect_bad_shot(drone):
                self.interceptor_states[drone] = InterceptorState.COVER
                drone.flush_actions()
                drone.assign(Cover(distance_ratio=self.INTERCEPTOR_COVER_RATIO))

    def _allow_intercept_state(self) -> bool:
        """"Only allows intercept state when no other drone is intercepting."""
        for d, state in self.interceptor_states.items():
            if InterceptorState.INTERCEPT == state:
                return False
        return True

    def _control_keeper(self):
        """Sets the keeper controls"""
        done = self.keeper_drone.step()

        # future goal predicted, ball near goal or ball in opposite corner -> go keeping
        if self._keeper_start_check() and not self.keeper_state == KeeperState.KEEPING:
            # print("Keeper state: Keeping")
            self.keeper_state = KeeperState.KEEPING
            self.keeper_drone.flush_actions()
            self.keeper_drone.assign(Keeper())

        # KEEPING done -> SHADOWING
        elif done and self.keeper_state == KeeperState.KEEPING:
            # print("Keeper state: Shadowing after keeping")
            self.keeper_state = KeeperState.SHADOWING
            self.keeper_drone.flush_actions()
            self.keeper_drone.assign(Shadowing())

        # SHADOWING done -> WAIT
        elif done and self.keeper_state == KeeperState.SHADOWING:
            # print("Keeper state: Wait after shadowing")
            self.keeper_drone.assign(Wait(face_ball=True))
            self.keeper_state = KeeperState.WAIT

        # If the ball is on the other side that where you are waiting, and it is far away enough, switch sides.
        # WAIT and ball on other side -> SHADOWING
        elif self.keeper_state == KeeperState.WAIT and self._ball_is_on_opposite_side_of_keeper():
            # print("Keeper state: Switch to other side")
            self.keeper_drone.flush_actions()
            self.keeper_drone.assign(Shadowing())

    def _ball_is_on_opposite_side_of_keeper(self) -> bool:
        """Check if the ball is on the opposite side of the keeper based on the y-centerline of the field"""
        return self.keeper_drone.car.physics.location.x * self.world.ball.physics.location.x > 0 and \
               abs(self.world.ball.physics.location.x) > self.KEEPER_SWITCH_TRESHOLD

    def _keeper_start_check(self) -> bool:
        """"Checks the conditions for the keeper to start"""
        ball_goal_dist = (Vec3.from_other_vec(self.world.ball.physics.location) - self.own_goal_location).magnitude()

        future_goal_predicted = self._future_goal_is_imminent()
        in_goal_circle = ball_goal_dist < self.START_KEEPER_CIRCLE_RANGE
        on_opposite_corner = self.keeper_drone.car.physics.location.x * self.world.ball.physics.location.x < 1 and \
                             0 < abs(self.world.ball.physics.location.x) < self.START_KEEPER_SIDE_RANGE and \
                             abs(self.own_goal_location.y - self.world.ball.physics.location.y) < \
                             self.START_KEEPER_CIRCLE_RANGE and self.world.ball.physics.location.z < self.JUMP_THRESHOLD

        return future_goal_predicted or in_goal_circle or on_opposite_corner

    def _future_goal_is_imminent(self) -> bool:
        """Returns whether a future goal is imminent"""
        return Ball.predict_future_goal() and Ball.predict_future_goal().physics.location.y * side(self.team) > 0 \
               and Ball.predict_future_goal().game_seconds - BaseCCP.world.game.seconds_elapsed < self.MAX_GOAL_TIME

    def _detect_bad_shot(self, drone: Drone) -> bool:
        """"Check if our shot is bad"""

        # Can only be False when we are close to the ball
        if self.world.calc_dist_to_ball(drone.car) < self.INTERCEPTOR_CANCEL_CHECK_RANGE:

            drone_to_ball = (Vec3.from_other_vec(self.world.ball.physics.location) -
                             Vec3.from_other_vec(drone.car.physics.location)).normalize()

            drone_to_goal = (Vec3.from_other_vec(self.own_goal_location) -
                             Vec3.from_other_vec(drone.car.physics.location)).normalize()

            # Cancel if we expect to fire to our own goal
            if drone_to_ball * drone_to_goal > self.MINIMUM_DIRECTION_RATIO:
                # print(f"Bad shot detected for drone {drone.index}")
                # print(f"Bad shot detected. Ball: {self.world.ball.physics.location.y} "
                #       f"Drone: {drone.car.physics.location.y}")
                return True

        return False
