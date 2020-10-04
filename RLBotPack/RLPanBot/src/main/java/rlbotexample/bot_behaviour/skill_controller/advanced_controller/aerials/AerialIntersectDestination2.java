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
import util.game_constants.RlConstants;
import util.renderers.ShapeRenderer;
import util.vector.Vector3;

import java.awt.*;

public class AerialIntersectDestination2 extends SkillController {

    private BotBehaviour bot;
    private AerialOrientationHandler aerialOrientationHandler;
    private JumpHandler jumpHandler;
    private Vector3 destination;
    private Vector3 orientation;

    public AerialIntersectDestination2(BotBehaviour bot) {
        this.bot = bot;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        this.jumpHandler = new JumpHandler();

        this.orientation = new Vector3();
        this.destination = new Vector3();
    }

    public void setDestination(Vector3 destination) {
        this.destination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;

        Vector3 unscaledOrientationWithGravity = destination.minus(input.car.position).normalized();
        // fancy math to retrieve the desired orientation of player from the applied acceleration vector, without gravity
        //double angleFromZCoordinate = Math.atan(globalOrientationWithGravity.minus(input.car.position).z / globalOrientationWithGravity.minus(input.car.position).flatten().magnitude());
        double angleFromZCoordinate = Math.atan(unscaledOrientationWithGravity.z / unscaledOrientationWithGravity.flatten().magnitude());
        double lengthOfVector = RlConstants.NORMAL_GRAVITY_STRENGTH + ((1 - Math.cos(angleFromZCoordinate)) * (RlConstants.ACCELERATION_DUE_TO_BOOST - RlConstants.NORMAL_GRAVITY_STRENGTH));
        Vector3 orientationWithGravity = unscaledOrientationWithGravity.scaledToMagnitude(lengthOfVector);
        orientation = orientationWithGravity.minus(new Vector3(0, 0, -RlConstants.NORMAL_GRAVITY_STRENGTH));
        orientation = orientation
                .minus(input.car.velocity.plus(input.car.velocity.projectOnto(input.car.position.minus(destination)).scaled(-1)).scaled(4))
                .plus(input.car.position);

        output.boost(input.car.orientation.noseVector.dotProduct(orientation.minus(input.car.position).normalized()) > 0.7);

        // set the desired orientation and apply it
        aerialOrientationHandler.setDestination(orientation);
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
        shapeRenderer.renderCross(destination, Color.red);
    }
}
