package rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.MiddleJump;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.ShortJump;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public class Flip extends SkillController {

    private BotBehaviour bot;
    private Vector3 destination;
    private JumpHandler jumpHandler;

    public Flip(BotBehaviour bot) {
        this.bot = bot;
        this.destination = new Vector3();
        this.jumpHandler = new JumpHandler();
    }

    public void setDestination(final Vector3 destination) {
        this.destination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        updateJumpBehaviour(input);
    }

    private void updateJumpBehaviour(DataPacket input) {
        // get useful values
        BotOutput output = bot.output();

        if (jumpHandler.isJumpFinished()) {
            //System.out.println(jumpHandler.hasSecondJump());
            if(jumpHandler.hasFirstJump()) {
                jumpHandler.setJumpType(new MiddleJump());
            }
            else if(jumpHandler.hasSecondJump()) {
                jumpHandler.setJumpType(new rlbotexample.bot_behaviour.skill_controller.jump.implementations.Flip());
            }
        }
        jumpHandler.updateJumpState(
                input,
                output,
                CarDestination.getLocal(destination, input),
                new Vector3()
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
