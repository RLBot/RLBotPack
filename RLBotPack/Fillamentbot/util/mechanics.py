from rlbot.agents.base_agent import SimpleControllerState

from util.sequence import Sequence, ControlStep

"""Sequences"""
def begin_front_flip(packet):
    #front flip
    active_sequence = Sequence([
        ControlStep(duration=0.14, controls=SimpleControllerState(jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)
    
def begin_left_flip(packet):
    #flip left
    active_sequence = Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, roll=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def begin_dleft_flip(packet):
    #flip diagonal left
    active_sequence = Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, roll=-1,pitch=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)
    
def begin_right_flip(packet):
    #flip right
    active_sequence = Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, roll=1)),
        ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])
        
    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def begin_dright_flip(packet):
    #flip diagonal right
    active_sequence = Sequence([
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, roll=1,pitch=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])
        
    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def right_diagonal(packet):
    #the kickoff
    active_sequence=Sequence([
        ControlStep(duration=0.45, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.10, controls=SimpleControllerState(boost=True,throttle=1,steer=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(boost=True,throttle=1,jump=True,pitch=-1,roll=-1)),
        ControlStep(duration=0.4, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.49, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(throttle=1,pitch=1)),
        ControlStep(duration=0.09, controls=SimpleControllerState(jump=True,throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False,throttle=1)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True,throttle=1,pitch=-1,roll=1)),
        ControlStep(duration=0.8, controls=SimpleControllerState())
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def left_diagonal(packet):
    #the kickoff
    active_sequence=Sequence([
        ControlStep(duration=0.45, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.10, controls=SimpleControllerState(boost=True,throttle=1,steer=-1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(boost=True,throttle=1,jump=True,pitch=-1,roll=1)),
        ControlStep(duration=0.4, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.49, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(throttle=1,pitch=1)),
        ControlStep(duration=0.09, controls=SimpleControllerState(jump=True,throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False,throttle=1)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True,throttle=1,pitch=-1,roll=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState())
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def long_right(packet):
    #the kickoff
    active_sequence=Sequence([
        ControlStep(duration=0.25, controls=SimpleControllerState(boost=True,throttle=1,steer=-0.6)),
        ControlStep(duration=0.45, controls=SimpleControllerState(boost=True,throttle=1,steer=0.1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=True)),
        ControlStep(duration=0.02, controls=SimpleControllerState(boost=True,throttle=1,jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(boost=True,throttle=1,jump=True,pitch=-1,roll=1)),
        ControlStep(duration=0.5, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.43, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.01, controls=SimpleControllerState(throttle=1,pitch=1)),
        ControlStep(duration=0.09, controls=SimpleControllerState(jump=True,throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False,throttle=1)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True,throttle=1,pitch=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState())
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def long_left(packet):
    #the kickoff
    active_sequence=Sequence([
        ControlStep(duration=0.25, controls=SimpleControllerState(boost=True,throttle=1,steer=0.6)),
        ControlStep(duration=0.45, controls=SimpleControllerState(boost=True,throttle=1,steer=-0.1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=True)),
        ControlStep(duration=0.02, controls=SimpleControllerState(boost=True,throttle=1,jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(boost=True,throttle=1,jump=True,pitch=-1,roll=-1)),
        ControlStep(duration=0.5, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.43, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.01, controls=SimpleControllerState(throttle=1,pitch=1)),
        ControlStep(duration=0.09, controls=SimpleControllerState(jump=True,throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False,throttle=1)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True,throttle=1,pitch=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState())
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def back_kick(packet):
    #the kickoff
    active_sequence=Sequence([
        ControlStep(duration=0.65, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.20, controls=SimpleControllerState(boost=True,throttle=1,steer=0.5)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=True)),
        ControlStep(duration=0.05, controls=SimpleControllerState(boost=True,throttle=1,jump=False)),
        ControlStep(duration=0.2, controls=SimpleControllerState(boost=True,throttle=1,jump=True,pitch=-0.5,roll=-1)),
        ControlStep(duration=0.7, controls=SimpleControllerState(boost=True,throttle=1)),
        ControlStep(duration=0.15, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.15, controls=SimpleControllerState(throttle=1)),
        ControlStep(duration=0.09, controls=SimpleControllerState(jump=True,throttle=1)),
        ControlStep(duration=0.05, controls=SimpleControllerState(jump=False,throttle=1)),
        ControlStep(duration=0.2, controls=SimpleControllerState(jump=True,throttle=1,pitch=-0.5,roll=-1)),
        ControlStep(duration=0.8, controls=SimpleControllerState())
    ])

    # Return the controls associated with the beginning of the sequence so we can start right away.
    return active_sequence, active_sequence.tick(packet)

def kickoff_idle(packet):
    active_sequence=Sequence([ControlStep(duration=1,controls=SimpleControllerState(throttle=0.2))])

    return active_sequence, active_sequence.tick(packet)

def wavedash(packet):
    active_sequence=Sequence([
        ControlStep(duration=0.02,controls=SimpleControllerState(throttle=1,jump=True)),
        ControlStep(duration=0.95,controls=SimpleControllerState(throttle=1,jump=False,pitch=0.2)),
        ControlStep(duration=0.02,controls=SimpleControllerState(throttle=1,jump=True,pitch=-1)),
        ControlStep(duration=0.05,controls=SimpleControllerState(throttle=1)),
    ])

    return active_sequence, active_sequence.tick(packet)

def doublejump(packet,hold_time:float=0.02):
    active_sequence=Sequence([
        ControlStep(duration=0.2,controls=SimpleControllerState(throttle=1,jump=True)),
        ControlStep(duration=0.02,controls=SimpleControllerState(throttle=1,jump=False)),
        ControlStep(duration=hold_time,controls=SimpleControllerState(throttle=1,jump=True))
    ])

    return active_sequence, active_sequence.tick(packet)

def long_jump(packet,hold_time:float=0.2):
    active_sequence=Sequence([
        ControlStep(duration=hold_time,controls=SimpleControllerState(throttle=1,jump=True))    
    ])

    return active_sequence, active_sequence.tick(packet)