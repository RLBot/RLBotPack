import itertools
from math import pi, sqrt
import threading
import time
from typing import Optional
import keyboard

from rlbot.messages.flat.ControllerState import ControllerState
from rlbot.messages.flat.PlayerInputChange import PlayerInputChange
from rlbot.socket.socket_manager import SocketRelay
from rlbot.utils.game_state_util import BallState, CarState, GameState, Physics, Vector3, Rotator, GameInfoState
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket, PlayerInfo
from rlbot.utils.structures.game_interface import GameInterface


def cstate_to_pinput(controls: ControllerState) -> PlayerInput:
    return PlayerInput(
        throttle=controls.Throttle(),
        steer=controls.Steer(),
        pitch=controls.Pitch(),
        yaw=controls.Yaw(),
        roll=controls.Roll(),
        jump=controls.Jump(),
        boost=controls.Boost(),
        handbrake=controls.Handbrake(),
        use_item=controls.UseItem(),
    )


def distance(a, b):
    return sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

class ControlsTracker:
    def __init__(self, target_index) -> None:
        self.target_controls = PlayerInput(0, 0, 0, 0, 0, False, False, False, False)
        self.target_index = target_index
        self.socket_man = SocketRelay()
        self.socket_man.player_input_change_handlers.append(self.track_human_inputs)
        self.socket_thread = threading.Thread(target=self.run_socket_relay)
        self.socket_thread.start()

    def track_human_inputs(self, change: PlayerInputChange, seconds: float, frame_num: int):
        if change.PlayerIndex() == self.target_index:
            self.target_controls = cstate_to_pinput(change.ControllerState())

    def run_socket_relay(self):
        self.socket_man.connect_and_run(wants_quick_chat=False, wants_game_messages=True, wants_ball_predictions=False)
        

class Replay:
    def __init__(self) -> None:
        self.snapshots = []
        self.current_index = 0
        self.finished = False

    def add_snapshot(self, t, snapshot):
        self.snapshots.append((t, snapshot))

    def playback(self, t: float) -> Optional[CarState]:
        try:
            index, snapshot = next(snapshot for snapshot in self.snapshots if snapshot[0] >= t)
        except StopIteration:
            self.finished = True
            return None
        
        if index > self.current_index:
            self.current_index = index
            return snapshot
        
        return None
    
    def reset(self):
        self.current_index = 0
        self.finished = False


class QuantumLeague:

    def __init__(self, interface: GameInterface, packet: GameTickPacket):
        self.interface = interface
        self.renderer = interface.renderer

        indices_cars = list(enumerate(packet.game_cars[:packet.num_cars]))
        self.human_index = next(index for index, car in indices_cars if not car.is_bot)
        self.blue_bots_indices = [index for index, car in indices_cars if car.is_bot and car.team == 0]
        self.orange_bots_indices = [index for index, car in indices_cars if car.is_bot and car.team == 1]

        self.controls_tracker = ControlsTracker(self.human_index)

        self.practice_mode = False

        self.restart_completely()
        self.start_stage(packet)

    def restart_completely(self):
        self.attack_replays = []
        self.defend_replays = []
        self.old_ball_replay = Replay()
        self.new_ball_replay = Replay()

        self.state = "attack"
        self.initial_delay = 2.0
        self.time_limit = 10.0
        self.attack_time_shift = 0.5
        self.defend_time_shift = 0.5

    def start_stage(self, packet):
        self.last_reset_time = None
        self.replaying_ball = True

        self.new_ball_replay = Replay()
        self.current_replay = Replay()
        
        self.old_ball_replay.reset()
        for replay in self.attack_replays + self.defend_replays:
            replay.reset()

        # initial game state
        self.interface.set_game_state(GameState(
            ball=BallState(Physics(
                location=Vector3(-1000, -3000, 93),
                rotation=Rotator(0, 0, 0),
                velocity=Vector3(0, 0, 0),
                angular_velocity=Vector3(0, 0, 0),
            ))
        ))
        time.sleep(0.1)

    def show_text(self, text, color):
        self.renderer.begin_rendering()
        scale = 5
        for dx in [-3, 0, 3]:
            for dy in [-3, 0, 3]:
                self.renderer.draw_string_2d(100+dx, 100+dy, scale, scale, text, self.renderer.black())
        for _ in range(3):
            self.renderer.draw_string_2d(100, 100, scale, scale, text, color)
        self.renderer.end_rendering()
    
    def fail(self, timeout=4.0):
        score = len(self.attack_replays) + len(self.defend_replays)
        if self.practice_mode:
            self.show_text(f"Score: {score}", self.renderer.lime())
        else:
            self.show_text(f"Game over. Score: {score}", self.renderer.red())
        self.interface.set_game_state(GameState(game_info=GameInfoState(game_speed=0.1)))
        time.sleep(timeout)
        self.interface.set_game_state(GameState(game_info=GameInfoState(game_speed=1.0)))
        if not self.practice_mode:
            self.restart_completely()

    def step(self, packet: GameTickPacket):
        if self.last_reset_time is None:
            self.last_reset_time = packet.game_info.seconds_elapsed
            self.prev_blue_score = packet.teams[0].score
            self.prev_orange_score = packet.teams[1].score

        t = packet.game_info.seconds_elapsed - self.last_reset_time

        max_t = self.time_limit + self.initial_delay

        if t < self.initial_delay:
            self.show_text("Get ready!", self.renderer.yellow())
        else:
            self.show_text(f"{max_t - t:.1f}", self.renderer.white())

        # next timeline
        if packet.teams[0].score > self.prev_blue_score:
            if self.state == "attack":
                self.prepare_next_stage()
            else:
                self.fail()
            return self.start_stage(packet)

        if packet.teams[1].score > self.prev_orange_score:
            if self.state == "defend":
                self.prepare_next_stage()
            else:
                self.fail()
            return self.start_stage(packet)

        if t > max_t:
            self.fail()
            return self.start_stage(packet)

        # reset button
        if t > self.initial_delay and keyboard.is_pressed("backspace"):
            self.fail(timeout=0.5)
            return self.start_stage(packet)
        
        # turn on practice mode
        if keyboard.is_pressed("f1"):
            self.practice_mode = True
            self.show_text("Restarting in practice mode", self.renderer.lime())
            self.interface.set_game_state(GameState(game_info=GameInfoState(game_speed=0.1)))
            time.sleep(3.0)
            self.interface.set_game_state(GameState(game_info=GameInfoState(game_speed=1.0)))
            self.restart_completely()
            return self.start_stage(packet)


        target_game_state = GameState(cars={})

        # car drop
        if t < self.initial_delay:
            time_to_spawn = self.initial_delay - t
            side_multiplier = 1 if self.state == "defend" else -1
            speed = 1000 if time_to_spawn < 0.1 else 0
            height_offset = time_to_spawn * 70 / max(self.attack_time_shift, self.defend_time_shift)

            target_game_state.cars[self.human_index] = CarState(
                physics=Physics(
                    location=Vector3(0, 4608 * side_multiplier, 18 + height_offset),
                    rotation=Rotator(0, -0.5 * pi * side_multiplier, 0),
                    velocity=Vector3(0, speed * -side_multiplier, 0),
                    angular_velocity=Vector3(0, 0, 0),
                ),
                boost_amount=100,
            )

        # record
        snapshot = GameState.create_from_gametickpacket(packet)
        self.current_replay.add_snapshot(t, (snapshot.cars[self.human_index], self.controls_tracker.target_controls))
        self.new_ball_replay.add_snapshot(t, snapshot.ball)

        # hide unused bots
        for index in self.blue_bots_indices + self.orange_bots_indices:
            target_game_state.cars[index] = CarState(Physics(Vector3(100_000 - (index // 5) * 150, 100_000 + (index % 5) * 150, 5_000)))

        # playback cars
        for index, replay in itertools.chain(
            zip(self.blue_bots_indices, reversed(self.attack_replays)),
            zip(self.orange_bots_indices, reversed(self.defend_replays)),
        ):
            if replay.finished:
                continue

            del target_game_state.cars[index]

            state = replay.playback(t)
            if state:
                car_state, controls = state

                # gets rid of the warning console spam
                car_state.jumped = None
                car_state.double_jumped = None

                self.interface.update_player_input(controls, index)
                target_game_state.cars[index] = car_state

        if distance(packet.game_cars[self.human_index].physics.location, packet.game_ball.physics.location) < 300:
            self.replaying_ball = False

        # playback ball
        ball_state = self.old_ball_replay.playback(t)
        if self.replaying_ball and ball_state:
            target_game_state.ball = ball_state

        self.interface.set_game_state(target_game_state)

    def prepare_next_stage(self):
        if self.state == "attack":
            self.attack_replays.append(self.current_replay)
        if self.state == "defend":
            self.defend_replays.append(self.current_replay)

        self.old_ball_replay = self.new_ball_replay

        self.state = "defend" if self.state == "attack" else "attack"

        if self.state == "attack":
            self.initial_delay += self.attack_time_shift
        if self.state == "defend":
            self.initial_delay += self.defend_time_shift
        self.time_limit -= 0.1

