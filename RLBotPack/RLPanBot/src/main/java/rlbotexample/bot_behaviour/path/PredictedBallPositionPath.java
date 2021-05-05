package rlbotexample.bot_behaviour.path;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class PredictedBallPositionPath extends PathHandler {

    public PredictedBallPositionPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        // get the future expected getNativeBallPrediction position
        Vector3 futureBallPosition = getFutureExpectedBallPosition(input);
        Vector3 destination = getDesiredDestination().getThrottleDestination();
        Vector3 steeringDestination = getDesiredDestination().getSteeringDestination();

        // creating the next path. Here, we do a little trick so we can generate
        // a new end point that goes to the getNativeBallPrediction prediction every frame.
        // It basically cuts the current path to where the throttle position is,
        // and creates a new path that starts there and ends where the
        // new predicted getNativeBallPrediction is.
        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(futureBallPosition);
        controlPoints.add(futureBallPosition.minus(new Vector3(0, 0, 1)));

        // generating the next path
        initiateNewPath(controlPoints, input.car.orientation.noseVector);
    }
}
