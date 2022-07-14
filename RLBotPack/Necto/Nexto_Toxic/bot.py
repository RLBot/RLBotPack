import numpy as np
import torch
import random
import math

from datetime import datetime

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats
from rlgym_compat import GameState

from agent import Agent
from nexto_obs import NextoObsBuilder, BOOST_LOCATIONS

KICKOFF_CONTROLS = (
        11 * 4 * [SimpleControllerState(throttle=1, boost=True)]
        + 4 * 4 * [SimpleControllerState(throttle=1, boost=True, steer=-1)]
        + 2 * 4 * [SimpleControllerState(throttle=1, jump=True, boost=True)]
        + 1 * 4 * [SimpleControllerState(throttle=1, boost=True)]
        + 1 * 4 * [SimpleControllerState(throttle=1, yaw=0.8, pitch=-0.7, jump=True, boost=True)]
        + 13 * 4 * [SimpleControllerState(throttle=1, pitch=1, boost=True)]
        + 10 * 4 * [SimpleControllerState(throttle=1, roll=1, pitch=0.5)]
)

KICKOFF_NUMPY = np.array([
    [scs.throttle, scs.steer, scs.pitch, scs.yaw, scs.roll, scs.jump, scs.boost, scs.handbrake]
    for scs in KICKOFF_CONTROLS
])


class Nexto(BaseAgent):
    def __init__(self, name, team, index,
                 beta=1, render=False, hardcoded_kickoffs=True, stochastic_kickoffs=True):
        super().__init__(name, team, index)

        self.obs_builder = None
        self.agent = Agent()
        self.tick_skip = 8

        # Beta controls randomness:
        # 1=best action, 0.5=sampling from probability, 0=random, -1=worst action, or anywhere inbetween
        self.beta = beta
        self.render = render
        self.hardcoded_kickoffs = False
        self.stochastic_kickoffs = stochastic_kickoffs

        self.game_state: GameState = None
        self.controls = None
        self.action = None
        self.update_action = True
        self.ticks = 0
        self.prev_time = 0
        self.kickoff_index = -1
        self.field_info = None
        self.gamemode = None

        # toxic handling
        self.isToxic = True
        self.orangeGoals = 0
        self.blueGoals = 0
        self.demoedCount = 0
        self.lastFrameBall = None
        self.lastFrameDemod = False
        self.demoCount = 0
        self.pesterCount = 0
        self.demoedTickCount = 0
        self.demoCalloutCount = 0
        self.lastPacket = None

        self.teams = 1
        file_str = "C:\\Users\\Daniel\\RLGymDev\\NextoPlayData\\"+str(self.teams)+"v"+str(self.teams)+".csv"
        print(file_str)
        self.file = open(file_str, "w")

        header_str = ""

        header_str += "num_cars,"

        header_str += "ball.location.x,"
        header_str += "ball.location.y,"
        header_str += "ball.location.z,"

        header_str += "ball.velocity.x,"
        header_str += "ball.velocity.y,"
        header_str += "ball.velocity.z,"

        header_str += "ball.angular_velocity.x,"
        header_str += "ball.angular_velocity.y,"
        header_str += "ball.angular_velocity.z,"

        header_str += "ball.rotation.yaw,"
        header_str += "ball.rotation.roll,"
        header_str += "ball.rotation.pitch,"

        print(self.teams*2)
        for car in range(self.teams*2):
            header_str += "car.name,"
            header_str += "car.team,"
            header_str += "car.jumped,"
            header_str += "car.double_jumped,"
            header_str += "car.boost,"

            header_str += "car.physics.location.x,"
            header_str += "car.physics.location.y,"
            header_str += "car.physics.location.z,"

            header_str += "car.physics.velocity.x,"
            header_str += "car.physics.velocity.y,"
            header_str += "car.physics.velocity.z,"

            header_str += "car.physics.angular_velocity.x,"
            header_str += "car.physics.angular_velocity.y,"
            header_str += "car.physics.angular_velocity.z,"

            header_str += "car.physics.rotation.yaw,"
            header_str += "car.physics.rotation.roll,"
            header_str += "car.physics.rotation.pitch,"

        header_str += "self.controls.throttle,"
        header_str += "self.controls.steer,"
        header_str += "self.controls.pitch,"
        header_str += "self.controls.yaw,"
        header_str += "self.controls.roll,"
        header_str += "self.controls.jump,"
        header_str += "self.controls.boost,"
        header_str += "self.controls.handbrake,"


        #print(header_str)
        self.file.write(header_str)
        self.file.write("\n")

        print('Nexto Ready - Index:', index)
        print("Remember to run Nexto at 120fps with vsync off! "
              "Stable 240/360 is second best if that's better for your eyes")
        print("Also check out the RLGym Twitch stream to watch live bot training and occasional showmatches!")

    def initialize_agent(self):
        # Initialize the rlgym GameState object now that the game is active and the info is available
        self.field_info = self.get_field_info()
        self.obs_builder = NextoObsBuilder(field_info=self.field_info)
        self.game_state = GameState(self.field_info)
        self.ticks = self.tick_skip  # So we take an action the first tick
        self.prev_time = 0
        self.controls = SimpleControllerState()
        self.action = np.zeros(8)
        self.update_action = True
        self.kickoff_index = -1
        match_settings = self.get_match_settings()
        mutators = match_settings.MutatorSettings()
        # Examples

        # Game mode
        game_modes = (
            "soccer",
            "hoops",
            "dropshot",
            "hockey",
            "rumble",
            "heatseeker"
        )
        self.gamemode = game_modes[match_settings.GameMode()]

    def render_attention_weights(self, weights, positions, n=3):
        if weights is None:
            return
        mean_weights = torch.mean(torch.stack(weights), dim=0).numpy()[0][0]

        top = sorted(range(len(mean_weights)), key=lambda i: mean_weights[i], reverse=True)
        top.remove(0)  # Self

        self.renderer.begin_rendering('attention_weights')

        invert = np.array([-1, -1, 1]) if self.team == 1 else np.ones(3)
        loc = positions[0] * invert
        mx = mean_weights[~(np.arange(len(mean_weights)) == 1)].max()
        c = 1
        for i in top[:n]:
            weight = mean_weights[i] / mx
            # print(i, weight)
            dest = positions[i] * invert
            color = self.renderer.create_color(255, round(255 * (1 - weight)), round(255),
                                               round(255 * (1 - weight)))
            self.renderer.draw_string_3d(dest, 2, 2, str(c), color)
            c += 1
            self.renderer.draw_line_3d(loc, dest, color)
        self.renderer.end_rendering()

    def log_packet(self, packet: GameTickPacket):
        cars = packet.game_cars[:packet.num_cars]
        ball = packet.game_ball.physics

        packet_str = ""

        packet_str += str(packet.num_cars) + ","

        packet_str += str(ball.location.x) + ","
        packet_str += str(ball.location.y) + ","
        packet_str += str(ball.location.z) + ","

        packet_str += str(ball.velocity.x) + ","
        packet_str += str(ball.velocity.y) + ","
        packet_str += str(ball.velocity.z) + ","

        packet_str += str(ball.angular_velocity.x) + ","
        packet_str += str(ball.angular_velocity.y) + ","
        packet_str += str(ball.angular_velocity.z) + ","

        packet_str += str(ball.rotation.yaw) + ","
        packet_str += str(ball.rotation.roll) + ","
        packet_str += str(ball.rotation.pitch) + ","

        for car in cars:
            packet_str += str(car.name) + ","
            packet_str += str(car.team) + ","
            packet_str += str(car.jumped) + ","
            packet_str += str(car.double_jumped) + ","
            packet_str += str(car.boost) + ","

            packet_str += str(car.physics.location.x) + ","
            packet_str += str(car.physics.location.y) + ","
            packet_str += str(car.physics.location.z) + ","

            packet_str += str(car.physics.velocity.x) + ","
            packet_str += str(car.physics.velocity.y) + ","
            packet_str += str(car.physics.velocity.z) + ","

            packet_str += str(car.physics.angular_velocity.x) + ","
            packet_str += str(car.physics.angular_velocity.y) + ","
            packet_str += str(car.physics.angular_velocity.z) + ","

            packet_str += str(car.physics.rotation.yaw) + ","
            packet_str += str(car.physics.rotation.roll) + ","
            packet_str += str(car.physics.rotation.pitch) + ","

        packet_str += str(self.controls.throttle) + ","
        packet_str += str(self.controls.steer) + ","
        packet_str += str(self.controls.pitch) + ","
        packet_str += str(self.controls.yaw) + ","
        packet_str += str(self.controls.roll) + ","
        packet_str += str(self.controls.jump) + ","
        packet_str += str(self.controls.boost) + ","
        packet_str += str(self.controls.handbrake)
        

        self.file.write(packet_str)
        self.file.write("\n")

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        cur_time = packet.game_info.seconds_elapsed
        delta = cur_time - self.prev_time
        self.prev_time = cur_time

        ticks_elapsed = round(delta * 120)
        self.ticks += ticks_elapsed
        self.game_state.decode(packet, ticks_elapsed)

        if self.isToxic:
            self.toxicity(packet)

        if self.update_action and len(self.game_state.players) > self.index:
            self.update_action = False

            player = self.game_state.players[self.index]
            teammates = [p for p in self.game_state.players if p.team_num == self.team and p != player]
            opponents = [p for p in self.game_state.players if p.team_num != self.team]

            self.game_state.players = [player] + teammates + opponents

            if self.gamemode == "heatseeker":
                self._modify_ball_info_for_heatseeker(packet, self.game_state)

            obs = self.obs_builder.build_obs(player, self.game_state, self.action)

            beta = self.beta
            if packet.game_info.is_match_ended:
                # or not (packet.game_info.is_kickoff_pause or packet.game_info.is_round_active): Removed due to kickoff
                beta = 0  # Celebrate with random actions
            if self.stochastic_kickoffs and packet.game_info.is_kickoff_pause:
                beta = 0.5
            self.action, weights = self.agent.act(obs, beta)

            if self.render:
                positions = np.asarray([p.car_data.position for p in self.game_state.players] +
                                       [self.game_state.ball.position] +
                                       list(BOOST_LOCATIONS))
                self.render_attention_weights(weights, positions)

        if self.ticks >= self.tick_skip - 1:
            self.update_controls(self.action)

        if self.ticks >= self.tick_skip:
            self.ticks = 0
            self.update_action = True

        if self.hardcoded_kickoffs:
            self.maybe_do_kickoff(packet, ticks_elapsed)

        self.log_packet(packet)

        return self.controls

    def maybe_do_kickoff(self, packet, ticks_elapsed):
        if packet.game_info.is_kickoff_pause:
            if self.kickoff_index >= 0:
                self.kickoff_index += round(ticks_elapsed)
            elif self.kickoff_index == -1:
                is_kickoff_taker = False
                ball_pos = np.array([packet.game_ball.physics.location.x, packet.game_ball.physics.location.y])
                positions = np.array([[car.physics.location.x, car.physics.location.y]
                                      for car in packet.game_cars[:packet.num_cars]])
                distances = np.linalg.norm(positions - ball_pos, axis=1)
                if abs(distances.min() - distances[self.index]) <= 10:
                    is_kickoff_taker = True
                    indices = np.argsort(distances)
                    for index in indices:
                        if abs(distances[index] - distances[self.index]) <= 10 \
                                and packet.game_cars[index].team == self.team \
                                and index != self.index:
                            if self.team == 0:
                                is_left = positions[index, 0] < positions[self.index, 0]
                            else:
                                is_left = positions[index, 0] > positions[self.index, 0]
                            if not is_left:
                                is_kickoff_taker = False  # Left goes

                self.kickoff_index = 0 if is_kickoff_taker else -2

            if 0 <= self.kickoff_index < len(KICKOFF_NUMPY) \
                    and packet.game_ball.physics.location.y == 0:
                action = KICKOFF_NUMPY[self.kickoff_index]
                self.action = action
                self.update_controls(self.action)
        else:
            self.kickoff_index = -1

    def update_controls(self, action):
        self.controls.throttle = action[0]
        self.controls.steer = action[1]
        self.controls.pitch = action[2]
        self.controls.yaw = action[3]
        self.controls.roll = action[4]
        self.controls.jump = action[5] > 0
        self.controls.boost = action[6] > 0
        self.controls.handbrake = action[7] > 0
        if self.gamemode == "rumble":
            self.controls.use_item = np.random.random() > (self.tick_skip / 1200)  # On average once every 10 seconds

    def _modify_ball_info_for_heatseeker(self, packet, game_state):
        assert self.field_info.num_goals == 2
        target_goal = self.field_info.goals[self.team].location
        target_goal = np.array([target_goal.x, target_goal.y, target_goal.z])

        ball_pos = game_state.ball.position
        ball_vel = game_state.ball.linear_velocity
        vel_mag = np.linalg.norm(ball_vel)

        current_dir = ball_vel / vel_mag

        goal_dir = target_goal - ball_pos
        goal_dist = np.linalg.norm(goal_dir)
        goal_dir = goal_dir / goal_dist

        self.game_state.ball.linear_velocity = 1.1 * vel_mag * (
                    goal_dir + (current_dir if packet.game_ball.latest_touch.team != self.team else goal_dir)) / 2
        self.game_state.inverted_ball.linear_velocity = self.game_state.ball.linear_velocity * np.array([-1, -1, 1])


    def toxicity(self, packet):
        """
        THE SALT MUST FLOW
        """

        # prep the toxic
        scored = False
        scoredOn = False
        demoed = False
        demo = False
        allyChance = False

        player = packet.game_cars[self.index]

        humanMates = [p for p in packet.game_cars[:packet.num_cars] if p.team == self.team and p.is_bot is False]
        humanOpps = [p for p in packet.game_cars[:packet.num_cars] if p.team != self.team and p.is_bot is False]
        goodGoal = [0, -5120] if self.team == 0 else [0, 5120]
        badGoal = [0, 5120] if self.team == 0 else [0, -5120]

        if player.is_demolished and self.demoedTickCount == 0:  # and not self.lastFrameDemod:
            demoed = True
            self.demoedTickCount = 120 * 4

        for p in packet.game_cars:
            if p.is_demolished and p.team != self.team and self.demoCalloutCount == 0:  # player is closest
                demo = True
                self.demoCalloutCount = 120 * 4

        if self.blueGoals != packet.teams[0].score:
            # blue goal!
            self.blueGoals = packet.teams[0].score
            if self.team == 0:
                scored = True
            else:
                scoredOn = True

        if self.orangeGoals != packet.teams[1].score:
            # orange goal
            self.orangeGoals = packet.teams[1].score
            if self.team == 1:
                scored = True
            else:
                scoredOn = True

        self.lastPacket = packet

        # ** NaCl **

        if scored:
            i = random.randint(0, 6)
            if i == 0:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Toxic_GitGut)
                return
            if i == 1:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_Thanks)
                return

            for p in humanOpps:

                d = math.sqrt((p.physics.location.x - badGoal[0]) ** 2 + (p.physics.location.y - badGoal[1]) ** 2)
                if d < 2000:
                    self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_WhatASave)
                    i = random.randint(0, 3)
                    if i == 0:
                        self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)
                        self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_WhatASave)
                    return

            for p in humanOpps:
                d = math.sqrt((p.physics.location.x - badGoal[0]) ** 2 + (p.physics.location.y - badGoal[1]) ** 2)
                if d > 9000:
                    self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_CloseOne)
                    return

        if scoredOn:
            for p in humanMates:
                d = math.sqrt((p.physics.location.x - goodGoal[0]) ** 2 + (p.physics.location.y - goodGoal[1]) ** 2)
                if d < 3000:
                    i = random.randint(0, 2)
                    if i == 0:
                        self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_NiceBlock)
                    else:
                        self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Compliments_WhatASave)
                    return

            i = random.randint(0, 3)
            if i == 0:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Excuses_Lag)
                return
            elif i == 1:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Okay)
                return

        if demo:
            i = random.randint(0, 2)
            if i == 0:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Useful_Bumping)

            elif i == 1:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Apologies_Sorry)

            return

        if demoed:
            self.demoCount += 1
            if self.demoCount >= 5:
                i = random.randint(0, 2)
                if i == 0:
                    self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Toxic_DeAlloc)

                return

            if self.demoCount >= 3:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Wow)

            self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Reactions_Okay)
            return

        for p in humanMates:
            onOpponentHalf = False

            if p.team == 1 and p.physics.location.y < 0:
                onOpponentHalf = True
            elif p.team == 0 and p.physics.location.y > 0:
                onOpponentHalf = True

            d = math.sqrt((p.physics.location.x - packet.game_ball.physics.location.x) ** 2 + (
                        p.physics.location.y - packet.game_ball.physics.location.y) ** 2)
            if d < 1000 and self.pesterCount == 0 and onOpponentHalf:
                self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_TakeTheShot)
                self.pesterCount = 120 * 7  # spam but not too much
                return

        if self.demoCalloutCount > 0:
            self.demoCalloutCount -= 1

        if self.demoedTickCount > 0:
            self.demoedTickCount -= 1

        if self.pesterCount > 0:
            self.pesterCount -= 1




