package rlbotexample.bot_behaviour.path.recreative_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class MimicOpponentPath extends PathHandler {

    public MimicOpponentPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        Vector3 opponentPosition = input.allCars.get(1-input.playerIndex).position;

        // adding the next position
        getDesiredDestination().getPath().addPoints(opponentPosition);
        // updating the t variable in the path composite
        getDesiredDestination().pathLengthIncreased(1, getDesiredDestination().getPath().getPoints().size());
    }
}
