from rlbot.agents.base_script import BaseScript
from scipy.special import comb


class SigBarScript(BaseScript):
    def __init__(self):
        print("Starting up significance bar!")
        super().__init__("Significance Bar")

    def run(self):
        print("Running significance bar!")
        old_score = 0
        # run a loop
        while True:
            # Get the packet
            packet = self.wait_game_tick_packet()

            # check if a goal has been scored
            if packet.teams[0].score + packet.teams[1].score == old_score:
                continue
            print("Goal scored! Let's update the bar!")
            old_score = packet.teams[0].score + packet.teams[1].score

            # Calculate the value
            blue_p = sum((
                comb(old_score, r) * .5**old_score for
                r in range(packet.teams[0].score, old_score + 1)
            ))

            blue_section = 600 - int(60 * blue_p) * 10

            orange_p = sum((
                comb(old_score, r) * .5**old_score for
                r in range(packet.teams[1].score, old_score + 1)
            ))

            orange_section = int(60 * orange_p) * 10

            # Because of the geq, the middle is counted twice. Draw white over that point.
            renderer = self.game_interface.renderer
            renderer.begin_rendering()
            renderer.draw_string_2d(15, 6, 1, 1, f"{min(blue_p, orange_p):.4f}", renderer.white())
            renderer.draw_rect_2d(30, 30, 5, blue_section, True, renderer.blue())
            renderer.draw_rect_2d(30, 30 + blue_section, 5, orange_section - blue_section, True, renderer.white())
            renderer.draw_rect_2d(30, 30 + orange_section, 5, 600 - orange_section, True, renderer.orange())
            renderer.end_rendering()

if __name__ == "__main__":
    script = SigBarScript()
    script.run()
