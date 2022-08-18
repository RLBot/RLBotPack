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
    print("Whelp TensorFlow GPU RUNTIME ERROR :(")
    print(e)
    


class MyBot(BaseAgent):

    def initialize_agent(self):
    
        # This runs once before the bot starts up
        self.controller_state = SimpleControllerState()
        if(self.team == 0): #blue
            modelDir = "src/blueModel"
        elif(self.team == 1): #orange
            modelDir = "src/orangeModel"
            
        self.model = tf.keras.models.load_model(modelDir) 
        self.isKickoff = True  

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:    
        if(packet.game_info.is_round_active == False):
            #reset back to kickoff rules
            self.isKickoff = True  
    
        #kickoff
        if((self.isKickoff == True and packet.game_info.is_round_active == True) or packet.game_ball.latest_touch.time_seconds == 0):       
            self.controller_state.throttle = 1
            self.controller_state.boost = True
            
            yP = packet.game_cars[self.index].physics.location.y
            xP = packet.game_cars[self.index].physics.location.x 
            
            ballY = packet.game_ball.physics.location.y
            ballX = packet.game_ball.physics.location.x
            
            carAngle = math.degrees(math.atan2(yP - ballY,xP - ballX))
            carAngle = (carAngle + 360) % 360
            
            ori = math.degrees(packet.game_cars[self.index].physics.rotation.yaw)
            ori = (((ori + 360) % 360) + 180) % 360
                 
            threshold = 4.0
            angleDiff = ori - carAngle
            if(abs(angleDiff) > threshold):            
                if(angleDiff < 1):
                    self.controller_state.steer = 0.3   
                elif(angleDiff > 1):
                   self.controller_state.steer = -0.3  
            
            diff = abs(packet.game_info.seconds_elapsed - packet.game_ball.latest_touch.time_seconds)            
            if(diff < 1):
                self.isKickoff = False
            
        else: #NN time!
        
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
            
            steerTensor, eulerTensor, jumpTensor, boostTensor = self.model(stateTensor)
            
            
            self.controller_state.throttle = tf.clip_by_value(steerTensor[0][0], -1, 1)
            self.controller_state.steer = tf.clip_by_value(steerTensor[0][1], -1, 1)
            
            self.controller_state.pitch = tf.clip_by_value(eulerTensor[0][0], -1, 1)
            self.controller_state.yaw = tf.clip_by_value(eulerTensor[0][1], -1, 1)
            self.controller_state.roll = tf.clip_by_value(eulerTensor[0][2], -1, 1)
            

            if(boostTensor[0][0] > .5):
                self.controller_state.boost = True
            else:
                self.controller_state.boost = False
            
            if(jumpTensor[0][0] > .5):
                self.controller_state.jump = True
            else:
                self.controller_state.jump = False

        return self.controller_state

