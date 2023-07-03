from rlbot.agents.base_script import BaseScript
from rlbot.utils.structures.game_data_struct import GameTickPacket
import matplotlib.pyplot as plt

class ScoreLogger(BaseScript):
    def __init__(self):
        super().__init__("Score Logger")
        self.graph_x = [0]
        self.graph_blue = [0]
        self.graph_orange = [0]
        self.goal_target = 300

    def main(self):
        while True:
            packet: GameTickPacket = self.wait_game_tick_packet()
            if (not packet.game_info.is_match_ended or packet.teams[0].score + packet.teams[1].score == 0) and packet.teams[0].score + packet.teams[1].score < self.goal_target:
                if packet.teams[0].score + packet.teams[1].score > self.graph_blue[-1] + self.graph_orange[-1]:
                    self.graph_x.append(packet.teams[0].score + packet.teams[1].score)
                    self.graph_blue.append(packet.teams[0].score)
                    self.graph_orange.append(packet.teams[1].score)
            else:
                plt.plot(self.graph_x, self.graph_blue)
                plt.plot(self.graph_x, self.graph_orange)
                bot_count = [0, 0]
                txt = ["", ""]
                for i in range(len(packet.game_cars)):
                    if packet.game_cars[i].name != "":
                        bot_count[packet.game_cars[i].team] += 1
                temp_count = [0, 0]
                for i in range(len(packet.game_cars)):
                    if packet.game_cars[i].name != "":
                        temp_count[packet.game_cars[i].team] += 1
                        if txt[packet.game_cars[i].team] != "":
                            if temp_count[packet.game_cars[i].team] == bot_count[packet.game_cars[i].team]:
                                txt[packet.game_cars[i].team] += " & "
                            else:
                                txt[packet.game_cars[i].team] += ", "
                        txt[packet.game_cars[i].team] += packet.game_cars[i].name
                plt.title("Team scores (" + str(bot_count[0]) + "v" + str(bot_count[1]) + ": " + txt[0] + " vs " + txt[1] + ")")
                plt.xlabel("Total score")
                plt.ylabel("Team score")
                plt.show()

if __name__ == "__main__":
    score_logger = ScoreLogger()
    score_logger.main()
