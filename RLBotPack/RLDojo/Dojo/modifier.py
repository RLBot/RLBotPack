import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

#######################################
### Custom Sandbox Object Modifiers ###
#######################################

def modify_object_x(object_to_modify, x):
    object_to_modify.physics.location.x += x
    utils.sanity_check_objects([object_to_modify])
    
def modify_object_y(object_to_modify, y):
    object_to_modify.physics.location.y += y
    utils.sanity_check_objects([object_to_modify])
    
def modify_object_z(object_to_modify, z):
    object_to_modify.physics.location.z += z
    utils.sanity_check_objects([object_to_modify])

def modify_pitch(object_to_modify, increase):
    if utils.hasattrdeep(object_to_modify, 'physics', 'rotation', 'pitch'):
        # Pitch should be grid-snapped to 1/16 of a full rotation to ensure we can always get perfect vertical or horizontal pitch
        # This function will increase the pitch by 1/16 of a full rotation and lock it to the nearest 1/16 of a full rotation
        # Pitch is expressed in radians
        # 1/16 of a full rotation is 1/8 * pi radians
        # We want to increase the pitch by 1/8 * pi radians and lock it to the nearest 1/8 * pi radians
        current_pitch = object_to_modify.physics.rotation.pitch
        
        # Round to the nearest 1/8 * pi radians
        new_pitch = round(current_pitch / (0.125 * np.pi)) * (0.125 * np.pi)
        if increase:
            new_pitch += (0.125 * np.pi)
        else:
            new_pitch -= (0.125 * np.pi)
        
        # Modulo over 2 * pi to ensure we don't go over a full rotation
        new_pitch = new_pitch % (2 * np.pi)
        
        # Set the new pitch
        object_to_modify.physics.rotation.pitch = new_pitch
        
        # Update the velocity to match the new pitch
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(object_to_modify.physics.rotation, 1000, 2000)
    else:
        # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
        yaw = np.arctan2(object_to_modify.physics.velocity.y, object_to_modify.physics.velocity.x)
        pitch = np.arctan2(object_to_modify.physics.velocity.z, np.sqrt(object_to_modify.physics.velocity.x**2 + object_to_modify.physics.velocity.y**2))

        if increase:
            pitch += (0.125 * np.pi)
        else:
            pitch -= (0.125 * np.pi)

        # Convert back to velocity components
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)
    

def modify_yaw(object_to_modify, increase):
    if utils.hasattrdeep(object_to_modify, 'physics', 'rotation', 'yaw'):
        # Yaw should be grid-snapped to 1/16 of a full rotation to ensure we can always get perfect horizontal yaw
        # This function will increase the yaw by 1/16 of a full rotation and lock it to the nearest 1/16 of a full rotation
        # Yaw is expressed in radians
        # 1/16 of a full rotation is 1/8 * pi radians
        # We want to increase the yaw by 1/8 * pi radians and lock it to the nearest 1/8 * pi radians
        current_yaw = object_to_modify.physics.rotation.yaw
        new_yaw = round(current_yaw / (0.125 * np.pi)) * (0.125 * np.pi)
        if increase:
            new_yaw += (0.125 * np.pi)
        else:
            new_yaw -= (0.125 * np.pi)
        
        # Modulo over 2 * pi to ensure we don't go over a full rotation
        new_yaw = new_yaw % (2 * np.pi)
        
        object_to_modify.physics.rotation.yaw = new_yaw
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(object_to_modify.physics.rotation, 1000, 2000)
    else:
        # Ball doesn't have rotation, use the velocity components to determine and modify trajectory
        yaw = np.arctan2(object_to_modify.physics.velocity.y, object_to_modify.physics.velocity.x)
        pitch = np.arctan2(object_to_modify.physics.velocity.z, np.sqrt(object_to_modify.physics.velocity.x**2 + object_to_modify.physics.velocity.y**2))

        if increase:
            yaw += (0.125 * np.pi)
        else:
            yaw -= (0.125 * np.pi)

        # Convert back to velocity components
        object_to_modify.physics.velocity = utils.get_velocity_from_rotation(Rotator(yaw=yaw, pitch=pitch, roll=0), 1000, 2000)

def modify_roll(object_to_modify, increase):
    if utils.hasattrdeep(object_to_modify, 'physics', 'rotation', 'roll'):
        # Roll should be grid-snapped to 1/16 of a full rotation to ensure we can always get perfect horizontal roll
        # This function will increase the roll by 1/16 of a full rotation and lock it to the nearest 1/16 of a full rotation
        # Roll is expressed in radians
        # 1/16 of a full rotation is 1/8 * pi radians
        # We want to increase the roll by 1/8 * pi radians and lock it to the nearest 1/8 * pi radians
        current_roll = object_to_modify.physics.rotation.roll
        new_roll = round(current_roll / (0.125 * np.pi)) * (0.125 * np.pi)
        if increase:
            new_roll += (0.125 * np.pi)
        else:
            new_roll -= (0.125 * np.pi)
        
        object_to_modify.physics.rotation.roll = new_roll

def modify_velocity(object_to_modify, velocity_percentage_delta):
    # Velocity is a 3-dimensional vector, scale each component by the same percentage
    x = object_to_modify.physics.velocity.x
    y = object_to_modify.physics.velocity.y
    z = object_to_modify.physics.velocity.z

    x += x * velocity_percentage_delta
    y += y * velocity_percentage_delta
    z += z * velocity_percentage_delta

    object_to_modify.physics.velocity = Vector3(x, y, z)

def modify_boost(object_to_modify, increase):
    if utils.hasattrdeep(object_to_modify, 'boost_amount'):
        if increase:
            object_to_modify.boost_amount += 1
        else:
            object_to_modify.boost_amount -= 1
