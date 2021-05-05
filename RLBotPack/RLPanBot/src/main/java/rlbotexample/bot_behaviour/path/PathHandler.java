package rlbotexample.bot_behaviour.path;

import rlbot.cppinterop.RLBotDll;
import rlbot.flat.BallPrediction;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.bezier_curve.QuadraticPath;
import util.vector.Vector3;

import java.util.List;

public abstract class PathHandler {

    private CarDestination desiredDestination;

    public PathHandler(CarDestination desiredDestination) {
        this.desiredDestination = desiredDestination;
    }

    public abstract void generateNewPath(DataPacket input);

    public void updateDestination(DataPacket input) {
        generateNewPath(input);
        desiredDestination.advanceOneStep(input);
    }

    public CarDestination getDesiredDestination() {
        return desiredDestination;
    }

    public static Vector3 getFutureExpectedBallPosition(DataPacket input) {
        try {
            // Get the "thanks-god" implementation of the getNativeBallPrediction prediction and use it to find
            // the next likely future position
            Vector3 myPosition = input.car.position;
            Vector3 currentBallPosition = input.ball.position;
            BallPrediction ballPrediction = RLBotDll.getBallPrediction();
            Vector3 futureBallPosition = new Vector3(ballPrediction.slices(0).physics().location());
            double divisor = (double)ballPrediction.slicesLength()/2;
            int currentBallPositionIndex = (int)divisor;
            double initialBallTime;
            double futureBallTime;
            double timeToGo;

            // pinpoint the position where PanBot will hit the getNativeBallPrediction
            while(divisor >= 1) {
                divisor /= 2;
                futureBallPosition = new Vector3(ballPrediction.slices(currentBallPositionIndex).physics().location());
                initialBallTime = ballPrediction.slices(0).gameSeconds();
                futureBallTime = ballPrediction.slices(currentBallPositionIndex).gameSeconds();
                timeToGo = (myPosition.minus(futureBallPosition).magnitude() - 150)/input.car.velocity.magnitude();

                if(timeToGo > futureBallTime - initialBallTime) {
                    currentBallPositionIndex += divisor;
                }
                else {
                    currentBallPositionIndex -= divisor;
                }
            }

            // return hte predicted getNativeBallPrediction position
            return futureBallPosition;
        }
        catch(Exception e) {
            e.printStackTrace();

            // return a 0ed vector if getNativeBallPrediction prediction is not working.
            return new Vector3();
        }
    }

    public void initiateNewPath(List<Vector3> controlPoints, Vector3 initialDirection) {
        this.desiredDestination.setPath(new QuadraticPath(controlPoints, initialDirection));
    }

}
