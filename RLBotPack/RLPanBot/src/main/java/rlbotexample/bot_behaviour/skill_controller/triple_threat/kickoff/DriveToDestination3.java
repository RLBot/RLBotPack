package rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.AerialOrientationHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.HalfFlip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.SimpleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.parameter_configuration.ArbitraryValueSerializer;
import util.parameter_configuration.PidSerializer;
import util.vector.Vector2;
import util.vector.Vector3;

public class DriveToDestination3 extends SkillController {

    private PidController throttlePid;
    private PidController steerPid;

    private AerialOrientationHandler aerialOrientationHandler;

    private Vector3 destination = new Vector3();
    private BotBehaviour bot;

    private double boostForThrottleThreshold = 1;
    private double driftForSteerThreshold = 1;

    public DriveToDestination3(BotBehaviour bot) {
        super();
        this.bot = bot;

        throttlePid = new PidController(0.01, 0, 0.005);
        steerPid = new PidController(7, 0, 10);

        aerialOrientationHandler = new AerialOrientationHandler(bot);
    }

    public void setDestination(Vector3 destination) {
        this.destination = destination;
        this.aerialOrientationHandler.setDestination(destination);
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
    }

    private void throttle(DataPacket input) {
        // get useful variables
        BotOutput output = bot.output();
        Vector3 playerSpeed = input.car.velocity;
        Vector3 playerDestination = destination;
        Vector3 lastPlayerDestination = destination;
        Vector3 playerLocalDestination = CarDestination.getLocal(playerDestination, input);
        Vector3 lastPlayerLocalDestination = CarDestination.getLocal(lastPlayerDestination, input);
        Vector3 playerDestinationSpeed = playerLocalDestination.minus(lastPlayerLocalDestination).scaled(30);

        // compute the pid value for throttle
        double throttleAmount = -throttlePid.process(playerSpeed.minus(playerDestinationSpeed).x, playerLocalDestination.x*10);

        // send the result to the botOutput controller
        output.throttle(throttleAmount);
        output.boost(throttleAmount > boostForThrottleThreshold);

        if(input.car.velocity.magnitude() < 50) {
            output.throttle(1);
        }
    }

    private void steer(DataPacket input) {
        // get useful variables
        BotOutput output = bot.output();
        Vector3 mySteeringDestination = destination;
        Vector3 myLocalSteeringDestination = CarDestination.getLocal(mySteeringDestination, input);

        // transform the destination into an angle so it's easier to handle with the pid
        Vector2 myLocalSteeringDestination2D = myLocalSteeringDestination.flatten();
        Vector2 desiredLocalSteeringVector = new Vector2(1, 0);
        double steeringCorrectionAngle = myLocalSteeringDestination2D.correctionAngle(desiredLocalSteeringVector);

        // compute the pid value for steering
        double steerAmount = steerPid.process(steeringCorrectionAngle, 0);

        // send the result to the botOutput controller
        output.steer(steerAmount);
        output.drift(Math.abs(steerAmount) > 9);
    }

    private void pitchYawRoll(DataPacket input) {
        aerialOrientationHandler.setRollOrientation(input.car.position.plus(new Vector3(0, 0, 1000)));
        aerialOrientationHandler.updateOutput(input);
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

    @Override
    public void setupController() {
        // instantiate new pid controllers based on the data files that corresponds
        //throttlePid = PidSerializer.fromFileToPid(PidSerializer.THROTTLE_FILENAME, throttlePid);

        boostForThrottleThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.BOOST_FOR_THROTTLE_THRESHOLD_FILENAME);
        driftForSteerThreshold = ArbitraryValueSerializer.serialize(ArbitraryValueSerializer.DRIFT_FOR_STEERING_THRESHOLD_FILENAME);
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
