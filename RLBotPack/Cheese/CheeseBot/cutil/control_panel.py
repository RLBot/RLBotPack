import math

DEBUG_ALWAYS_GO_FOR_SHOT = False #controls whether the bot shoulld always go for the ball. Default False, should be False when not debugging.

MAIN_PULL_BACK_AVERAGE_TEAMMATE_Y_MAX = 2400 #if teammate's average y positions are greater than this value, pull back. Only applies in non 1v1 games, default 2400.
MAIN_MIN_SHOT_SPEED = 1000 #minimum speed of shot bot will go for, unless the ball is going into the net or into the goal. Default 1000.
MAIN_MAX_SHOT_TIME_DEFAULT = 4.5 #how far into the future (in seconds) will the bot look for shots. Default 3.0.
MAIN_MAX_SHOT_TIME_PANIC = 6.0 #how far into the future (in seconds) will the bot look for shots if the ball's going into our net. Default 5.0

MAIN_GET_BOOST_MAX_Y_DIST_IN_FRONT_OF_BALL = 2100 #if a boost pad is further than this in front of the ball when get_nearest_boost is called, it is not considered. Default 1750.
MAIN_GET_BOOST_CONSIDER_BALL_VELOCITY = True

MAIN_SHOULD_GO_FOR_SHOT_PROACTIVITY_BONUS = 0.0 #time added (in seconds) to all teammate intercepts in should_go_for_shot. Higher values makes the bot ignore teammates more. Default 0.0.
MAIN_SHOULD_GO_FOR_SHOT_MIN_ALIGN_FOR_GOOD_INTERCEPT = 0.3 #minimum alignment value for a teammate's intercept to be considered "good". Default 0.3
MAIN_SHOULD_GO_FOR_SHOT_TEAMMATE_DRIVING_TOWARDS_INTERCEPT_ANGLE = math.pi/3 #angle (in radians). If angle between a teammate's intercept vector and their velocity vector is less than this, they're considered to be driving towards the ball. Default math.pi/3 radians, or 60 degrees.

MAIN_GET_BOOST_MIN_VALUE = 36 #if the bot has less boost than this, it considers getting boost (if all other params are true). Default 36.
MAIN_REPOSITION_DISTANCE_DEFAULT = 3000 #how far behind its earliest intercept the bot positions itself by default. Default 1000.
MAIN_REPOSITION_DISTANCE_PULL_BACK = 3000 #how far behind its earliest intercept the bot positions itself when pulling back. Default 1000.

ROUTINES_GOTO_SLOW_DOWN_DISTANCE = 750 #if the goto.slow_down is True, start slowing down when this far from the target. Default 2000.
ROUTINES_GOTO_SLOW_DOWN_MIN_SPEED = 800 #minimum speed the bot is capped to when slowing down. Default 800.
ROUTINES_GOTO_SLOW_DOWN_MAX_SPEED = 1400 #maximum speed the bot is capped to when slowing down. Default 1400.
ROUTINES_GOTO_HANDBRAKE_ANGLE = 1.7 #if the angle between the car's facing and the car to target vector is greater than this, pull the handbrake. Lower values make the bot pull the handbrake more frequently. Default is 1.7.
ROUTINES_GOTO_BOOST_CONTROL_MIN_DISTANCE = 1600 #if the bot is less than this distance away from the target and its speed is lower than ROUTINES_GOTO_BOOST_MAX_SPEED, it will not boost. Default 1600.
ROUTINES_GOTO_BOOST_CONTROL_MAX_SPEED = 1000 #if the bot is moving faster than this and it is less than ROUTINES_GOTO_BOOST_MIN_DISTANCE away from the target, it will not boost. Default 1000.
ROUTINES_GOTO_BOOST_CONTROL_MIN_BOOST_LEVEL = 23 #if the bot has less boost than this, it will not boost. Default 10.
ROUTINES_GOTO_BOOST_CONTROL_MIN_BOOST_ANGLE = math.pi / 4 #if the angle between the bot's facing and the target is greater than this, it will not boost. Default math.pi/4 radians, or 45 degrees.

ROUTINES_GOTO_MIN_FLIP_ANGLE = 0.1 #if the angle between the car to target vector and the bot's facing is greater than this, the bot will not flip. Default 0.1 radians.
ROUTINES_GOTO_MIN_FLIP_VELOCITY = 600 #if the bot's current velocity is less than this, the bot will not flip. Default 600.
ROUTINES_GOTO_MAX_FLIP_VELOCITY = 2150 #if the bot's current velocity is greater than this, the bot will not flip. Default 2150
ROUTINES_GOTO_FLIP_DISTANCE_VELOCITY_RATIO = 2.0 #if distance remaining divided by the bot's current velocity is less than this, the bot will not flip.
ROUTINES_GOTO_FLIP_MAX_BOOST = 40 #if the bot has more boost than this, it will not flip. Default 40. (it should boost instead)

ROUTINES_GOTO_BOOST_SLOW_DOWN_DISTANCE = 1280 #if the bot is closer to the boost pad than this (and there is a larger angle between the pad and the facing than _), the bot will cap its speed. Default 1280.
ROUTINES_GOTO_BOOST_SLOW_DOWN_ANGLE = 1.7 #if the angle between the bot's facing and the boost pad to bot vector is less than this (and the bot is close enough), the bot will slow down. Default 1.7 radians.
ROUTINES_GOTO_BOOST_SLOW_DOWN_MIN_SPEED = 1000
ROUTINES_GOTO_BOOST_SLOW_DOWN_MAX_SPEED = 1400
ROUTINES_GOTO_BOOST_BOOST_CONTROL_ANGLE = 0.3 #the bot will boost if the boost pad is large and the angle between the bot and the target is less than this. Default 0.3 radians.
ROUTINES_GOTO_BOOST_HANDBRAKE_CONTROL_ANGLE = 1.35 #the bot will pull the handbrake if the angle between the pad to bot vector and bot's facing is greater than this. Default 1.35 radians.
ROUTINES_GOTO_BOOST_MIN_FLIP_ANGLE = 0.05 #if the angle between the car to target vector and the bot's facing is greater than this, the bot will not flip. Default 0.1 radians.
ROUTINES_GOTO_BOOST_MIN_FLIP_VELOCITY = 600 #if the bot's current velocity is less than this, the bot will not flip. Default 600.
ROUTINES_GOTO_BOOST_MAX_FLIP_VELOCITY = 2150 #if the bot's current velocity is greater than this, the bot will not flip. Default 2150
ROUTINES_GOTO_BOOST_FLIP_DISTANCE_VELOCITY_RATIO = 2.0 #if distance remaining divided by the bot's current velocity is less than this, the bot will not flip.

ROUTINES_JUMP_SHOT_BOOST_CONTROL_ANGLE = 0.75 #default 0.3
ROUTINES_JUMP_SHOT_HANDBRAKE_CONTROL_ANGLE = 1.2


CTOOLS_DETERMINE_SHOT_MIN_SHOT_ALIGNMENT_DEFAULT = 0.05 #minimum alignment for a shot to be considered under normal circumstances (i.e. we aren't firing at an anti_target). Default 0.15.
