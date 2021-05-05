package rlbotexample.bot_behaviour.path;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class OponentPositionPath extends PathHandler {

    public OponentPositionPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        Vector3 opponentPosition = input.allCars.get(1-input.playerIndex).position;
        Vector3 myNoseVector = input.car.orientation.noseVector;

        // adding the next position
        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(opponentPosition);
        controlPoints.add(opponentPosition.plus(new Vector3(0, 0, 1)));

        initiateNewPath(controlPoints, myNoseVector);
    }
}
