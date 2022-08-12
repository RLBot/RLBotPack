from stable_baselines3 import PPO
import pathlib
from action.discrete_act import DiscreteAction


class Agent_Omus:
    def __init__(self):
        _path = pathlib.Path(__file__).parent.resolve()
        custom_objects = {
            "lr_schedule": 5e-5,
            "clip_range": .02,
            "n_envs": 1,
        }
        
        self.omus_50 = PPO.load(str(_path) + '/Omus_50_model.zip', device='cpu', custom_objects=custom_objects)
        self.omus_ko = PPO.load(str(_path) + '/Omus_KO_model.zip', device='cpu', custom_objects=custom_objects)
        self.parser = DiscreteAction()


    def act(self, state, gamemode):
        if gamemode =='fiftyfifty':
            action = self.omus_50.predict(state, deterministic=True)
        elif gamemode =='kickoff':
            action = self.omus_ko.predict(state, deterministic=True)
        return action[0]

if __name__ == "__main__":
    print("You're doing it wrong.")