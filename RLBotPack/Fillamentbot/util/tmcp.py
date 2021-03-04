"""
Helper classes for the Team Match Communication Protocol.
https://github.com/RLBot/RLBot/wiki/Team-Match-Communication-Protocol
Made by Will
"""

from enum import Enum
from time import perf_counter
from queue import Empty
from typing import List, Optional

from rlbot.agents.base_agent import BaseAgent
from rlbot.matchcomms.client import MatchcommsClient

MAX_PACKETS_PER_TICK: int = 50
TIME_BETWEEN_MESSAGES: float = 0.1
TMCP_VERSION = [0, 5]


class ActionType(Enum):
    BALL = "BALL"
    BOOST = "BOOST"
    DEMO = "DEMO"
    WAIT = "WAIT"


class TMCPMessage:
    def __init__(self, team: int, index: int, action_type: ActionType):
        self.team = team
        self.index = index
        self.action_type = action_type

    @classmethod
    def ball_action(cls, team: int, index: int, time: float = -1.0) -> "TMCPMessage":
        self = cls(team, index, ActionType.BALL)
        self.time = time
        return self

    @classmethod
    def boost_action(cls, team: int, index: int, target: int) -> "TMCPMessage":
        self = cls(team, index, ActionType.BOOST)
        self.target = target
        return self

    @classmethod
    def demo_action(
        cls, team: int, index: int, target: int, time: float = -1.0
    ) -> "TMCPMessage":
        self = cls(team, index, ActionType.DEMO)
        self.target = target
        self.time = time
        return self

    @classmethod
    def wait_action(cls, team: int, index: int) -> "TMCPMessage":
        self = cls(team, index, ActionType.WAIT)
        return self

    @classmethod
    def from_dict(cls, message: dict) -> Optional["TMCPMessage"]:
        try:
            team: int = message["team"]
            index: int = message["index"]

            action: dict = message["action"]
            action_type: ActionType = ActionType(action["type"])

            if action_type == ActionType.BALL:
                msg = cls.ball_action(team, index, action["time"])
            elif action_type == ActionType.BOOST:
                msg = cls.boost_action(team, index, action["target"])
            elif action_type == ActionType.DEMO:
                msg = cls.demo_action(team, index, action["target"], action["time"])
            elif action_type == ActionType.WAIT:
                msg = cls.wait_action(team, index)
            else:
                raise NotImplementedError
            return msg

        except (KeyError, ValueError):
            return None

    def to_dict(self) -> dict:
        if self.action_type == ActionType.BALL:
            action = {
                "type": "BALL",
                "time": self.time,
            }
        elif self.action_type == ActionType.BOOST:
            action = {
                "type": "BOOST",
                "target": self.target,
            }
        elif self.action_type == ActionType.DEMO:
            action = {
                "type": "DEMO",
                "target": self.target,
                "time": self.time,
            }
        elif self.action_type == ActionType.WAIT:
            action = {"type": "WAIT"}
        else:
            raise NotImplementedError

        return {
            "tmcp_version": TMCP_VERSION,
            "team": self.team,
            "index": self.index,
            "action": action,
        }

    def __repr__(self):
        return str(self.to_dict())


class TMCPHandler:
    """The class for handling TMCP.
    Create an instance by just passing your agent in:
    ```
    def initialize_agent(self):
        self.tmcp_handler = TMCPHandler(self)
    ```
    Usage is also very straightforward:
    ```
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        new_messages: List[TMCPMessage] = self.tmcp_handler.recv()
        if new_messages:
            # Handle TMCPMessages.
            ...
        # You can send messages like this.
        self.tmcp_handler.send_wait_action()
        # Or you can create them and send them more directly:
        my_message = TMCPMessage.ball_action(self.team, self.index, 123.45)
        self.send(my_message)
    ```
    """

    def __init__(self, agent: BaseAgent):
        self.matchcomms: MatchcommsClient = agent.matchcomms
        self.index: int = agent.index
        self.team: int = agent.team
        self.last_time: float = 0.0

    def send(self, message: TMCPMessage) -> bool:
        """Send a TMCPMessage over match comms. Will not send messages if they are coming too quickly.
        Returns whether a message was sent."""
        current_time = perf_counter()
        if current_time - self.last_time < TIME_BETWEEN_MESSAGES:
            return False
        self.matchcomms.outgoing_broadcast.put_nowait(message.to_dict())
        self.last_time: float = current_time
        return True

    def recv(self) -> List[TMCPMessage]:
        messages = []
        # Receive messages until we reach the maximum packets per tick or the queue is empty.
        for _ in range(MAX_PACKETS_PER_TICK):
            try:
                message = self.parse(self.matchcomms.incoming_broadcast.get_nowait())
                if message is not None:
                    messages.append(message)
            except Empty:
                break
        return messages

    def parse(self, message: dict) -> Optional[TMCPMessage]:
        # Ignore messages using a different version of the protocol.
        if message.get("tmcp_version") != TMCP_VERSION:
            return None
        # Ignore messages by opposing team.
        if message.get("team") != self.team:
            return None

        return TMCPMessage.from_dict(message)

    def send_ball_action(self, time: Optional[float] = None) -> bool:
        """The bot is going for the ball.
        `time` - Game time that your bot will arrive at the ball.
        """
        if time is None:
            msg = TMCPMessage.ball_action(self.team, self.index)
        else:
            msg = TMCPMessage.ball_action(self.team, self.index, time)
        return self.send(msg)

    def send_boost_action(self, target: int) -> bool:
        """The bot is going for boost.
        `target` - Index of the boost pad the bot is going to collect.
        """
        return self.send(TMCPMessage.boost_action(self.team, self.index, target))

    def send_demo_action(self, target: int, time: Optional[float] = None) -> bool:
        """The bot is going to demolish another car.
        `target` - Index of the bot that will be demoed.
        `time` - Game time that the bot will demo the other bot.
        """
        if time is None:
            msg = TMCPMessage.demo_action(self.team, self.index, target)
        else:
            msg = TMCPMessage.demo_action(self.team, self.index, target, time)
        return self.send(msg)

    def send_wait_action(self) -> bool:
        """The bot is waiting for a chance to go for the ball or boost.
        Some examples are positioning (retreating/shadowing) and recovering.
        """
        return self.send(TMCPMessage.wait_action(self.team, self.index))
