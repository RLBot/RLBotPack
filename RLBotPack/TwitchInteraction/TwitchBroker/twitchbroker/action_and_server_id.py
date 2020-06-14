from dataclasses import dataclass
from typing import List

from rlbot_action_client.models import BotAction, AvailableActions

@dataclass
class ActionAndServerId:
    bot_action: BotAction
    entity_name: str
    action_server_id: str


@dataclass
class AvailableActionsAndServerId:
    available_actions: AvailableActions
    action_server_id: str
