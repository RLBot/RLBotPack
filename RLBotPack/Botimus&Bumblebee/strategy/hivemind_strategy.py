from typing import List, Optional, Dict

from maneuvers.general_defense import GeneralDefense
from maneuvers.kickoffs.drive_backwards_to_goal import DriveBackwardsToGoal
from maneuvers.kickoffs.half_flip_pickup import HalfFlipPickup
from maneuvers.recovery import Recovery
from maneuvers.pickup_boostpad import PickupBoostPad
from rlutilities.linear_algebra import norm
from rlutilities.simulation import BoostPad
from strategy import offense, defense, kickoffs
from strategy.boost_management import choose_boostpad_to_pickup
from tools.drawing import DrawingTool
from tools.drone import Drone
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import align, ground, ground_distance, distance


class HivemindStrategy:
    def __init__(self, info: GameInfo, logger):
        self.info: GameInfo = info
        self.logger = logger

        # the drone that is currently committed to hitting the ball
        self.drone_going_for_ball: Optional[Drone] = None
        self.defending_drone: Optional[Drone] = None

        self.boost_reservations: Dict[Drone, BoostPad] = dict()

    def set_kickoff_maneuvers(self, drones: List[Drone]):
        nearest_drone = min(drones, key=lambda drone: ground_distance(drone.car, self.info.ball))
        nearest_drone.maneuver = kickoffs.choose_kickoff(self.info, nearest_drone.car)
        self.drone_going_for_ball = nearest_drone

        self.boost_reservations.clear()
        corner_drones = [drone for drone in drones if abs(drone.car.position[0]) > 2000]
        if len(corner_drones) > 1:
            other_corner_drone = next(drone for drone in corner_drones if drone is not nearest_drone)
            nearest_pad = min(self.info.large_boost_pads, key=lambda pad: distance(other_corner_drone.car, pad))
            other_corner_drone.maneuver = HalfFlipPickup(other_corner_drone.car, nearest_pad)
            self.boost_reservations[other_corner_drone] = nearest_pad

        self.defending_drone = max(drones, key=lambda drone: ground_distance(drone.car, self.info.ball))
        self.defending_drone.maneuver = DriveBackwardsToGoal(self.defending_drone.car, self.info)

        for drone in drones:
            if drone not in corner_drones + [self.defending_drone] + [self.drone_going_for_ball]:
                self.send_drone_for_boost(drone)

    def send_drone_for_boost(self, drone: Drone):
        reserved_pads = set(self.boost_reservations.values())
        best_boostpad = choose_boostpad_to_pickup(self.info, drone.car, forbidden_pads=reserved_pads)
        if best_boostpad is None:
            return
        drone.maneuver = PickupBoostPad(drone.car, best_boostpad)
        self.boost_reservations[drone] = best_boostpad  # reserve chosen boost pad

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
                            and (drone.maneuver is None or drone.maneuver.interruptible())
                            and drone.car.position[2] < 300]
            if not ready_drones:
                return

            info.predict_ball()
            our_intercepts = [Intercept(drone.car, info.ball_predictions) for drone in ready_drones]
            good_intercepts = [i for i in our_intercepts if align(i.car.position, i.ball, their_goal) > 0.3 and ground_distance(i.car, i) > 2000]

            if good_intercepts:
                best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
            else:
                best_intercept = min(our_intercepts, key=lambda i: ground_distance(i.car, our_goal))

            # find out which drone does the intercept belong to
            self.drone_going_for_ball = next(drone for drone in ready_drones if drone.car == best_intercept.car)

            # if not completely out of position, go for a shot
            if (
                align(best_intercept.car.position, best_intercept.ball, their_goal) > 0
                or ground_distance(best_intercept, our_goal) > 6000
            ):
                strike = offense.any_shot(info, best_intercept.car, their_goal, best_intercept)

            else:  # otherwise try to clear
                strike = defense.any_clear(info, best_intercept.car)

            self.drone_going_for_ball.maneuver = strike

            if self.drone_going_for_ball is self.defending_drone:
                self.defending_drone = None

        # clear expired boost reservations
        for drone in drones:
            if not isinstance(drone.maneuver, PickupBoostPad) and drone in self.boost_reservations:
                del self.boost_reservations[drone]

        # drones that need boost go for boost
        for drone in drones:
            if drone.maneuver is None:
                if drone.car.boost < 30:
                    self.send_drone_for_boost(drone)

        # pick one drone that will stay far back
        unemployed_drones = [drone for drone in drones if drone.maneuver is None]
        if unemployed_drones and self.defending_drone is None:
            self.defending_drone = min(unemployed_drones, key=lambda d: ground_distance(d.car, info.my_goal.center))
            self.defending_drone.maneuver = GeneralDefense(self.defending_drone.car, info, info.ball.position, 7000)
            unemployed_drones.remove(self.defending_drone)

        for drone in unemployed_drones:
            drone.maneuver = GeneralDefense(drone.car, info, info.ball.position, 4000)

    def avoid_demos_and_team_bumps(self, drones: List[Drone]):
        collisions = self.info.detect_collisions(time_limit=0.2, dt=1 / 60)
        drones_by_index: Dict[int, Drone] = {drone.index: drone for drone in drones}

        for collision in collisions:
            index1, index2, time = collision
            self.logger.debug(f"Collision: {index1} ->*<- {index2} in {time:.2f} seconds.")

            # avoid team bumps
            if index1 in drones_by_index and index2 in drones_by_index:
                if drones_by_index[index1] is self.drone_going_for_ball:
                    drones_by_index[index2].controls.jump = drones_by_index[index2].car.on_ground
                else:
                    drones_by_index[index1].controls.jump = drones_by_index[index1].car.on_ground
                # TODO: if both drones aren't going for ball, decide which one is the better choice for jumping

            # dodge demolitions
            # TODO: Refactor so there's no duplicate code
            elif index1 in drones_by_index:
                opponent = self.info.cars[index2]
                if norm(opponent.velocity) > 2000:
                    drones_by_index[index1].controls.jump = drones_by_index[index1].car.on_ground

            elif index2 in drones_by_index:
                opponent = self.info.cars[index1]
                if norm(opponent.velocity) > 2000:
                    drones_by_index[index2].controls.jump = drones_by_index[index2].car.on_ground

    def render(self, draw: DrawingTool):
        pass
