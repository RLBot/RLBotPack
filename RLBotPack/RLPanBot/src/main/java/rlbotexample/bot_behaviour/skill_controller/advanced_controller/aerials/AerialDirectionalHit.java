package rlbotexample.bot_behaviour.skill_controller.advanced_controller.aerials;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.RlUtils;
import rlbotexample.input.prediction.Parabola3D;
import rlbotexample.input.prediction.Predictions;
import rlbotexample.output.BotOutput;
import util.game_constants.RlConstants;
import util.renderers.ShapeRenderer;
import util.vector.Vector3;

import java.awt.*;
import java.util.List;

public class AerialDirectionalHit extends SkillController {

    private BotBehaviour bot;
    private AerialOrientationHandler aerialOrientationHandler;
    private JumpHandler jumpHandler;
    private Vector3 ballDestination;

    private Vector3 orientation;
    private Vector3 hitPositionOnBall;
    private Vector3 ballFuturePosition;
    private Vector3 playerFuturePosition;

    public AerialDirectionalHit(BotBehaviour bot) {
        this.bot = bot;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        this.jumpHandler = new JumpHandler();
        this.ballDestination = new Vector3();

        this.orientation = new Vector3();
        this.hitPositionOnBall = new Vector3();
        this.ballFuturePosition = new Vector3();
        this.playerFuturePosition = new Vector3();
    }

    public void setBallDestination(Vector3 destination) {
        ballDestination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerDistanceFromBall = input.ball.position.minus(playerPosition);
        Vector3 playerSpeedFromBall = input.ball.velocity.minus(playerSpeed);

        double timeBeforeReachingBall = RlUtils.timeToReachAerialDestination(input, playerDistanceFromBall, playerSpeedFromBall);

        /*
        final List<Double> timeOfBallBounces = input.ballPrediction.ballBounceTimes();
        for(int i = 0; i < timeOfBallBounces.size(); i++) {
            if(timeBeforeReachingBall < timeOfBallBounces.get(i)) {
                break;
            }
            double nextTimeOfBallBounce = timeOfBallBounces.get(i);
            BallData nextBallBounce = input.ballPrediction.ballAtTime(nextTimeOfBallBounce);
            timeBeforeReachingBall = nextTimeOfBallBounce + RlUtils.timeToReachAerialDestination(input, playerDistanceFromBall, nextBallBounce.velocity.minus(playerSpeed));
        }*/

        // get the future player and getNativeBallPrediction positions
        //playerFuturePosition = input.ballPrediction.carsAtTime(timeBeforeReachingBall).get(input.playerIndex).position;
        playerFuturePosition = new Parabola3D(input.car.position,
                input.car.velocity,
                new Vector3(0, 0, -1).scaled(RlConstants.NORMAL_GRAVITY_STRENGTH), 0)
                .compute(timeBeforeReachingBall);
        BallData futureBall = input.ballPrediction.ballAtTime(timeBeforeReachingBall);

        //////// added stuff to help cope with unreachable balls... not too successful maybe ^^'

        //System.out.println(timeBeforeReachingBall);
        ////////

        // get the getNativeBallPrediction offset so we actually hit the getNativeBallPrediction to make it go in the desired direction
        Vector3 ballOffset = futureBall.position.minus(ballDestination)
                //.plus(new Vector3(0, 0, -1).scaled(Math.max((2040 - futureBall.position.z) - ballDestination.z, 0) * 2))
                .scaledToMagnitude(RlConstants.BALL_RADIUS);

        // get the orientation we should have to hit the ball
        Vector3 orientation = futureBall.position.plus(ballOffset).minus(playerFuturePosition);

        // update variables so we can print them later in the debugger
        hitPositionOnBall = futureBall.position.plus(ballOffset);
        this.orientation = orientation;
        this.ballFuturePosition = futureBall.position;

        // boost to the destination
        if(input.car.orientation.noseVector.dotProduct(orientation)/orientation.magnitude() > 0.7) {
            output.boost(true);
        }
        else {
            output.boost(false);
        }
        if(playerFuturePosition.minus(ballFuturePosition).magnitude() < RlConstants.BALL_RADIUS) {
            output.boost(false);
        }

        // set the desired orientation and apply it
        aerialOrientationHandler.setDestination(orientation.plus(playerPosition));
        aerialOrientationHandler.setRollOrientation(ballFuturePosition);
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
        //renderer.drawLine3d(Color.green, input.car.position, orientation.plus(input.car.position));
        renderer.drawLine3d(Color.green, hitPositionOnBall, playerFuturePosition);

        ShapeRenderer shapeRenderer = new ShapeRenderer(renderer);
        shapeRenderer.renderCross(hitPositionOnBall, Color.red);
        renderer.drawLine3d(Color.CYAN, ballFuturePosition, hitPositionOnBall);
    }
}
