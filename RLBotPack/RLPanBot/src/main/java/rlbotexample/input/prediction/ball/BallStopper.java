package rlbotexample.input.prediction.ball;

import rlbotexample.input.dynamic_data.BallData;
import util.game_constants.RlConstants;
import util.vector.Vector3;

public class BallStopper {

    private double amountOfTimeSinceCriticalSlowSpeedReached;

    public BallStopper() {
        this.amountOfTimeSinceCriticalSlowSpeedReached = 0;
    }

    public BallData compute(BallData ballData, double deltaTime) {
        amountOfTimeSinceCriticalSlowSpeedReached += deltaTime;

        Vector3 newPosition = ballData.position;
        Vector3 newVelocity = ballData.velocity;
        Vector3 newSpin = ballData.spin;

        if(hasStoppedMoving(ballData)) {
            amountOfTimeSinceCriticalSlowSpeedReached = 0;
            newVelocity = new Vector3();
            newSpin = new Vector3();
        }

        return new BallData(newPosition, newVelocity, newSpin, 0);
    }

    private boolean hasStoppedMoving(BallData ballData) {
        return ballData.velocity.magnitudeSquared() < square(RlConstants.BALL_MINIMUM_ROLLING_SPEED)
                && amountOfTimeSinceCriticalSlowSpeedReached > RlConstants.BALL_CRITICAL_AMOUNT_OF_TIME_OF_SLOW_SPEED_ROLLING_BEFORE_COMPLETE_STOP
                && ballData.spin.scaled(1/(Math.PI*2)).magnitudeSquared() < square(RlConstants.BALL_MINIMUM_RPM_WHEN_ROLLING_BEFORE_COMPLETE_STOP/60);
    }

    private double square(double x) {
        return x*x;
    }
}
