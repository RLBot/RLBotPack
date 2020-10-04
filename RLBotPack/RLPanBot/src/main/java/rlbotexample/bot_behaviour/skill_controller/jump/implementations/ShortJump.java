package rlbotexample.bot_behaviour.skill_controller.jump.implementations;

import rlbotexample.bot_behaviour.skill_controller.jump.JumpType;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public class ShortJump extends JumpType {

    private static final int JUMP_DURATION = 2;
    private static final int[] JUMP_TIME_FRAMES = {2};

    public ShortJump() {
        super(JUMP_DURATION, JUMP_TIME_FRAMES);
    }

    @Override
    public void jump(DataPacket input, BotOutput output, Vector3 desiredFrontOrientation, Vector3 desiredRoofOrientation) {
        updateCurrentJumpCallCounter();

        if(this.getCurrentJumpCallCounter() < JUMP_TIME_FRAMES[0]) {
            output.pitch(0);
            output.yaw(0);
            output.roll(0);
        }

        if(this.getCurrentJumpCallCounter() + 1 == JUMP_TIME_FRAMES[0]) {
            setJumpState(false);
        }
        else {
            setJumpState(getCurrentJumpCallCounter() <= JUMP_DURATION);
        }
    }
}
