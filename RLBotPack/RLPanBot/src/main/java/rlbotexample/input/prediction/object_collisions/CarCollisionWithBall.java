package rlbotexample.input.prediction.object_collisions;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.dynamic_data.HitBox;
import util.vector.Vector3;

public class CarCollisionWithBall {

    final CarData initialCar;

    public CarCollisionWithBall(final CarData carData, final BallData ballData) {
        this.initialCar = carData;
    }

    public CarData compute(final double deltaTime) {
        return initialCar;
    }
}
