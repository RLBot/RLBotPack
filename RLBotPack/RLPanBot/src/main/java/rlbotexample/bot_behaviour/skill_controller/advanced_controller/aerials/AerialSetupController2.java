package rlbotexample.bot_behaviour.skill_controller.advanced_controller.aerials;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.metagame.advanced_gamestate_info.AerialInfo;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.DrivingSpeedController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.GroundOrientationController;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.RlUtils;
import rlbotexample.input.prediction.Parabola3D;
import rlbotexample.input.prediction.ball.AdvancedBallPrediction;
import rlbotexample.output.BotOutput;
import util.game_constants.RlConstants;
import util.renderers.ShapeRenderer;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class AerialSetupController2 extends SkillController {

    private BotBehaviour bot;
    private AerialDirectionalHit3 aerialDirectionalHit2;
    private DrivingSpeedController drivingSpeedController;
    private GroundOrientationController groundOrientationController;

    private Parabola3D jumpPhaseTrajectory;
    private double closestApproachTimeBetweenParabolaAndBallPrediction;

    private Vector3 ballDestination;
    private boolean isAerialing;

    public AerialSetupController2(BotBehaviour bot) {
        this.bot = bot;
        this.aerialDirectionalHit2 = new AerialDirectionalHit3(bot);
        this.drivingSpeedController = new DrivingSpeedController(bot);
        this.groundOrientationController = new GroundOrientationController(bot);
        this.closestApproachTimeBetweenParabolaAndBallPrediction = 0;

        this.ballDestination = new Vector3();
        this.isAerialing = false;
    }

    public void setBallDestination(final Vector3 ballDestination) {
        this.ballDestination = ballDestination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        jumpPhaseTrajectory = new Parabola3D(input.car.position,
                input.car.velocity.plus(input.car.orientation.roofVector.scaled(input.car.hasWheelContact ? 2 * 291.667 : 0)),
                new Vector3(0, 0, -RlConstants.NORMAL_GRAVITY_STRENGTH),
                0);

        closestApproachTimeBetweenParabolaAndBallPrediction = findClosestTimeBetween(input.ballPrediction, input);

        Vector3 bestApproachPointOfPlayer = playerAerialTrajectory(closestApproachTimeBetweenParabolaAndBallPrediction, input);
        Vector3 bestApproachPointOfBall = input.ballPrediction.ballAtTime(closestApproachTimeBetweenParabolaAndBallPrediction).position;
        Vector3 distanceBetweenParabolaAndBallPrediction = bestApproachPointOfBall.minus(bestApproachPointOfPlayer);

        double speedToReachBallDestinationInTime = input.ballPrediction.ballAtTime(closestApproachTimeBetweenParabolaAndBallPrediction).position
                    .minus(input.car.position).magnitude()
                /closestApproachTimeBetweenParabolaAndBallPrediction;
        speedToReachBallDestinationInTime *= (input.car.velocity.normalized().dotProduct(distanceBetweenParabolaAndBallPrediction.normalized())) < 0 ? 0.5 : 1;
        drivingSpeedController.setSpeed(speedToReachBallDestinationInTime);
        drivingSpeedController.updateOutput(input);

        boolean boostValue = speedToReachBallDestinationInTime*speedToReachBallDestinationInTime > input.car.velocity.magnitudeSquared()-50
                && speedToReachBallDestinationInTime > 1400
                && speedToReachBallDestinationInTime < RlConstants.CAR_MAX_SPEED
                && input.car.hasWheelContact;
        bot.output().boost(boostValue);

        Vector3 futureBallPosition = input.ballPrediction.ballAtTime(closestApproachTimeBetweenParabolaAndBallPrediction).position;
        groundOrientationController.setDestination(futureBallPosition.plus(futureBallPosition.minus(ballDestination).scaledToMagnitude(RlConstants.BALL_RADIUS)));
        groundOrientationController.updateOutput(input);

        if(distanceBetweenParabolaAndBallPrediction.magnitude() < RlConstants.BALL_RADIUS
        && AerialInfo.isBallConsideredAerial(input.ballPrediction.ballAtTime(closestApproachTimeBetweenParabolaAndBallPrediction), input.car.hitBox)) {
            isAerialing = true;
        }
        if(distanceBetweenParabolaAndBallPrediction.magnitude() > 600
        || input.ball.position.z < 200) {
            isAerialing = false;
        }

        if(isAerialing) {
            aerialDirectionalHit2.setBallDestination(ballDestination);
            aerialDirectionalHit2.updateOutput(input);
        }
    }

    private double findClosestTimeBetween(AdvancedBallPrediction ballPrediction, DataPacket input) {
        Vector3 closestDistance = new Vector3(10000000, 10000000, 10000000);
        double bestTimeFound = RlUtils.BALL_PREDICTION_TIME;

        for(int i = 0; i < RlUtils.BALL_PREDICTION_TIME*RlUtils.BALL_PREDICTION_REFRESH_RATE; i++) {
            double timeToTest = RlUtils.BALL_PREDICTION_TIME - i/RlUtils.BALL_PREDICTION_REFRESH_RATE;
            Vector3 distanceToTest = ballPrediction.ballAtTime(timeToTest).position.minus(playerAerialTrajectory(timeToTest, input));
            if(closestDistance.magnitudeSquared() > distanceToTest.magnitudeSquared()) {
                bestTimeFound = timeToTest;
                closestDistance = distanceToTest;
            }
        }

        return bestTimeFound;
    }

    private Vector3 playerAerialTrajectory(double timeInTheFuture, DataPacket input) {
        double timeToReachDesiredOrientation = input.car.orientation.noseVector.flatten().magnitude()*0.45;
        if(timeInTheFuture < timeToReachDesiredOrientation) {
            return jumpPhaseTrajectory.compute(timeInTheFuture);
        }
        else {
            Parabola3D continuation = new Parabola3D(jumpPhaseTrajectory.compute(timeToReachDesiredOrientation),
                    jumpPhaseTrajectory.derivative(timeToReachDesiredOrientation),
                    new Vector3(0, 0, RlConstants.ACCELERATION_DUE_TO_BOOST - RlConstants.NORMAL_GRAVITY_STRENGTH),
                    0);
            return continuation.compute(timeInTheFuture - timeToReachDesiredOrientation);
        }
    }

    @Override
    public void setupController() {
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        ShapeRenderer sr = new ShapeRenderer(renderer);
        // render weird player traj function
        Vector3 previousPosition = playerAerialTrajectory(0, input);
        for(int i = 1; i < 40; i++) {
            Vector3 nextPosition = playerAerialTrajectory(i*3/40.0, input);
            renderer.drawLine3d(Color.red, nextPosition, previousPosition);
            previousPosition = nextPosition;
        }
        Vector3 bestApproachPointOfPlayer = playerAerialTrajectory(closestApproachTimeBetweenParabolaAndBallPrediction, input);
        Vector3 bestApproachPointOfBall = input.ballPrediction.ballAtTime(closestApproachTimeBetweenParabolaAndBallPrediction).position;
        renderer.drawLine3d(Color.cyan, bestApproachPointOfPlayer, bestApproachPointOfBall);
        sr.renderBallPrediction(input.ballPrediction, 2,  Color.magenta);
    }
}
