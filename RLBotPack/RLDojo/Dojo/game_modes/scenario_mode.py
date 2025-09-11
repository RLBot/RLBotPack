import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

from .base_mode import BaseGameMode
from game_state import ScenarioPhase, CarIndex, CUSTOM_MODES
from scenario import Scenario, OffensiveMode, DefensiveMode
from constants import BACK_WALL, GOAL_DETECTION_THRESHOLD, BALL_GROUND_THRESHOLD, FREE_GOAL_TIMEOUT
from playlist import PlaylistRegistry, PlayerRole
import utils
import time
from custom_scenario import CustomScenario

class ScenarioMode(BaseGameMode):
    """Handles scenario-based training mode"""
    
    def __init__(self, game_state, game_interface):
        super().__init__(game_state, game_interface)
        self.rlbot_game_state = None
        self.prev_time = 0
        self.playlist_registry = None  # Will be set via set_playlist_registry
        self.current_playlist = None
        self.last_menu_phase_time = 0
        self.custom_mode_active = False
        self.custom_scenario = None
        self.custom_trial_active = False
        self.trial_start_time = 0
            
    def set_custom_scenario(self, scenario):
        """Set the custom scenario"""
        self.custom_scenario = scenario
        self.custom_mode_active = True
    
    def set_playlist_registry(self, registry):
        """Set the playlist registry to use"""
        self.playlist_registry = registry
        
    def clear_playlist(self):
        """Clear the active playlist"""
        self.current_playlist = None
    
    def set_playlist(self, playlist_name):
        """Set the active playlist"""
        if not self.playlist_registry:
            print("Error: Playlist registry not set")
            return
            
        self.current_playlist = self.playlist_registry.get_playlist(playlist_name)
        if self.current_playlist:
            self.game_state.timeout = self.current_playlist.settings.timeout
            self.game_state.rule_zero_mode = self.current_playlist.settings.rule_zero
    
    def initialize(self):
        """Initialize scenario mode"""
        np.random.seed(0)
        self.game_state.started_time = self.game_state.cur_time
        self.game_state.game_phase = ScenarioPhase.SETUP
        
        if self.game_state.free_goal_mode:
            self.set_playlist("Free Goal")
            self.game_state.rule_zero_mode = False
    
    def cleanup(self):
        """Clean up scenario mode resources"""
        pass
    
    def update(self, packet):
        """Update scenario mode based on current game phase"""
        if self.game_state.paused:
            return
            
        phase_handlers = {
            ScenarioPhase.INIT: self._handle_init_phase,
            ScenarioPhase.SETUP: self._handle_setup_phase,
            ScenarioPhase.MENU: self._handle_menu_phase,
            ScenarioPhase.EXITING_MENU: self._handle_menu_exiting_phase,
            ScenarioPhase.PAUSED: self._handle_paused_phase,
            ScenarioPhase.ACTIVE: self._handle_active_phase,
            ScenarioPhase.CUSTOM_OFFENSE: self._handle_custom_phase,
            ScenarioPhase.CUSTOM_BALL: self._handle_custom_phase,
            ScenarioPhase.CUSTOM_DEFENSE: self._handle_custom_phase,
            ScenarioPhase.CUSTOM_TRIAL: self._handle_custom_trial_phase,
            ScenarioPhase.CUSTOM_NAMING: self._handle_custom_phase,
        }
        
        handler = phase_handlers.get(self.game_state.game_phase)
        if handler:
            handler(packet)
    
    def get_rlbot_game_state(self):
        """Get the current RLBot game state"""
        return self.rlbot_game_state
    
    def _handle_init_phase(self, packet):
        """Handle initialization phase"""
        self.initialize()
    
    def _handle_setup_phase(self, packet):
        """Handle setup phase - create new scenario"""
        if self.current_playlist:
            self._setup_playlist_mode()
        
        self._set_next_game_state()
        self.prev_time = self.game_state.cur_time
        self.game_state.game_phase = ScenarioPhase.PAUSED
    
    def _handle_menu_phase(self, packet):
        """Handle menu phase - freeze game state"""
        if self.rlbot_game_state:
            self.set_game_state(self.rlbot_game_state)
        self.last_menu_phase_time = time.time()
            
    def _handle_menu_exiting_phase(self, packet):
        """Unfreeze game state after a 3 second countdown"""
        # For each second, render a countdown from 3 to 1
        if time.time() - self.last_menu_phase_time > 3:
            self.game_state.game_phase = ScenarioPhase.ACTIVE
            
            # Reset prev time so we don't instantly timeout 
            self.prev_time = self.game_state.cur_time
        else:
            self.game_interface.renderer.begin_rendering()
            self.game_interface.renderer.draw_string_2d(850, 200, 15, 15, str(3 - int(time.time() - self.last_menu_phase_time)), self.game_interface.renderer.white())
            self.game_interface.renderer.end_rendering()
            self.set_game_state(self.rlbot_game_state)
    
    def _handle_paused_phase(self, packet):
        """Handle paused phase - wait before starting scenario"""
        time_elapsed = self.game_state.cur_time - self.prev_time
        if (time_elapsed < self.game_state.pause_time or 
            self.goal_scored(packet) or 
            packet.game_info.is_kickoff_pause):
            if self.rlbot_game_state:
                self.set_game_state(self.rlbot_game_state)
        else:
            self.game_state.game_phase = ScenarioPhase.ACTIVE
    
    def _handle_active_phase(self, packet):
        """Handle active scenario phase"""
        # Handle goal reset disabled mode
        if self.game_state.disable_goal_reset:
            if self._check_ball_in_goal(packet):
                return
        
        # Handle kickoff pause
        if packet.game_info.is_kickoff_pause:
            self.game_state.game_phase = ScenarioPhase.SETUP
            return
        
        # Handle timeout
        time_elapsed = self.game_state.cur_time - self.prev_time
        if time_elapsed > self.game_state.timeout:
            if (packet.game_ball.physics.location.z < BALL_GROUND_THRESHOLD or 
                not self.game_state.rule_zero_mode):
                self._award_defensive_goal()
                self.game_state.game_phase = ScenarioPhase.SETUP
                self.game_state.scored_time = self.game_state.cur_time
    
    def _handle_custom_phase(self, packet):
        """Handle custom sandbox phases"""
        if self.rlbot_game_state:
            self.set_game_state(self.rlbot_game_state)
            
    def _handle_custom_trial_phase(self, packet):
        if not self.custom_trial_active:
            self.custom_trial_active = True
            self.trial_start_time = self.game_state.cur_time
        
        if self.game_state.cur_time - self.trial_start_time > 3.0:
            self.custom_trial_active = False
            self.game_state.game_phase = ScenarioPhase.CUSTOM_OFFENSE
            return
    
    def _setup_playlist_mode(self):
        """Setup scenario based on current playlist"""
        self.custom_mode_active = False
        scenario_config, is_custom = self.current_playlist.get_next_scenario()
        if scenario_config and not is_custom:
            self.game_state.offensive_mode = scenario_config.offensive_mode
            self.game_state.defensive_mode = scenario_config.defensive_mode
            self.game_state.player_offense = (scenario_config.player_role == PlayerRole.OFFENSE)
        elif scenario_config and is_custom:
            self.custom_scenario = scenario_config
            self.custom_mode_active = True
            
    def _set_next_game_state(self):
        """Create and set the next scenario game state"""
        if not self.game_state.freeze_scenario and not self.custom_mode_active:
            print(f"Setting next game state: {self.game_state.offensive_mode}, {self.game_state.defensive_mode}")
            
            # Get boost range from current playlist if available
            boost_range = None
            if self.current_playlist and self.current_playlist.settings.boost_range:
                boost_range = self.current_playlist.settings.boost_range
                print(f"Using playlist boost range: {boost_range}")
            
            scenario = Scenario(self.game_state.offensive_mode, self.game_state.defensive_mode, boost_range=boost_range)
            if self.game_state.player_offense:
                scenario.Mirror()
            
            self.game_state.scenario_history.append(scenario)
            self.game_state.freeze_scenario_index = len(self.game_state.scenario_history) - 1
        else:
            if self.custom_mode_active:
                scenario = Scenario.FromGameState(self.custom_scenario.to_rlbot_game_state())
            else:
                scenario = self.game_state.scenario_history[self.game_state.freeze_scenario_index]
        
        self.rlbot_game_state = scenario.GetGameState()
        self.set_game_state(self.rlbot_game_state)
    
    def _check_ball_in_goal(self, packet) -> bool:
        """Check if ball is in goal and award points accordingly"""
        ball_y = packet.game_ball.physics.location.y
        
        
        # Check if ball is in blue goal (back wall is blue)
        # Bot scored
        if ball_y < BACK_WALL - GOAL_DETECTION_THRESHOLD:
            self.game_state.bot_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        # Check if ball is in orange goal (negate back wall)
        # Human scored
        elif ball_y > (-BACK_WALL + GOAL_DETECTION_THRESHOLD):
            self.game_state.human_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        # Check for actual goal scored
        if self.goal_scored(packet):
            team_scored = self.get_team_scored(packet)
            if team_scored == CarIndex.HUMAN.value:
                self.game_state.human_score += 1
            else:
                self.game_state.bot_score += 1
            self.game_state.game_phase = ScenarioPhase.SETUP
            return True
        
        return False
    
    def _award_defensive_goal(self):
        """Award a goal to the defensive team"""
        if self.game_state.player_offense:
            self.game_state.bot_score += 1
        else:
            self.game_state.human_score += 1 
