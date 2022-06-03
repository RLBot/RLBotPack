from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

import numpy as np
import keyboard

from agent import Agent
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
        self.agent = Agent()
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
        keyboard.add_hotkey('5', self.bot_toggle) # swap bots for different gamemodes


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        if len(self.game_state.players) == 1:
            if not self.trainer_init:
                self.trainer_init = True
                keyboard.unhook_all_hotkeys()
                self.initialize_trainer()
            return self.get_output_trainer(packet)
        else:
            cur_time = packet.game_info.seconds_elapsed
            delta = cur_time - self.prev_time
            self.prev_time = cur_time

            ticks_elapsed = round(delta * 120)
            self.ticks += ticks_elapsed
            self.game_state.decode(packet, ticks_elapsed)

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
                self.action = self.act_parser.parse_actions(self.agent.act(obs, self.gamemode), self.game_state)[0]  # Dim is (N, 8)

            if self.ticks >= self.tick_skip - 1:#  and self.game_on == True:
                self.update_controls(self.action)

            if self.ticks >= self.tick_skip:
                self.ticks = 0
                self.update_action = True

            return self.controls


    def update_controls(self, action):
        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = 0 if action[5] > 0 else action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0


    def bot_toggle(self):
        if self.gamemode == 'fiftyfifty':
            self.gamemode = 'kickoff'
        else:
            self.gamemode = 'fiftyfifty'


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
        self.gpad_controls = ['JStick-','JStick-','JStick-','No','GPad-','GPad-','GPad-','GPad-']
        self.first_jump = True
        self.control_pressed = [False]*11
        self.controls = ['']*11
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
        self.instructions = 'Off'
        self.awaiting_gpad = False
        self.altkey = False
        self.bind_is_set = True
        self.game_phase = 'Menu/Freeplay'
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

        # user changing keybinds
        if 'On' in self.set_controls:
            self.rebind_key(self.set_controls.index('On'), self.awaiting_gpad)

        # rendering
        color = self.renderer.yellow()
        color2 = self.renderer.lime()
        bg_color = self.renderer.create_color(100, 0, 0, 0)
        text = f"Select input number to toggle training, \
        \nController keybind, hold ctrl+number\
        \nKeyboard keybind, hold ctrl+alt+number\
        \n'1' Handbrake (not required) (keybind: {self.gpad_controls[7] if self.gpad_controls[7] != 'No' else ''}{self.controls[10] if self.set_controls[7] == 'Off' else 'Awaiting input'})\
        \n'2' Thrtle (easy): {self.train_controls[0]} (keybind(s): {self.gpad_controls[0] if self.gpad_controls[0] != 'No' else ''}{self.controls[0] if self.set_controls[0] == 'Off' else 'Awaiting input, if discrete input throttle then reverse'}{f', {self.controls[1]}' if self.set_controls[0] == 'Off' and self.controls[1] != '?' else ''})\
        \n'3' Boost  (easy): {self.train_controls[6]} (keybind: {self.gpad_controls[6] if self.gpad_controls[6] != 'No' else ''}{self.controls[9] if self.set_controls[6] == 'Off' else 'Awaiting input'})\
        \n'4' Roll   (easy): {self.train_controls[4]} (keybind(s): {self.gpad_controls[4] if self.gpad_controls[4] != 'No' else ''}{self.controls[6] if self.set_controls[4] == 'Off' else 'Awaiting input, if discrete input roll left then right'}{f', {self.controls[7]}' if self.set_controls[4] == 'Off' and self.controls[7] != '?' else ''})\
        \n'5' Jump   (hard): {self.train_controls[5]} (keybind: {self.gpad_controls[5] if self.gpad_controls[5] != 'No' else ''}{self.controls[8] if self.set_controls[5] == 'Off' else 'Awaiting input'})\
        \n'6' Steer  (hard): {self.train_controls[1]} (keybind(s): {self.gpad_controls[1] if self.gpad_controls[1] != 'No' else ''}{self.controls[2] if self.set_controls[1] == 'Off' else 'Awaiting input, if discrete input steer left then right'}{f', {self.controls[3]}' if self.set_controls[1] == 'Off' and self.controls[3] != '?' else ''})\
        \n'7' Pitch  (hard): {self.train_controls[2]} (keybind(s): {self.gpad_controls[2] if self.gpad_controls[2] != 'No' else ''}{self.controls[4] if self.set_controls[2] == 'Off' else 'Awaiting input, if discrete input pitch down then up'}{f', {self.controls[5]}' if self.set_controls[2] == 'Off' and self.controls[5] != '?' else ''})\
        \nBegin in yellow rings or press 'backspace'\
        \nPress '8' to toggle speedflip instructions"
        text2 = f"This flip can be done on keyboard or controller\
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
        self.renderer.begin_rendering()
        self.renderer.draw_polyline_3d(self.circle(), color) if self.game_phase == 'Menu/Freeplay' else None
        self.renderer.draw_polyline_3d(self.circle(z=25), color) if self.game_phase == 'Menu/Freeplay' else None
        self.renderer.draw_polyline_3d(self.circle(z=40), color) if self.game_phase == 'Menu/Freeplay' else None
        self.renderer.draw_rect_2d(10, 40, 570, 300, True, bg_color)
        self.renderer.draw_string_2d(20, 50, 1, 1, text, color)
        self.renderer.draw_rect_2d(10, 360, 500, 360, True, bg_color) if self.instructions == 'On' else None
        self.renderer.draw_string_2d(20, 370, 1, 1, text2, color) if self.instructions == 'On' else None
        self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
        self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
        self.renderer.draw_string_2d(900, 380, 5, 5, self.center_text, color2)
        self.renderer.end_rendering()

        # speedflip selected
        if self.game_phase == 'Menu/Freeplay' and -570 <= trainer.physics.location.x <= -330 and -570 <= trainer.physics.location.y <= -330:
            self.game_phase = 'Speedflip_Pause'
            self.prev_time = self.cur_time
            keyboard.unhook_all_hotkeys()

        # pause for countdown
        if self.game_phase == 'Speedflip_Pause' and self.cur_time - self.prev_time <= 4:
            self.setup_kickoff()
            self.center_text = f'{5-int(np.ceil(self.cur_time-self.prev_time))}'
            if self.center_text == '4' or self.center_text == '5':
                self.center_text = ''
        elif self.game_phase == 'Speedflip_Pause':
            self.game_phase = 'Speedflip'
            self.auto_control = True
            self.center_text = ''
            self.prev_time = self.ticks #self.cur_time

        # auto speedflip
        if self.game_phase == 'Speedflip':
            step_20hz = int(np.floor((self.ticks-self.prev_time)/6))
            if self.train_controls[5] == 'On':
                if (step_20hz == 8 and self.first_jump) or step_20hz == 10:
                    self.center_text = '^'
                else:
                    self.center_text = ''
                if step_20hz <= 15 and self.first_jump:
                    if self.controller_state.jump == 1:
                        self.first_jump = False
                        self.prev_time = self.ticks - 43
                    elif step_20hz > 7:
                        step_20hz = 6
            try:
                hardcoded_controls = self.speedflip_array[step_20hz]
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
                    elif setkey_remapped in [2,4,6] and abs(event.value) > 0.6:
                        self.controls[setkey_remapped] = event.axis
                        self.controls[setkey_remapped+1] = '?'
                        self.gpad_controls[setkey] = 'JStick-'
                        self.set_controls[setkey] = 'Off'
                        self.bind_is_set = True
                        self.altkey = False
                        self.ticks = 0
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


    def setup_kickoff(self):
        car_states = {}
        pos = Vector3(-2048, -2560, 17)
        yaw = np.pi * 0.25
        car_state = CarState(boost_amount=33.3, physics=Physics(location=pos, rotation=Rotator(yaw=yaw, pitch=0, roll=0), velocity=Vector3(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)))
        car_states[0] = car_state
        ball_state = BallState(Physics(location=Vector3(0, 0, 100), velocity=Vector3(0,0,-1), angular_velocity=Vector3(0, 0, 0)))
        game_state = GameState2(ball=ball_state, cars=car_states)
        self.set_game_state(game_state)


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
            self.instructions = 'On'
        else:
            self.instructions = 'Off'


    def menu_bspace_toggle(self):
            if self.game_phase == 'Menu/Freeplay':
                self.game_phase = 'Speedflip_Pause'
                self.prev_time = self.cur_time
                keyboard.unhook_all_hotkeys()