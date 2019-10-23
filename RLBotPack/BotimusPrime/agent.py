from rlbot.agents.base_agent import BaseAgent, GameTickPacket, SimpleControllerState

from rlutilities.simulation import Input
from rlutilities.linear_algebra import norm

from tools.drawing import DrawingTool
from tools.quick_chats import QuickChatTool
from rlbot.matchcomms.common_uses.set_attributes_message import handle_set_attributes_message
from rlbot.matchcomms.common_uses.reply import reply_to

from maneuvers.kit import Maneuver
from maneuvers.kickoffs.kickoff import Kickoff
from maneuvers.kickoffs.diagonal import DiagonalKickoff
from maneuvers.shadow_defense import ShadowDefense

from strategy.soccar_strategy import SoccarStrategy
from strategy.training import get_maneuver_by_name

from utils.vector_math import distance
from utils.game_info import GameInfo

import time

class BotimusPrime(BaseAgent):
    
    RENDERING = True

    PREDICTION_RATE = 120
    PREDITION_DURATION = 8

    # def is_hot_reload_enabled(self):
    #     return False

    def initialize_agent(self):
        self.info: GameInfo = GameInfo(self.index, self.team)
        self.controls: SimpleControllerState = SimpleControllerState()
        self.maneuver: Maneuver = None

        self.info.set_mode("soccar")

        self.time = 0
        self.prev_time = 0
        self.last_touch_time = 0
        self.reset_time = 0
        self.ticks = 0

        self.draw: DrawingTool = DrawingTool(self.renderer)

        self.strategy = SoccarStrategy(self.info, self.draw)

        # variables related to quick chats
        self.chat = QuickChatTool(self)
        self.last_ball_vel = 0
        self.said_gg = False
        self.last_time_said_all_yours = 0
        self.num_of_our_goals_reacted_to = 0
        self.num_of_their_goals_reacted_to = 0

        self.matchcomms_message = ""

    def handle_training_matchcomms(self) -> bool:
        try:
            msg = self.matchcomms.incoming_broadcast.get_nowait()
            if handle_set_attributes_message(msg, self, allowed_keys=['matchcomms_message']):
                reply_to(self.matchcomms, msg)
                return True
        except:
            return False
        return False

    def get_output(self, packet: GameTickPacket):
        self.time = packet.game_info.seconds_elapsed
        dt = self.time - self.prev_time
        if packet.game_info.is_kickoff_pause and not isinstance(self.maneuver, Kickoff):
            self.maneuver = None

        self.prev_time = self.time
        self.ticks += 1
        self.info.read_packet(packet, self.get_field_info())
        self.strategy.packet = packet
        if self.ticks < 10:
            return Input()

        #reset maneuver when another car hits the ball
        touch = packet.game_ball.latest_touch
        if ((
            touch.time_seconds > self.last_touch_time
            and touch.player_name != packet.game_cars[self.index].name
        ) or (
            touch.player_name == '' and # if latest touch info is missing
            any([distance(self.info.ball, car) < 300 for car in self.info.opponents + self.info.teammates])
        )):
            self.last_touch_time = touch.time_seconds
            if (
                self.info.my_car.on_ground and not self.controls.jump
                and (not isinstance(self.maneuver, ShadowDefense) or self.maneuver.travel.driving)
            ):
                self.maneuver = None
                #self.reset_time = self.time

        if self.handle_training_matchcomms():
            self.info.predict_ball(self.PREDICTION_RATE * self.PREDITION_DURATION, 1 / self.PREDICTION_RATE)
            self.maneuver = get_maneuver_by_name(self.matchcomms_message, self.info)
            print("Training: Setting " + self.matchcomms_message)


        # choose maneuver
        if self.maneuver is None:

            if self.RENDERING:
                self.draw.clear()
            
            self.info.predict_ball(self.PREDICTION_RATE * self.PREDITION_DURATION, 1 / self.PREDICTION_RATE)
            
            self.maneuver = self.strategy.choose_maneuver()
            
            name = str(type(self.maneuver).__name__)
            print(name)

            self.last_ball_vel = norm(self.info.ball.velocity)

        
        # execute maneuver
        if self.maneuver is not None:
            self.maneuver.step(dt)
            self.controls = self.maneuver.controls

            if self.RENDERING:
                self.draw.group("maneuver")
                self.maneuver.render(self.draw)

            if self.maneuver.finished:
                self.maneuver = None

        for pad in self.info.large_boost_pads:
            self.draw.string(pad.position, str(pad.is_full_boost))


        if self.RENDERING:
            self.draw.execute()

        self.maybe_chat(packet)
        self.chat.step(packet)

        return self.controls

    def maybe_chat(self, packet: GameTickPacket):
        chat = self.chat

        for team in packet.teams:
            if team.team_index == self.team:
                our_score = team.score
            else:
                their_score = team.score

        # last second goal
        if their_score > self.num_of_their_goals_reacted_to or our_score > self.num_of_our_goals_reacted_to:
            if abs(their_score - our_score) < 2 and packet.game_info.game_time_remaining < 5:
                for _ in range(6):
                    self.chat.send_random([
                        chat.Reactions_OMG,
                        chat.PostGame_Gg,
                        chat.Reactions_HolyCow,
                        chat.Reactions_NoWay,
                        chat.Reactions_Wow,
                        chat.Reactions_OMG
                    ])

        # they scored
        if their_score > self.num_of_their_goals_reacted_to:
            self.num_of_their_goals_reacted_to = their_score
            for _ in range(2):
                if self.last_ball_vel > 2000:
                    self.chat.send_random([
                        chat.Compliments_NiceShot,
                        chat.Compliments_NiceOne,
                        chat.Reactions_Wow,
                        chat.Reactions_OMG,
                        chat.Reactions_Noooo
                    ])
                else:
                    self.chat.send_random([
                        chat.Reactions_Whew,
                        chat.Apologies_Whoops,
                        chat.Apologies_Oops,
                        chat.Apologies_Cursing
                    ])

        # we scored
        if our_score > self.num_of_our_goals_reacted_to:
            self.num_of_our_goals_reacted_to = our_score

            if self.last_ball_vel > 3000:
                self.chat.send(chat.Reactions_Siiiick)

            if self.last_ball_vel < 300:
                self.chat.send(chat.Compliments_WhatASave)

        # game is over
        if packet.game_info.is_match_ended and not self.said_gg:
            self.said_gg = True

            self.chat.send(chat.PostGame_Gg)
            self.chat.send(chat.PostGame_WellPlayed)

            if our_score < their_score:
                self.chat.send(chat.PostGame_OneMoreGame)

        # all yours :D
        if self.time > self.last_time_said_all_yours + 40:
            if isinstance(self.maneuver, ShadowDefense) and distance(self.info.my_car, self.info.ball) > 6000:
                self.last_time_said_all_yours = self.time
                self.chat.send(chat.Information_AllYours)


