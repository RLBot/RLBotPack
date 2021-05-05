package rlbotexample.bot_behaviour.skill_controller.basic_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.controllers.ThrottleController;
import util.vector.Vector3;

import java.awt.*;

public class DriveToDestination2Controller extends SkillController {

    private final BotBehaviour bot;
    private final DrivingSpeedController drivingSpeedController;
    private final GroundOrientationController groundOrientationController;
    private final AerialOrientationHandler aerialOrientationHandler;
    private double speedToReach;
    private Vector3 destination;

    public DriveToDestination2Controller(BotBehaviour bot) {
        this.bot = bot;
        this.drivingSpeedController = new DrivingSpeedController(bot);
        this.groundOrientationController = new GroundOrientationController(bot);
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        this.speedToReach = 1410;
    }

    public void setDestination(final Vector3 destination) {
        this.destination = destination;
    }

    public void setSpeed(final double speedToReach) {
        this.speedToReach = speedToReach;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        drivingSpeedController.setSpeed(speedToReach);
        groundOrientationController.setDestination(destination);
        aerialOrientationHandler.setDestination(destination);
        aerialOrientationHandler.setRollOrientation(new Vector3(0, 0, 10000));

        drivingSpeedController.updateOutput(input);
        groundOrientationController.updateOutput(input);
        aerialOrientationHandler.updateOutput(input);
        output.boost(speedToReach > 1410 && input.car.velocity.magnitude() < speedToReach && input.car.orientation.noseVector.dotProduct(destination.minus(input.car.position).normalized()) > 0);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {

    }
}
