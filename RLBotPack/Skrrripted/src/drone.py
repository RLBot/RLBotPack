from pathlib import Path
from rlbot.agents.hivemind.drone_agent import DroneAgent

class Drone(DroneAgent):
   hive_key = "skrrripted"
   hive_name = "Skrrripted"
   hive_path = str(Path(__file__).parent / "hive.py")
