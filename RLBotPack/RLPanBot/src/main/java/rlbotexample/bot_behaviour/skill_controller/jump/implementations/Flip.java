package rlbotexample.bot_behaviour.skill_controller.jump.implementations;

import rlbotexample.bot_behaviour.skill_controller.jump.JumpType;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector2;
import util.vector.Vector3;

public class Flip extends JumpType {

    private static final int JUMP_DURATION = 20;
    private static final int[] JUMP_TIME_FRAMES = {2};

    public Flip() {
        super(JUMP_DURATION, JUMP_TIME_FRAMES);
    }

    @Override
    public void jump(DataPacket input, BotOutput output, Vector3 desiredFrontOrientation, Vector3 desiredRoofOrientation) {
        updateCurrentJumpCallCounter();
        setJumpState(false);

        if(this.getCurrentJumpCallCounter() == JUMP_TIME_FRAMES[0]) {
            Vector2 flipDirections = desiredFrontOrientation.flatten().normalized();
            output.pitch(-flipDirections.x);
            output.yaw(-flipDirections.y);
            output.roll(0);
            setJumpState(true);
            //System.out.println(flipDirections);
        }
        else if(this.getCurrentJumpCallCounter() > JUMP_TIME_FRAMES[0] && !this.isJumpFinished()) {
            output.pitch(0);
            output.yaw(0);
            output.roll(0);
        }
    }
}
