package rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.get_boost;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Flip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.HalfFlip;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.Wait;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public class BoostAndHalfFlipToDestination extends SkillController {

    private Vector3 destination;
    private final BotBehaviour bot;

    private JumpHandler jumpHandler;
    private boolean hasJumped;

    public BoostAndHalfFlipToDestination(BotBehaviour bot) {
        this.bot = bot;
        this.jumpHandler = new JumpHandler();
    }

    public void setDestination(Vector3 destination) {
        this.destination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        updateJumpBehaviour(input);
    }

    private void updateJumpBehaviour(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseVector = input.car.orientation.noseVector;
        Vector3 playerRoofVector = input.car.orientation.roofVector;
        Vector3 ballPosition = input.ball.position;

        if (jumpHandler.isJumpFinished()) {
            if(input.car.hasWheelContact) {
                jumpHandler.setJumpType(new ShortJump());
                output.boost(true);
                hasJumped = true;
                //System.out.println("set jump");
            }
            else if(hasJumped) {
                jumpHandler.setJumpType(new Flip());
                output.boost(false);
                hasJumped = false;
                //System.out.println("set flip");
            }
            else {
                jumpHandler.setJumpType(new Wait());
            }
        }
        Vector3 localDestination = destination.minus(playerPosition).normalized().minusAngle(playerNoseVector);
        jumpHandler.updateJumpState(
                input,
                output,
                localDestination,
                playerRoofVector.minusAngle(new Vector3(0, 0, 1))
        );
        output.jump(jumpHandler.getJumpState());
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
