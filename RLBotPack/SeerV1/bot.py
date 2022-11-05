from SeerPPO import SeerBot, Agent
from SeerPPO.V1 import SeerActionV1
from SeerPPO.V1 import SeerObsV1
from SeerPPO.V1 import SeerNetworkV1


class SeerV1(SeerBot):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        self.obs_builder = SeerObsV1()
        self.act_parser = SeerActionV1()
        self.agent = Agent("./SeerV1/SeerV1_30000.pt", SeerNetworkV1())
        self.name = "SeerV1"
