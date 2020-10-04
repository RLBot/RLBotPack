package rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Flip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public class Flick extends SkillController {

    private static final double PLAYER_DISTANCE_FROM_BALL_WHEN_CONSIDERED_FLICKING = 130;

    private CarDestination desiredDestination;
    private BotBehaviour bot;
    private Dribble dribbleController;
    private JumpHandler jumpHandler;
    private boolean isFlicking;
    private boolean isLastFlickingFrame;

    public Flick(CarDestination desiredDestination, BotBehaviour bot) {
        this.desiredDestination = desiredDestination;
        this.bot = bot;
        this.dribbleController = new Dribble(desiredDestination, bot);
        this.jumpHandler = new JumpHandler();
        this.isFlicking = false;
        this.isLastFlickingFrame = false;
    }

    @Override
    public void updateOutput(DataPacket input) {
        // get useful values
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;
        Vector3 ballPosition = input.ball.position;
        Vector3 localBallPosition = CarDestination.getLocal(ballPosition, input);
        //Vector3 nonUniformScaledPlayerDistanceFromBall = ((aerialKinematicBody.minus(getNativeBallPrediction)).minusAngle(playerNoseOrientation)).scaled(1, 1, 1);

        /*
        // if the bot can flick
        if(nonUniformScaledPlayerDistanceFromBall.magnitude() < PLAYER_DISTANCE_FROM_BALL_WHEN_CONSIDERED_FLICKING) {
            // flick
            isFlicking = true;
        } */

        // if the bot can flick
        if(Math.abs(localBallPosition.z) < 160
                && Math.abs(localBallPosition.x) < 120
                && Math.abs(localBallPosition.y) < 155
                && !isFlicking) {
            // flick
            isFlicking = true;
            //System.out.println("flick");
        }

        if(isFlicking) {
            updateJumpBehaviour(input);
        }
        else {
            // try to dribble so we can flick afterwards
            dribbleController.updateOutput(input);
        }
    }

    private void updateJumpBehaviour(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 myRoofVector = input.car.orientation.roofVector;
        Vector3 playerDestination = desiredDestination.getThrottleDestination();
        Vector3 ballPosition = input.ball.position;

        if (jumpHandler.isJumpFinished()) {

            if(jumpHandler.hasFirstJump()) {
                jumpHandler.setJumpType(new ShortJump());
                isLastFlickingFrame = false;

                // don't rotate before flicking
                output.pitch(0);
                output.yaw(0);
                output.roll(0);

            }
            else if(jumpHandler.hasSecondJump()) {
                jumpHandler.setJumpType(new Flip());
                isLastFlickingFrame = true;
            }
        }
        jumpHandler.updateJumpState(
                input,
                output,
                CarDestination.getLocal(ballPosition, input),
                new Vector3()
        );

        if (jumpHandler.isJumpFinished()) {
            if (isLastFlickingFrame) {
                isFlicking = false;
            }
        }
        output.jump(jumpHandler.getJumpState());
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        dribbleController.debug(renderer, input);
    }
}
