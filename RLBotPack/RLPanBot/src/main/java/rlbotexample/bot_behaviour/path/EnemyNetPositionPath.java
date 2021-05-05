package rlbotexample.bot_behaviour.path;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class EnemyNetPositionPath extends PathHandler {

    public EnemyNetPositionPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        if(!getDesiredDestination().hasNext()) {
            Vector3 initialDirection = new Vector3(0, -1, 0);
            List<Vector3> controlPoints = new ArrayList<>();
            if(input.car.team == 0) {
                double playerDistanceFromGoal = input.car.position.minus(new Vector3(0, 5500, 50)).magnitude();
                controlPoints.add(new Vector3(0, 5500 - Math.min(playerDistanceFromGoal/3, 2000), 50));
                controlPoints.add(new Vector3(0, 5501 - Math.min(playerDistanceFromGoal/3, 2000), 50));
            }
            else {
                double playerDistanceFromGoal = input.car.position.minus(new Vector3(0, -5500, 50)).magnitude();
                controlPoints.add(new Vector3(0, -5500 + Math.min(playerDistanceFromGoal/3, 2000), 50));
                controlPoints.add(new Vector3(0, -5501 + Math.min(playerDistanceFromGoal/3, 2000), 50));
            }

            initiateNewPath(controlPoints, initialDirection);
        }
    }
}
