package rlbotexample.bot_behaviour.skill_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.DrivingSpeedController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.HalfFlip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.game_constants.RlConstants;
import util.parameter_configuration.ArbitraryValueSerializer;
import util.parameter_configuration.PidSerializer;
import util.vector.Vector2;
import util.vector.Vector3;

public class KickoffController extends SkillController {
    private BotBehaviour bot;
    private final DrivingSpeedController drivingSpeedController;

    public KickoffController(BotBehaviour bot) {
        super();
        this.bot = bot;
        drivingSpeedController = new DrivingSpeedController(bot);
        drivingSpeedController.setSpeed(RlConstants.CAR_MAX_SPEED);
    }

    @Override
    public void updateOutput(DataPacket input) {
        drivingSpeedController.updateOutput(input);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
