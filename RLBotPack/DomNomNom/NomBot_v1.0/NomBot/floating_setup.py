from utils import main, sanitize_output_vector, EasyGameState
if __name__ == '__main__':
    main()  # blocking

import bakkes
import student_agents
import time
from random import random

# Calling bakkesmod too often may cause a crash.
# Therefore ratelimit it by dropping some calls.
MIN_DELAY_BETWEEN_BAKKES_CALLS = 3 * 1/60.
last_bakkes_call = {}  # player_index -> time of last call
def should_call_bakkes(player_index):
    # Note: this function mutates external state: last_bakkes_call.
    global last_bakkes_call
    now = time.clock()
    if now - last_bakkes_call.get(player_index, 0) > MIN_DELAY_BETWEEN_BAKKES_CALLS:
        last_bakkes_call[player_index] = now
        return True
    return False

def make_player_float(player_index, location):
    # Call this every frame to reset the players position
    if not should_call_bakkes(player_index):
        return
    height = 250 + 200*player_index
    # Hopefully this dependence onc bakkesmod will be removed with the new RLBot api
    bakkes.rcon(';'.join([
        'player {} location {} {} {}'.format(player_index, *location),
        'player {} velocity -0 0 10'.format(player_index),
    ]))

def make_ball_float(location=(200, 0, 500)):
    if not should_call_bakkes('BALL'):
        return
    bakkes.rcon(';'.join([
        'ball location {} {} {}'.format(*location),
        'ball velocity 0 0 10',
    ]))


last_rotation_modification = {}  # player_index -> time of last change of rotation/angular vel
def set_random_rotation_and_angular_vel_periodically(player_index, period=2.0):
    now = time.clock()
    global last_rotation_modification
    if now - last_rotation_modification.get(player_index, 0) > period:
        last_rotation_modification[player_index] = now
        set_random_rotation_and_angular_vel(player_index)

def set_random_rotation_and_angular_vel(player_index):
    bakkes.rcon(';'.join([
        'player {} rotation {} {} {}'.format(       player_index, (100000 * (random() - 0.5)), 100000 * (random() - 0.5), 100000 * (random() - 0.5)),
        'player {} angularvelocity {} {} {}'.format(player_index, (    10 * (random() - 0.5)),     10 * (random() - 0.5),     10 * (random() - 0.5)),
    ]))

# Note: This is similar to utils.graduate_student_into_agent(AirStabilizerTowardsBall)
#       but we want the index to call bakkesmod with it.
class Agent:
    def __init__(self, name, team, index):
        self.name = name
        self.team = team
        self.index = index
        self.student = student_agents.AirStabilizerTowardsBall()
    def get_output_vector(self, game_tick_packet):
        player_float_location = [-222, 0, 200 * (2 + self.index)]
        make_ball_float()
        make_player_float(self.index, player_float_location)
        set_random_rotation_and_angular_vel_periodically(self.index, period=1.5)

        s = EasyGameState(game_tick_packet, self.team, self.index)
        return sanitize_output_vector(self.student.get_output_vector(s))
