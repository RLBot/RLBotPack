package rlbotexample.bot_behaviour.skill_controller.jump.implementations;

import rlbotexample.bot_behaviour.skill_controller.jump.JumpType;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector2;
import util.vector.Vector3;

public class HalfFlip extends JumpType {

    private static final int JUMP_DURATION = 20;
    private static final int[] JUMP_TIME_FRAMES = {2};

    public HalfFlip() {
        super(JUMP_DURATION, JUMP_TIME_FRAMES);
    }

    @Override
    public void jump(DataPacket input, BotOutput output, Vector3 desiredFrontOrientation, Vector3 desiredRoofOrientation) {
        updateCurrentJumpCallCounter();


        if(this.getCurrentJumpCallCounter() >= JUMP_TIME_FRAMES[0]) {
            Vector2 flipDirections = desiredFrontOrientation.flatten().scaledToMagnitude(2);
            output.pitch(-flipDirections.x);
            output.yaw(-flipDirections.y);
            output.roll(0);
        }
        if(this.getCurrentJumpCallCounter() + 1 == JUMP_TIME_FRAMES[0]) {
            // send a "no-jump" so we can jump a second time the next frame
            setJumpState(false);
        }
        else {
            setJumpState(getCurrentJumpCallCounter() <= JUMP_DURATION);
        }
    }
}
