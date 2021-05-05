package rlbotexample.output;

public class BotOutput {

    private ControlsOutput output;

    public BotOutput() {
        // default value (do nothing)
        output = new ControlsOutput().withThrottle(0)
                .withSteer(0)
                .withJump(false)
                .withBoost(false)
                .withSlide(false)
                .withPitch(0)
                .withRoll(0)
                .withYaw(0);
    }

    public ControlsOutput getForwardedOutput() {
        return output;
    }

    public void throttle(double throttleAmount) {
        output.withThrottle((float)throttleAmount);
    }

    public double throttle() {
        return output.getThrottle();
    }

    public void steer(double steerAmount) {
        output.withSteer((float)steerAmount);
    }

    public double steer() {
        return output.getSteer();
    }

    public void jump(boolean isJumping) {
        output.withJump(isJumping);
    }

    public boolean jump() {
        return output.holdJump();
    }

    public void boost(boolean isBoosting) {
        output.withBoost(isBoosting);
    }

    public boolean boost() {
        return output.holdBoost();
    }

    public void drift(boolean isDrifting) {
        output.withSlide(isDrifting);
    }

    public boolean drift() {
        return output.holdHandbrake();
    }

    public void pitch(double pitchAmount) {
        output.withPitch((float)pitchAmount);
    }

    public double pitch() {
        return output.getPitch();
    }

    public void roll(double rollAmount) {
        output.withRoll((float)rollAmount);
    }

    public double roll() {
        return output.getRoll();
    }

    public void yaw(double yawAmount) {
        output.withYaw((float)yawAmount);
    }

    public double yaw() {
        return output.getYaw();
    }


}
