package rlbotexample.input.prediction.ball;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.geometry.StandardMapSplitMesh;
import rlbotexample.input.prediction.object_collisions.BallCollisionWithCar;
import rlbotexample.input.prediction.object_collisions.CarCollisionWithBall;
import rlbotexample.input.prediction.player.CarBounce;
import rlbotexample.input.prediction.player.PlayerPredictedAerialTrajectory;
import util.game_constants.RlConstants;
import util.shapes.Sphere;
import util.vector.Ray3;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class AdvancedBallPrediction {

    public final List<BallData> balls = new ArrayList<>();
    public final List<List<CarData>> cars = new ArrayList<>();
    private final double amountOfAvailableTime;
    private final double refreshRate;
    private final BallData initialBall;
    private final List<CarData> initialCars;
    private final BallStopper ballStopper = new BallStopper();
    private final StandardMapSplitMesh standardMap = new StandardMapSplitMesh();
    private final List<Integer> nextBallBounceIndexes = new ArrayList<>();
    private final Integer[] carsHitOnBallTimeIndexes;

    public AdvancedBallPrediction(final BallData initialBall, final List<CarData> initialCars, final double amountOfAvailableTime, final double refreshRate) {
        this.initialBall = initialBall;
        this.initialCars = initialCars;
        this.amountOfAvailableTime = amountOfAvailableTime;
        this.refreshRate = refreshRate;
        this.carsHitOnBallTimeIndexes = new Integer[initialCars.size()];
        loadCustomBallPrediction(amountOfAvailableTime);
    }

    public BallData ballAtTime(final double deltaTime) {
        if((int) (refreshRate * deltaTime) >= balls.size()) {
            return balls.get(balls.size() - 1);
        }
        else if((int) (refreshRate * deltaTime) < 0) {
            return balls.get(0);
        }
        return balls.get((int) (refreshRate * deltaTime));
    }

    public List<Double> ballBounceTimes() {
        final List<Double> timeList = new ArrayList<>();
        for (Integer nextBallBounceIndex : nextBallBounceIndexes) {
            timeList.add(balls.get(nextBallBounceIndex).time);
        }
        return timeList;
    }

    public double timeOfCollisionBetweenCarAndBall(final int playerIndex) {
        if(carsHitOnBallTimeIndexes[playerIndex] == null) {
            return Double.MAX_VALUE;
        }
        return balls.get(carsHitOnBallTimeIndexes[playerIndex]).time;
    }

    public List<CarData> carsAtTime(final double deltaTime) {
        if((int) (refreshRate * deltaTime) >= cars.size()) {
            return cars.get(cars.size() - 1);
        }
        else if((int) (refreshRate * deltaTime) < 0) {
            return cars.get(0);
        }
        return cars.get((int) (refreshRate * deltaTime));
    }

    private void loadCustomBallPrediction(final double amountOfPredictionTimeToLoad) {
        // clear the current ball path so we can load the next one
        balls.clear();
        balls.add(initialBall);
        cars.clear();
        cars.add(initialCars);

        nextBallBounceIndexes.clear();

        // instantiate useful values
        BallData previousPredictedBall = initialBall;
        BallData predictedBall;
        List<CarData> previousPredictedCars = initialCars;
        List<CarData> predictedCars = new ArrayList<>();
        for(int i = 0; i < amountOfPredictionTimeToLoad*refreshRate; i++) {
            // handle aerial ball
            predictedBall = updateAerialBall(previousPredictedBall, 1/refreshRate);

            // update cars' positions
            for(CarData previousPredictedCar: previousPredictedCars) {
                final CarData notBouncedCar = updateAerialCar(previousPredictedCar, 1/refreshRate);
                final CarData predictedCar = updateCarBounceFromMap(notBouncedCar, 1/refreshRate);
                predictedCars.add(predictedCar);
            }

            // save the current ball to compute the car's bounce with it just after computing the ball itself
            final BallData savedPredictedBallForCarCollisions = predictedBall;

            // bounce the ball off of cars
            for(CarData predictedCar: predictedCars) {
                predictedBall = updateBallFromCollision(predictedBall, predictedCar, 1/refreshRate);
            }

            // bounce the cars off of the saved ball
            final List<CarData> carListForSwap = new ArrayList<>();
            for(int j = 0; j < predictedCars.size(); j++) {
                carListForSwap.add(updateCarFromCollision(predictedCars.get(j), savedPredictedBallForCarCollisions, j, i, 1/refreshRate));
            }
            predictedCars = carListForSwap;

            // handle ball bounces and roll (ball stay unchanged if no collision)
            predictedBall = updateBallBounceAndRoll(predictedBall, 1/refreshRate, i);

            // stop the ball if it's rolling too slowly
            predictedBall = updateBallStopper(predictedBall, 1/refreshRate);

            // make sure to set the predicted game time correctly (these are seconds from the in-game current time frame)
            predictedBall = new BallData(predictedBall.position, predictedBall.velocity, predictedBall.spin, i/refreshRate);

            // save and reset the ball
            balls.add(predictedBall);
            previousPredictedBall = predictedBall;

            // save and reset the cars
            cars.add(predictedCars);
            previousPredictedCars = predictedCars;
            predictedCars = new ArrayList<>();
        }
    }

    private BallData updateAerialBall(final BallData ballData, final double deltaTime) {
        final BallAerialTrajectory ballTrajectory = new BallAerialTrajectory(ballData);
        return ballTrajectory.compute(deltaTime);
    }

    private BallData updateBallBounceAndRoll(final BallData ball, final double deltaTime, final int predictedINdex) {
        final Ray3 rayNormal = standardMap.getCollisionRayOrElse(
                new Sphere(ball.position, RlConstants.BALL_RADIUS),
                new Ray3());

        if(!rayNormal.direction.isZero() && rayNormal.direction.dotProduct(ball.velocity) < 0) {
            nextBallBounceIndexes.add(predictedINdex);
            return new BallBounce(ball, rayNormal).compute(deltaTime);
        }

        return ball;
    }

    private BallData updateBallStopper(final BallData ballData, final double deltaTime) {
        return ballStopper.compute(ballData, deltaTime);
    }

    private CarData updateAerialCar(final CarData carData, final double deltaTime) {
        final PlayerPredictedAerialTrajectory carTrajectory = new PlayerPredictedAerialTrajectory(carData);
        return carTrajectory.compute(deltaTime);
    }

    // this might not work for wheel collisions...
    private CarData updateCarBounceFromMap(final CarData carData, final double deltaTime) {
        final Ray3 rayNormal = standardMap.getCollisionRayOrElse(carData.hitBox, new Ray3());

        if(!rayNormal.direction.isZero() && rayNormal.direction.dotProduct(carData.velocity) < 0) {
            return new CarBounce(carData, rayNormal).compute(deltaTime);
        }

        return carData;
    }

    /*
    private CarData updateGroundCar(final double deltaTime) {
        return null;
    }
    */

    private BallData updateBallFromCollision(final BallData ballData, final CarData carData, final double deltaTime) {
        final Vector3 carCenterHitBoxPosition = carData.hitBox.centerPosition;
        final Vector3 pointOnCarSurfaceTowardBall = carData.hitBox.projectPointOnSurface(ballData.position);
        final double specificCarRadiusWithRespectToBall = pointOnCarSurfaceTowardBall.minus(carCenterHitBoxPosition).magnitude();

        if(carCenterHitBoxPosition.minus(ballData.position).magnitude() < specificCarRadiusWithRespectToBall + RlConstants.BALL_RADIUS) {
            return new BallCollisionWithCar(ballData, carData).compute(deltaTime);
        }

        return ballData;
    }

    private CarData updateCarFromCollision(final CarData carData, final BallData ballData, final int playerIndex, final int predictedFrameCount, final double deltaTime) {
        final Vector3 carCenterHitBoxPosition = carData.hitBox.centerPosition;
        final Vector3 pointOnCarSurfaceTowardBall = carData.hitBox.projectPointOnSurface(ballData.position);
        final double specificCarRadiusWithRespectToBall = pointOnCarSurfaceTowardBall.minus(carCenterHitBoxPosition).magnitude();

        if(carCenterHitBoxPosition.minus(ballData.position).magnitude() < specificCarRadiusWithRespectToBall + RlConstants.BALL_RADIUS) {
            carsHitOnBallTimeIndexes[playerIndex] = predictedFrameCount;
            return new CarCollisionWithBall(carData, ballData).compute(deltaTime);
        }

        return carData;
    }

    private CarData updateCarFromCollision(final CarData carToUpdate, final CarData carToCollideWith, final double deltaTime) {
        return carToUpdate;
    }
}
