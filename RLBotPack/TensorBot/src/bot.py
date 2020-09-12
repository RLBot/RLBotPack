#https://github.com/RLBot/RLBotPythonExample/wiki/Input-and-Output-Data
import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tensorflow.python.client import device_lib
import tensorflow as tf
import numpy

import sys
import time

#attempt to limit GPU usages
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
  try:
    for gpu in gpus:
      tf.config.experimental.set_memory_growth(gpu, True)
  except RuntimeError as e:
    print("Whelp, RUNTIME ERROR :(")
    print(e)
    


class MyBot(BaseAgent):

    def initialize_agent(self):
    
        # This runs once before the bot starts up
        self.controller_state = SimpleControllerState()
        if(self.team == 0): #blue
            modelDir = "src\\blueModel"
        elif(self.team == 1): #orange
            modelDir = "src\\orangeModel"
            
        self.model = tf.keras.models.load_model(modelDir) 
        print("\n\n\n\n\n****************FINISHED LOADED\n\n\n\n\n")


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        #************************************************
		#put these 24 normalized state items into tensor and feed into network
        stateList = []
        phys = packet.game_cars[self.index].physics
        
        stateList.append(self.team)       
    
        stateList.append(phys.location.x / 4096.0)
        stateList.append(phys.location.y / 5120.0)
        stateList.append(phys.location.z / 2044.0)
        
        stateList.append(phys.rotation.pitch / (math.pi/2.0))
        stateList.append(phys.rotation.yaw / math.pi)
        stateList.append(phys.rotation.roll / math.pi)
        
        stateList.append(phys.velocity.x / 2300.0)
        stateList.append(phys.velocity.y / 2300.0)
        stateList.append(phys.velocity.z / 2300.0)
        
        stateList.append(phys.angular_velocity.x / 5.5)
        stateList.append(phys.angular_velocity.y / 5.5)
        stateList.append(phys.angular_velocity.z / 5.5)
        		
        stateList.append(packet.game_cars[self.index].has_wheel_contact)
        stateList.append(packet.game_cars[self.index].is_super_sonic)
        stateList.append(packet.game_cars[self.index].jumped)
        stateList.append(packet.game_cars[self.index].double_jumped)
        stateList.append(packet.game_cars[self.index].boost / 100.0)        

        stateList.append(packet.game_ball.physics.location.x / 4096.0)
        stateList.append(packet.game_ball.physics.location.y / 5120.0)
        stateList.append(packet.game_ball.physics.location.z / 2044.0)
        
        stateList.append(packet.game_ball.physics.velocity.x / 6000.0)
        stateList.append(packet.game_ball.physics.velocity.y / 6000.0)
        stateList.append(packet.game_ball.physics.velocity.z / 6000.0)
             
        stateTensor = numpy.array(stateList)
        stateTensor = stateTensor[numpy.newaxis, :]
        
        #************************************************
		#actions are here. establish what they are and set controller to it
        steerTensor, eulerTensor, jumpTensor, boostTensor = self.model.predict(stateTensor, verbose=0)
        
        self.controller_state.throttle = steerTensor[0][0]
        self.controller_state.steer = steerTensor[0][1]
        
        self.controller_state.pitch = eulerTensor[0][0]
        self.controller_state.yaw = eulerTensor[0][1]
        self.controller_state.roll = eulerTensor[0][2]
        

        if(boostTensor[0][0] > .5):
            self.controller_state.boost = True
        else:
            self.controller_state.boost = False
        
        if(jumpTensor[0][0] > .5):
            self.controller_state.jump = True
        else:
            self.controller_state.jump = False

        return self.controller_state

