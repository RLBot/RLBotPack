import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

SIDE_WALL=4096
# From perspective of default scenario - blue team defending
BLUE_WALL=-5120
ORANGE_WALL=5120

BACK_WALL=BLUE_WALL

def hasattrdeep(obj, *names):
    for name in names:
       if not hasattr(obj, name):
            return False
       obj = getattr(obj, name)
    return True


def add_vector3(vector1, vector2):
    return Vector3(vector1.x + vector2.x, vector1.y + vector2.y, vector1.z + vector2.z)

def vector3_to_list(vector3):
    return [vector3.x, vector3.y, vector3.z]


def get_play_yaw():
    rand1 = np.random.random()
    if rand1 < 1/7:
        play_yaw = -np.pi * 0.25
    elif rand1 < 2/7:
        play_yaw = -np.pi * 0.375
    elif rand1 < 5/7:
        play_yaw = -np.pi * 0.5
    elif rand1 < 6/7:
        play_yaw = -np.pi * 0.625
    elif rand1 < 7/7:
        play_yaw = -np.pi * 0.75
    # 50% parallel/mirrored yaw compared to other team
    if np.random.random() < 0.5:
        play_yaw_mir = play_yaw-np.pi
    else:
        play_yaw_mir = -play_yaw
    return play_yaw, play_yaw_mir

def random_between(min_value, max_value):
    return min_value + np.random.random() * (max_value - min_value)

def get_velocity_from_yaw(yaw, min_velocity, max_velocity):
    # yaw is in radians, use this to get the ratio of x/y velocity
    # X = cos(yaw) 
    # Y = sin(yaw)
    # Z = 0
    velocity_factor = random_between(min_velocity, max_velocity)
    velocity_x = velocity_factor * np.cos(yaw)
    velocity_y = velocity_factor * np.sin(yaw)
    return Vector3(velocity_x, velocity_y, 0)

# Rotation consists of pitch, yaw, roll
# Yaw is on the x/y plane
# Pitch is radians above/below the x/y plane
# Roll is irrelevant
# We want to convert this to a velocity vector
def get_velocity_from_rotation(rotation, min_velocity, max_velocity):
    # Get the yaw from the rotation
    yaw = rotation.yaw
    # Get the pitch from the rotation
    pitch = rotation.pitch
    
    velocity_factor = random_between(min_velocity, max_velocity)
    velocity_x = (velocity_factor * np.cos(yaw)) * np.cos(pitch)
    velocity_y = (velocity_factor * np.sin(yaw)) * np.cos(pitch)
    velocity_z = velocity_factor * np.sin(pitch)
    return Vector3(velocity_x, velocity_y, velocity_z)

def sanity_check_objects(objects):
    '''If any of the objects have been placed outside of the map, move them to the nearest edge of the map'''
    # Back wall is biased toward the negative end, which makes this math a little fucky
    for object in objects:
        if object.physics.location.x < -SIDE_WALL:
            object.physics.location.x = -(SIDE_WALL-100)
        elif object.physics.location.x > SIDE_WALL:
            object.physics.location.x = SIDE_WALL-100
        if object.physics.location.y > -BACK_WALL:
            # Make an exception if in the goal, which is between -/+893 x
            if not (object.physics.location.x > -893 and object.physics.location.x < 893):
                object.physics.location.y = -(BACK_WALL+100)
        elif object.physics.location.y < BACK_WALL:
            # Make an exception if in the goal, which is between -/+893 x
            if not (object.physics.location.x > -893 and object.physics.location.x < 893):
                object.physics.location.y = BACK_WALL+100

        # Also account for corners, which is going to suck
        # Corners start 1152 units in from the side walls and back walls
        # That translates to 4096 - 1152 = 2944 in X axis
        # And 5120 - 1152 = 3968 in Y axis
        # So if the object is outside of both of those, move it inside
        if object.physics.location.x > 2944 and object.physics.location.y > 3968:
            object.physics.location.x = 2944
            object.physics.location.y = 3968
        elif object.physics.location.x < -2944 and object.physics.location.y > 3968:
            object.physics.location.x = -2944
            object.physics.location.y = 3968
        elif object.physics.location.x > 2944 and object.physics.location.y < -3968:
            object.physics.location.x = 2944
            object.physics.location.y = -3968
        elif object.physics.location.x < -2944 and object.physics.location.y < -3968:
            object.physics.location.x = -2944
            object.physics.location.y = -3968
