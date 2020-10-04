package rlbotexample.bot_behaviour.skill_controller.basic_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.renderers.ShapeRenderer;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class GroundOrientationController extends SkillController {

    final private BotBehaviour bot;
    final PidController turningRatePid = new PidController(5, 0, 1);
    double turningRate;
    Vector3 destination;

    public GroundOrientationController(BotBehaviour bot) {
        this.bot = bot;
        this.turningRate = 0;
        this.destination = new Vector3();
    }

    public void setDestination(final Vector3 destinationToFace) {
        this.destination = destinationToFace;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 localDestination = destination.minus(input.car.position).toFrameOfReference(input.car.orientation.noseVector, input.car.orientation.roofVector);
        turningRate = turningRatePid.process(localDestination.flatten().correctionAngle(new Vector2(1, 0)), 0);
        output.steer(turningRate);
        output.drift(Math.abs(turningRate) > 7);

        //System.out.println(turningRate);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        ShapeRenderer shapeRenderer = new ShapeRenderer(renderer);
        shapeRenderer.renderCross(destination, Color.blue);
    }
}
