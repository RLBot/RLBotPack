import json
import os
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

class Vector3Model(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)

class RotatorModel(BaseModel):
    pitch: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    roll: float = Field(default=0.0)

class PhysicsModel(BaseModel):
    location: Vector3Model = Field(default_factory=Vector3Model)
    rotation: RotatorModel = Field(default_factory=RotatorModel)
    velocity: Vector3Model = Field(default_factory=Vector3Model)
    angular_velocity: Optional[Vector3Model] = None

class CarStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)
    boost_amount: float = Field(default=0.0)
    jumped: bool = Field(default=False)
    double_jumped: bool = Field(default=False)

class BallStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)

class TypedGameState(BaseModel):
    cars: Dict[int, CarStateModel] = Field(default_factory=dict)
    ball: Optional[BallStateModel] = None

    @classmethod
    def from_game_state(cls, game_state: GameState) -> 'TypedGameState':
        """Convert RLBot GameState to TypedGameState"""
        cars = {}
        if game_state.cars is not None:
            for idx, car in game_state.cars.items():
                if car is None:
                    continue
                
                cars[idx] = CarStateModel(
                    # Check all members of car.physics are not None
                    physics=PhysicsModel(
                        location=Vector3Model(
                            x=car.physics.location.x if car.physics.location is not None else 0.0,
                            y=car.physics.location.y if car.physics.location is not None else 0.0,
                            z=car.physics.location.z if car.physics.location is not None else 0.0
                        ),
                        rotation=RotatorModel(
                            pitch=car.physics.rotation.pitch if car.physics.rotation is not None else 0.0,
                            yaw=car.physics.rotation.yaw if car.physics.rotation is not None else 0.0,
                            roll=car.physics.rotation.roll if car.physics.rotation is not None else 0.0
                        ),
                        velocity=Vector3Model(
                            x=car.physics.velocity.x if car.physics.velocity is not None else 0.0,
                            y=car.physics.velocity.y if car.physics.velocity is not None else 0.0,
                            z=car.physics.velocity.z if car.physics.velocity is not None else 0.0
                        ),
                        angular_velocity=Vector3Model(
                            x=car.physics.angular_velocity.x if car.physics.angular_velocity is not None else 0.0,
                            y=car.physics.angular_velocity.y if car.physics.angular_velocity is not None else 0.0,
                            z=car.physics.angular_velocity.z if car.physics.angular_velocity is not None else 0.0
                        )
                    ),
                    boost_amount=car.boost_amount if car.boost_amount is not None else 0.0,
                    jumped=car.jumped if car.jumped is not None else False,
                    double_jumped=car.double_jumped if car.double_jumped is not None else False
                )

        ball = None
        if game_state.ball is not None:
            ball = BallStateModel(
                physics=PhysicsModel(
                    location=Vector3Model(
                        x=game_state.ball.physics.location.x if game_state.ball.physics.location is not None else 0.0,
                        y=game_state.ball.physics.location.y if game_state.ball.physics.location is not None else 0.0,
                        z=game_state.ball.physics.location.z if game_state.ball.physics.location is not None else 0.0
                    ),
                    rotation=RotatorModel(
                        pitch=game_state.ball.physics.rotation.pitch if game_state.ball.physics.rotation is not None else 0.0,
                        yaw=game_state.ball.physics.rotation.yaw if game_state.ball.physics.rotation is not None else 0.0,
                        roll=game_state.ball.physics.rotation.roll if game_state.ball.physics.rotation is not None else 0.0
                    ),
                    velocity=Vector3Model(
                        x=game_state.ball.physics.velocity.x if game_state.ball.physics.velocity is not None else 0.0,
                        y=game_state.ball.physics.velocity.y if game_state.ball.physics.velocity is not None else 0.0,
                        z=game_state.ball.physics.velocity.z if game_state.ball.physics.velocity is not None else 0.0
                    ),
                    angular_velocity=Vector3Model(
                        x=game_state.ball.physics.angular_velocity.x if game_state.ball.physics.angular_velocity is not None else 0.0,
                        y=game_state.ball.physics.angular_velocity.y if game_state.ball.physics.angular_velocity is not None else 0.0,
                        z=game_state.ball.physics.angular_velocity.z if game_state.ball.physics.angular_velocity is not None else 0.0
                    )
                )
            )

        return cls(cars=cars, ball=ball)

    def to_game_state(self) -> GameState:
        """Convert TypedGameState back to RLBot GameState"""
        cars = {}
        for idx, car in self.cars.items():
            cars[idx] = CarState(
                physics=Physics(
                    location=Vector3(
                        x=car.physics.location.x,
                        y=car.physics.location.y,
                        z=car.physics.location.z
                    ),
                    rotation=Rotator(
                        pitch=car.physics.rotation.pitch,
                        yaw=car.physics.rotation.yaw,
                        roll=car.physics.rotation.roll
                    ),
                    velocity=Vector3(
                        x=car.physics.velocity.x,
                        y=car.physics.velocity.y,
                        z=car.physics.velocity.z
                    ),
                    angular_velocity=Vector3(
                        x=car.physics.angular_velocity.x,
                        y=car.physics.angular_velocity.y,
                        z=car.physics.angular_velocity.z
                    )
                ),
                boost_amount=car.boost_amount,
                jumped=car.jumped,
                double_jumped=car.double_jumped
            )

        ball = None
        if self.ball is not None:
            ball = BallState(
                physics=Physics(
                    location=Vector3(
                        x=self.ball.physics.location.x,
                        y=self.ball.physics.location.y,
                        z=self.ball.physics.location.z
                    ),
                    rotation=Rotator(
                        pitch=self.ball.physics.rotation.pitch,
                        yaw=self.ball.physics.rotation.yaw,
                        roll=self.ball.physics.rotation.roll
                    ),
                    velocity=Vector3(
                        x=self.ball.physics.velocity.x,
                        y=self.ball.physics.velocity.y,
                        z=self.ball.physics.velocity.z
                    ),
                    angular_velocity=Vector3(
                        x=self.ball.physics.angular_velocity.x,
                        y=self.ball.physics.angular_velocity.y,
                        z=self.ball.physics.angular_velocity.z
                    )
                )
            )

        return GameState(cars=cars, ball=ball)

class CustomScenario(BaseModel):
    """A custom scenario that can be saved to and loaded from disk.
    
    Attributes:
        name: The name of the scenario
        game_state: The game state for this scenario
    """
    name: str
    game_state: TypedGameState

    @classmethod
    def from_rlbot_game_state(cls, name: str, game_state: GameState) -> 'CustomScenario':
        """Create a CustomScenario from an RLBot GameState"""
        return cls(
            name=name,
            game_state=TypedGameState.from_game_state(game_state)
        )

    def to_rlbot_game_state(self) -> GameState:
        """Convert this scenario back to an RLBot GameState"""
        return self.game_state.to_game_state()

    def save(self) -> None:
        """Save this scenario to disk"""
        if not self.name:
            raise ValueError("Scenario must have a name before saving")
        
        # Ensure the scenarios directory exists
        os.makedirs(_get_custom_scenarios_path(), exist_ok=True)
        
        # Save to file
        file_path = os.path.join(_get_custom_scenarios_path(), f"{self.name}.json")
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, name: str) -> 'CustomScenario':
        """Load a specific scenario by name"""
        file_path = os.path.join(_get_custom_scenarios_path(), f"{name}.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No scenario found with name '{name}'")
        
        with open(file_path, "r") as f:
            return cls.model_validate_json(f.read())



def get_custom_scenarios():
    """Get all custom scenarios"""
    custom_scenarios = {}
    for file in os.listdir(_get_custom_scenarios_path()):
        if file.endswith(".json"):
            custom_scenarios[file.replace(".json", "")] = CustomScenario.load(file.replace(".json", ""))
    return custom_scenarios

def _get_custom_scenarios_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios"))
    return os.path.join(appdata_path, "RLBot", "Dojo", "Scenarios")
