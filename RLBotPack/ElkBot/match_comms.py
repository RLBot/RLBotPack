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
                msg = self.agent.matchcomms.incoming_broadcast.get()
                if msg.get('tmcp_version') != None:
                    if msg.get("team") == self.agent.team and msg.get("index") != self.agent.index:
                        self.agent.handle_tmcp_packet(msg)
                else:
                    self.agent.handle_match_comm(msg)
            except Exception:
                print_exc()
