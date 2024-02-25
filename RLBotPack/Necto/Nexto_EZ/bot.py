import numpy as np
from config import *

from pathlib import Path
from rlbot.botmanager.helper_process_request import HelperProcessRequest
from rlbot.utils.structures.game_data_struct import GameTickPacket

from multiprocessing import shared_memory
import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
nexto_dir = parent

sys.path.append(nexto_dir)
sys.path.append(nexto_dir + '/Nexto')
from Nexto.bot import Nexto


class Nexto_EZ(Nexto):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        self.shared_memory = shared_memory.SharedMemory(create=True, size=1)
        self.shared_memory.buf[0] = int(round(STRENGTH * 2.55))

    def update_controls(self, packet: GameTickPacket):
        if np.random.random() * 255 > self.shared_memory.buf[0]:
            super().update_controls(packet)
        else:
            # Randomize inputs. Don't influence long term inputs such as jump.
            self.controls.throttle = np.random.random()
            self.controls.steer = np.random.random() * 2 - 1
            self.controls.pitch = np.random.random() * 2 - 1
            self.controls.yaw = np.random.random() * 2 - 1
            self.controls.roll = np.random.random() * 2 - 1

    def get_helper_process_request(self):
        if SHOW_GUI:
            return HelperProcessRequest(str(Path(__file__).parent / "gui.py"), "nexto-ez", options={
                "shared_memory_name": self.shared_memory.name,
            })
