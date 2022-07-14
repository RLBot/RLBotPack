from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

import numpy as np
import keyboard
import pickle

from agent_omus import Agent_Omus
from obs.advanced_obs import AdvancedObs
from action.discrete_act import DiscreteAction
from rlgym_compat import GameState
import pygame
from pygame.locals import *
from rlbot.utils.game_state_util import BallState, CarState, Physics, Vector3, Rotator
from rlbot.utils.game_state_util import GameState as GameState2

class Omus(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        # FIXME Hey, botmaker. Start here:
        # Swap the obs builder if you are using a different one, RLGym's AdvancedObs is also available
        self.obs_builder = AdvancedObs()
        # Swap the action parser if you are using a different one, RLGym's Discrete and Continuous are also available
        self.act_parser = DiscreteAction()
        # Your neural network logic goes inside the Agent class, go take a look inside src/agent.py
        self.agent_omus = Agent_Omus()
        # Adjust the tickskip if your agent was trained with a different value
        self.tick_skip = 6

        self.game_state: GameState = None
        self.controls = None
        self.action = None
        self.update_action = True
        self.ticks = 0
        self.prev_time = 0
        self.gamemode ='fiftyfifty'
        print('Omus Ready - Index:', index)


    def initialize_agent(self):
        # Initialize the rlgym GameState object now that the game is active and the info is available
        self.game_state = GameState(self.get_field_info())
        self.ticks = self.tick_skip  # So we take an action the first tick
        self.prev_time = 0
        self.controls = SimpleControllerState()
        self.action = np.zeros(8)
        self.update_action = True
        self.trainer_init = False
        self.ko_diag_array = np.array([
        [1, 0, 0, 0, 0,0,1,0], #0
        [1, 0, 0, 0, 0,0,1,0],
        [1, 0, 0, 0, 0,0,1,0],
        [1, 0, 0, 0, 0,0,1,0],
        [1, 0,-1, 0, 1,0,1,0],
        [1, 0,-1, 0, 1,0,1,0],
        [1, 0,-1, 0, 1,0,1,0],
        [1,-1,-1, 0, 1,0,1,0],
        [1,-1,-1,-1, 1,1,1,0],
        [1, 0,-1,-1, 1,0,1,0],
        [1, 0,-1, 0, 1,1,1,0], #10
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 0, 1,0,1,0],
        [1, 0, 1, 1, 1,0,1,0], #20
        [1, 0, 1, 1, 1,0,1,0],
        [1, 0, 1, 1, 1,0,1,0],
        [1, 0, 1, 1, 1,0,1,0],
        [1, 0, 1, 1, 1,0,0,0],
        [1, 0, 1, 1, 1,0,0,0],
        [1, 0, 1, 1, 1,0,0,0],
        [1, 0, 0, 0, 0,0,0,0],
        [1, 0, 0,-1, 0,0,0,0],
        [1,-1, 0,-1, 0,0,0,0],
        [1,-1, 0,-1, 0,0,0,0], #30
        [1,-1, 0, 0, 0,0,0,0],
        [1, 0, 0, 0, 0,0,0,0],
    ])
        self.kickoff_time = 0
        self.ticks2 = -1
        self.ko_spawn_pos = 'Center'
        

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        if len(self.game_state.players) == 1:
            if not self.trainer_init:
                self.trainer_init = True
                self.initialize_trainer()
            return self.get_output_trainer(packet)
        else:
            cur_time = packet.game_info.seconds_elapsed
            delta = cur_time - self.prev_time
            self.prev_time = cur_time

            ticks_elapsed = round(delta * 120)
            self.ticks += ticks_elapsed
            self.game_state.decode(packet, ticks_elapsed)
            self.ticks2 += 1

            if self.update_action:
                self.update_action = False

                # FIXME Hey, botmaker. Verify that this is what you need for your agent
                # By default we treat every match as a 1v1 against a fixed opponent,
                # by doing this your bot can participate in 2v2 or 3v3 matches. Feel free to change this
                player = self.game_state.players[self.index]
                teammates = [p for p in self.game_state.players if p.team_num == self.team]
                opponents = [p for p in self.game_state.players if p.team_num != self.team]

                if len(opponents) == 0:
                    # There's no opponent, we assume this model is 1v0
                    self.game_state.players = [player]
                else:
                    # Sort by distance to ball
                    teammates.sort(key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))
                    opponents.sort(key=lambda p: np.linalg.norm(self.game_state.ball.position - p.car_data.position))

                    # Grab opponent in same "position" relative to it's teammates
                    opponent = opponents[min(teammates.index(player), len(opponents) - 1)]

                    self.game_state.players = [player, opponent]

                obs = self.obs_builder.build_obs(player, self.game_state, self.action)
                self.action = self.act_parser.parse_actions(self.agent_omus.act(obs, self.gamemode), self.game_state)[0]  # Dim is (N, 8)

            if self.ticks >= self.tick_skip - 1:
                self.update_controls(self.action)

            if self.ticks >= self.tick_skip:
                self.ticks = 0
                self.update_action = True
            
            # substitute fiftyfifty or kickoff model based on spawn
            if abs(self.game_state.players[self.team].car_data.position[0]) <= 2 and 998 <= abs(self.game_state.players[self.team].car_data.position[1]) <= 1002 and abs(self.game_state.players[self.team].car_data.linear_velocity[0]) <= 30:
                self.gamemode = 'fiftyfifty'
            if 2046 <= abs(self.game_state.players[self.team].car_data.position[0]) <= 2050 and 2558 <= abs(self.game_state.players[self.team].car_data.position[1]) <= 2562 and abs(self.game_state.players[self.team].car_data.linear_velocity[0]) <= 30:
                self.kickoff_time = self.ticks2
                self.gamemode = 'kickoff'
                if self.game_state.players[0].car_data.position[0] > 0:
                    self.ko_spawn_pos = 'Diagonal L'
                elif self.game_state.players[0].car_data.position[0] < 0:
                    self.ko_spawn_pos = 'Diagonal R'
            elif 254 <= abs(self.game_state.players[self.team].car_data.position[0]) <= 258 and 3838 <= abs(self.game_state.players[self.team].car_data.position[1]) <= 3842 and abs(self.game_state.players[self.team].car_data.linear_velocity[0]) <= 30:
                self.kickoff_time = self.ticks2
                self.gamemode = 'kickoff'
                if self.game_state.players[0].car_data.position[0] > 0:
                    self.ko_spawn_pos = 'Offset L'
                elif self.game_state.players[0].car_data.position[0] < 0:
                    self.ko_spawn_pos = 'Offset R'
            elif abs(self.game_state.players[self.team].car_data.position[0]) <= 2 and 4606 <= abs(self.game_state.players[self.team].car_data.position[1]) <= 4610 and abs(self.game_state.players[self.team].car_data.linear_velocity[0]) <= 30:
                self.kickoff_time = self.ticks2
                self.gamemode = 'kickoff'
                self.ko_spawn_pos = 'Center'
            # counter-fake kickoffs
            step_20hz = int(np.floor((self.ticks2-self.kickoff_time)/6))
            if self.ko_spawn_pos == 'Diagonal L':
                if step_20hz <= 30:
                    self.update_controls(self.ko_diag_array[step_20hz])
            elif self.ko_spawn_pos == 'Center':
                if 25 <= step_20hz <= 35:
                    self.controls.handbrake = 1
            if np.linalg.norm(self.game_state.ball.position - np.zeros(3)) < 1050:
                if (step_20hz <= 78 and (self.ko_spawn_pos == 'Diagonal L' or self.ko_spawn_pos == 'Diagonal R')) or\
                    (step_20hz <= 85 and (self.ko_spawn_pos != 'Diagonal L' or self.ko_spawn_pos != 'Diagonal R')):
                    if np.linalg.norm(self.game_state.ball.position - self.game_state.players[1-self.team].car_data.position) - np.linalg.norm(self.game_state.ball.position - self.game_state.players[self.team].car_data.position) > 400:
                        self.controls.boost = 0
                        if step_20hz >= 29:
                            self.gamemode = 'fiftyfifty'
                        if np.linalg.norm(self.game_state.ball.position - self.game_state.players[1-self.team].car_data.position) - np.linalg.norm(self.game_state.ball.position - self.game_state.players[self.team].car_data.position) > 800:
                            if 800 > np.linalg.norm(self.game_state.ball.position - self.game_state.players[self.team].car_data.position):
                                if abs(np.linalg.norm(self.game_state.players[self.team].car_data.linear_velocity)) > 700:
                                    self.controls.throttle = -1
                            if abs(np.linalg.norm(self.game_state.players[self.team].car_data.linear_velocity)) < 500:
                                self.controls.throttle = 1
            return self.controls


    def update_controls(self, action):
        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0


    def initialize_trainer(self):
        # Gamepad/Controller stuff 
        pygame.init()
        pygame.joystick.init()
        self.motion = [0, 0]
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.controller_state = SimpleControllerState()
        self.ticks = 0
        self.center_text = ""
        self.train_controls = ['Off']*8
        self.set_controls = ['Off']*8
        self.first_jump = True
        self.control_pressed = [False]*11
        try:
            with open("Omus/keybinds.pkl", "rb") as f:
                saved_controls = pickle.load(f)
                self.controls = saved_controls[0]
                self.gpad_controls = saved_controls[1]
        except:
            self.controls = ['']*11
            self.gpad_controls = ['JStick-','JStick-','JStick-','No','GPad-','GPad-','GPad-','GPad-']
            self.controls[0] = 5 # throttle_bind
            self.controls[1] = 4 # reverse_bind
            self.controls[2] = 0 # steer_bind1 if discrete, this is left (also yaw)
            self.controls[3] = '?' # steer_bind2  if discrete, this is right (also yaw)
            self.controls[4] = 1 # pitch_bind1 if discrete, this is nose down
            self.controls[5] = '?' # pitch_bind2 if discrete, this is nose up
            self.controls[6] = 2 # roll_bind1 if discrete, this is left
            self.controls[7] = 15 # roll_bind2 if discrete, this is right
            self.controls[8] = 0 # jump_bind
            self.controls[9] = 1 # boost_bind
            self.controls[10] = 9 # handbrake_bind
            with open("Omus/keybinds.pkl", "wb") as f:
                pickle.dump([self.controls,self.gpad_controls], f)
        self.instructions = 'Off'
        self.awaiting_gpad = False
        self.altkey = False
        self.bind_is_set = True
        self.game_phase = 'Menu/Freeplay'
        self.last_selection = 'Speedflip'
        self.pause_time = 4
        self.auto_control = False
        self.speedflip_array = np.array([
            [1,0, 0, 0, 0,0,1,0], #0
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0,-1, 0,-1,0,1,0],
            [1,0,-1, 0,-1,0,1,0],
            [1,0,-1, 0,-1,0,1,0],
            [1,1,-1, 0,-1,0,1,0],
            [1,1,-1, 1,-1,1,1,0],
            [1,0,-1, 1,-1,0,1,0],
            [1,0,-1, 0,-1,1,1,0], #10
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0], #20
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 1,-1,-1,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0], #30
            [1,0, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,1, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [0,0, 0, 0, 0,0,0,0] #40
        ])
        self.flipreset_array = np.array([
            [0,0, 0, 0, 0,0,0,0], #0
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0], #20
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0], #40
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [-1,0, 0, 0, 0,0,0,0],
            [-1,0, 0, 0, 0,0,0,0],
            [0,0, 1,-1, 0,1,0,0], #jump off wall
            [1,0, 1,-1, 0,0,0,0],
            [1,0, 1,-1, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 0, 1, 0,0,1,0],
            [1,0, 0, 1, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 1, 0,-1,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 1,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0], #60
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0,-1, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0], #80
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0,-1, 0, 0,0,0,0], # flip reset contact
            [1,0,-1, 0, 0,0,0,0],
            [1,0,-1, 0, 0,0,0,0],
            [1,0,-1, 0, 0,0,0,0],
            [1,0,-1, 0, 0,0,0,0],
            [1,0,-1, 0, 0,0,0,0],
            [1,0,-1, 1, 0,0,0,0],
            [1,0,-1, 1, 0,0,0,0],
            [1,0, 1, 1, 0,0,0,0],
            [1,0, 1, 1, 1,0,0,0],
            [1,0, 1, 1, 1,0,0,0],
            [1,0, 1, 1, 1,0,0,0],
            [1,0, 1, 1, 1,0,0,0],
            [1,0, 0,-1, 1,0,0,0],
            [1,0, 0,-1, 1,0,0,0],
            [1,0, 0,-1, 1,0,0,0],
            [1,0, 0,-1, 1,0,0,0], #100
            [1,0, 0,-1, 1,0,0,0],
            [1,0, 0,-1, 0,0,0,0],
            [1,0, 0,-1,-1,0,1,0],
            [1,0, 0, 0, 0,0,1,0],
            [1,0, 0, 1, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,1,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0], #120
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 0, 0, 0,0,0,0],
            [1,0, 1, 0, 0,0,0,0],
            [1,0, 1, 0, 0,1,0,0], # musty flick
            [1,0, 1, 0, 0,0,0,0],
        ])


    def circle(self, x=-450, y=-450, z=10):
        return [(round(np.cos(2*np.pi/60*i)*120)+x,round(np.sin(2*np.pi/60*i)*120)+y,z) for i in range(0,60+1)]


    def get_output_trainer(self, packet: GameTickPacket) -> SimpleControllerState:
        self.cur_time = packet.game_info.seconds_elapsed
        trainer = packet.game_cars[self.index]
        self.ticks += 1

        # initialise reading keyboard for menu selection
        if self.ticks <= 1:
            keyboard.add_hotkey('ctrl+1', self.menu_1a_toggle)
            keyboard.add_hotkey('ctrl+alt+1', self.menu_1b_toggle)
            keyboard.add_hotkey('2', self.menu_2_toggle)
            keyboard.add_hotkey('ctrl+2', self.menu_2a_toggle)
            keyboard.add_hotkey('ctrl+alt+2', self.menu_2b_toggle)
            keyboard.add_hotkey('3', self.menu_3_toggle)
            keyboard.add_hotkey('ctrl+3', self.menu_3a_toggle)
            keyboard.add_hotkey('ctrl+alt+3', self.menu_3b_toggle)
            keyboard.add_hotkey('4', self.menu_4_toggle)
            keyboard.add_hotkey('ctrl+4', self.menu_4a_toggle)
            keyboard.add_hotkey('ctrl+alt+4', self.menu_4b_toggle)
            keyboard.add_hotkey('5', self.menu_5_toggle)
            keyboard.add_hotkey('ctrl+5', self.menu_5a_toggle)
            keyboard.add_hotkey('ctrl+alt+5', self.menu_5b_toggle)
            keyboard.add_hotkey('6', self.menu_6_toggle)
            keyboard.add_hotkey('ctrl+6', self.menu_6a_toggle)
            keyboard.add_hotkey('ctrl+alt+6', self.menu_6b_toggle)
            keyboard.add_hotkey('7', self.menu_7_toggle)
            keyboard.add_hotkey('ctrl+7', self.menu_7a_toggle)
            keyboard.add_hotkey('ctrl+alt+7', self.menu_7b_toggle)
            keyboard.add_hotkey('8', self.menu_8_toggle)
            keyboard.add_hotkey('backspace', self.menu_bspace_toggle)
        
        if not self.auto_control:
            # user changing keybinds
            if 'On' in self.set_controls:
                self.rebind_key(self.set_controls.index('On'), self.awaiting_gpad)

            # rendering
            color = self.renderer.yellow()
            color2 = self.renderer.lime()
            color3 = self.renderer.pink()
            bg_color = self.renderer.create_color(100, 0, 0, 0)
            text = f"Press a number from the menu to toggle training\
            \nTo set a new controller keybind, press CTRL+NUM\
            \nTo set a new keyboard keybind, press CTRL+ALT+NUM\
            \n'1' Handbrake (cannot train) (keybind: {self.gpad_controls[7] if self.gpad_controls[7] != 'No' else ''}{self.controls[10] if self.set_controls[7] == 'Off' else 'Awaiting input'})\
            \n'2' Thrtle: {self.train_controls[0]} (keybind(s): {self.gpad_controls[0] if self.gpad_controls[0] != 'No' else ''}{self.controls[0] if self.set_controls[0] == 'Off' else 'If not JStick, press throttle then reverse'}{f', {self.controls[1]}' if self.set_controls[0] == 'Off' and self.controls[1] != '?' else ''})\
            \n'3' Boost : {self.train_controls[6]} (keybind: {self.gpad_controls[6] if self.gpad_controls[6] != 'No' else ''}{self.controls[9] if self.set_controls[6] == 'Off' else 'Awaiting input'})\
            \n'4' Roll  : {self.train_controls[4]} (keybind(s): {self.gpad_controls[4] if self.gpad_controls[4] != 'No' else ''}{self.controls[6] if self.set_controls[4] == 'Off' else 'If not JStick, press roll left then right'}{f', {self.controls[7]}' if self.set_controls[4] == 'Off' and self.controls[7] != '?' else ''})\
            \n'5' Jump  : {self.train_controls[5]} (keybind: {self.gpad_controls[5] if self.gpad_controls[5] != 'No' else ''}{self.controls[8] if self.set_controls[5] == 'Off' else 'Awaiting input'})\
            \n'6' Steer : {self.train_controls[1]} (keybind(s): {self.gpad_controls[1] if self.gpad_controls[1] != 'No' else ''}{self.controls[2] if self.set_controls[1] == 'Off' else 'If not JStick, press steer left then right'}{f', {self.controls[3]}' if self.set_controls[1] == 'Off' and self.controls[3] != '?' else ''})\
            \n'7' Pitch : {self.train_controls[2]} (keybind(s): {self.gpad_controls[2] if self.gpad_controls[2] != 'No' else ''}{self.controls[4] if self.set_controls[2] == 'Off' else 'If not JStick, press pitch down then up'}{f', {self.controls[5]}' if self.set_controls[2] == 'Off' and self.controls[5] != '?' else ''})\
            \n'backspace' to replay last\
            \nBakkes game speed can be reduced!\
            \nPress '8' to toggle instructions"
            text2 = f"Speedflip can be done on keyboard or controller\
            \nIt requires an air-roll left button\
            \n\nHold boost and throttle throughout\
            \nHold roll left until just before landing\
            \n\nDouble jump quickly, within 50-100ms\
            \nsee the jump indicators for timings\
            \n\nSteer/Yaw: tap right just before jumping,\
            \nyaw left while upside down,\
            \nafter landing steer right to ball\
            \n\nPitch forwards until flip then immediately\
            \npitch back and hold until just before landing\
            \n\nHandbrake is not required but is available"
            text3 = f"FLIP-RESET MUSTY! YO, YOU STYLIN?\
            \n\nGreen rings, aim to get the flip reset\
            \nPink rings, recover then shoot however you like\
            \nYellow rings demonstrates the full mechanic\
            \nIf should execute perfectly at 120 fps,\
            \nif not, you may have packet loss\
            \n\nHighly recommend first watching\
            \n'wayton pilkin flip reset' on youtube\
            \n\nTry bringing up bakkes mod->current game\
            \nand experiment with reduced game speed\
            \n\nExperiment with one or multiple inputs\
            \nWhilst its almost impossible to perfectly match\
            \nthe demonstration, it will help you learn timings"

            self.renderer.begin_rendering()
            self.renderer.draw_polyline_3d(self.circle(), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(z=25), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(z=40), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=-300), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=-300,z=25), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=-300,z=40), color) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=800,y=0), color2) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=800,y=0,z=25), color2) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=800,y=0,z=40), color2) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=300), color3) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=300,z=25), color3) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_polyline_3d(self.circle(x=500,y=300,z=40), color3) if self.game_phase == 'Menu/Freeplay' else None
            self.renderer.draw_rect_2d(10, 40, 570, 300, True, bg_color)
            self.renderer.draw_string_2d(20, 50, 1, 1, text, color)
            self.renderer.draw_rect_2d(10, 360, 500, 360, True, bg_color) if self.instructions != 'Off' else None
            self.renderer.draw_string_2d(20, 370, 1, 1, text2, color) if self.instructions == 'On_SF' else None
            self.renderer.draw_string_2d(20, 370, 1, 1, text3, color) if self.instructions == 'On_FR' else None
            self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
            self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
            self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
            self.renderer.end_rendering()

            # pause for countdown (happens after selection, placed here for consistent timings)
            if self.game_phase == 'Pause' and self.cur_time - self.prev_time <= self.pause_time:
                self.setup_kickoff()
                self.center_text = f'{self.pause_time+1-int(np.ceil(self.cur_time-self.prev_time))}'
                if self.center_text == '4' or self.center_text == '5':
                    self.center_text = ''
            elif self.game_phase == 'Pause':
                self.game_phase = self.last_selection
                self.auto_control = True
                self.center_text = ''
                if self.last_selection == 'FlipReset_Contact':
                    self.prev_time = self.ticks-1
                else:
                    self.prev_time = self.ticks

            # speedflip selected
            if self.game_phase == 'Menu/Freeplay' and ((trainer.physics.location.x - -450)**2+(trainer.physics.location.y - -450)**2)**0.5 < 120:
                self.game_phase = 'Pause'
                self.last_selection = 'Speedflip'
                self.pause_time = 4
                self.prev_time = self.cur_time
                keyboard.unhook_all_hotkeys()
            
            # flip-reset selected
            if self.game_phase == 'Menu/Freeplay' and ((trainer.physics.location.x - 500)**2+(trainer.physics.location.y - -300)**2)**0.5 < 120:
                self.game_phase = 'Pause'
                self.last_selection = 'FlipReset'
                self.pause_time = 1
                self.prev_time = self.cur_time
                keyboard.unhook_all_hotkeys()
            
             # flip-reset selected - just after jumping off the wall
            if self.game_phase == 'Menu/Freeplay' and ((trainer.physics.location.x - 800)**2+(trainer.physics.location.y - 0)**2)**0.5 < 120:
                self.game_phase = 'Pause'
                self.last_selection = 'FlipReset_OffWall'
                self.pause_time = 1
                self.prev_time = self.cur_time
                keyboard.unhook_all_hotkeys()

            # flip-reset selected - just after flip-reset contact
            if self.game_phase == 'Menu/Freeplay' and ((trainer.physics.location.x - 500)**2+(trainer.physics.location.y - 300)**2)**0.5 < 120:
                self.game_phase = 'Pause'
                self.last_selection = 'FlipReset_Contact'
                self.pause_time = 1
                self.prev_time = self.cur_time
                keyboard.unhook_all_hotkeys()

        # auto mechanic
        if self.game_phase == self.last_selection:
            step_20hz = int(np.floor((self.ticks-self.prev_time)/6))
            if self.game_phase == 'Speedflip':
                if self.train_controls[5] == 'On':
                    if (step_20hz == 8 and self.first_jump) or step_20hz == 10:
                        self.center_text = '^^'
                    else:
                        self.center_text = ''
                    if step_20hz <= 15 and self.first_jump:
                        if self.controller_state.jump == 1:
                            self.first_jump = False
                            self.prev_time = self.ticks - 43
                        elif step_20hz > 7:
                            step_20hz = 6
                    self.renderer.begin_rendering()
                    self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, self.renderer.lime())
                    self.renderer.end_rendering()
            try:
                if self.game_phase == 'Speedflip':
                    hardcoded_controls = self.speedflip_array[step_20hz]
                elif self.game_phase == 'FlipReset':
                    hardcoded_controls = self.flipreset_array[step_20hz]
                elif self.game_phase == 'FlipReset_OffWall':
                    hardcoded_controls = self.flipreset_array[step_20hz+47]
                    if step_20hz+47 > 90:
                        hardcoded_controls = [0]*8
                        self.game_phase = 'Menu/Freeplay'
                        self.auto_control = False
                        self.first_jump = True
                        self.ticks = 0
                elif self.game_phase == 'FlipReset_Contact':
                    hardcoded_controls = self.flipreset_array[step_20hz+84]
                self.controller_state.throttle = hardcoded_controls[0] if self.train_controls[0] == 'Off' else self.controller_state.throttle
                self.controller_state.steer = hardcoded_controls[1] if self.train_controls[1] == 'Off' else self.controller_state.steer
                self.controller_state.yaw = hardcoded_controls[3] if self.train_controls[1] == 'Off' else self.controller_state.yaw
                self.controller_state.boost = hardcoded_controls[6] if self.train_controls[6] == 'Off' else self.controller_state.boost
                self.controller_state.jump = hardcoded_controls[5] if self.train_controls[5] == 'Off' else self.controller_state.jump
                self.controller_state.pitch = hardcoded_controls[2] if self.train_controls[2] == 'Off' else self.controller_state.pitch
                self.controller_state.roll = hardcoded_controls[4] if self.train_controls[4] == 'Off' else self.controller_state.roll
            except:
                self.game_phase = 'Menu/Freeplay'
                self.auto_control = False
                self.first_jump = True
                self.ticks = 0

        
        # remote controlling the trainer bot (controller)
        for event in pygame.event.get():
            if event.type == JOYBUTTONDOWN:
                if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[0] == 'GPad-' and event.button == self.controls[0]:
                        self.control_pressed[0] = True
                if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[0] == 'GPad-' and event.button == self.controls[1]:
                        self.control_pressed[1] = True
                if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[1] == 'GPad-' and event.button == self.controls[2]:
                        self.control_pressed[2] = True
                if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[1] == 'GPad-' and event.button == self.controls[3]:
                        self.control_pressed[3] = True
                if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[2] == 'GPad-' and event.button == self.controls[4]:
                        self.control_pressed[4] = True
                if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[2] == 'GPad-' and event.button == self.controls[5]:
                        self.control_pressed[5] = True
                if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[4] == 'GPad-' and event.button == self.controls[6]:
                        self.control_pressed[6] = True
                if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[4] == 'GPad-' and event.button == self.controls[7]:
                        self.control_pressed[7] = True
                if (self.train_controls[5] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[5] == 'GPad-' and event.button == self.controls[8]:
                        self.controller_state.jump = 1.0
                if (self.train_controls[6] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[6] == 'GPad-' and event.button == self.controls[9]:
                        self.controller_state.boost = 1.0
                if self.gpad_controls[7] == 'GPad-' and event.button == self.controls[10]:
                    self.controller_state.handbrake = 1.0
            if event.type == JOYBUTTONUP:
                if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[0] == 'GPad-' and event.button == self.controls[0]:
                        self.control_pressed[0] = False
                if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[0] == 'GPad-' and event.button == self.controls[1]:
                        self.control_pressed[1] = False
                if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[1] == 'GPad-' and event.button == self.controls[2]:
                        self.control_pressed[2] = False
                if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[1] == 'GPad-' and event.button == self.controls[3]:
                        self.control_pressed[3] = False
                if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[2] == 'GPad-' and event.button == self.controls[4]:
                        self.control_pressed[4] = False
                if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[2] == 'GPad-' and event.button == self.controls[5]:
                        self.control_pressed[5] = False
                if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[4] == 'GPad-' and event.button == self.controls[6]:
                        self.control_pressed[6] = False
                if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[4] == 'GPad-' and event.button == self.controls[7]:
                        self.control_pressed[7] = False
                if (self.train_controls[5] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[5] == 'GPad-' and event.button == self.controls[8]:
                        self.controller_state.jump = 0.0
                if (self.train_controls[6] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[6] == 'GPad-' and event.button == self.controls[9]:
                        self.controller_state.boost = 0.0
                if self.gpad_controls[7] == 'GPad-' and event.button == self.controls[10]:
                    self.controller_state.handbrake = 0.0
            if event.type == JOYAXISMOTION:
                if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[0] == 'JStick-' and event.axis == self.controls[0]:
                        if abs(event.value) > 1:
                            self.control_pressed[8] = (round(event.value)+1)/2
                        else:
                            self.control_pressed[8] = (event.value+1)/2
                    if self.gpad_controls[1] == 'JStick-' and event.axis == self.controls[1]:
                        if abs(event.value) > 1:
                            self.control_pressed[9] = -(round(event.value)+1)/2
                        else:
                            self.control_pressed[9] = -(event.value+1)/2
                if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[1] == 'JStick-' and event.axis == self.controls[2]:
                        if abs(event.value) > 1:
                            self.controller_state.steer = self.controller_state.yaw = round(event.value)
                        else:
                            self.controller_state.steer = self.controller_state.yaw = event.value
                if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[2] == 'JStick-' and event.axis == self.controls[4]:
                        if abs(event.value) > 1:
                            self.controller_state.pitch = round(event.value)
                        else:
                            self.controller_state.pitch = event.value
                if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
                    if self.gpad_controls[4] == 'JStick-' and event.axis == self.controls[6]:
                        if abs(event.value) > 1:
                            self.controller_state.roll = round(event.value)
                        else:
                            self.controller_state.roll = event.value
            if event.type == JOYDEVICEADDED:
                self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            if event.type == JOYDEVICEREMOVED:
                self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        # continued controller setting for non-binary inputs
        if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[0] == 'GPad-':
                if self.control_pressed[0] and self.control_pressed[1]:
                    self.controller_state.throttle = 0.0
                elif self.control_pressed[0]:
                    self.controller_state.throttle = 1.0
                elif self.control_pressed[1]:
                    self.controller_state.throttle = -1.0
                else:
                    self.controller_state.throttle = 0.0
            if self.gpad_controls[0] == 'JStick-':
                self.controller_state.throttle = self.control_pressed[8] + self.control_pressed[9]
        if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[1] == 'GPad-':
                if self.control_pressed[2] and self.control_pressed[3]:
                    self.controller_state.steer = 0.0
                    self.controller_state.yaw = 0.0
                elif self.control_pressed[2]:
                    self.controller_state.steer = -1.0
                    self.controller_state.yaw = -1.0
                elif self.control_pressed[3]:
                    self.controller_state.steer = 1.0
                    self.controller_state.yaw = 1.0
                else:
                    self.controller_state.steer = 0.0
                    self.controller_state.yaw = 0.0
        if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[2] == 'GPad-':
                if self.control_pressed[4] and self.control_pressed[5]:
                    self.controller_state.pitch = 0.0
                elif self.control_pressed[5]:
                    self.controller_state.pitch = 1.0
                elif self.control_pressed[4]:
                    self.controller_state.pitch = -1.0
                else:
                    self.controller_state.pitch = 0.0
        if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[4] == 'GPad-':
                if self.control_pressed[6] and self.control_pressed[7]:
                    self.controller_state.roll = 0.0
                elif self.control_pressed[6]:
                    self.controller_state.roll = -1.0
                elif self.control_pressed[7]:
                    self.controller_state.roll = 1.0
                else:
                    self.controller_state.roll = 0.0

        # remote controlling the trainer bot (keyboard)
        if (self.train_controls[0] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[0] == 'No':
                if keyboard.is_pressed(self.controls[0]) and keyboard.is_pressed(self.controls[1]):
                    self.controller_state.throttle = 0.0
                elif keyboard.is_pressed(self.controls[0]):
                    self.controller_state.throttle = 1.0
                elif keyboard.is_pressed(self.controls[1]):
                    self.controller_state.throttle = -1.0
                else:
                    self.controller_state.throttle = 0.0
        if (self.train_controls[1] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[1] == 'No':
                if keyboard.is_pressed(self.controls[2]) and keyboard.is_pressed(self.controls[3]):
                    self.controller_state.steer = 0.0
                    self.controller_state.yaw = 0.0
                elif keyboard.is_pressed(self.controls[2]):
                    self.controller_state.steer = -1.0
                    self.controller_state.yaw = -1.0
                elif keyboard.is_pressed(self.controls[3]):
                    self.controller_state.steer = 1.0
                    self.controller_state.yaw = 1.0
                else:
                    self.controller_state.steer = 0.0
                    self.controller_state.yaw = 0.0
        if (self.train_controls[2] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[2] == 'No':
                if keyboard.is_pressed(self.controls[5]) and keyboard.is_pressed(self.controls[4]):
                    self.controller_state.pitch = 0.0
                elif keyboard.is_pressed(self.controls[5]):
                    self.controller_state.pitch = 1.0
                elif keyboard.is_pressed(self.controls[4]):
                    self.controller_state.pitch = -1.0
                else:
                    self.controller_state.pitch = 0.0
        if (self.train_controls[4] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[4] == 'No':
                if keyboard.is_pressed(self.controls[6]) and keyboard.is_pressed(self.controls[7]):
                    self.controller_state.roll = 0.0
                elif keyboard.is_pressed(self.controls[6]):
                    self.controller_state.roll = -1.0
                elif keyboard.is_pressed(self.controls[7]):
                    self.controller_state.roll = 1.0
                else:
                    self.controller_state.roll = 0.0
        if (self.train_controls[5] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[5] == 'No':
                if keyboard.is_pressed(self.controls[8]):
                    self.controller_state.jump = 1.0
                else:
                    self.controller_state.jump = 0.0
        if (self.train_controls[6] == 'On' and self.auto_control) or not self.auto_control:
            if self.gpad_controls[6] == 'No':
                if keyboard.is_pressed(self.controls[9]):
                    self.controller_state.boost = 1.0
                else:
                    self.controller_state.boost = 0.0
        if self.gpad_controls[7] == 'No':
            if keyboard.is_pressed(self.controls[10]):
                self.controller_state.handbrake = 1.0
            else:
                self.controller_state.handbrake = 0.0
        return self.controller_state


    def rebind_key(self, setkey, gpad):
        keyboard.unhook_all_hotkeys()
        self.bind_is_set = False
        setkey_remapped = {0:0,1:2,2:4,3:2,4:6,5:8,6:9,7:10}
        setkey_remapped = setkey_remapped[setkey]
        if self.altkey:
            setkey_remapped +=1
        if gpad:
            for event in pygame.event.get():
                if event.type == JOYBUTTONDOWN:
                    if setkey_remapped in [0,2,4,6]:
                        self.altkey = True
                        self.controls[setkey_remapped] = event.button
                        self.bind_is_set = True
                    elif (setkey_remapped in [1,3,5,7] and self.controls[setkey_remapped-1] != event.button) or setkey_remapped >= 8:
                        self.controls[setkey_remapped] = event.button
                        self.gpad_controls[setkey] = 'GPad-'
                        self.set_controls[setkey] = 'Off'
                        self.altkey = False
                        self.ticks = 0
                        with open("Omus/keybinds.pkl", "wb") as f:
                            pickle.dump([self.controls,self.gpad_controls], f)
                if event.type == JOYAXISMOTION:
                    if setkey_remapped == 0 and abs(event.value) > 0.6:
                        self.altkey = True
                        self.controls[setkey_remapped] = event.axis
                        self.bind_is_set = True
                    elif setkey_remapped == 1 and abs(event.value) > 0.6 and self.controls[setkey_remapped-1] != event.axis:
                        self.controls[setkey_remapped] = event.axis
                        self.gpad_controls[setkey] = 'JStick-'
                        self.set_controls[setkey] = 'Off'
                        self.bind_is_set = True
                        self.altkey = False
                        self.ticks = 0
                        with open("Omus/keybinds.pkl", "wb") as f:
                            pickle.dump([self.controls,self.gpad_controls], f)
                    elif setkey_remapped in [2,4,6] and abs(event.value) > 0.6:
                        self.controls[setkey_remapped] = event.axis
                        self.controls[setkey_remapped+1] = '?'
                        self.gpad_controls[setkey] = 'JStick-'
                        self.set_controls[setkey] = 'Off'
                        self.bind_is_set = True
                        self.altkey = False
                        self.ticks = 0
                        with open("Omus/keybinds.pkl", "wb") as f:
                            pickle.dump([self.controls,self.gpad_controls], f)
        if not self.bind_is_set and not gpad:
            key = keyboard.read_key()
            if not key in {'1','2','3','4','5','6','7','9','8','0','ctrl','alt'}:
                if setkey_remapped in [0,2,4,6]:
                    self.altkey = True
                    self.controls[setkey_remapped] = key
                    self.bind_is_set = True
                elif (setkey_remapped in [1,3,5,7] and self.controls[setkey_remapped-1] != key) or setkey_remapped >= 8:
                    self.controls[setkey_remapped] = key
                    self.gpad_controls[setkey] = 'No'
                    self.set_controls[setkey] = 'Off'
                    self.altkey = False
                    self.ticks = 0
                    with open("Omus/keybinds.pkl", "wb") as f:
                            pickle.dump([self.controls,self.gpad_controls], f)


    def setup_kickoff(self):
        car_states = {}
        if self.last_selection == 'Speedflip':
            pos = Vector3(-2048, -2560, 17)
            yaw = np.pi * 0.25
            car_state = CarState(boost_amount=33.3, physics=Physics(location=pos, rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
                angular_velocity=Vector3(0, 0, 0)))
            ball_state = BallState(Physics(location=Vector3(0, 0, 93), velocity=Vector3(0,0,-1), angular_velocity=Vector3(0, 0, 0)))
        elif self.last_selection == 'FlipReset':
            pos = Vector3(-1200, -240, 17)
            yaw = np.pi * 0.96
            car_state = CarState(boost_amount=100.0, physics=Physics(location=pos, rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(-1200, 160, 0),
                angular_velocity=Vector3(0, 0, 0)))
            ball_state = BallState(Physics(location=Vector3(-1500, -200, 93), velocity=Vector3(-1800,240,-1), angular_velocity=Vector3(0, -4, 0.1)))
        elif self.last_selection == 'FlipReset_OffWall' or self.last_selection == 'FlipReset_Contact':
            if self.last_selection == 'FlipReset_OffWall':
                fr2 = [-4065.179931640625, 169.47999572753906, 485.3199768066406, 1.41739821434021, 1.365913987159729, -1.774911642074585, 331.5010070800781, 117.44099426269531, 825.3409423828125, -0.11900999397039413, -0.2544099986553192, -0.08241000026464462, 92, -3888.33984375, 229.489990234375, 678.1799926757812, 799.7709350585938, 356.20098876953125, 1265.700927734375, -0.540910005569458, 0.6030099987983704, 0.08750999718904495]
            elif self.last_selection == 'FlipReset_Contact':
                fr2 = [-2530.239990234375, 803.3299560546875, 1801.22998046875, -0.7645935416221619, 0.2552160620689392, -3.0624008178710938, 1426.3109130859375, 543.1609497070312, 251.18099975585938, -2.2634098529815674, 4.41940975189209, 0.26431000232696533, 44, -2444.179931640625, 872.7099609375, 1857.3199462890625, 755.6409301757812, 336.6809997558594, 21.96099853515625, -0.540910005569458, 0.6030099987983704, 0.08740999549627304]
            car_state = CarState(boost_amount=fr2[12], physics=Physics(location=Vector3(fr2[0],fr2[1],fr2[2]), rotation=Rotator(pitch=fr2[3],yaw=fr2[4],roll=fr2[5]),
            velocity=Vector3(fr2[6],fr2[7],fr2[8]), angular_velocity=Vector3(fr2[9],fr2[10],fr2[11])))
            ball_state = BallState(Physics(location=Vector3(fr2[13],fr2[14],fr2[15]), velocity=Vector3(fr2[16],fr2[17],fr2[18]), angular_velocity=Vector3(fr2[19],fr2[20],fr2[21])))
        car_states[0] = car_state
        game_state = GameState2(ball=ball_state, cars=car_states)
        self.set_game_state(game_state)


    def save_gamestate(self, packet):
            trainer = packet.game_cars[self.index]
            ball = packet.game_ball
            cur_state = [0]*22
            cur_state[0] = trainer.physics.location.x
            cur_state[1] = trainer.physics.location.y
            cur_state[2] = trainer.physics.location.z
            cur_state[3] = trainer.physics.rotation.pitch
            cur_state[4] = trainer.physics.rotation.yaw
            cur_state[5] = trainer.physics.rotation.roll
            cur_state[6] = trainer.physics.velocity.x
            cur_state[7] = trainer.physics.velocity.y
            cur_state[8] = trainer.physics.velocity.z
            cur_state[9] = trainer.physics.angular_velocity.x
            cur_state[10] = trainer.physics.angular_velocity.y
            cur_state[11] = trainer.physics.angular_velocity.z
            cur_state[12] = trainer.boost
            cur_state[13] = ball.physics.location.x
            cur_state[14] = ball.physics.location.y
            cur_state[15] = ball.physics.location.z
            cur_state[16] = ball.physics.velocity.x
            cur_state[17] = ball.physics.velocity.y
            cur_state[18] = ball.physics.velocity.z
            cur_state[19] = ball.physics.angular_velocity.x
            cur_state[20] = ball.physics.angular_velocity.y
            cur_state[21] = ball.physics.angular_velocity.z
            return cur_state


    def menu_1a_toggle(self):
        if self.set_controls[7] == 'Off':
            self.set_controls[7] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[7] = 'Off'


    def menu_1b_toggle(self):
        if self.set_controls[7] == 'Off':
            self.set_controls[7] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[7] = 'Off'


    def menu_2_toggle(self):
        if self.train_controls[0] == 'Off':
            self.train_controls[0] = 'On'
        else:
            self.train_controls[0] = 'Off'


    def menu_2a_toggle(self):
        if self.set_controls[0] == 'Off':
            self.set_controls[0] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[0] = 'Off'


    def menu_2b_toggle(self):
        if self.set_controls[0] == 'Off':
            self.set_controls[0] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[0] = 'Off'


    def menu_3_toggle(self):
        if self.train_controls[6] == 'Off':
            self.train_controls[6] = 'On'
        else:
            self.train_controls[6] = 'Off'


    def menu_3a_toggle(self):
        if self.set_controls[6] == 'Off':
            self.set_controls[6] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[6] = 'Off'


    def menu_3b_toggle(self):
        if self.set_controls[6] == 'Off':
            self.set_controls[6] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[6] = 'Off'


    def menu_4_toggle(self):
        if self.train_controls[4] == 'Off':
            self.train_controls[4] = 'On'
        else:
            self.train_controls[4] = 'Off'


    def menu_4a_toggle(self):
        if self.set_controls[4] == 'Off':
            self.set_controls[4] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[4] = 'Off'


    def menu_4b_toggle(self):
        if self.set_controls[4] == 'Off':
            self.set_controls[4] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[4] = 'Off'


    def menu_5_toggle(self):
        if self.train_controls[5] == 'Off':
            self.train_controls[5] = 'On'
        else:
            self.train_controls[5] = 'Off'


    def menu_5a_toggle(self):
        if self.set_controls[5] == 'Off':
            self.set_controls[5] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[5] = 'Off'


    def menu_5b_toggle(self):
        if self.set_controls[5] == 'Off':
            self.set_controls[5] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[5] = 'Off'


    def menu_6_toggle(self):
        if self.train_controls[1] == 'Off':
            self.train_controls[1] = 'On'
        else:
            self.train_controls[1] = 'Off'


    def menu_6a_toggle(self):
        if self.set_controls[1] == 'Off':
            self.set_controls[1] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[1] = 'Off'


    def menu_6b_toggle(self):
        if self.set_controls[1] == 'Off':
            self.set_controls[1] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[1] = 'Off'


    def menu_7_toggle(self):
        if self.train_controls[2] == 'Off':
            self.train_controls[2] = 'On'
        else:
            self.train_controls[2] = 'Off'


    def menu_7a_toggle(self):
        if self.set_controls[2] == 'Off':
            self.set_controls[2] = 'On'
            self.awaiting_gpad = True
        else:
            self.set_controls[2] = 'Off'


    def menu_7b_toggle(self):
        if self.set_controls[2] == 'Off':
            self.set_controls[2] = 'On'
            self.awaiting_gpad = False
        else:
            self.set_controls[2] = 'Off'


    def menu_8_toggle(self):
        if self.instructions == 'Off':
            self.instructions = 'On_SF'
        elif self.instructions == 'On_SF':
            self.instructions = 'On_FR'
        else:
            self.instructions = 'Off'


    def menu_bspace_toggle(self):
        if self.game_phase == 'Menu/Freeplay':
            self.game_phase = 'Pause'
            self.prev_time = self.cur_time
            keyboard.unhook_all_hotkeys()
