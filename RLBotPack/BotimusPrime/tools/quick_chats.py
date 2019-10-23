import random
from collections import deque
from rlbot.agents.base_agent import BaseAgent, GameTickPacket

class QuickChatTool:

    chat_interval = 0.5

    def __init__(self, agent: BaseAgent):
        self.last_time_chat_sent = 0
        self.agent = agent
        self.queue = deque()

    def send(self, chat_id):
        self.queue.append(chat_id)

    def send_random(self, chat_ids):
        self.send(random.choice(chat_ids))

    def step(self, packet: GameTickPacket):
        time = packet.game_info.seconds_elapsed
        if self.queue and time > self.last_time_chat_sent + self.chat_interval:
            self.last_time_chat_sent = time
            self.agent.send_quick_chat(False, self.queue.popleft())

    Information_IGotIt = 0
    Information_NeedBoost = 1
    Information_TakeTheShot = 2
    Information_Defending = 3
    Information_GoForIt = 4
    Information_Centering = 5
    Information_AllYours = 6
    Information_InPosition = 7
    Information_Incoming = 8
    Compliments_NiceShot = 9
    Compliments_GreatPass = 10
    Compliments_Thanks = 11
    Compliments_WhatASave = 12
    Compliments_NiceOne = 13
    Compliments_WhatAPlay = 14
    Compliments_GreatClear = 15
    Compliments_NiceBlock = 16
    Reactions_OMG = 17
    Reactions_Noooo = 18
    Reactions_Wow = 19
    Reactions_CloseOne = 20
    Reactions_NoWay = 21
    Reactions_HolyCow = 22
    Reactions_Whew = 23
    Reactions_Siiiick = 24
    Reactions_Calculated = 25
    Reactions_Savage = 26
    Reactions_Okay = 27
    Apologies_Cursing = 28
    Apologies_NoProblem = 29
    Apologies_Whoops = 30
    Apologies_Sorry = 31
    Apologies_MyBad = 32
    Apologies_Oops = 33
    Apologies_MyFault = 34
    PostGame_Gg = 35
    PostGame_WellPlayed = 36
    PostGame_ThatWasFun = 37
    PostGame_Rematch = 38
    PostGame_OneMoreGame = 39
    PostGame_WhatAGame = 40
    PostGame_NiceMoves = 41
    PostGame_EverybodyDance = 42
    # Custom text chats made by bot makers
    MaxPysonixQuickChatPresets = 43
    # Waste of CPU cycles
    Custom_Toxic_WasteCPU = 44
    # Git gud*
    Custom_Toxic_GitGut = 45
    # De-Allocate Yourself
    Custom_Toxic_DeAlloc = 46
    # 404: Your skill not found
    Custom_Toxic_404NoSkill = 47
    # Get a virus
    Custom_Toxic_CatchVirus = 48
    # Passing!
    Custom_Useful_Passing = 49
    # Faking!
    Custom_Useful_Faking = 50
    # Demoing!
    Custom_Useful_Demoing = 51
    # BOOPING
    Custom_Useful_Bumping = 52
    # The chances of that was 47525 to 1*
    Custom_Compliments_TinyChances = 53
    # Who upped your skill level?
    Custom_Compliments_SkillLevel = 54
    # Your programmer should be proud
    Custom_Compliments_proud = 55
    # You're the GC of Bots
    Custom_Compliments_GC = 56
    # Are you <Insert Pro>Bot? *
    Custom_Compliments_Pro = 57
        
