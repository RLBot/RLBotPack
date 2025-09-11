import numpy as np
import time
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

from .base_mode import BaseGameMode
from game_state import RacePhase, CarIndex
import race
from race_record import RaceRecord, RaceRecords, store_race_records


class RaceMode(BaseGameMode):
    """Handles race-based training mode"""
    
    def __init__(self, game_state, game_interface):
        super().__init__(game_state, game_interface)
        self.race = None
        self.rlbot_game_state = None
        self.last_menu_phase_time = 0
    
    def initialize(self):
        """Initialize race mode"""
        np.random.seed(0)
        self.game_state.human_score = 0
        self.game_state.bot_score = 0
        self.game_state.started_time = self.game_state.cur_time
        self.game_state.game_phase = RacePhase.SETUP
        
        # Set up initial car positions
        car_states = {}
        
        # Spawn the player car in the middle of the map
        player_car_state = CarState(
            physics=Physics(
                location=Vector3(0, 0, 0), 
                velocity=Vector3(0, 0, 0), 
                rotation=Rotator(0, 0, 0)
            )
        )
        
        # Tuck the bot above the map
        bot_car_state = CarState(
            physics=Physics(
                location=Vector3(0, 0, 2500), 
                velocity=Vector3(0, 0, 0), 
                rotation=Rotator(0, 0, 0)
            )
        )
        
        car_states[CarIndex.HUMAN.value] = player_car_state
        car_states[CarIndex.BOT.value] = bot_car_state
        
        self.rlbot_game_state = GameState(cars=car_states)
        self.set_game_state(self.rlbot_game_state)
    
    def cleanup(self):
        """Clean up race mode resources"""
        self.race = None
    
    def update(self, packet):
        """Update race mode based on current game phase"""
        if self.game_state.paused:
            return
            
        phase_handlers = {
            RacePhase.INIT: self._handle_init_phase,
            RacePhase.SETUP: self._handle_setup_phase,
            RacePhase.ACTIVE: self._handle_active_phase,
            RacePhase.MENU: self._handle_menu_phase,
            RacePhase.EXITING_MENU: self._handle_menu_exiting_phase,
            RacePhase.FINISHED: self._handle_finished_phase,
        }
        
        handler = phase_handlers.get(self.game_state.game_phase)
        if handler:
            handler(packet)
    
    def _handle_init_phase(self, packet):
        """Handle initialization phase"""
        self.initialize()
    
    def _handle_setup_phase(self, packet):
        """Handle setup phase - create new race"""
        self.race = race.Race()
        ball_state = self.race.BallState()
        
        self.rlbot_game_state = GameState(ball=ball_state)
        self.set_game_state(self.rlbot_game_state)
        self.game_state.game_phase = RacePhase.ACTIVE
    
    def _handle_active_phase(self, packet):
        """Handle active race phase"""
        # Check if the current ball location has moved significantly
        if self._ball_moved_significantly(packet):
            self.game_state.human_score += 1
            self.game_state.game_phase = RacePhase.SETUP
            
            if self.game_state.human_score >= self.game_state.num_trials:
                self.game_state.game_phase = RacePhase.FINISHED
                return
        
        # Continue setting the ball location to the race ball location
        self._update_game_state(packet)
    
    def _handle_menu_phase(self, packet):
        """Handle menu phase"""
        self.set_game_state(self.rlbot_game_state)
        self.last_menu_phase_time = time.time()
        
    def _handle_menu_exiting_phase(self, packet):
        """Unfreeze game state after a 3 second countdown"""
        # For each second, render a countdown from 3 to 1
        if time.time() - self.last_menu_phase_time > 3:
            self.game_state.game_phase = RacePhase.ACTIVE
        else:
            self.game_interface.renderer.begin_rendering()
            self.game_interface.renderer.draw_string_2d(850, 200, 15, 15, str(3 - int(time.time() - self.last_menu_phase_time)), self.game_interface.renderer.white())
            self.game_interface.renderer.end_rendering()
            self.set_game_state(self.rlbot_game_state)
    
    def _handle_finished_phase(self, packet):
        """Handle finished phase - save records and restart"""
        self.set_game_state(self.rlbot_game_state)
        
        # Save the record
        if self.game_state.human_score >= self.game_state.num_trials:
            total_time = self.game_state.cur_time - self.game_state.started_time
            print(f"Race completed in {total_time} seconds")
            
            record = RaceRecord(
                number_of_trials=self.game_state.num_trials,
                time_to_finish=float(total_time)
            )
            self.game_state.race_mode_records.set_record(record)
            store_race_records(self.game_state.race_mode_records)
        
        time.sleep(10)
        self.game_state.game_phase = RacePhase.INIT
    
    def _ball_moved_significantly(self, packet) -> bool:
        """Check if the ball has moved significantly from its target position"""
        if not self.rlbot_game_state or not self.rlbot_game_state.ball:
            return False
            
        target_pos = self.rlbot_game_state.ball.physics.location
        current_pos = packet.game_ball.physics.location
        
        return (abs(target_pos.x - current_pos.x) > 2 or
                abs(target_pos.y - current_pos.y) > 2 or
                abs(target_pos.z - current_pos.z) > 2)
    
    def _update_game_state(self, packet):
        """Update the game state with current car position and race ball position"""
        ball_state = self.race.BallState()
        car_states = {}
        
        # Preserve human car state
        human_car = packet.game_cars[CarIndex.HUMAN.value]
        human_car_state = CarState(
            physics=Physics(
                location=Vector3(
                    human_car.physics.location.x,
                    human_car.physics.location.y,
                    human_car.physics.location.z
                ),
                velocity=Vector3(
                    human_car.physics.velocity.x,
                    human_car.physics.velocity.y,
                    human_car.physics.velocity.z
                ),
                rotation=Rotator(
                    human_car.physics.rotation.pitch,
                    human_car.physics.rotation.yaw,
                    human_car.physics.rotation.roll
                )
            )
        )
        
        # Keep bot tucked away
        bot_car_state = CarState(
            physics=Physics(
                location=Vector3(0, 0, 2500),
                velocity=Vector3(0, 0, 0),
                rotation=Rotator(0, 0, 0)
            )
        )
        
        car_states[CarIndex.HUMAN.value] = human_car_state
        car_states[CarIndex.BOT.value] = bot_car_state
        
        self.rlbot_game_state = GameState(cars=car_states, ball=ball_state)
        self.set_game_state(self.rlbot_game_state) 
