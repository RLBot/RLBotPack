from typing import Optional

from rlbot.matchcomms.client import MatchcommsClient
from rlbot.training.training import Grade, Pass, Fail
from rlbottraining.grading.grader import Grader
from rlbottraining.grading.training_tick_packet import TrainingTickPacket


class MatchcommsGrader(Grader):
    matchcomms: MatchcommsClient = None
    initialized = False

    def on_tick(self, tick: TrainingTickPacket) -> Optional[Grade]:
        assert self.matchcomms
        incoming = self.matchcomms.incoming_broadcast
        outgoing = self.matchcomms.outgoing_broadcast

        while not incoming.empty():
            message = incoming.get_nowait()
            if message == "initialized":
                self.initialized = True
            elif message == "pass" and self.initialized:
                return Pass()
            elif message == "fail" and self.initialized:
                return Fail()

        if not self.initialized:
            outgoing.put_nowait("start")

        return None
