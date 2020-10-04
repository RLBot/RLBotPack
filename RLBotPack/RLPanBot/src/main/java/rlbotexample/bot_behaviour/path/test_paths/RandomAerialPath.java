package rlbotexample.bot_behaviour.path.test_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class RandomAerialPath extends PathHandler {

    public RandomAerialPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        if(!getDesiredDestination().hasNext()) {
            Vector3 myPosition = input.car.position;
            Vector3 myNoseVector = input.car.orientation.noseVector;
            List<Vector3> controlPoints = new ArrayList<>();
            controlPoints.add(myPosition);

            double x;
            double y;
            double z;
            for (int i = 0; i < 10; i++) {
                x = ((Math.random() - 0.5) * 2) * 3000;
                y = ((Math.random() - 0.5) * 2) * 4000;
                z = Math.random() * 600;
                controlPoints.add(new Vector3(x, y, 800 + z));
            }

            initiateNewPath(controlPoints, myNoseVector);
        }
    }
}
