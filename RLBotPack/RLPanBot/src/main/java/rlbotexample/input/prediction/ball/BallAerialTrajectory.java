package rlbotexample.input.prediction.ball;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.prediction.Parabola3D;
import util.game_constants.RlConstants;
import util.vector.Vector3;

public class BallAerialTrajectory {

    private final Parabola3D ballTrajectory;
    private final Vector3 spin;

    public BallAerialTrajectory(final BallData ballData) {
        this.ballTrajectory = new Parabola3D(ballData.position, ballData.velocity, new Vector3(0, 0, -RlConstants.NORMAL_GRAVITY_STRENGTH), RlConstants.BALL_AIR_DRAG_COEFFICIENT);
        this.spin = ballData.spin;
    }

    public BallData compute(double deltaTime) {
        final Vector3 newPosition = ballTrajectory.compute(deltaTime);
        final Vector3 newVelocity = ballTrajectory.derivative(deltaTime);

        return new BallData(newPosition, newVelocity, spin, 0);
    }

}
