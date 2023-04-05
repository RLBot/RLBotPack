from SeerPPO.V1 import SeerV1Template


class SeerV1(SeerV1Template):
    def __init__(self, name, team, index):
        super().__init__(name, team, index, "./SeerV1/SeerV1_30000.pt")
