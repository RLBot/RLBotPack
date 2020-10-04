package rlbotexample.bot_behaviour.path.test_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class RandomAerialPoint extends PathHandler {

    public RandomAerialPoint(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        double x = ((Math.random() - 0.5) * 2) * 3000;
        double y = ((Math.random() - 0.5) * 2) * 4000;
        double z = (Math.random() * 400) + 700;

        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(new Vector3(x, y, 800 + z));
        controlPoints.add(new Vector3(x, y, 801 + z));

        initiateNewPath(controlPoints, new Vector3(0, 0, 1));
    }
}
