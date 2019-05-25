from RLUtilities.GameInfo import GameInfo, BoostPad
from rlbot.messages.flat import GameTickPacket, FieldInfo

from rlmath import *


class EBoostPad(BoostPad):
    def __init__(self, index, pos, is_big, is_active, timer):
        super().__init__(index, pos, is_active, timer)
        self.is_big = is_big


class EGameInfo(GameInfo):
    def __init__(self, index, team):
        super().__init__(index, team)

        self.team_sign = -1 if team == 0 else 1

        self.dt = 0.016666
        self.current_game_time = 0
        self.is_kickoff = False

        self.own_goal = vec3(0, self.team_sign * FIELD_LENGTH / 2, 0)
        self.own_goal_field = vec3(0, self.team_sign * (FIELD_LENGTH / 2 - 560), 0)
        self.enemy_goal = vec3(0, -self.team_sign * FIELD_LENGTH / 2, 0)
        self.enemy_goal_right = vec3(820 * self.team_sign, -5120 * self.team_sign, 0)
        self.enemy_goal_left = vec3(-820 * self.team_sign, -5120 * self.team_sign, 0)

        self.field_info_loaded = False

    def read_field_info(self, field_info: FieldInfo):
        if field_info is None or field_info.num_boosts == 0:
            return

        self.boost_pads = []
        for i in range(field_info.num_boosts):
            pad = field_info.boost_pads[i]
            pos = vec3(pad.location.x, pad.location.y, pad.location.z)
            self.boost_pads.append(EBoostPad(i, pos, pad.is_full_boost, True, 0.0))
        self.convenient_boost_pad = self.boost_pads[0]
        self.convenient_boost_pad_score = 0

        self.field_info_loaded = True

    def read_packet(self, packet: GameTickPacket):
        super().read_packet(packet)

        # Game state
        self.dt = packet.game_info.seconds_elapsed - self.current_game_time
        self.current_game_time = packet.game_info.seconds_elapsed
        self.is_kickoff = packet.game_info.is_kickoff_pause

        # Boost pads
        self.convenient_boost_pad_score = 0
        for pad in self.boost_pads:
            pad_state = packet.game_boosts[pad.index]
            pad.is_active = pad_state.is_active
            pad.timer = pad_state.timer

            score = self.get_boost_pad_convenience_score(pad)
            if score > self.convenient_boost_pad_score:
                self.convenient_boost_pad = pad

    def get_boost_pad_convenience_score(self, pad):
        if not pad.is_active:
            return 0

        car_to_pad = pad.pos - self.my_car.pos
        angle = angle_between(self.my_car.forward(), car_to_pad)

        # Pads behind the car is bad
        if abs(angle) > 1.3:
            return 0

        dist = norm(car_to_pad)

        dist_score = 1 - clip((abs(dist) / 2500)**2, 0, 1)
        angle_score = 1 - clip((abs(angle) / 3), 0, 1)

        return dist_score * angle_score * (0.8, 1)[pad.is_big]

    def closest_enemy(self, pos: vec3):
        enemy = None
        dist = -1
        for e in self.opponents:
            d = norm(e.pos - pos)
            if enemy is None or d < dist:
                enemy = e
                dist = d
        return enemy, dist
