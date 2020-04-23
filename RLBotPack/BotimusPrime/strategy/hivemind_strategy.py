from typing import List, Optional, Dict

from maneuvers.air.recovery import Recovery
from maneuvers.half_flip_pickup import HalfFlipPickup
from maneuvers.refuel import Refuel
from maneuvers.shadow_defense import ShadowDefense
from maneuvers.strikes.clear_into_corner import ClearIntoCorner
from rlutilities.simulation import Pad
from strategy.kickoffs import KickoffStrategy
from strategy.offense import Offense
from utils.drawing import DrawingTool
from utils.drone import Drone
from utils.game_info import GameInfo
from utils.intercept import Intercept
from utils.vector_math import align, ground, ground_distance, distance


class HivemindStrategy:
    def __init__(self, info: GameInfo):
        self.info: GameInfo = info
        self.offense: Offense = Offense(info)

        # the drone that is currently committed to hitting the ball
        self.drone_going_for_ball: Optional[Drone] = None
        self.defending_drone: Optional[Drone] = None

        self.boost_reservations: Dict[Drone, Pad] = {}

    def set_kickoff_maneuvers(self, drones: List[Drone]):
        nearest_drone = min(drones, key=lambda drone: ground_distance(drone.car, self.info.ball))
        nearest_drone.maneuver = KickoffStrategy.choose_kickoff(self.info, nearest_drone.car)
        self.drone_going_for_ball = nearest_drone

        self.boost_reservations.clear()
        corner_drones = [drone for drone in drones if abs(drone.car.position[0]) > 2000]
        if len(corner_drones) > 1:
            other_corner_drone = next(drone for drone in corner_drones if drone is not nearest_drone)
            nearest_pad = min(self.info.large_boost_pads, key=lambda pad: distance(other_corner_drone.car, pad))
            other_corner_drone.maneuver = HalfFlipPickup(other_corner_drone.car, nearest_pad)
            self.boost_reservations[other_corner_drone] = nearest_pad

        for drone in drones:
            if drone is not nearest_drone and drone not in corner_drones:
                reserved_pads = {self.boost_reservations[d] for d in self.boost_reservations}
                drone.maneuver = Refuel(drone.car, self.info, self.info.my_goal.center, forbidden_pads=reserved_pads)
                self.boost_reservations[drone] = drone.maneuver.pad

    def set_maneuvers(self, drones: List[Drone]):
        info = self.info
        their_goal = ground(info.their_goal.center)
        our_goal = ground(info.my_goal.center)

        if self.drone_going_for_ball is not None and self.drone_going_for_ball.maneuver is None:
            self.drone_going_for_ball = None

        if self.defending_drone is not None and self.defending_drone.maneuver is None:
            self.defending_drone = None

        # recovery
        for drone in drones:
            if drone.maneuver is None and not drone.car.on_ground:
                drone.maneuver = Recovery(drone.car)

        # decide which drone is gonna commit
        if self.drone_going_for_ball is None:
            ready_drones = [drone for drone in drones if not drone.car.demolished
                            and (drone.maneuver is None or drone.maneuver.interruptible())]
            if not ready_drones:
                return

            info.predict_ball()
            our_intercepts = [Intercept(drone.car, info.ball_predictions) for drone in ready_drones]
            good_intercepts = [i for i in our_intercepts if align(i.car.position, i.ball, their_goal) > 0.0]

            if good_intercepts:
                best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
            else:
                best_intercept = min(our_intercepts, key=lambda i: ground_distance(i.car, our_goal))

            # find out which drone does the intercept belong to
            self.drone_going_for_ball = next(drone for drone in ready_drones if drone.car == best_intercept.car)

            # if not completely out of position, go for a shot
            if (
                align(best_intercept.car.position, best_intercept.ball, their_goal) > -0.3
                or ground_distance(best_intercept, our_goal) > 6000
            ):
                strike = self.offense.any_shot(best_intercept.car, their_goal, best_intercept)

            else:  # otherwise try to clear
                strike = ClearIntoCorner(best_intercept.car, info)

            self.drone_going_for_ball.maneuver = strike

        # clear expired boost reservations
        for drone in drones:
            if not isinstance(drone.maneuver, Refuel) and drone in self.boost_reservations:
                del self.boost_reservations[drone]

        # drones that need boost go for boost
        for drone in drones:
            if drone.maneuver is None:
                if drone.car.boost < 40:
                    reserved_pads = {self.boost_reservations[drone] for drone in self.boost_reservations}
                    drone.maneuver = Refuel(drone.car, info, info.ball.position, forbidden_pads=reserved_pads)
                    self.boost_reservations[drone] = drone.maneuver.pad  # reserve chosen boost pad

        # pick one drone that will stay far back
        unemployed_drones = [drone for drone in drones if drone.maneuver is None]
        if unemployed_drones:
            self.defending_drone = min(unemployed_drones, key=lambda d: ground_distance(d.car, info.my_goal.center))

        for drone in unemployed_drones:
            shadow_distance = 7000 if drone is self.defending_drone else 3000
            drone.maneuver = ShadowDefense(self.defending_drone.car, info, info.ball.position, shadow_distance)

    def render(self, draw: DrawingTool):
        pass
