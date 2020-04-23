from pathlib import Path
from rlbot.agents.hivemind.drone_agent import DroneAgent


class BotimusDroneAgent(DroneAgent):
    hive_path = str(Path(__file__).parent / 'hivemind.py')
    hive_key = 'bumblebee-hive'
    hive_name = 'Beehive'
