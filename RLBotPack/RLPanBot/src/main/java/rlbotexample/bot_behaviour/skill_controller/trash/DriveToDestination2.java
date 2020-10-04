package rlbotexample.bot_behaviour.skill_controller.trash;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.HalfFlip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.controllers.ThrottleController;
import util.parameter_configuration.ArbitraryValueSerializer;
import util.parameter_configuration.PidSerializer;
import util.vector.Vector2;
import util.vector.Vector3;

public class DriveToDestination2 extends SkillController {

    private PidController throttlePid;
    private PidController steerPid;

    private PidController pitchPid;
    private PidController yawPid;
    private PidController rollPid;

    private JumpHandler jumpHandler;

    private CarDestination desiredDestination;
    private BotBehaviour bot;

    private double boostForThrottleThreshold = 1;
    private double driftForSteerThreshold = 1;

    public DriveToDestination2(CarDestination desiredDestination, BotBehaviour bot) {
        super();
        this.desiredDestination = desiredDestination;
        this.bot = bot;

        throttlePid = new PidController(5, 0, 10);
        steerPid = new PidController(0.02, 0, 0.04);

        pitchPid = new PidController(200, 0, 5000);
        yawPid = new PidController(200, 0, 5000);
        rollPid = new PidController(200, 0, 5000);

        jumpHandler = new JumpHandler();
    }

    @Override
    public void updateOutput(DataPacket input) {
        // drive and turn to reach destination F
        throttle(input);
        steer(input);

        // for when the car is accidentally in the air...
        // this allows for a basic handling of air control in the
        // case that the car happens to be in mid-air when this class is used
        pitchYawRoll(input);

        // stop boosting if supersonic
        preventUselessBoost(input);

        // halfFlips and stuff
        updateJumpBehaviour(input);
    }

    private void throttle(DataPacket input) {
        // get useful variables
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerDestination = desiredDestination.getThrottleDestination();
        Vector3 lastPlayerDestination = desiredDestination.getThrottleDestination();
        Vector3 playerLocalDestination = CarDestination.getLocal(playerDestination, input);
        Vector3 lastPlayerLocalDestination = CarDestination.getLocal(lastPlayerDestination, input);
        Vector3 playerDestinationSpeed = playerLocalDestination.minus(lastPlayerLocalDestination).scaled(30);

        // compute the pid value for throttle
        double throttleAmount = -throttlePid.process(playerSpeed.minus(playerDestinationSpeed).x, playerLocalDestination.x*10);
        throttleAmount = ThrottleController.process(throttleAmount);

        // send the result to the botOutput controller
        if(playerPosition.minus(playerDestination).magnitude() > 400) {
            throttleAmount = Math.abs(throttleAmount);
        }
        output.throttle(throttleAmount*2);
        output.boost(throttleAmount > boostForThrottleThreshold/4);
    }

    private void steer(DataPacket input) {
        // get useful variables
        BotOutput output = bot.output();
        Vector3 mySteeringDestination = desiredDestination.getSteeringDestination();
        Vector3 myLocalSteeringDestination = CarDestination.getLocal(mySteeringDestination, input);

        // transform the destination into an angle so it's easier to handle with the pid
        Vector2 myLocalSteeringDestination2D = myLocalSteeringDestination.flatten();
        Vector2 desiredLocalSteeringVector = new Vector2(1, 0);
        double steeringCorrectionAngle = myLocalSteeringDestination2D.correctionAngle(desiredLocalSteeringVector);

        // compute the pid value for steering
        double steerAmount = steerPid.process(steeringCorrectionAngle, 0);

        // send the result to the botOutput controller
        output.steer(steerAmount);
        output.drift(Math.abs(steerAmount) > driftForSteerThreshold);
    }

    private void pitchYawRoll(DataPacket input) {
        // get useful variables
        BotOutput output = bot.output();
        Vector3 mySteeringDestination = desiredDestination.getSteeringDestination();
        Vector3 myLocalSteeringDestination = CarDestination.getLocal(mySteeringDestination, input);

        // compute the pitch, roll, and yaw pid values
        double pitchAmount = pitchPid.process(myLocalSteeringDestination.z, 0);
        double yawAmount = yawPid.process(-myLocalSteeringDestination.y, 0);
        double rollAmount = rollPid.process(myLocalSteeringDestination.x, 0);

        // send the result to the botOutput controller
        output.pitch(pitchAmount);
        output.yaw(yawAmount);
        //output.roll(rollAmount);
    }

    private void preventUselessBoost(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 ballPosition = input.ball.position;

        if(playerSpeed.magnitude() >= 2200) {
            output.boost(false);
        }
    }

    private void updateJumpBehaviour(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 mySpeed = input.car.velocity;
        Vector3 myNoseVector = input.car.orientation.noseVector;
        Vector3 myRoofVector = input.car.orientation.roofVector;

        if (jumpHandler.isJumpFinished()) {
            if(mySpeed.minusAngle(myNoseVector).x < -200) {
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
        // instantiate new pid controllers based on the data files that corresponds
        throttlePid = PidSerializer.fromFileToPid(PidSerializer.THROTTLE_FILENAME, throttlePid);
        steerPid = PidSerializer.fromFileToPid(PidSerializer.STEERING_FILENAME, steerPid);
        pitchPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, pitchPid);
        yawPid = PidSerializer.fromFileToPid(PidSerializer.PITCH_YAW_FILENAME, yawPid);
        rollPid = PidSerializer.fromFileToPid(PidSerializer.ROLL_FILENAME, rollPid);

        boostForThrottleThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.BOOST_FOR_THROTTLE_THRESHOLD_FILENAME);
        driftForSteerThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.DRIFT_FOR_STEERING_THRESHOLD_FILENAME);
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
