from json import loads
from math import pi, floor
from pathlib import Path
from rlbot.agents.hivemind.python_hivemind import PythonHivemind
from rlbot.utils.game_state_util import GameState
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket
from shutil import copyfile
from typing import Dict

import os

def translate(tick, instructions, controller, physics):
   edit = False
   duration = 0
   for instruction in instructions:
      arguments = instruction.split(' ')
      if arguments[0] == 'wait':
         duration = duration + int(arguments[1])
      elif arguments[0] == 'boost':
         if tick == duration:
            controller.boost = True
         elif tick == duration + floor(max(float(arguments[1]), 0)):
            controller.boost = False
      elif arguments[0] == 'handbrake':
         if tick == duration:
            controller.handbrake = True
         elif tick == duration + floor(max(float(arguments[1]), 0)):
            controller.handbrake = False
      elif arguments[0] == 'jump':
         if tick == duration:
            controller.jump = True
         elif tick == duration + floor(max(float(arguments[1]), 0)):
            controller.jump = False
      elif arguments[0] == 'roll':
         if tick == duration:
            if arguments[1] == 'left':
               controller.roll = min(max(float(arguments[2]), 0), 1) * -1
            elif arguments[0] == 'right':
               controller.roll = min(max(float(arguments[2]), 0), 1)
         elif tick == duration + floor(max(float(arguments[3]), 0)):
            controller.roll = 0
      elif arguments[0] == 'spin':
         if tick == duration:
            if arguments[1] == 'left':
               controller.yaw = min(max(float(arguments[2]), 0), 1) * -1
            elif arguments[0] == 'right':
               controller.yaw = min(max(float(arguments[2]), 0), 1)
         elif tick == duration + floor(max(float(arguments[3]), 0)):
            controller.yaw = 0
      elif arguments[0] == 'steer':
         if tick == duration:
            if arguments[1] == 'left':
               controller.steer = min(max(float(arguments[2]), 0), 1) * -1
            elif arguments[0] == 'right':
               controller.steer = min(max(float(arguments[2]), 0), 1)
         elif tick == duration + floor(max(float(arguments[3]), 0)):
            controller.steer = 0
      elif arguments[0] == 'throttle':
         if tick == duration:
            if arguments[1] == 'backwards':
               controller.throttle = min(max(float(arguments[2]), 0), 1) * -1
            elif arguments[0] == 'forwards':
               controller.throttle = min(max(float(arguments[2]), 0), 1)
         elif tick == duration + floor(max(float(arguments[3]), 0)):
            controller.throttle = 0
      elif arguments[0] == 'tilt':
         if tick == duration:
            if arguments[1] == 'forwards':
               controller.pitch = min(max(float(arguments[2]), 0), 1) * -1
            elif arguments[0] == 'backwards':
               controller.pitch = min(max(float(arguments[2]), 0), 1)
         elif tick == duration + floor(max(float(arguments[3]), 0)):
            controller.pitch = 0
      elif arguments[0] == 'position':
         if tick == duration:
            physics.location.x = float(arguments[1])
            physics.location.y = float(arguments[2])
            physics.location.z = float(arguments[3])
            edit = True
      elif arguments[0] == 'rotation':
         if tick == duration:
            physics.rotation.roll = float(arguments[1]) * (pi / 180)
            physics.rotation.pitch = float(arguments[2]) * (pi / 180)
            physics.rotation.yaw = float(arguments[3]) * (pi / 180)
            edit = True
      elif arguments[0] == 'velocity':
         if tick == duration:
            physics.velocity.x = float(arguments[1])
            physics.velocity.y = float(arguments[2])
            physics.velocity.z = float(arguments[3])
            edit = True
      elif arguments[0] == 'angular-velocity':
         if tick == duration:
            physics.angular_velocity.x = float(arguments[1])
            physics.angular_velocity.y = float(arguments[2])
            physics.angular_velocity.z = float(arguments[3])
            edit = True
   return edit
         
session = { 'drones': [], 'mode': 0, 'script': {}, 'tick': 0 }

script_folder = os.path.expanduser('~/Documents/Skrrripted')
script_file = os.path.join(script_folder, 'script.json')

if not os.path.isdir(script_folder):
   os.makedirs(script_folder)

if not os.path.isfile(script_file):
   copyfile(str(Path(__file__).parent / "script.json"), script_file)

class Hive(PythonHivemind):
   def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:
      if packet.game_info.is_round_active:
         if session['mode'] == 0:
            session['mode'] = 1
            session['tick'] = 0
            session['script'] = loads(open(script_file, 'r').read())
         else:
            edit = False
            state = GameState.create_from_gametickpacket(packet)
            script = session['script']
            try:
               if (translate(session['tick'], script['ball'], None, state.ball.physics)):
                  edit = True
            except:
               pass
            for drone in session['drones']:
               if drone['drone'] < len(script['drones']):
                  try:
                     if (translate(session['tick'], script['drones'][drone['drone']], drone['controller'], state.cars[drone['index']].physics)):
                        edit = True
                  except:
                     pass
            if edit:
               self.set_game_state(state)
            session['tick'] += 1
      else:
         if session['mode'] == 1:
            session['mode'] = 0
            for drone in session['drones']:
               controller = drone['controller']
               controller.boost = False
               controller.handbrake = False
               controller.jump = False
               controller.pitch = 0
               controller.roll = 0
               controller.steer = 0
               controller.throttle = 0
               controller.yaw = 0
      controllers = {}
      for drone in session['drones']:
         if drone['index'] in self.drone_indices:
            controllers[drone['index']] = drone['controller']
      return controllers
   def initialize_hive(self, packet: GameTickPacket) -> None:
      for index in self.drone_indices:
         session['drones'].append({ 'index': index, 'controller': PlayerInput(), 'drone': len(session['drones'])})