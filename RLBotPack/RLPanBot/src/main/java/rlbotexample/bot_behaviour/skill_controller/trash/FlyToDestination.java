package rlbotexample.bot_behaviour.skill_controller.trash;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.parameter_configuration.PidSerializer;
import util.controllers.PidController;
import util.vector.Vector2;
import util.vector.Vector3;

public class FlyToDestination extends SkillController {

    //private static final double SPEED_FACTOR_FOR_AERIAL_PID_CONTROLLERS = 24;
    private static final double SPEED_FACTOR_FOR_AERIAL_PID_CONTROLLERS = 0;

    private PidController pitchPid;
    private PidController yawPid;
    private PidController rollPid;

    private PidController aerialOrientationXPid;
    private PidController aerialOrientationYPid;
    private PidController aerialBoostPid;

    private CarDestination desiredDestination;
    private BotBehaviour bot;

    private Vector3 lastAerialDestination;

    private JumpHandler jumpHandler;

    Vector3 aerialDestination;

    public FlyToDestination(CarDestination desiredDestination, BotBehaviour bot) {
        super();
        this.desiredDestination = desiredDestination;
        this.bot = bot;

        aerialOrientationXPid = new PidController(2, 0, 0.1);
        aerialOrientationYPid = new PidController(2, 0, 0.1);
        aerialBoostPid = new PidController(100000, 0, 0);

        pitchPid = new PidController(200, 0, 5000);
        yawPid = new PidController(200, 0, 5000);
        rollPid = new PidController(200, 0, 5000);

        lastAerialDestination = new Vector3();

        jumpHandler = new JumpHandler();

        aerialDestination = new Vector3();
    }

    @Override
    public void updateOutput(DataPacket input) {
        findDesiredAerialDirection(input);

        updateAerialOutput(input);

        updateJumpBehaviour(input);
    }

    private void findDesiredAerialDirection(DataPacket input) {
        Vector3 myDestination = desiredDestination.getThrottleDestination();
        Vector3 myPosition = input.car.position;
        Vector3 mySpeed = input.car.velocity;

        double myAerialDestinationX = aerialOrientationXPid.process(myDestination.minus(myPosition).x + SPEED_FACTOR_FOR_AERIAL_PID_CONTROLLERS*myDestination.minus(lastAerialDestination).x, mySpeed.x); // X
        double myAerialDestinationY = aerialOrientationYPid.process(myDestination.minus(myPosition).y + SPEED_FACTOR_FOR_AERIAL_PID_CONTROLLERS*myDestination.minus(lastAerialDestination).y, mySpeed.y); // Y
        Vector2 myAerialDestinationXY = new Vector2(myAerialDestinationX, myAerialDestinationY);                   // some calculations for Z...
        double myAerialDestinationLengthXY = myAerialDestinationXY.magnitude();                                    // same here...
        double myAerialDestinationZ = Math.max(1000, myAerialDestinationLengthXY);                                 // Z
        // note: the "1000" here in the max function is arbitrary. Actually, this value is being tweaked by the proportional
        // parameter in the pid controllers x and y. Scale the proportional factor up and the 1000 now seem to be closer.
        // Scale it down and it seems farther away.

        // normalize the vector to some arbitrary length so the pid can handle properly
        Vector3 myAerialDestination = new Vector3(myAerialDestinationX, myAerialDestinationY, myAerialDestinationZ).scaledToMagnitude(500);
        aerialDestination = myPosition.plus(myAerialDestination);
    }

    private void updateAerialOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 myLocalAerialDestination = CarDestination.getLocal(aerialDestination, input);
        Vector3 myDestination = desiredDestination.getThrottleDestination();
        Vector3 myPosition = input.car.position;
        Vector3 mySpeed = input.car.velocity;

        double pitchAmount = pitchPid.process(myLocalAerialDestination.z, 0);
        double yawAmount = yawPid.process(-myLocalAerialDestination.y, 0);
        double rollAmount = rollPid.process(myLocalAerialDestination.x, 0);
        boolean aerialBoostState = aerialBoostPid.process(myDestination.minus(myPosition).z + SPEED_FACTOR_FOR_AERIAL_PID_CONTROLLERS*myDestination.minus(lastAerialDestination).z, mySpeed.z) > 0;
        lastAerialDestination = myDestination;

        output.pitch(pitchAmount);
        output.yaw(yawAmount);
        output.roll(0);
        output.boost(aerialBoostState);
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
        aerialOrientationXPid = PidSerializer.fromFileToPid(PidSerializer.AERIAL_ANGLE_FILENAME, aerialOrientationXPid);
        aerialOrientationYPid = PidSerializer.fromFileToPid(PidSerializer.AERIAL_ANGLE_FILENAME, aerialOrientationYPid);
        aerialBoostPid = PidSerializer.fromFileToPid(PidSerializer.AERIAL_BOOST_FILENAME, aerialBoostPid);
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
