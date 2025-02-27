import numpy as np
from config import *

from collections import deque
from logging import DEBUG, StreamHandler, Formatter
from pathlib import Path
from rlbot.botmanager.helper_process_request import HelperProcessRequest
from rlbot.utils.logging_utils import get_logger, FORMAT
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
        self.logger = get_logger("nexto-ez")
        if DEBUG_RANDOM_TICKS:
            ch = StreamHandler()
            ch.setFormatter(Formatter(FORMAT))
            ch.setLevel(DEBUG)
            self.logger.addHandler(ch)

        self.shared_memory = shared_memory.SharedMemory(create=True, size=1)
        # buf[0] is a value from 0 - 255 (max random=255, max nexto=0)
        self.shared_memory.buf[0] = int(round((100-STRENGTH) * 2.55))
        self.random_debug_log_rate = STRENGTH_LOG_RATE
        self.random_debug_tick_count = 0
        self.random_debug_tick_history = deque(maxlen=TICK_HISTORY_LENGTH)

    def update_controls(self, packet: GameTickPacket):
        self.random_debug_tick_count += 1
        if self.random_debug_tick_count >= self.random_debug_log_rate:
            self.random_debug_tick_count = 0
            sum_, len_ = sum(self.random_debug_tick_history), len(self.random_debug_tick_history)
            self.logger.debug(
                "bot#:%d %d of the last %d (%.2f%%) ticks were random compared to configured value of %d%%",
                self.index, sum_, len_, sum_/len_ * 100, self.shared_memory.buf[0]/2.55
            )
        if np.random.random() * 255 > self.shared_memory.buf[0]:
            super().update_controls(packet)
            self.random_debug_tick_history.append(0) # not random this tick
        else:
            # Randomize inputs. Don't influence long term inputs such as jump.
            self.controls.throttle = np.random.random()
            self.controls.steer = np.random.random() * 2 - 1
            self.controls.pitch = np.random.random() * 2 - 1
            self.controls.yaw = np.random.random() * 2 - 1
            self.controls.roll = np.random.random() * 2 - 1
            self.random_debug_tick_history.append(1) # is random this tick

    def get_helper_process_request(self):
        if SHOW_GUI:
            return HelperProcessRequest(str(Path(__file__).parent / "gui.py"), "nexto-ez", options={
                "shared_memory_name": self.shared_memory.name,
            })
