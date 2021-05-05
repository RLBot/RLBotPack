package rlbotexample.bot_behaviour.path.test_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class RandomGroundPath1 extends PathHandler {

    public RandomGroundPath1(CarDestination desiredDestination) {
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
            for(int i = 0; i < 10; i++) {
                x = ((Math.random()-0.5)*2)*3000;
                y = ((Math.random()-0.5)*2)*4000;
                controlPoints.add(new Vector3(x, y, 50));
            }

            initiateNewPath(controlPoints, myNoseVector);
        }
    }
}
