import matplotlib.pyplot as plt
from scenario import Scenario, OffensiveMode, DefensiveMode

# You can use this __name__ == '__main__' thing to ensure that the script doesn't start accidentally if you
# merely reference its module from somewhere
if __name__ == "__main__":
    # scenario = Scenario(GameMode.SHADOW)
    scenario = Scenario(OffensiveMode.PASS, DefensiveMode.CORNER)
    scenario.Draw()
    scenario.Mirror()
    scenario.Draw()
    plt.show()
