package rlbotexample.bot_behaviour.skill_controller.basic_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.vector.Vector2;
import util.vector.Vector3;

public class AerialOrientationHandler extends SkillController {

    private BotBehaviour bot;
    private Vector3 playerDestination;
    private Vector3 rollOrientation;

    private PidController pitchPid;
    private PidController yawPid;
    private PidController rollPid;

    public AerialOrientationHandler(BotBehaviour bot) {
        this.bot = bot;
        this.playerDestination = new Vector3();
        this.rollOrientation = new Vector3();

        this.pitchPid = new PidController(2.6, 0, 21);
        this.yawPid = new PidController(2.6, 0, 21);
        this.rollPid = new PidController(2.9, 0, 20.5);
    }

    public void setDestination(Vector3 globalDestination) {
        playerDestination = globalDestination;
    }

    public void setRollOrientation(Vector3 rollOrientation) {
        this.rollOrientation = rollOrientation;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 localPlayerOrientationVector = CarDestination.getLocal(playerDestination, input);
        Vector3 localRollDestination = CarDestination.getLocal(rollOrientation, input);

        double pitchAmount = pitchPid.process(new Vector2(localPlayerOrientationVector.x, -localPlayerOrientationVector.z).correctionAngle(new Vector2(1, 0)), 0);
        double yawAmount = yawPid.process(new Vector2(localPlayerOrientationVector.x, localPlayerOrientationVector.y).correctionAngle(new Vector2(1, 0)), 0);
        double rollAmount = rollPid.process(new Vector2(localRollDestination.z, localRollDestination.y).correctionAngle(new Vector2(1, 0)), 0);

        output.pitch(pitchAmount);
        output.yaw(yawAmount);
        output.roll(rollAmount);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {

    }
}
