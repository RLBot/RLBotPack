package rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.HalfFlip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.RlUtils;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.controllers.ThrottleController;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class Dribble extends SkillController {

    private static final double PLAYER_DISTANCE_FROM_BALL_WHEN_CONSIDERED_DRIBBLING = 183;
    private static final double MINIMUM_TARGET_BALL_SPEED_FACTOR = 600;
    private static final double STRENGTH_OF_MINIMUM_TARGET_BALL_SPEED_FACTOR = 0.12;
    private static final double MAXIMUM_BALL_OFFSET = 50;

    private CarDestination desiredDestination;
    private BotBehaviour bot;
    private AerialOrientationHandler aerialOrientationHandler;

    private PidController ballDirectionOffsetXPid;
    private PidController ballDirectionOffsetYPid;

    private PidController ballSteeringDirectionOffsetXPid;
    private PidController ballSteeringDirectionOffsetYPid;

    private PidController throttlePid;
    private PidController steerPid;

    private PidController pitchPid;
    private PidController yawPid;
    private PidController rollPid;

    private Vector3 dribblingDestination;
    private Vector3 dribblingSteeringDestination;

    private double boostForThrottleThreshold;
    private double driftForSteerThreshold;

    private double playerGetAroundTheBallDistanceWhenDribblingLost = 120;
    private double maximumTargetBallSpeed;

    private boolean hadLossDribbling;
    private boolean isRegainingDribblingOnRight;

    private JumpHandler jumpHandler;

    public Dribble(CarDestination desiredDestination, BotBehaviour bot) {
        super();
        this.desiredDestination = desiredDestination;
        this.bot = bot;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);

        ballDirectionOffsetXPid = new PidController(0.05, 0, 0.01);
        ballDirectionOffsetYPid = new PidController(0.05, 0, 0.01);

        ballSteeringDirectionOffsetXPid = new PidController(0.05, 0, 0.01);
        ballSteeringDirectionOffsetYPid = new PidController(0.05, 0, 0.01);

        throttlePid = new PidController(0.01, 0, 0.005);
        steerPid = new PidController(7, 0, 10);

        pitchPid = new PidController(2.6, 0, 21);
        yawPid = new PidController(2.6, 0, 21);
        rollPid = new PidController(2.9, 0, 20.5);

        boostForThrottleThreshold = 1.1;
        driftForSteerThreshold = 10;

        jumpHandler = new JumpHandler();

        dribblingDestination = new Vector3();
        dribblingSteeringDestination = new Vector3();
        maximumTargetBallSpeed = 1410;

        hadLossDribbling = false;
        isRegainingDribblingOnRight = true;
    }

    @Override
    public void updateOutput(DataPacket input) {
        playerGetAroundTheBallDistanceWhenDribblingLost = 120 + ((2300 - input.car.velocity.magnitude())/50);
        maximumTargetBallSpeed = Math.min(800 + input.car.boost * 8, input.car.velocity.magnitude()*2);
        throttle(input);
        steer(input);
        preventUselessBoost(input);
        pitchYawRoll(input);
        //updateJumpBehaviour(input);
    }

    private void throttle(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;
        Vector3 ballPosition = input.ball.position;
        Vector3 ballSpeed = input.ball.velocity;
        Vector3 ballDestination = desiredDestination.getThrottleDestination();

        Vector2 cappedTargetBallSpeed = new Vector2(
                Math.max(-maximumTargetBallSpeed, Math.min(maximumTargetBallSpeed, ballPosition.minus(ballDestination).x)),
                Math.max(-maximumTargetBallSpeed, Math.min(maximumTargetBallSpeed, ballPosition.minus(ballDestination).y))
        );

        // compute the desired offset from the getNativeBallPrediction to be able to accelerate or slow down, turn left or right accordingly...
        double desiredPlayerOffsetX = ballDirectionOffsetXPid.process(cappedTargetBallSpeed.x, -ballSpeed.x);
        double desiredPlayerOffsetY = ballDirectionOffsetYPid.process(cappedTargetBallSpeed.y, -ballSpeed.y);

        desiredPlayerOffsetX = Math.max(-MAXIMUM_BALL_OFFSET, Math.min(MAXIMUM_BALL_OFFSET, desiredPlayerOffsetX));
        desiredPlayerOffsetY = Math.max(-MAXIMUM_BALL_OFFSET, Math.min(MAXIMUM_BALL_OFFSET, desiredPlayerOffsetY));

        // compute the actual player destination
        Vector3 desiredPlayerOffset = new Vector3(desiredPlayerOffsetX, desiredPlayerOffsetY, 0);
        /* prevent too slow maneuvers */ {
            double slowDownPreventingThresholdFactor = 0;
            if (ballSpeed.magnitude() < MINIMUM_TARGET_BALL_SPEED_FACTOR) {
                slowDownPreventingThresholdFactor = ballSpeed.magnitude() - MINIMUM_TARGET_BALL_SPEED_FACTOR;
                slowDownPreventingThresholdFactor *= STRENGTH_OF_MINIMUM_TARGET_BALL_SPEED_FACTOR;
            }
            desiredPlayerOffset = desiredPlayerOffset.plus(playerNoseOrientation.scaled(slowDownPreventingThresholdFactor));
        }
        Vector3 playerDestination = ballPosition.plus(desiredPlayerOffset);

        dribblingDestination = playerDestination;

        // transform it into the player's local coordinate system
        Vector3 localDestination = CarDestination.getLocal(playerDestination, input);

        // compute the throttle value
        double throttleAmount = -throttlePid.process(playerSpeed.minus(ballSpeed).minusAngle(playerNoseOrientation).x, localDestination.x*10);
        // YAMETEEE
        if(playerPosition.minus(ballPosition).magnitude() > 400) {
            throttleAmount = Math.abs(throttleAmount);
        }
        throttleAmount = ThrottleController.process(throttleAmount);

        output.throttle(throttleAmount);
        output.boost(throttleAmount > boostForThrottleThreshold);
    }

    private void steer(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;
        Vector3 ballPosition = input.ball.position;
        Vector3 ballSpeed = input.ball.velocity;
        Vector3 ballDestination = desiredDestination.getSteeringDestination();

        Vector2 cappedTargetBallSpeed = new Vector2(
                Math.max(-maximumTargetBallSpeed, Math.min(maximumTargetBallSpeed, ballPosition.minus(ballDestination).x)),
                Math.max(-maximumTargetBallSpeed, Math.min(maximumTargetBallSpeed, ballPosition.minus(ballDestination).y))
        );

        // compute the desired offset from the getNativeBallPrediction to be able to accelerate or slow down, turn left or right accordingly...
        double desiredPlayerOffsetX = ballSteeringDirectionOffsetXPid.process(cappedTargetBallSpeed.x, -ballSpeed.x);
        double desiredPlayerOffsetY = ballSteeringDirectionOffsetYPid.process(cappedTargetBallSpeed.y, -ballSpeed.y);

        desiredPlayerOffsetX = Math.max(-MAXIMUM_BALL_OFFSET, Math.min(MAXIMUM_BALL_OFFSET, desiredPlayerOffsetX));
        desiredPlayerOffsetY = Math.max(-MAXIMUM_BALL_OFFSET, Math.min(MAXIMUM_BALL_OFFSET, desiredPlayerOffsetY));

        // compute the player steering destination from getNativeBallPrediction speed and getNativeBallPrediction steering destination
        // here, we steer in the direction of the getNativeBallPrediction's velocity.
        Vector3 desiredPlayerOffset = new Vector3(desiredPlayerOffsetX, desiredPlayerOffsetY, 0);
        Vector3 playerDestination = ballPosition.plus(desiredPlayerOffset);
        /* handle loss of getNativeBallPrediction control. Regain that control damn it! (We consider loss of control if behind the getNativeBallPrediction and not close enough.)*/ {
            if (playerPosition.minus(ballPosition).magnitude() > PLAYER_DISTANCE_FROM_BALL_WHEN_CONSIDERED_DRIBBLING
                && playerPosition.minus(ballPosition).dotProduct(ballSpeed) < 0
                || ballSpeed.magnitude() < 1) {

                if(!hadLossDribbling) {
                    hadLossDribbling = true;
                    // should the player go to the right or to the left of the getNativeBallPrediction's velocity vector?
                    if (playerPosition.minus(ballPosition).minusAngle(ballDestination.minus(ballPosition)).y < 0) {
                        isRegainingDribblingOnRight = true;
                    } else {
                        isRegainingDribblingOnRight = false;
                    }
                }
                Vector3 alternativeDesiredPlayerOffset;
                if(isRegainingDribblingOnRight) {
                    alternativeDesiredPlayerOffset = new Vector3(0, playerGetAroundTheBallDistanceWhenDribblingLost, 0);
                }
                else {
                    alternativeDesiredPlayerOffset = new Vector3(0, -playerGetAroundTheBallDistanceWhenDribblingLost, 0);
                }
                playerDestination = ballPosition.plus(alternativeDesiredPlayerOffset.plusAngle(ballSpeed.plus(new Vector3(0, 0.1, 0))));
            }
            else {
                hadLossDribbling = false;
            }
        }

        Vector3 steeringDestination = playerDestination.plus(ballSpeed.scaled(0.28));
        dribblingSteeringDestination = steeringDestination;

        // transform it into the player's local coordinate system
        Vector3 localSteeringDestination = CarDestination.getLocal(steeringDestination, input);

        // transform the destination into an angle so it's easier to handle with the pid
        Vector2 myLocalSteeringDestination2D = localSteeringDestination.flatten();
        Vector2 desiredLocalSteeringVector = new Vector2(1, 0);
        double steeringCorrectionAngle = myLocalSteeringDestination2D.correctionAngle(desiredLocalSteeringVector);

        // compute the steer value
        double steerAmount = steerPid.process(steeringCorrectionAngle, 0);

        output.steer(steerAmount);
        output.drift(Math.abs(steerAmount) > driftForSteerThreshold);
    }

    private void preventUselessBoost(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 ballPosition = input.ball.position;

        if(playerSpeed.magnitude() >= 2200 || playerPosition.minus(ballPosition).flatten().magnitude() > 300) {
            output.boost(false);
        }
    }

    private void pitchYawRoll(DataPacket input) {
        // get useful variables
        /*
        BotOutput output = bot.output();
        Vector3 getNativeBallPrediction = input.getNativeBallPrediction.position;
        Vector3 localBallPosition = CarDestination.getLocal(getNativeBallPrediction, input);

        // compute the pitch, roll, and yaw pid values
        double pitchAmount = pitchPid.process(localBallPosition.z, 0);
        double yawAmount = yawPid.process(-localBallPosition.y, 0);
        double rollAmount = rollPid.process(localBallPosition.x, 0);
        */

        aerialOrientationHandler.setRollOrientation(new Vector3(0, 0, 10000));
        double timeToReachBall = RlUtils.timeToReachAerialDestination(input, input.car.position.minus(input.ball.position), input.car.velocity.minus(input.ball.velocity));
        aerialOrientationHandler.setDestination(input.ballPrediction.ballAtTime(timeToReachBall).position);
        aerialOrientationHandler.updateOutput(input);

        /*BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;

        Vector3 ballPosition = input.ball.position;
        Vector3 playerOrientationVector = ballPosition;
        Vector3 localPlayerOrientationVector = CarDestination.getLocal(playerOrientationVector, input);
        Vector3 localRollDestination = CarDestination.getLocal(playerPosition.plus(new Vector3(0, 0, 5000)), input);

        double pitchAmount = pitchPid.process(new Vector2(localPlayerOrientationVector.x, -localPlayerOrientationVector.z).correctionAngle(new Vector2(1, 0)), 0);
        double yawAmount = yawPid.process(new Vector2(localPlayerOrientationVector.x, localPlayerOrientationVector.y).correctionAngle(new Vector2(1, 0)), 0);
        double rollAmount = rollPid.process(new Vector2(localRollDestination.z, localRollDestination.y).correctionAngle(new Vector2(1, 0)), 0);

        // send the result to the botOutput controller
        output.pitch(pitchAmount);
        output.yaw(yawAmount);
        output.roll(rollAmount);*/
    }

    private void updateJumpBehaviour(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 mySpeed = input.car.velocity;
        Vector3 myNoseVector = input.car.orientation.noseVector;
        Vector3 myRoofVector = input.car.orientation.roofVector;
        Vector3 ballPosition = input.ball.position;

        if (jumpHandler.isJumpFinished()) {
            if(mySpeed.minusAngle(myNoseVector).x < -400) {
                if(input.car.hasWheelContact) {
                    jumpHandler.setJumpType(new SimpleJump());
                }
                else {
                    jumpHandler.setJumpType(new HalfFlip());
                }
            }
            else {
                jumpHandler.setJumpType(new Wait());
            }
        }
        jumpHandler.updateJumpState(
                input,
                output,
                CarDestination.getLocal(ballPosition, input),
                myRoofVector.minusAngle(new Vector3(0, 0, 1))
        );
        output.jump(jumpHandler.getJumpState());
    }

    @Override
    public void setupController() {
        /*
        ballDirectionOffsetXPid = PidSerializer.fromFileToPid(PidSerializer.DRIBBLE_FILENAME, ballDirectionOffsetXPid);
        ballDirectionOffsetYPid = PidSerializer.fromFileToPid(PidSerializer.DRIBBLE_FILENAME, ballDirectionOffsetYPid);
        ballSteeringDirectionOffsetXPid = PidSerializer.fromFileToPid(PidSerializer.DRIBBLE_FILENAME, ballSteeringDirectionOffsetXPid);
        ballSteeringDirectionOffsetYPid = PidSerializer.fromFileToPid(PidSerializer.DRIBBLE_FILENAME, ballSteeringDirectionOffsetYPid);
        throttlePid = PidSerializer.fromFileToPid(PidSerializer.THROTTLE_FILENAME, throttlePid);
        steerPid = PidSerializer.fromFileToPid(PidSerializer.STEERING_FILENAME, steerPid);
        pitchPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, pitchPid);
        yawPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, yawPid);
        rollPid = PidSerializer.fromFileToPid(PidSerializer.ROLL_FILENAME, rollPid);

        boostForThrottleThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.BOOST_FOR_THROTTLE_DRIBBLE_THRESHOLD_FILENAME);
        driftForSteerThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.DRIFT_FOR_STEERING_THRESHOLD_FILENAME);
        */
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.ORANGE, new Vector3(dribblingDestination.flatten().x, dribblingDestination.flatten().y, input.ball.position.z + 100), new Vector3(input.ball.position.flatten().x, input.ball.position.flatten().y, input.ball.position.z + 100));
        renderer.drawCenteredRectangle3d(Color.ORANGE, new Vector3(dribblingDestination.flatten().x, dribblingDestination.flatten().y, input.ball.position.z + 100), 10, 10, true);
        renderer.drawLine3d(Color.red, dribblingSteeringDestination, input.car.position);
    }
}
