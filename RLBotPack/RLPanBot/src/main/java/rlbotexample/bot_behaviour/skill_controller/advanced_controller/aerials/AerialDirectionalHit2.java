package rlbotexample.bot_behaviour.skill_controller.advanced_controller.aerials;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.prediction.Parabola3D;
import rlbotexample.output.BotOutput;
import util.controllers.BoostController;
import util.game_constants.RlConstants;
import util.renderers.ShapeRenderer;
import util.vector.Vector3;

import java.awt.*;

public class AerialDirectionalHit2 extends SkillController {

    private BotBehaviour bot;
    private AerialOrientationHandler aerialOrientationHandler;
    private JumpHandler jumpHandler;
    private Vector3 ballDestination;
    private Vector3 playerDestination;
    private Vector3 futureBallPosition;
    private Vector3 orientation;
    private double timeToReachAerial;

    public AerialDirectionalHit2(BotBehaviour bot) {
        this.bot = bot;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        this.jumpHandler = new JumpHandler();

        this.orientation = new Vector3();
        this.ballDestination = new Vector3();
        this.playerDestination = new Vector3();
        this.futureBallPosition = new Vector3();
        this.timeToReachAerial = 0;
    }

    public void setBallDestination(Vector3 destination) {
        this.ballDestination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;

        playerDestination = input.ballPrediction.ballAtTime(0).position;
        // uh... try to binary search the right ball I guess?
        Vector3 orientationWithoutGravity = new Vector3();
        for(int i = 0; i < 100; i++) {
            Vector3 unscaledOrientationWithGravity = playerDestination.minus(input.car.velocity.plus(input.car.velocity.projectOnto(input.car.position.minus(playerDestination)).scaled(-1)).scaled(10))
                    .minus(input.car.position);
            //Vector3 unscaledOrientationWithGravity = playerDestination.minus(input.car.position).normalized();
            // fancy math to retrieve the desired orientation of player from the applied acceleration vector, without gravity
            //double angleFromZCoordinate = Math.atan(globalOrientationWithGravity.minus(input.car.position).z / globalOrientationWithGravity.minus(input.car.position).flatten().magnitude());
            double angleFromZCoordinate = Math.atan(unscaledOrientationWithGravity.z / unscaledOrientationWithGravity.flatten().magnitude());
            double lengthOfVector = RlConstants.NORMAL_GRAVITY_STRENGTH + ((1 - Math.cos(angleFromZCoordinate)) * (RlConstants.ACCELERATION_DUE_TO_BOOST - RlConstants.NORMAL_GRAVITY_STRENGTH));
            Vector3 orientationWithGravity = unscaledOrientationWithGravity.scaledToMagnitude(lengthOfVector);
            orientationWithoutGravity = orientationWithGravity.minus(new Vector3(0, 0, -RlConstants.NORMAL_GRAVITY_STRENGTH));
            orientation = orientationWithoutGravity
            //        .minus(input.car.velocity.plus(input.car.velocity.projectOnto(input.car.position.minus(playerDestination)).scaled(-1)).scaled(3))
                    .plus(input.car.position);

            // try to calculate the time it'll take to reach the destination?
            double a = input.car.orientation.noseVector.scaled(RlConstants.ACCELERATION_DUE_TO_BOOST)
                    .plus(Vector3.UP_VECTOR.scaled(RlConstants.NORMAL_GRAVITY_STRENGTH))
                    .projectOnto(input.car.position.minus(playerDestination)).magnitude()/2;
            double b = input.car.velocity.projectOnto(input.car.position.minus(playerDestination)).magnitude();
            double c = -input.car.position.minus(playerDestination).magnitude();
            timeToReachAerial = (-b + Math.sqrt(b*b - 4*a*c))
                                                    / (2*a);
            //System.out.println(timeToReachDestination);

            futureBallPosition = input.ballPrediction.ballAtTime(timeToReachAerial).position;

            Vector3 offset = futureBallPosition.minus(ballDestination).scaledToMagnitude(RlConstants.BALL_RADIUS);
            playerDestination = futureBallPosition.plus(offset);
        }

        //output.boost(input.car.orientation.noseVector.dotProduct(orientationWithoutGravity.normalized()) > 0.7);
        output.boost(BoostController.process(input.car.orientation.noseVector.dotProduct(orientation.minus(input.car.position).normalized())*1.3));

        // set the desired orientation and apply it
        aerialOrientationHandler.setDestination(orientation);
        if(timeToReachAerial < 1.5) {
            aerialOrientationHandler.setRollOrientation(input.ball.position);
        }
        else {
            aerialOrientationHandler.setRollOrientation(input.car.position.plus(input.car.orientation.roofVector));
        }
        aerialOrientationHandler.updateOutput(input);

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
        renderer.drawLine3d(Color.green, input.car.position, orientation);
        ShapeRenderer shapeRenderer = new ShapeRenderer(renderer);
        shapeRenderer.renderCross(playerDestination, Color.red);
        shapeRenderer.renderCross(ballDestination, Color.MAGENTA);
        renderer.drawLine3d(Color.cyan, playerDestination, futureBallPosition);
    }
}
