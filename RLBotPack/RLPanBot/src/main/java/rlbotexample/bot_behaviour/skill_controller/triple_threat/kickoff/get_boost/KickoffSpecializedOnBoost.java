package rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.get_boost;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.comit_to_ball.BoostAndFlipToDestination;
import rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.DriveToDestination3;
import rlbotexample.input.boost.BoostManager;
import rlbotexample.input.boost.BoostPad;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

import java.util.List;

public class KickoffSpecializedOnBoost extends SkillController {

    private final BotBehaviour bot;
    private DriveToDestination3 driveToDestinationController;
    private BoostAndFlipToDestination diagonalFlipWithBoostTap;
    private Vector3 destination;

    public KickoffSpecializedOnBoost(BotBehaviour bot) {
        this.bot = bot;
        this.driveToDestinationController = new DriveToDestination3(bot);
        this.diagonalFlipWithBoostTap = new BoostAndFlipToDestination(bot);
        this.destination = new Vector3();
    }

    public void setDestination(Vector3 destination) {
        this.destination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        BotOutput output = bot.output();
        driveToDestinationController.setDestination(destination);
        diagonalFlipWithBoostTap.setDestination(destination);

        if(true) {
            driveToDestinationController.updateOutput(input);
            output.boost(true);
        }
        else {
            driveToDestinationController.updateOutput(input);
            diagonalFlipWithBoostTap.updateOutput(input);
        }
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
