package rlbotexample.input.prediction.object_collisions;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.CarData;
import util.vector.Vector3;

public class BallCollisionWithCar {

    final BallData initialBallData;
    final CarData initialCarData;

    public BallCollisionWithCar(final BallData ballData, final CarData carData) {
        initialBallData = ballData;
        initialCarData = carData;
    }

    public BallData compute(final double deltaTime) {
        final double collisionEfficiencyRatio = Math.atan(1.0/20)/(Math.PI/2);
        final Vector3 deltaSpeed = initialBallData.velocity.minus(initialCarData.velocity);
        final Vector3 normal = initialBallData.position.minus(initialCarData.position).normalized();
        final Vector3 paraBallSpeed = initialBallData.velocity.projectOnto(normal);
        final Vector3 paraDeltaSpeed = deltaSpeed.projectOnto(normal);

        return new BallData(initialBallData.position, initialBallData.velocity.minus(paraDeltaSpeed).plus(paraDeltaSpeed.scaled(collisionEfficiencyRatio)), initialBallData.spin, 0);
    }
}
