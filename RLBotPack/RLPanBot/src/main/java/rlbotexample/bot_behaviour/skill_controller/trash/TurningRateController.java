package rlbotexample.bot_behaviour.skill_controller.trash;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.controllers.ThrottleController;
import util.vector.Vector3;

import java.awt.*;

public class TurningRateController extends SkillController {

    final private BotBehaviour bot;
    final PidController steerPid = new PidController(1, 0, 0);
    double turningRateToReach;
    double steerAmount;
    double actualTurningRate;

    public TurningRateController(BotBehaviour bot) {
        this.bot = bot;
        turningRateToReach = 1410;
        steerAmount = 0;
        actualTurningRate = 0;
    }

    public void setTurningRate(final double turningRateToReach) {
        this.turningRateToReach = turningRateToReach;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        actualTurningRate = input.car.spin.dotProduct(input.car.orientation.roofVector);
        if(input.car.hasWheelContact) {
            steerAmount = steerPid.process(turningRateToReach, actualTurningRate);
        }
        //System.out.println(steerAmount);
        //System.out.println(steerPid.getIntegralAmount());
        //System.out.println(actualTurningRate);
        output.steer(steerAmount);
        output.drift(Math.abs(steerAmount) > 1);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        if(actualTurningRate-turningRateToReach < 0) {
            renderer.drawLine3d(Color.green, input.car.position.plus(new Vector3(0, 0, 100)), input.car.position.plus(input.car.orientation.rightVector.scaled(actualTurningRate-turningRateToReach * -100)).plus(new Vector3(0, 0, 100)));
        }
        else {
            renderer.drawLine3d(Color.red, input.car.position.plus(new Vector3(0, 0, 100)), input.car.position.plus(input.car.orientation.rightVector.scaled(actualTurningRate-turningRateToReach * -100)).plus(new Vector3(0, 0, 100)));
        }
        if(steerAmount > 1) {
            renderer.drawCenteredRectangle3d(Color.blue, input.car.position.plus(new Vector3(0, 0, 100)), 10, 10, true);
        }
    }
}
