"""
Custom playlist creation and management system for Dojo.

This module provides functionality for users to create, edit, and save
custom playlists that persist between sessions.
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from playlist import Playlist, ScenarioConfig, PlaylistSettings, PlayerRole
from scenario import OffensiveMode, DefensiveMode
from menu import MenuRenderer, UIElement
from pydantic import BaseModel, Field, ValidationError
from custom_scenario import CustomScenario, get_custom_scenarios

class CustomPlaylistManager:
    def __init__(self, renderer, main_menu_renderer):
        self.renderer = renderer
        self.main_menu_renderer = main_menu_renderer
        # Current playlist being created/edited
        self.current_playlist_name = ""
        self.current_scenarios = []
        self.current_custom_scenarios = []
        self.current_boost_range = [12, 100]  # Default boost range
        self.current_timeout = 7.0
        self.current_rule_zero = False
        
    def load_custom_playlists(self):
        """Load custom playlists from disk and return a list of all custom playlists"""
        custom_playlists = {}
        for file in os.listdir(_get_custom_playlists_path()):
            if file.endswith(".json"):
                with open(os.path.join(_get_custom_playlists_path(), file), "r") as f:
                    custom_playlists[file.replace(".json", "")] = Playlist.model_validate_json(f.read())
        return custom_playlists
    
    def create_playlist_creation_menu(self):
        """Create the main playlist creation menu"""
        menu = MenuRenderer(self.renderer, columns=1, render_function=self._render_playlist_details)
        menu.add_element(UIElement("Create Custom Playlist", header=True))
        menu.add_element(UIElement("Set Playlist Name", submenu=self._create_name_input_menu(), display_value_function=self.get_current_playlist_name))
        menu.add_element(UIElement("Add PresetScenarios", submenu=self._create_scenario_selection_menu()))
        menu.add_element(UIElement("Add Custom Scenario", submenu=self._create_custom_scenario_selection_menu()))
        menu.add_element(UIElement("Set Boost Range", submenu=self._create_boost_range_menu(), display_value_function=self.get_current_playlist_boost_range))
        menu.add_element(UIElement("Set Timeout", submenu=self._create_timeout_menu(), display_value_function=self.get_current_playlist_timeout))
        menu.add_element(UIElement("Toggle Rule Zero", function=self._toggle_rule_zero, display_value_function=self.get_current_playlist_rule_zero))
        menu.add_element(UIElement("Save Playlist", function=self._save_current_playlist))
        menu.add_element(UIElement("Cancel", function=self._cancel_playlist_creation))
        return menu
        
    ### Element value retrieval functions
    def get_current_playlist_name(self):
        return self.current_playlist_name
        
    
    def get_current_playlist_boost_range(self):
        return self.current_boost_range
    
    def get_current_playlist_timeout(self):
        return self.current_timeout
    
    def get_current_playlist_rule_zero(self):
        return self.current_rule_zero

    def _render_playlist_details(self):
        # Create a playlist out of current settings
        playlist = Playlist(
            name=self.current_playlist_name,
            description=f"Custom playlist with {len(self.current_scenarios)} scenarios",
            scenarios=self.current_scenarios.copy(),
            custom_scenarios=self.current_custom_scenarios.copy(),
            settings=PlaylistSettings(timeout=self.current_timeout, shuffle=True, boost_range=self.current_boost_range, rule_zero=self.current_rule_zero)
        )
        playlist.render_details(self.renderer)
    
    def _create_name_input_menu(self):
        """Create menu for setting playlist name"""
        menu = MenuRenderer(self.renderer, columns=1, text_input=True, text_input_callback=self._set_playlist_name)
        return menu
    
    def _create_scenario_selection_menu(self):
        """Create menu for selecting scenarios to add"""
        menu = MenuRenderer(self.renderer, columns=3, show_selections=True, render_function=self._render_playlist_details)
        
        # Column 1: Offensive modes
        menu.add_element(UIElement("Offensive Mode", header=True), column=0)
        for mode in OffensiveMode:
            menu.add_element(UIElement(
                mode.name.replace('_', ' ').title(),
                function=self._set_temp_offensive_mode,
                function_args=mode,
                chooseable=True,
            ), column=0)
        
        # Column 2: Defensive modes
        menu.add_element(UIElement("Defensive Mode", header=True), column=1)
        for mode in DefensiveMode:
            menu.add_element(UIElement(
                mode.name.replace('_', ' ').title(),
                function=self._set_temp_defensive_mode,
                function_args=mode,
                chooseable=True,
            ), column=1)
        
        # Column 3: Player role and actions
        menu.add_element(UIElement("Player Role", header=True), column=2)
        menu.add_element(UIElement("Offense", function=self._set_temp_player_role, function_args=PlayerRole.OFFENSE, chooseable=True), column=2)
        menu.add_element(UIElement("Defense", function=self._set_temp_player_role, function_args=PlayerRole.DEFENSE, chooseable=True), column=2)
        menu.add_element(UIElement("", header=True), column=2)  # Spacer
        menu.add_element(UIElement("Add Scenario", function=self._add_current_scenario), column=2)
        
        
        return menu
        
    def _create_custom_scenario_selection_menu(self):
        """Create menu for selecting custom scenarios to add"""
        menu = MenuRenderer(self.renderer, columns=2, show_selections=True, render_function=self._render_playlist_details)
        custom_scenarios = get_custom_scenarios()
        
        # Column 1: Custom scenarios
        for scenario_name in custom_scenarios:
            menu.add_element(UIElement(scenario_name, function=self._add_custom_scenario, function_args=scenario_name))
            
        # Column 2: Player role and actions
        return menu
    
    def _create_boost_range_menu(self):
        """Create menu for setting boost range"""
        menu = MenuRenderer(self.renderer, columns=2, render_function=self._render_playlist_details)
        
        # Column 1: Min boost
        menu.add_element(UIElement("Min Boost", header=True), column=0)
        for boost in [0, 12, 20, 30, 40, 50, 60, 70]:
            menu.add_element(UIElement(
                str(boost),
                function=self._set_min_boost,
                function_args=boost
            ), column=0)
        
        # Column 2: Max boost
        menu.add_element(UIElement("Max Boost", header=True), column=1)
        for boost in [50, 60, 70, 80, 90, 100]:
            menu.add_element(UIElement(
                str(boost),
                function=self._set_max_boost,
                function_args=boost
            ), column=1)
        
        return menu
    
    def _create_timeout_menu(self):
        """Create menu for setting timeout"""
        menu = MenuRenderer(self.renderer, columns=1, render_function=self._render_playlist_details)
        menu.add_element(UIElement("Set Timeout (seconds)", header=True))
        
        for timeout in [5.0, 7.0, 10.0, 15.0, 20.0, 30.0]:
            menu.add_element(UIElement(
                f"{timeout}s",
                function=self._set_timeout,
                function_args=timeout
            ))
        
        return menu
    
    # Temporary variables for scenario creation
    temp_offensive_mode = None
    temp_defensive_mode = None
    temp_player_role = None
    
    def _set_playlist_name(self, name):
        self.current_playlist_name = name
        print(f"Playlist name set to: {name}")
    
    def _set_temp_offensive_mode(self, mode):
        self.temp_offensive_mode = mode
        print(f"Selected offensive mode: {mode.name}")
    
    def _set_temp_defensive_mode(self, mode):
        self.temp_defensive_mode = mode
        print(f"Selected defensive mode: {mode.name}")
    
    def _set_temp_player_role(self, role):
        self.temp_player_role = role
        print(f"Selected player role: {role.name}")
    
    def _add_current_scenario(self):
        """Add the currently selected scenario configuration"""
        if self.temp_offensive_mode and self.temp_defensive_mode and self.temp_player_role:
            scenario = ScenarioConfig(
                offensive_mode=self.temp_offensive_mode,
                defensive_mode=self.temp_defensive_mode,
                player_role=self.temp_player_role
            )
            self.current_scenarios.append(scenario)
            print(f"Added scenario: {self.temp_offensive_mode.name} vs {self.temp_defensive_mode.name} ({self.temp_player_role.name})")
            
            # Reset temp variables
            self.temp_offensive_mode = None
            self.temp_defensive_mode = None
            self.temp_player_role = None
            
            # Exit the submenu
            if self.main_menu_renderer:
                self.main_menu_renderer.handle_back_key()
        else:
            print("Please select offensive mode, defensive mode, and player role first")
    
    
    
    def _set_min_boost(self, boost):
        """Set minimum boost value"""
        self.current_boost_range = (boost, max(boost + 10, self.current_boost_range[1]))
        print(f"Set boost range: {self.current_boost_range}")
    
    def _set_max_boost(self, boost):
        """Set maximum boost value"""
        self.current_boost_range = (min(boost - 10, self.current_boost_range[0]), boost)
        print(f"Set boost range: {self.current_boost_range}")
    
    def _set_timeout(self, timeout):
        """Set scenario timeout"""
        self.current_timeout = timeout
        print(f"Set timeout: {timeout}s")
    
    def _toggle_rule_zero(self):
        """Toggle rule zero setting"""
        self.current_rule_zero = not self.current_rule_zero
        print(f"Rule zero: {'ON' if self.current_rule_zero else 'OFF'}")
    
    
    def _save_current_playlist(self):
        """Save the currently configured playlist to file, and register it in the playlist registry"""
        if not self.current_playlist_name:
            print("Please set a playlist name first")
            return
        
        # Register the playlist in the playlist registry 
        # and save it to file
        playlist = Playlist(
            name=self.current_playlist_name,
            description=f"Custom playlist with {len(self.current_scenarios)} scenarios",
            scenarios=self.current_scenarios.copy(),
            custom_scenarios=self.current_custom_scenarios.copy(),
            settings=PlaylistSettings(timeout=self.current_timeout, shuffle=True, boost_range=self.current_boost_range, rule_zero=self.current_rule_zero)
        )
        
        with open(os.path.join(_get_custom_playlists_path(), f"{self.current_playlist_name}.json"), "w") as f:
            f.write(playlist.model_dump_json())

    def _cancel_playlist_creation(self):
        """Cancel playlist creation and reset"""
        self._reset_current_playlist()
        print("Playlist creation cancelled")
    
    def _reset_current_playlist(self):
        """Reset current playlist creation data"""
        self.current_playlist_name = ""
        self.current_scenarios = []
        self.current_custom_scenarios = []
        self.current_boost_range = [12, 100]
        self.current_timeout = 7.0
        self.current_rule_zero = False
        self.temp_offensive_mode = None
        self.temp_defensive_mode = None
        self.temp_player_role = None
        
    def _add_custom_scenario(self, scenario_name):
        """Add a custom scenario"""
        self.current_custom_scenarios.append(CustomScenario.load(scenario_name))
        print(f"Added custom scenario: {scenario_name}")
    
    def get_custom_playlists(self):
        """Get all custom playlists"""
        # Load all custom playlists from disk
        custom_playlists = {}
        for file in os.listdir(_get_custom_playlists_path()):
            if file.endswith(".json"):
                with open(os.path.join(_get_custom_playlists_path(), file), "r") as f:
                    custom_playlists[file.replace(".json", "")] = Playlist.model_validate_json(f.read())
        return custom_playlists
    

def _get_custom_playlists_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo", "Playlists")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo", "Playlists"))
    return os.path.join(appdata_path, "RLBot", "Dojo", "Playlists")
