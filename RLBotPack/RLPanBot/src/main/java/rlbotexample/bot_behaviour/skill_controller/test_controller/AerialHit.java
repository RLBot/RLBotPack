package rlbotexample.bot_behaviour.skill_controller.test_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.prediction.Predictions;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

import java.awt.*;

public class AerialHit extends SkillController {

    private BotBehaviour bot;
    private Predictions predictions;
    private AerialOrientationHandler aerialOrientationHandler;
    private JumpHandler jumpHandler;
    private Vector3 orientation;

    public AerialHit(BotBehaviour bot, Predictions predictions) {
        this.bot = bot;
        this.predictions = predictions;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        this.jumpHandler = new JumpHandler();
        this.orientation = new Vector3();
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;

        // try to predict the point in time with which we should try to hit the getNativeBallPrediction
        double timeBeforeReachingBall = input.ball.position.minus(playerPosition).magnitude()/(input.ball.velocity.minus(playerSpeed).magnitude()*1.2);
        if(timeBeforeReachingBall > 6) {
            timeBeforeReachingBall = 6;
        }

        // get the future player and getNativeBallPrediction positions
        Vector3 playerFuturePosition = input.ball.position;
        if(input.ball.velocity.magnitude() > 0.1) {
            playerFuturePosition = predictions.aerialKinematicBody(playerPosition, playerSpeed, timeBeforeReachingBall).getPosition();
        }
        Vector3 ballFuturePosition = predictions.getNativeBallPrediction(input.ball.position, timeBeforeReachingBall).getPosition();

        // get the orientation we should have to hit the getNativeBallPrediction
        Vector3 orientation = ballFuturePosition.minus(playerFuturePosition);

        this.orientation = orientation;

        // set the desired orientation and apply it
        aerialOrientationHandler.setDestination(orientation.plus(playerPosition));
        aerialOrientationHandler.updateOutput(input);

        // boost to the destination
        if(input.car.orientation.noseVector.dotProduct(orientation)/orientation.magnitude() > 0.7) {
            output.boost(true);
        }
        else {
            output.boost(false);
        }

        // jump to the destination if we're on the ground
        if (jumpHandler.isJumpFinished()) {
            if(input.car.hasWheelContact) {
                jumpHandler.setJumpType(new ShortJump());
            }
            else {
                jumpHandler.setJumpType(new SimpleJump());
            }
        }
        jumpHandler.updateJumpState(
                input,
                output,
                CarDestination.getLocal(
                        orientation.minus(playerPosition),
                        input
                ),
                new Vector3()
        );
        output.jump(jumpHandler.getJumpState());
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.green, input.car.position, orientation.plus(input.car.position));

    }
}
