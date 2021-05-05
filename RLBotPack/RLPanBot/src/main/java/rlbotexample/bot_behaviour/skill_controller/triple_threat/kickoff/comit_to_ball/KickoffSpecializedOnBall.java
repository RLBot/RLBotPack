package rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.comit_to_ball;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.DriveToDestination3;
import rlbotexample.input.boost.BoostManager;
import rlbotexample.input.boost.BoostPad;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

import java.util.List;

public class KickoffSpecializedOnBall extends SkillController {

    private final BotBehaviour bot;
    private DriveToDestination3 driveToDestinationController;
    private BoostAndFlipToDestination diagonalFlipWithBoostTap;
    private Vector3 destination;

    public KickoffSpecializedOnBall(BotBehaviour bot) {
        this.bot = bot;
        this.driveToDestinationController = new DriveToDestination3(bot);
        this.diagonalFlipWithBoostTap = new BoostAndFlipToDestination(bot);
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        destination = getClosestKickoffBoost(input);
        driveToDestinationController.setDestination(destination);
        diagonalFlipWithBoostTap.setDestination(input.ball.position);

        if(input.car.position.magnitude() > 3000) {
            driveToDestinationController.updateOutput(input);
            output.boost(true);
        }
        else {
            driveToDestinationController.setDestination(input.ball.position);
            driveToDestinationController.updateOutput(input);
            diagonalFlipWithBoostTap.updateOutput(input);
        }
    }

    private Vector3 getClosestKickoffBoost(DataPacket input) {
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseVector = input.car.orientation.noseVector;
        Vector3 ballPosition = input.ball.position;
        List<BoostPad> boostPads = BoostManager.getOrderedBoosts();
        BoostPad closestAlignedBoostPad = boostPads.get(0);
        double bestCloseness = Double.MAX_VALUE;
        for (BoostPad boostPad : boostPads) {
            double closeness = boostPad.getLocation().minus(playerPosition).magnitude()
                    * playerNoseVector.dotProduct(ballPosition.minus(boostPad.getLocation()).normalized());
            if (closeness < bestCloseness) {
                bestCloseness = closeness;
                closestAlignedBoostPad = boostPad;
            }
        }

        return closestAlignedBoostPad.getLocation();
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
