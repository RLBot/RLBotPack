package rlbotexample.bot_behaviour.skill_controller.test_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.game_constants.RlConstants;
import util.parameter_configuration.PidSerializer;
import util.controllers.PidController;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class AirDribbleTest1 extends SkillController {

    private static final double MAXIMUM_TARGET_BALL_SPEED = 400;
    private static final double MAXIMUM_BALL_OFFSET = 10;

    private PidController playerDestinationOffsetXPid;
    private PidController playerDestinationOffsetYPid;
    private PidController playerDestinationOffsetZPid;

    private PidController playerOrientationXPid;
    private PidController playerOrientationYPid;
    private PidController playerOrientationZPid;

    private PidController pitchPid;
    private PidController yawPid;
    private PidController rollPid;

    private PidController aerialBoostPid;

    private CarDestination desiredDestination;
    private BotBehaviour bot;

    private Vector3 playerOrientationVector;
    private Vector3 playerDestination;
    private Vector3 playerNosePosition;

    private JumpHandler jumpHandler;

    public AirDribbleTest1(CarDestination desiredDestination, BotBehaviour bot) {
        super();
        this.desiredDestination = desiredDestination;
        this.bot = bot;

        playerDestinationOffsetXPid = new PidController(0.1, 0, 0.8);
        playerDestinationOffsetYPid = new PidController(0.1, 0, 0.8);
        playerDestinationOffsetZPid = new PidController(0, 0, 0);

        playerOrientationXPid = new PidController(100, 0, 50);
        playerOrientationYPid = new PidController(100, 0, 50);
        playerOrientationZPid = new PidController(40, 0, 5);
        aerialBoostPid = new PidController(1, 0, 0);

        pitchPid = new PidController(6, 0, 60);
        yawPid = new PidController(6, 0, 60);
        rollPid = new PidController(4.3, 0, 14);

        playerOrientationVector = new Vector3();
        playerDestination = new Vector3();
        playerNosePosition = new Vector3();

        jumpHandler = new JumpHandler();
    }

    @Override
    public void updateOutput(DataPacket input) {
        findDesiredAerialDirection(input);

        updateAerialOutput(input);

        updateJumpBehaviour(input);
    }

    private void findDesiredAerialDirection(DataPacket input) {
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;
        Vector3 playerRoofOrientation = input.car.orientation.roofVector;
        playerNosePosition = playerPosition.plus(playerRoofOrientation.scaled(5));
        Vector3 ballPosition = input.ball.position;
        Vector3 ballSpeed = input.ball.velocity;
        Vector3 ballDestination = desiredDestination.getThrottleDestination();


        // cap the max desired getNativeBallPrediction speed.
        Vector3 cappedTargetBallSpeed = ballPosition.minus(ballDestination);
        if(cappedTargetBallSpeed.magnitude() > MAXIMUM_TARGET_BALL_SPEED) {
            cappedTargetBallSpeed = cappedTargetBallSpeed.scaledToMagnitude(MAXIMUM_TARGET_BALL_SPEED);
        }

        // compute next player offset from getNativeBallPrediction in X and Y
        double playerDestinationOffsetX = -playerDestinationOffsetXPid.process(ballSpeed.x, cappedTargetBallSpeed.x);
        double playerDestinationOffsetY = -playerDestinationOffsetYPid.process(ballSpeed.y, cappedTargetBallSpeed.y);

        // cap the max offset from getNativeBallPrediction so everything stays in control and doesn't explode lul
        Vector2 playerDestinationOffsetXY = new Vector2(playerDestinationOffsetX, playerDestinationOffsetY);
        if(playerDestinationOffsetXY.magnitudeSquared() > MAXIMUM_BALL_OFFSET*MAXIMUM_BALL_OFFSET) {
            double userProofCappedMaxOffset = Math.min(RlConstants.BALL_RADIUS, Math.max(0, MAXIMUM_BALL_OFFSET));
            playerDestinationOffsetXY = playerDestinationOffsetXY.scaledToMagnitude(userProofCappedMaxOffset);
            playerDestinationOffsetX = playerDestinationOffsetXY.x;
            playerDestinationOffsetY = playerDestinationOffsetXY.y;
        }

        // get the z coordinate on the surface of the getNativeBallPrediction, so the player tries to go to that coordinate instead of a wacky
        // through-the-getNativeBallPrediction destination...
        double ballOffsetZ = Math.sqrt(RlConstants.BALL_RADIUS* RlConstants.BALL_RADIUS - new Vector2(playerDestinationOffsetX, playerDestinationOffsetY).magnitudeSquared());

        // compute next player offset from getNativeBallPrediction in Z
        double playerDestinationOffsetZ = playerDestinationOffsetZPid.process(ballSpeed.z, cappedTargetBallSpeed.z);
        playerDestinationOffsetZ -= ballOffsetZ;

        // regroup the player destination coordinate into a single vector object
        playerDestination = new Vector3(playerDestinationOffsetX, playerDestinationOffsetY, playerDestinationOffsetZ).plus(ballPosition);

        // compute the player's desired orientation
        // I don't have a fucking clue what's going on here
        // I mean, with this code, the bot tries to go in the direction of the getNativeBallPrediction (plus some pid effects to actually handle the behaviour)
        // But WHY CAN I PUT 200000000 million something as a factor and nothing breaks??? Makes no sense.
        // gotta fix this somehow...

        // rescaling the desired speed
        Vector3 desiredSpeed = playerNosePosition.minus(playerDestination).scaledToMagnitude(40000);

        // applying PIDs...
        double playerOrientationX = playerOrientationXPid.process(playerSpeed.x, desiredSpeed.x);
        double playerOrientationY = playerOrientationYPid.process(playerSpeed.y, desiredSpeed.y);
        double playerOrientationZ = playerOrientationZPid.process(playerSpeed.z + 650, desiredSpeed.z);

        playerOrientationVector = new Vector3(playerOrientationX, playerOrientationY, playerOrientationZ).plus(ballPosition);
    }

    private void updateAerialOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;
        Vector3 localPlayerOrientationVector = CarDestination.getLocal(playerOrientationVector, input);
        Vector3 localRoofDestination = CarDestination.getLocal(new Vector3(playerPosition.x, playerPosition.y, 5000), input).scaledToMagnitude(500);

        double pitchAmount = pitchPid.process(new Vector2(localPlayerOrientationVector.x, -localPlayerOrientationVector.z).correctionAngle(new Vector2(1, 0)), 0);
        double yawAmount = yawPid.process(new Vector2(localPlayerOrientationVector.x, localPlayerOrientationVector.y).correctionAngle(new Vector2(1, 0)), 0);
        double rollAmount = rollPid.process(new Vector2(localRoofDestination.z, localRoofDestination.y).correctionAngle(new Vector2(1, 0)), 0);
        boolean aerialBoostState = aerialBoostPid.process(playerDestination.minus(playerPosition).z, playerSpeed.z) > 0;

        output.pitch(pitchAmount);
        output.yaw(yawAmount);
        output.roll(rollAmount);
        output.boost(aerialBoostState);
        //output.boost(playerOrientationVector.dotProduct(playerNoseOrientation)/playerOrientationVector.magnitude() > 0.97);
    }

    private void updateJumpBehaviour(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 mySpeed = input.car.velocity;
        Vector3 myNoseVector = input.car.orientation.noseVector;
        Vector3 myRoofVector = input.car.orientation.roofVector;

        if (jumpHandler.isJumpFinished()) {
            if(input.car.hasWheelContact) {
                jumpHandler.setJumpType(new SimpleJump());
            }
            else {
                jumpHandler.setJumpType(new Wait());
            }
        }
        jumpHandler.updateJumpState(
                input,
                output,
                CarDestination.getLocal(
                        desiredDestination.getThrottleDestination(),
                        input
                ),
                myRoofVector.minusAngle(new Vector3(0, 0, 1))
        );
        output.jump(jumpHandler.getJumpState());
    }

    @Override
    public void setupController() {
        pitchPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, pitchPid);
        yawPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, yawPid);
        rollPid = PidSerializer.fromFileToPid(PidSerializer.ROLL_FILENAME, rollPid);

        playerOrientationXPid = PidSerializer.fromFileToPid(PidSerializer.AIR_DRIBBLE_ORIENTATION_XY_FILENAME, playerOrientationXPid);
        playerOrientationYPid = PidSerializer.fromFileToPid(PidSerializer.AIR_DRIBBLE_ORIENTATION_XY_FILENAME, playerOrientationYPid);
        playerOrientationZPid = PidSerializer.fromFileToPid(PidSerializer.AIR_DRIBBLE_ORIENTATION_Z_FILENAME, playerOrientationZPid);

        aerialBoostPid = PidSerializer.fromFileToPid(PidSerializer.AERIAL_BOOST_FILENAME, aerialBoostPid);
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.green, input.car.position, playerOrientationVector);
        renderer.drawRectangle3d(Color.green, playerNosePosition, 10, 10, true);
        renderer.drawLine3d(Color.orange, input.ball.position, playerDestination);
        renderer.drawRectangle3d(Color.orange, playerDestination, 10, 10, true);
    }
}
