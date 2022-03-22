import random
from time import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

from playsound import playsound

from settings import MIN_SOUND_INTERVAL, PLAY_SOUNDS


@dataclass
class TrailHitSound:
    file: Path
    strength_min: float
    strength_max: float


class SoundPlayer:
    def __init__(self):
        path = Path(__file__).parent / "sounds"
        self.trail_ball_hit_sounds = [
            TrailHitSound(path / "electro hum.wav", 100, 400),
            TrailHitSound(path / "electro hum 2.wav", 100, 400),
            TrailHitSound(path / "electro hum 3.wav", 300, 600),
            TrailHitSound(path / "electro bounce light.wav", 500, 900),
            TrailHitSound(path / "electro bounce light 2.wav", 400, 800),
            TrailHitSound(path / "electro bounce medium.wav", 700, 1600),
            TrailHitSound(path / "electro bounce heavy.wav", 1600, 3000),
        ]
        self.trail_car_hit_sounds = [
            TrailHitSound(path / "electro hum.wav", 100, 400),
            TrailHitSound(path / "electro hum 2.wav", 100, 400),
            TrailHitSound(path / "electro hum 3.wav", 300, 600),
            TrailHitSound(path / "electro crash light.wav", 500, 900),
            TrailHitSound(path / "electro crash light 2.wav", 400, 800),
            TrailHitSound(path / "electro crash medium.wav", 700, 1600),
            TrailHitSound(path / "electro crash heavy.wav", 1600, 3000),
        ]
        self.last_sound_time = time()

    def ball_hit(self, strength):
        if not PLAY_SOUNDS:
            return
        sounds = list(filter(lambda s: s.strength_min <= strength <= s.strength_max, self.trail_ball_hit_sounds))
        if len(sounds) > 0 and self.last_sound_time < time() - MIN_SOUND_INTERVAL:
            sound_file = random.choice(sounds).file
            Thread(target=playsound, args=[str(sound_file)]).start()
            self.last_sound_time = time()

    def car_hit(self, strength):
        if not PLAY_SOUNDS:
            return
        sounds = list(filter(lambda s: s.strength_min <= strength <= s.strength_max, self.trail_car_hit_sounds))
        if len(sounds) > 0 and self.last_sound_time < time() - MIN_SOUND_INTERVAL:
            sound_file = random.choice(sounds).file
            Thread(target=playsound, args=[str(sound_file)]).start()
            self.last_sound_time = time()


if __name__ == '__main__':
    sounds = SoundPlayer()
    sounds.ball_hit(400)
