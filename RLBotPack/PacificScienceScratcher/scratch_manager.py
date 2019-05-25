import asyncio
import json
import os
import queue
import time
from datetime import datetime, timedelta

import flatbuffers
import websockets
from rlbot.botmanager.agent_metadata import AgentMetadata
from rlbot.botmanager.bot_helper_process import BotHelperProcess
from rlbot.messages.flat import GameTickPacket, ControllerState, PlayerInput, TinyPacket, TinyPlayer, Vector3, Rotator, \
    TinyBall
from rlbot.utils.logging_utils import get_logger
from rlbot.utils.structures.game_interface import GameInterface
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

MAX_AGENT_CALL_PERIOD = timedelta(seconds=1.0)


def index_to_player_string(idx):
    return str(idx + 1)


class ScratchManager(BotHelperProcess):

    def __init__(self, agent_metadata_queue, quit_event, options):
        super().__init__(agent_metadata_queue, quit_event, options)
        self.logger = get_logger('scratch_mgr')
        self.game_interface = GameInterface(self.logger)
        self.current_sockets = set()
        self.running_indices = set()
        self.port: int = options['port']
        self.sb3_file = options['sb3-file']
        self.has_received_input = False

    async def data_exchange(self, websocket, path):
        async for message in websocket:
            controller_states = json.loads(message)

            if not self.has_received_input:
                self.has_received_input = True
                self.logger.info(f"Just got first input from Scratch {self.sb3_file} {self.port}")

            for key, scratch_state in controller_states.items():
                self.game_interface.update_player_input_flat(self.convert_to_flatbuffer(scratch_state, int(key)))

            self.current_sockets.add(websocket)

    def try_receive_agent_metadata(self):
        """
        As agents start up, they will dump their configuration into the metadata_queue.
        Read from it to learn about all the bots intending to use this scratch manager.
        """
        while True:  # will exit on queue.Empty
            try:
                single_agent_metadata: AgentMetadata = self.metadata_queue.get(timeout=0.1)
                self.running_indices.add(single_agent_metadata.index)
            except queue.Empty:
                return
            except Exception as ex:
                self.logger.error(ex)

    def start(self):
        self.logger.info("Starting scratch manager")

        self.game_interface.load_interface()

        # Wait a moment for all agents to have a chance to start up and send metadata
        time.sleep(1)
        self.try_receive_agent_metadata()

        self.logger.info(self.running_indices)

        if self.options['spawn_browser']:
            options = Options()
            options.headless = self.options['headless']

            # This prevents an error message about AudioContext when running in headless mode.
            options.add_argument("--autoplay-policy=no-user-gesture-required")

            current_folder = os.path.dirname(os.path.realpath(__file__))
            driver_path = os.path.join(current_folder, "chromedriver.exe")
            driver = webdriver.Chrome(driver_path, chrome_options=options)

            players_string = ",".join(map(index_to_player_string, self.running_indices))
            driver.get(f"http://scratch.rlbot.org?host=localhost:{str(self.port)}&players={players_string}")

            if self.sb3_file is not None:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "sb3-selenium-uploader"))
                )
                # TODO: This sleep is designed to avoid a race condition. Instead of sleeping,
                # Consider passing a url param to make scratch not load the default project.
                # Hopefully that will make the race go away.
                time.sleep(5)
                element.send_keys(self.sb3_file)

        asyncio.get_event_loop().run_until_complete(websockets.serve(self.data_exchange, port=self.port))
        asyncio.get_event_loop().run_until_complete(self.game_loop())

    async def game_loop(self):

        last_tick_game_time = None  # What the tick time of the last observed tick was
        last_call_real_time = datetime.now()  # When we last called the Agent

        # Run until main process tells to stop
        while not self.quit_event.is_set():
            before = datetime.now()

            game_tick_flat_binary = self.game_interface.get_live_data_flat_binary()
            if game_tick_flat_binary is None:
                continue

            game_tick_flat = GameTickPacket.GameTickPacket.GetRootAsGameTickPacket(game_tick_flat_binary, 0)

            # Run the Agent only if the gameInfo has updated.
            tick_game_time = self.get_game_time(game_tick_flat)
            worth_communicating = tick_game_time != last_tick_game_time or \
                                  datetime.now() - last_call_real_time >= MAX_AGENT_CALL_PERIOD

            ball = game_tick_flat.Ball()
            if ball is not None and worth_communicating:
                last_tick_game_time = tick_game_time
                last_call_real_time = datetime.now()

                tiny_player_offsets = []
                builder = flatbuffers.Builder(0)

                for i in range(game_tick_flat.PlayersLength()):
                    tiny_player_offsets.append(copy_player(game_tick_flat.Players(i), builder))

                TinyPacket.TinyPacketStartPlayersVector(builder, game_tick_flat.PlayersLength())
                for i in reversed(range(0, len(tiny_player_offsets))):
                    builder.PrependUOffsetTRelative(tiny_player_offsets[i])
                players_offset = builder.EndVector(len(tiny_player_offsets))

                ballOffset = copy_ball(ball, builder)

                TinyPacket.TinyPacketStart(builder)
                TinyPacket.TinyPacketAddPlayers(builder, players_offset)
                TinyPacket.TinyPacketAddBall(builder, ballOffset)
                packet_offset = TinyPacket.TinyPacketEnd(builder)

                builder.Finish(packet_offset)
                buffer = bytes(builder.Output())

                filtered_sockets = {s for s in self.current_sockets if s.open}
                for socket in filtered_sockets:
                    await socket.send(buffer)

                self.current_sockets = filtered_sockets

            after = datetime.now()
            duration = (after - before).total_seconds()

            sleep_secs = 1 / 60 - duration
            if sleep_secs > 0:
                await asyncio.sleep(sleep_secs)

    def get_game_time(self, game_tick_flat):
        try:
            return game_tick_flat.GameInfo().SecondsElapsed()
        except AttributeError:
            return 0.0

    def convert_to_flatbuffer(self, json_state: dict, index: int):
        builder = flatbuffers.Builder(0)

        ControllerState.ControllerStateStart(builder)
        ControllerState.ControllerStateAddSteer(builder, json_state['steer'])
        ControllerState.ControllerStateAddThrottle(builder, json_state['throttle'])
        ControllerState.ControllerStateAddPitch(builder, json_state['pitch'])
        ControllerState.ControllerStateAddYaw(builder, json_state['yaw'])
        ControllerState.ControllerStateAddRoll(builder, json_state['roll'])
        ControllerState.ControllerStateAddJump(builder, json_state['jump'])
        ControllerState.ControllerStateAddBoost(builder, json_state['boost'])
        ControllerState.ControllerStateAddHandbrake(builder, json_state['handbrake'])
        controller_state = ControllerState.ControllerStateEnd(builder)

        PlayerInput.PlayerInputStart(builder)
        PlayerInput.PlayerInputAddPlayerIndex(builder, index)
        PlayerInput.PlayerInputAddControllerState(builder, controller_state)
        player_input = PlayerInput.PlayerInputEnd(builder)

        builder.Finish(player_input)
        return builder


def copy_v3(v3, builder):
    return Vector3.CreateVector3(builder, v3.X(), v3.Y(), v3.Z())


def copy_rot(rot, builder):
    return Rotator.CreateRotator(builder, rot.Pitch(), rot.Yaw(), rot.Roll())


def copy_player(player, builder):
    TinyPlayer.TinyPlayerStart(builder)
    TinyPlayer.TinyPlayerAddLocation(builder, copy_v3(player.Physics().Location(), builder))
    TinyPlayer.TinyPlayerAddVelocity(builder, copy_v3(player.Physics().Velocity(), builder))
    TinyPlayer.TinyPlayerAddRotation(builder, copy_rot(player.Physics().Rotation(), builder))
    TinyPlayer.TinyPlayerAddTeam(builder, player.Team())
    TinyPlayer.TinyPlayerAddBoost(builder, player.Boost())
    return TinyPlayer.TinyPlayerEnd(builder)


def copy_ball(ball, builder):
    phys = ball.Physics()
    TinyBall.TinyBallStart(builder)
    TinyBall.TinyBallAddLocation(builder, copy_v3(phys.Location(), builder))
    TinyBall.TinyBallAddVelocity(builder, copy_v3(phys.Velocity(), builder))
    return TinyBall.TinyBallEnd(builder)
