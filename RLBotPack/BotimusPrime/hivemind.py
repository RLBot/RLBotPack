from typing import Dict, List

from rlbot.agents.hivemind.python_hivemind import PythonHivemind
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket

from maneuvers.kickoffs.kickoff import Kickoff
from rlutilities.linear_algebra import vec3
from strategy.hivemind_strategy import HivemindStrategy
from utils.drawing import DrawingTool
from utils.drone import Drone
from utils.game_info import GameInfo


class BotimusHivemind(PythonHivemind):
    def __init__(self, *args):
        super().__init__(*args)
        self.info: GameInfo = None
        self.team: int = None
        self.draw: DrawingTool = None
        self.drones: List[Drone] = []
        self.strategy: HivemindStrategy = None

        self.last_latest_touch_time = 0.0

    def initialize_hive(self, packet: GameTickPacket) -> None:
        index = next(iter(self.drone_indices))
        self.team = packet.game_cars[index].team

        self.info = GameInfo(self.team)
        self.info.set_mode("soccar")
        self.strategy = HivemindStrategy(self.info)
        self.draw = DrawingTool(self.renderer)
        self.drones = [Drone(self.info.cars[i], i) for i in self.drone_indices]

        self.logger.info('Botimus hivemind initialized')

    def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:
        self.info.read_packet(packet, self.get_field_info())

        # if a kickoff is happening and none of the drones have a Kickoff maneuver active, reset all drone maneuvers
        if (
            packet.game_info.is_kickoff_pause
            and self.info.ball.position[0] == 0
            and not any(isinstance(drone.maneuver, Kickoff) for drone in self.drones)
        ):
            self.strategy.set_kickoff_maneuvers(self.drones)

        # reset drone maneuvers when an opponent hits the ball
        touch = packet.game_ball.latest_touch
        if touch.time_seconds > self.last_latest_touch_time and touch.team != self.team:
            self.last_latest_touch_time = touch.time_seconds
            for drone in self.drones:
                if drone.maneuver and drone.maneuver.interruptible():  # don't reset a drone while dodging/recovering
                    drone.maneuver = None

        # reset drone maneuver when it gets demoed
        for drone in self.drones:
            if drone.maneuver and drone.car.demolished:
                drone.maneuver = None

        # if at least one drone doesn't have an active maneuver, execute strategy code
        if None in [drone.maneuver for drone in self.drones]:
            self.logger.info("Setting maneuvers")
            self.strategy.set_maneuvers(self.drones)

        for drone in self.drones:
            if drone.maneuver is None:
                continue

            # execute maneuvers
            drone.maneuver.step(self.info.time_delta)
            drone.controls = drone.maneuver.controls

            drone.maneuver.render(self.draw)

            # draw names of maneuvers above our drones
            self.draw.color(self.draw.yellow)
            self.draw.string(drone.car.position + vec3(0, 0, 50), type(drone.maneuver).__name__)

            # expire finished maneuvers
            if drone.maneuver.finished:
                drone.maneuver = None

        self.strategy.render(self.draw)
        self.draw.execute()
        return {drone.index: drone.get_player_input() for drone in self.drones}
