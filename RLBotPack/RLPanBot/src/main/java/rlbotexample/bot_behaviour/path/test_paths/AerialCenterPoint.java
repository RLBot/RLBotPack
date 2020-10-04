package rlbotexample.bot_behaviour.path.test_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class AerialCenterPoint extends PathHandler {

    public AerialCenterPoint(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        double x = 0;
        double y = 0;
        double z = 500;

        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(new Vector3(x, y, z));
        controlPoints.add(new Vector3(x, y, z+1));

        initiateNewPath(controlPoints, new Vector3(0, 0, 1));
    }
}
