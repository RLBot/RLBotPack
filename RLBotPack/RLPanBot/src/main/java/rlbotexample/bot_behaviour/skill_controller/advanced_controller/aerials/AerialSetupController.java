package rlbotexample.bot_behaviour.skill_controller.advanced_controller.aerials;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.DrivingSpeedController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.GroundOrientationController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.RlUtils;
import rlbotexample.output.BotOutput;
import util.game_constants.RlConstants;
import util.renderers.ShapeRenderer;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class AerialSetupController extends SkillController {

    private BotBehaviour bot;
    private AerialDirectionalHit aerialDirectionalHit;
    private DrivingSpeedController drivingSpeedController;
    private GroundOrientationController groundOrientationController;

    private Vector3 ballFuturePosition;
    private Vector3 ballDestination;
    private double timeOfAerialHit;
    private int integralAerialingCounter;

    public AerialSetupController(BotBehaviour bot) {
        this.bot = bot;
        this.aerialDirectionalHit = new AerialDirectionalHit(bot);
        this.drivingSpeedController = new DrivingSpeedController(bot);
        this.groundOrientationController = new GroundOrientationController(bot);

        this.ballFuturePosition = new Vector3();
        this.ballDestination = new Vector3();
        this.timeOfAerialHit = 2;
        this.integralAerialingCounter = 0;
    }

    public void setBallDestination(final Vector3 ballDestination) {
        this.ballDestination = ballDestination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerDistanceFromBall = input.ball.position.minus(input.car.position);
        Vector3 playerSpeedFromBall = input.ball.velocity.minus(input.car.velocity);

        //timeOfAerialHit = RlUtils.timeToReachAerialDestination(playerDistanceFromBall, playerSpeedFromBall)*1.45;
        timeOfAerialHit = RlUtils.timeToReachAerialDestination(input, playerDistanceFromBall, playerSpeedFromBall);

        ballFuturePosition = input.ballPrediction.ballAtTime(timeOfAerialHit).position;

        Vector3 localBallPosition = input.car.position.minus(ballFuturePosition).matrixRotation(input.car.orientation);
        Vector2 flatBallPosition = localBallPosition.flatten();
        final double targetDrivingSpeed = flatBallPosition.magnitude()/(timeOfAerialHit);
        drivingSpeedController.setSpeed(targetDrivingSpeed);
        groundOrientationController.setDestination(ballFuturePosition);
        aerialDirectionalHit.setBallDestination(ballDestination);

        drivingSpeedController.updateOutput(input);
        groundOrientationController.updateOutput(input);

        output.boost( input.car.velocity.magnitude() - 50 < targetDrivingSpeed);

        // compute the time it will take to boost to the ball considering only the z coordinate
        // (assuming the car is going in the right direction and speed in x and y)
        double a = (RlConstants.ACCELERATION_DUE_TO_BOOST - RlConstants.NORMAL_GRAVITY_STRENGTH)/2.1;
        double b = 291.667*2*input.car.orientation.roofVector.z;
        double c = -(ballFuturePosition.z - input.car.position.z);
        double ballisticTimeToReachFutureBall = (-b + Math.sqrt(b*b - 4*a*c))/(2*a);

        Vector3 futureBallPosition = input.ballPrediction.ballAtTime(ballisticTimeToReachFutureBall).position;
        double timeBeforeReachingUnderDestination = ((input.car.velocity.magnitude() + targetDrivingSpeed)/2)/input.car.position.minus(futureBallPosition).magnitude();

        Vector3 futureCarPosition = input.ballPrediction.carsAtTime(timeOfAerialHit).get(input.playerIndex).position;
        Vector3 futureLocalBallPosition = input.car.position.minus(ballFuturePosition).matrixRotation(input.car.orientation);
        if(targetDrivingSpeed < 2300
                && input.car.velocity.magnitude() > (targetDrivingSpeed)
                && futureLocalBallPosition.flatten().normalized().dotProduct(new Vector2(-1, 0)) > 0.9
                && timeBeforeReachingUnderDestination > timeOfAerialHit
                && timeOfAerialHit < 3
                && ballFuturePosition.z > 180) {
            integralAerialingCounter++;
        }

        if(//ballisticTimeToReachFutureBall > timeOfAerialHit
                ballFuturePosition.z < 200) {
            integralAerialingCounter = 0;
        }

        if(integralAerialingCounter > 1) {
            aerialDirectionalHit.updateOutput(input);
        }
    }

    @Override
    public void setupController() {
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        if(integralAerialingCounter > 1) {
            //renderer.drawRectangle3d(Color.red, input.car.position.plus(new Vector3(0, 0, 200)), 30, 30, true);
        }
    }
}
