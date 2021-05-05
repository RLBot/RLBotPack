package rlbotexample.input.prediction.player;

import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.prediction.Parabola3D;
import util.game_constants.RlConstants;
import util.vector.Vector3;

public class PlayerPredictedAerialTrajectory {

    private final Parabola3D ballTrajectory;
    private final CarData initialCarData;

    public PlayerPredictedAerialTrajectory(CarData carData) {
        this.ballTrajectory = new Parabola3D(carData.position, carData.velocity, new Vector3(0, 0, -RlConstants.NORMAL_GRAVITY_STRENGTH), 0);
        this.initialCarData = carData;
    }

    public CarData compute(double deltaTime) {
        final Vector3 newPosition = ballTrajectory.compute(deltaTime);
        final Vector3 newVelocityUncapped = ballTrajectory.derivative(deltaTime);

        // make sure to take into consideration that the car can't exceed 2300 uu/s
        final Vector3 newVelocity;
        if(newVelocityUncapped.magnitudeSquared() > RlConstants.CAR_MAX_SPEED * RlConstants.CAR_MAX_SPEED) {
            newVelocity = newVelocityUncapped.scaledToMagnitude(RlConstants.CAR_MAX_SPEED);
        }
        else {
            newVelocity = newVelocityUncapped;
        }

        return new CarData(newPosition, newVelocity, initialCarData.spin, initialCarData.boost, initialCarData.hitBox.generateHypotheticalHitBox(newPosition), 0);
    }
}
