package rlbotexample.input.prediction.player;

import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.dynamic_data.ExtendedCarData;
import rlbotexample.input.dynamic_data.Orientation;
import util.vector.Vector3;

public class PlayerPredictedGroundTrajectory {

    private final CarData carData;

    public PlayerPredictedGroundTrajectory(CarData carData) {
        this.carData = carData;
    }

    public CarData predict(double secondsInTheFuture) {
        Vector3 playerPosition = carData.position;
        Vector3 playerSpeed = carData.velocity;
        Vector3 playerSpin = carData.spin;
        double spinAmount = -playerSpin.z;

        if(Math.abs(spinAmount) < 0.000001) {
            spinAmount = 0.000001;
        }

        double timeToDoOneRotation = 2*Math.PI/spinAmount;
        double circumference = timeToDoOneRotation * playerSpeed.magnitude();
        double radius = circumference/(2*Math.PI);

        double arcDistance = playerSpeed.magnitude()*secondsInTheFuture;
        double deltaRadiansOnCircle = arcDistance/radius;

        double deltaPositionXOnCircle = Math.cos(deltaRadiansOnCircle) * radius;
        double deltaPositionYOnCircle = Math.sin(deltaRadiansOnCircle) * radius;
        Vector3 initialDeltaPositionOnCircle = new Vector3(radius, 0, 0);
        Vector3 nextDeltaPositionOnCircle = new Vector3(deltaPositionXOnCircle, deltaPositionYOnCircle, 0);
        Vector3 nextPositionOnCenteredCircle = nextDeltaPositionOnCircle.minus(initialDeltaPositionOnCircle).plusAngle(playerSpeed).plusAngle(new Vector3(0, -1, 0));

        Vector3 futurePlayerPosition = nextPositionOnCenteredCircle.plus(playerPosition);
        Vector3 futurePlayerSpeed = playerSpeed;

        // TODO
        //  Rotate that predicted hit box too
        return new CarData(futurePlayerPosition, futurePlayerSpeed, carData.spin, carData.boost, carData.hitBox, secondsInTheFuture);
    }

}
