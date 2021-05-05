package rlbotexample.bot_behaviour.skill_controller.jump;

import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

public abstract class JumpType {
    private int jumpDuration;
    private int[] jumpKeyTimeFrames;
    private int currentJumpCallCounter;
    private boolean jumpState;
    private boolean lastJumpState;

    public JumpType(int jumpDuration, int[] keyTimeFrames) {
        this.jumpDuration = jumpDuration;
        this.jumpKeyTimeFrames = keyTimeFrames;
        currentJumpCallCounter = 0;
        lastJumpState = false;
        jumpState = false;
    }

    public abstract void jump(DataPacket input, BotOutput output, Vector3 desiredFrontOrientation, Vector3 desiredRoofOrientation);

    public boolean getLastJumpState() {
        return lastJumpState;
    }

    public boolean getJumpState() {
        return jumpState;
    }

    public void setJumpState(boolean jumpState) {
        this.lastJumpState = this.jumpState;
        this.jumpState = jumpState;
    }

    public int getJumpDuration() {
        return jumpDuration;
    }

    public int[] getKeyTimeFrames() {
        return jumpKeyTimeFrames;
    }

    public void updateCurrentJumpCallCounter() {
        currentJumpCallCounter++;
    }

    public int getCurrentJumpCallCounter() {
        return currentJumpCallCounter;
    }

    public boolean isJumpFinished() {
        return currentJumpCallCounter >= jumpDuration;
    }
}
