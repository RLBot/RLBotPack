package rlbotexample.bot_behaviour.skill_controller.jump.implementations;

import rlbotexample.bot_behaviour.skill_controller.jump.JumpType;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public class MiddleJump extends JumpType {

    private static final int JUMP_DURATION = 4;
    private static final int[] JUMP_TIME_FRAMES = {4};

    public MiddleJump() {
        super(JUMP_DURATION, JUMP_TIME_FRAMES);
    }

    @Override
    public void jump(DataPacket input, BotOutput output, Vector3 desiredFrontOrientation, Vector3 desiredRoofOrientation) {
        updateCurrentJumpCallCounter();
        setJumpState(false);

        if(this.getCurrentJumpCallCounter() < JUMP_TIME_FRAMES[0]) {
            output.pitch(0);
            output.yaw(0);
            output.roll(0);
            setJumpState(true);
        }

        if(this.getCurrentJumpCallCounter() + 1 == JUMP_TIME_FRAMES[0]) {
        }
        else {
            //setJumpState(getCurrentJumpCallCounter() <= JUMP_DURATION);
        }
    }
}
