from threading import Thread
from traceback import print_exc


class MatchComms(Thread):
    def __init__(self, agent):
        super().__init__(daemon=True)
        self.agent = agent
        self.online = 1

    def stop(self):
        self.online = 0

    def run(self):
        while self.online:
            try:
                self.agent.handle_match_comm(self.agent.matchcomms.incoming_broadcast.get())
            except Exception:
                print_exc()
