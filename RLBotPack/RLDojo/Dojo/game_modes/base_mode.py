from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import DojoGameState


class BaseGameMode(ABC):
    """Abstract base class for all game modes in Dojo"""
    
    def __init__(self, game_state: 'DojoGameState', game_interface):
        self.game_state = game_state
        self.game_interface = game_interface
    
    @abstractmethod
    def update(self, packet) -> None:
        """Update the game mode with the current packet"""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the game mode"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources when switching away from this mode"""
        pass
    
    def set_game_state(self, game_state):
        """Helper method to set the RLBot game state"""
        self.game_interface.set_game_state(game_state)
    
    def goal_scored(self, packet) -> bool:
        """Check if a goal was scored in the last tick"""
        team_scores = tuple(map(lambda x: x.score, packet.teams))
        score_diff = max(team_scores) - min(team_scores)
        
        if score_diff != self.game_state.scoreDiff_prev:
            self.game_state.scoreDiff_prev = score_diff
            return True
        return False
    
    def get_team_scored(self, packet) -> int:
        """Determine which team scored"""
        from game_state import CarIndex
        
        team_scores = tuple(map(lambda x: x.score, packet.teams))
        human_score = team_scores[CarIndex.HUMAN.value]
        bot_score = team_scores[CarIndex.BOT.value]
        
        team = CarIndex.HUMAN.value if human_score > self.game_state.score_human_prev else CarIndex.BOT.value
        
        self.game_state.score_human_prev = human_score
        self.game_state.score_bot_prev = bot_score
        return team 
