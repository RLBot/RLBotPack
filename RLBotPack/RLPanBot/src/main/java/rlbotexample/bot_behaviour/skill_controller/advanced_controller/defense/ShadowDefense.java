package rlbotexample.bot_behaviour.skill_controller.advanced_controller.defense;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.trash.DriveToDestination2;
import rlbotexample.input.dynamic_data.ExtendedCarData;
import rlbotexample.input.dynamic_data.DataPacket;
import util.game_constants.RlConstants;
import util.vector.Vector3;

import java.awt.*;

public class ShadowDefense extends SkillController {
    private CarDestination desiredDestination;
    private BotBehaviour bot;
    private SkillController driveToDestinationController;
    private boolean isShadowDefenseSchmidtTriggerThresholdReached;

    public ShadowDefense(BotBehaviour bot) {
        this.desiredDestination = new CarDestination();
        this.bot = bot;
        this.driveToDestinationController = new DriveToDestination2(desiredDestination, bot);
        this.isShadowDefenseSchmidtTriggerThresholdReached = false;
    }

    @Override
    public void updateOutput(DataPacket input) {
        Vector3 playerNetCenterPosition;
        Vector3 playerPosition = input.car.position;
        Vector3 playerSpeed = input.car.velocity;
        Vector3 ballPosition = input.ball.position;
        Vector3 ballSpeed = input.ball.velocity;
        if(input.team == 0) {
            playerNetCenterPosition = new Vector3(0, -5500, 50);
        }
        else {
            playerNetCenterPosition = new Vector3(0, 5500, 50);
        }

        // find the threatening player
        ExtendedCarData closestCarToBall = input.allCars.get(0);
        for(ExtendedCarData car: input.allCars) {
            if(closestCarToBall.position.minus(ballPosition).magnitude() > car.position.minus(ballPosition).magnitude()) {
                closestCarToBall = car;
            }
        }

        // find the sweet spot shadow position (try to mimic what the opponent do, with some variations here and there)
        Vector3 shadowPosition;
        // add some distance in the direction of the player net
        if(input.team == 0) {
            shadowPosition = new Vector3(0, -2000, 0);
        }
        else {
            shadowPosition = new Vector3(0, 2000, 0);
        }
        // scale down in Y proportionally to the distance from the player net
        shadowPosition = shadowPosition.scaled(1, Math.abs(closestCarToBall.position.y - playerNetCenterPosition.y)/16000.0, 1);
        // scale down in X proportionally to the distance from the player net
        // shadowPosition = shadowPosition.scaled(closestCarToBall.position.minus(playerNetCenterPosition).scaled(1/4000.0).magnitude(), 1, 1);
        // add opponent position
        shadowPosition = closestCarToBall.position.plus(shadowPosition);

        // prohibiting center positioning
        // first, do a schmidt trigger to avoid unwanted back and forth
        if(shadowPosition.x > (RlConstants.GOAL_SIZE_X/2)*1.5) {
            isShadowDefenseSchmidtTriggerThresholdReached = true;
        }
        else if(shadowPosition.x < (-RlConstants.GOAL_SIZE_X/2)*1.5) {
            isShadowDefenseSchmidtTriggerThresholdReached = false;
        }
        // then, apply the prohibition with respect to the schmidt trigger if the player is within the center
        if(shadowPosition.x < RlConstants.GOAL_SIZE_X/2*closestCarToBall.position.minus(playerNetCenterPosition).scaled(1/25000.0).magnitude() && shadowPosition.x > -RlConstants.GOAL_SIZE_X/2*closestCarToBall.position.minus(playerNetCenterPosition).scaled(1/25000.0).magnitude()) {
            if(isShadowDefenseSchmidtTriggerThresholdReached) {
                shadowPosition = new Vector3(RlConstants.GOAL_SIZE_X/2*closestCarToBall.position.minus(playerNetCenterPosition).scaled(1/25000.0).magnitude(), shadowPosition.y, shadowPosition.z);
            }
            else {
                shadowPosition = new Vector3(-RlConstants.GOAL_SIZE_X/2*closestCarToBall.position.minus(playerNetCenterPosition).scaled(1/25000.0).magnitude(), shadowPosition.y, shadowPosition.z);
            }
        }
        // prohibiting too far away positions in X
        if(shadowPosition.x > RlConstants.WALL_DISTANCE_X - 400) {
            shadowPosition = new Vector3(RlConstants.WALL_DISTANCE_X - 400, shadowPosition.y, shadowPosition.z);
        }
        else if(shadowPosition.x < -RlConstants.WALL_DISTANCE_X + 400) {
            shadowPosition = new Vector3(-RlConstants.WALL_DISTANCE_X + 400, shadowPosition.y, shadowPosition.z);
        }

        desiredDestination.setThrottleDestination(shadowPosition);
        desiredDestination.setSteeringDestination(shadowPosition.plus(closestCarToBall.orientation.noseVector.scaled(500)));

        driveToDestinationController.setupAndUpdateOutputs(input);
        bot.output().jump(false);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.CYAN, desiredDestination.getThrottleDestination(), input.car.position);
        renderer.drawLine3d(Color.ORANGE, desiredDestination.getSteeringDestination(), input.car.position);
    }
}
