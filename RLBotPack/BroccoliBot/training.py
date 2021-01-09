from pathlib import Path

from rlbottraining.common_exercises.wall_play import BallRollingTowardsWall
from rlbot.matchconfig.match_config import PlayerConfig, Team

def make_default_playlist():
    exercises = [
        BallRollingTowardsWall('Test Training!'),
    ]
    for exercise in exercises:
        exercise.match_config.player_configs = [
            PlayerConfig.bot_config(
                Path(__file__).absolute().parent / 'BroccoliBot.cfg',
                Team.BLUE)
        ]

    return exercises