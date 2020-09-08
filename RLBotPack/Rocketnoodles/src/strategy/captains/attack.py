from strategy.base_ccp import BaseCaptain
from gosling.utils import *
from physics.math import Vec3
from strategy.drone import Drone
from strategy.players import *
import numpy as np


class DefenderState:
    """"
    In shadowing, the keeper goes to the goal and focuses on strategic positioning.
    Once the correct position is reached we wait for a shot at goal
    In keeping, the keeper attempts to prevent a goal
    """
    GET_BOOST = 0
    COVER = 1
    COVER_NEAR = 2
    SHOOT = 3
    INACTIVE = 4


class AttackerState:
    """
    Gets boost in the mid area, then shoots the ball if it is on the enemy side.
    If not on the enemy side -> Call prepare first to ensure positioning is correct.
    After the optional Prepare step it shoots.
    """
    PREPARE = 1
    SHOOT = 2
    COVER = 3


class Attack(BaseCaptain):
    """"
    Assign the roles (tactics) to the bots in the current team when defending.
    We have one bot who is the assigned keeper and two other bots who fetch boost.
    """
    LENGTH_MAP_ONE_SIDE = 5250
    BOOST_THRESHOLD = 30
    SHOOT_RANGE = 3000

    ATTACKER_COVER_DIST_RATIO = 0.70  # Ratio at which the attacking drones cover
    ATTACKER_CANCEL_CHECK_RANGE = 1500  # Range at which we consider to cancel our shot
    ATTACKER_PREPARE_OFFSETS = [1500, 2500]  # Prepare offest range

    DEFENDER_COVER_DIST_RATIO = 0.40  # Ratio at which the defending drone covers
    DEFENDER_COVER_PREP_RATIO = 0.75
    DEFENDER_DRONE_PREPARE_X_WINDOW = 2400  # Max distance from y-centerline to consider preparing
    DEFENDER_DRONE_SHOOT_X_WINDOW = 1400  # Max distance from y-centerline to consider shooting

    FACTOR_SCORE_HIGH_PENALTY = 1000  # The factor by which we multiply score (higher score is bad)

    def __init__(self):
        self.team = self.drones[0].team
        self.own_goal_location = Vec3(0, self.LENGTH_MAP_ONE_SIDE * side(self.team), 0)
        self.other_goal_location = Vec3(0, self.LENGTH_MAP_ONE_SIDE * side(self.team) * -1, 0)

        # Clear the stacks
        for drone in self.drones:
            drone.flush_actions()

        drone_closest_to_ball = self._get_teammate_closest_to_ball(prefer_friendly_side=True)
        self.attacker_drones = [drone_closest_to_ball]
        self.attacker_states = {drone_closest_to_ball: AttackerState.PREPARE}
        drone_closest_to_ball.assign(Prepare())

        # Select keeper from remaining drones
        remaining_drones = [drone for drone in self.drones if (drone != drone_closest_to_ball)]
        if len(remaining_drones) > 0:
            goal_dist = {(Vec3.from_other_vec(drone.car.physics.location) - self.own_goal_location).magnitude(): drone
                         for drone in remaining_drones}
            self.defender_drone = goal_dist[min(goal_dist.keys())]
            self.defender_state = DefenderState.COVER
            self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_DIST_RATIO))
        else:
            self.defender_drone = None
            self.defender_state = DefenderState.INACTIVE

        # All other drones
        remaining_drones = [drone for drone in remaining_drones if (drone != self.defender_drone)]
        for idx, drone in enumerate(remaining_drones):
            self.attacker_states[drone] = AttackerState.COVER
            self.attacker_drones.append(drone)
            drone.assign(Cover(distance_ratio=self.ATTACKER_COVER_DIST_RATIO))

        offsets = np.linspace(*self.ATTACKER_PREPARE_OFFSETS, num=len(self.attacker_drones))
        self.attacker_offsets = {drone: offset for drone, offset in zip(self.attacker_drones, offsets)}

    def step(self):
        """
        Return whether this captain is done or not
        Assigns bots, to get boost and then go to the ball or shadow.
        Assigns one bot to keeper which, intercept the ball if there is a predicted goal

        :return: Done flag, true if finished
        :rtype: bool
        """
        if self.defender_drone is not None:
            self._control_defender()
        self._control_attacker_drones()

    def _control_defender(self):
        """Sets the control for the keeper drone"""
        # Controlling the keeper
        done = self.defender_drone.step()

        centerline_dist = abs(self.world.ball.physics.location.x)

        # done and COVER -> SHOOT if opportunity else COVER
        if done and self.defender_state == DefenderState.COVER:
            self._defender_act_ball_near_center(centerline_dist)

        elif done and self.defender_state == DefenderState.COVER_NEAR:
            # print("CPT ATTACK: DEFENDER - INTERCEPT")
            self.defender_drone.assign(Intercept())
            self.defender_state = DefenderState.SHOOT

        elif self.defender_state == DefenderState.COVER_NEAR:

            if centerline_dist > self.DEFENDER_DRONE_PREPARE_X_WINDOW:
                # print("CPT ATTACK: DEFENDER - Too far from center - Back to Cover")
                self.defender_drone.flush_actions()
                self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_DIST_RATIO))
                self.defender_state = DefenderState.COVER

            elif centerline_dist < self.DEFENDER_DRONE_SHOOT_X_WINDOW:
                # print("CPT ATTACK: DEFENDER - Right in center -> Skip prepare! SHOOT!")
                self.defender_drone.flush_actions()
                self.defender_drone.assign(Intercept())
                self.defender_state = DefenderState.SHOOT

        # done and SHOOT -> COVER
        elif self.defender_state == DefenderState.SHOOT:
            if done:
                # print("CPT ATTACK: DEFENDER - SHOT DONE - Returning")
                self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_DIST_RATIO))
                self.defender_state = DefenderState.COVER
            elif centerline_dist > self.DEFENDER_DRONE_PREPARE_X_WINDOW:
                # print("CPT ATTACK: DEFENDER - Shot out of window")
                self.defender_drone.flush_actions()
                self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_DIST_RATIO))
                self.defender_state = DefenderState.COVER

    def _defender_act_ball_near_center(self, centerline_dist: float):
        """ Controls the defender drone depending on how far the ball is from the center Y-axis """
        if centerline_dist < self.DEFENDER_DRONE_SHOOT_X_WINDOW:
            # print("CPT ATTACK: DEFENDER - Right in center - COVER -> INTERCEPT")
            self.defender_drone.assign(Intercept())
            self.defender_state = DefenderState.SHOOT

        elif centerline_dist < self.DEFENDER_DRONE_PREPARE_X_WINDOW:
            # print("CPT ATTACK: DEFENDER - NEAR CENTER - START PREPARING")
            self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_PREP_RATIO))
            self.defender_state = DefenderState.COVER_NEAR
        else:
            self.defender_drone.assign(Cover(distance_ratio=self.DEFENDER_COVER_DIST_RATIO))

    def _control_attacker_drones(self):
        """Sets the controls for all other drones"""
        # All other drones get boost and try to intercept
        for drone in self.attacker_drones:
            drone_state = self.attacker_states[drone]
            done = drone.step()

            if done:
                self._select_state_attacker_drone(drone, drone_state)
            else:
                self._check_and_adjust_current_state_attacker_drone(drone, drone_state)

    def _select_state_attacker_drone(self, drone: Drone, drone_state: int):
        """Switch to different state upon completion. Assumes that the current state is done"""
        if drone_state == AttackerState.PREPARE:
            if self._allow_shoot_state():
                self.attacker_states[drone] = AttackerState.SHOOT
                drone.assign(Intercept())
            else:
                self.attacker_states[drone] = AttackerState.PREPARE
                drone.assign(Prepare(offset_in_ball_direction=self.attacker_offsets[drone]))

        elif drone_state == AttackerState.SHOOT:
            self.attacker_states[drone] = AttackerState.COVER
            drone.assign(Cover(distance_ratio=self.ATTACKER_COVER_DIST_RATIO))

        elif drone_state == AttackerState.COVER:
            self.attacker_states[drone] = AttackerState.PREPARE
            drone.assign(Prepare(offset_in_ball_direction=self.attacker_offsets[drone]))

    def _check_and_adjust_current_state_attacker_drone(self, drone: Drone, drone_state: int):
        """Switch to different state before completion of the task when particular conditions are met"""
        if drone_state == AttackerState.SHOOT:
            if self._detect_bad_shot(drone):
                self.attacker_states[drone] = AttackerState.COVER
                drone.flush_actions()
                drone.assign(Cover(distance_ratio=self.ATTACKER_COVER_DIST_RATIO))

    def _allow_shoot_state(self) -> bool:
        """"Only allows shoot state when no other drone is shooting."""
        for d, state in self.attacker_states.items():
            if AttackerState.SHOOT == state:
                return False
        return True

    def _get_teammate_closest_to_ball(self, prefer_friendly_side: bool = False) -> Drone:
        """ Select the drone closest to the ball to attack first drones on correct side have a higher preference """
        if prefer_friendly_side:
            penalty_points = {}
            for drone in self.drones:
                ball_dist = self.world.calc_dist_to_ball(drone.car)
                if drone.car.physics.location.y * side(self.team) > self.world.ball.physics.location.y * \
                        side(self.team):
                    penalty_points[ball_dist * self.FACTOR_SCORE_HIGH_PENALTY] = drone
                else:
                    penalty_points[ball_dist] = drone
            drone_closest_to_ball = penalty_points[min(penalty_points.keys())]
        else:
            ball_dist = {self.world.calc_dist_to_ball(drone.car): drone for drone in
                         self.drones}
            drone_closest_to_ball = ball_dist[min(ball_dist.keys())]
        return drone_closest_to_ball

    def _detect_bad_shot(self, drone: Drone) -> bool:
        """"Check if our shot is bad"""
        # Can only be False when we are close to the ball
        if (Vec3.from_other_vec(self.world.ball.physics.location) -
            Vec3.from_other_vec(drone.car.physics.location)).magnitude() < self.ATTACKER_CANCEL_CHECK_RANGE:

            # Cancel if we expect to fire to our own goal
            if (self.world.ball.physics.location.y - drone.car.physics.location.y) * side(self.team) > 0:
                # print(f"Bad shot detected. Ball: {self.world.ball.physics.location.y} "
                #       f"Drone: {drone.car.physics.location.y}")
                return True

        return False
