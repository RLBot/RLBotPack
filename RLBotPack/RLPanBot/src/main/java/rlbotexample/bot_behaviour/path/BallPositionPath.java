package rlbotexample.bot_behaviour.path;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class BallPositionPath extends PathHandler {

    public BallPositionPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        Vector3 destination = getDesiredDestination().getThrottleDestination();
        Vector3 steeringDestination = getDesiredDestination().getSteeringDestination();

        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(input.ball.position);
        controlPoints.add(input.ball.position.minus(new Vector3(0, 0, 1)));

        // generating the next path
        initiateNewPath(controlPoints, steeringDestination.minus(destination));
    }
}
