# RocketNoodles
RocketNoodles is the rocket league bot designed and built by [Serpentine](serpentinai.nl). 

## Quick Start
The easiest way to start a python bot is demonstrated here!
https://youtu.be/YJ69QZ-EX7k

It shows you how to:
- Install the RLBot GUI
- Use it to create a new bot

The original repository can be found at 
[the python rlbot repository](https://github.com/RLBot/RLBotPythonExample) on github.

### Changing the bot

- Bot behavior is controlled by `src/main.py`
- Bot appearance is controlled by `src/appearance.cfg`

See https://github.com/RLBot/RLBotPythonExample/wiki for documentation and tutorials.

## Repository Structure
```
.
|-- src             # Contains main.py to run bot                     
|   |-- gosling     # Library for agent behaviour and control
|   |-- physics     # Models and predictions of ingame physics
|   |-- scenario    # Ingame test scenarios
|   |-- settings    # Agent configuration files loaded on bot startup
|   |-- strategy    # System for agent strategy, coordination and tactics
|   |-- world       # World model, agent representation of the game
|
|-- logger          # Tools and utilities
```
Some of these directories are explained in more detail below. 

### Gosling
[GoslingUtils](https://github.com/ddthj/GoslingUtils) is a library that executes agent behaviour
and provides basic controllers for doing so. **We rely on Gosling in strategy but are 
working to phase out the library in the future.** It will allow us greater flexibility
in the design of our bot and a neater repository.

### Strategy
Strategic reasoning and coordination is done here. The system consists of three parts: 
Coaches, Captains and Players. They do the following:
- _Coaches_: Highest level in strategy. Determine which strategy will be executed by the captain.
Examples could be: Play offensively, defensively, use trick shots or add keeper to offense.
- _Captains_: Coordinate individual agents. The captain assigns a task to each active agent. 
- _Players_: Behaviour of an individual agents. 