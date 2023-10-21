from typing import Optional

from rlbot.agents.base_agent import BaseAgent, GameTickPacket, SimpleControllerState

from maneuvers.kickoffs.kickoff import Kickoff
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Input
from strategy import solo_strategy, teamplay_strategy
from tools.drawing import DrawingTool
from tools.game_info import GameInfo


class BotimusPrime(BaseAgent):
    RENDERING = True

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.info: GameInfo = None
        self.draw: DrawingTool = None

        self.tick_counter = 0
        self.last_latest_touch_time = 0

        self.maneuver: Optional[Maneuver] = None
        self.controls: SimpleControllerState = SimpleControllerState()

    def initialize_agent(self):
        self.info = GameInfo(self.team)
        self.info.set_mode("soccar")
        self.info.read_field_info(self.get_field_info())
        self.draw = DrawingTool(self.renderer, self.team)

    def is_hot_reload_enabled(self):
        return False

    def get_output(self, packet: GameTickPacket):
        # wait a few ticks after initialization, so we work correctly in rlbottraining
        if self.tick_counter < 20:
            self.tick_counter += 1
            return Input()

        self.info.read_packet(packet)

        # cancel maneuver if a kickoff is happening and current maneuver isn't a kickoff maneuver
        if packet.game_info.is_kickoff_pause and not isinstance(self.maneuver, Kickoff):
            self.maneuver = None

        # reset maneuver when another car hits the ball
        touch = packet.game_ball.latest_touch
        if (
            touch.time_seconds > self.last_latest_touch_time
            and touch.player_name != packet.game_cars[self.index].name
        ):
            self.last_latest_touch_time = touch.time_seconds

            # don't reset when we're dodging, wavedashing or recovering
            if self.maneuver and self.maneuver.interruptible():
                self.maneuver = None

        # choose maneuver
        if self.maneuver is None:

            if self.RENDERING:
                self.draw.clear()
            
            if self.info.get_teammates(self.info.cars[self.index]):
                self.maneuver = teamplay_strategy.choose_maneuver(self.info, self.info.cars[self.index])
            else:
                self.maneuver = solo_strategy.choose_maneuver(self.info, self.info.cars[self.index])
        
        # execute maneuver
        if self.maneuver is not None:
            self.maneuver.step(self.info.time_delta)
            self.controls = self.maneuver.controls

            if self.RENDERING:
                self.draw.group("maneuver")
                self.draw.color(self.draw.yellow)
                self.draw.string(self.info.cars[self.index].position + vec3(0, 0, 50), type(self.maneuver).__name__)
                self.maneuver.render(self.draw)

            # cancel maneuver when finished
            if self.maneuver.finished:
                self.maneuver = None

        if self.RENDERING:
            self.draw.execute()

        return self.controls


