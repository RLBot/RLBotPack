# Invisibot

Invisibot is Rocket League bot that has invisiblity powers. 

It is powered by Nexto and RLUtilities.

# How does it work?

The bot is hidden when the ball or opponent are not near.

The game packet is manipulated to convince the "core" bot
that the car is still on the field.
Then controls are used to simulate where the car
would move to. This is repeated till the car is close
and can reappear.

RLUtilities is used for simulating
jumps/dodges/aerials while simple ground logic is
used for simulating driving and turning.

`invisibot.py` contains the core logic. It can be easily used to
give other bots invisibility powers. Here are the requirements:

- The bot shoudl be implemented in Python
- The bot should only use `get_output` as the source of game packet
- The bot currently can't use rlutilities (this should be fixed in the future)

# Status

The bot is working pretty well. Sometimes the simulation is not perfect and it results
in the bot not being in the place that the "controlling" bot expects. This results in
invisibot performing worse than the "controlling" bot. Since the controlling bot is
Nexto though, a bad Nexto still performs pretty well.


