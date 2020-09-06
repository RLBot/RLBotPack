from pathlib import Path
from rlbot.agents.hivemind.drone_agent import DroneAgent


class RocketNoodlesDroneAgent(DroneAgent):
    """"Drone agent class used by the PythonHivemind class."""

    hive_path = str(Path(__file__).parent / 'main.py')
    hive_key = 'noodle-hive'
    hive_name = 'NoodleHive'
