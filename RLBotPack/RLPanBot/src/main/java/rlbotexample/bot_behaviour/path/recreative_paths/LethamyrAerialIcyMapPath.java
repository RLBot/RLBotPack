package rlbotexample.bot_behaviour.path.recreative_paths;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class LethamyrAerialIcyMapPath extends PathHandler {

    public LethamyrAerialIcyMapPath(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void generateNewPath(DataPacket input) {
        if(!getDesiredDestination().hasNext()) {
            Vector3 myPosition = input.car.position;
            Vector3 myNoseVector = input.car.orientation.noseVector;
            List<Vector3> controlPoints = new ArrayList<>();
            controlPoints.add(myPosition);
            controlPoints.add(new Vector3(0, 0, 800));

            // level 1
            controlPoints.add(new Vector3(800, -1500, 800));
            controlPoints.add(new Vector3(2500, -5000, 1600));
            controlPoints.add(new Vector3(4100, -8000, 1500));
            controlPoints.add(new Vector3(8000, -13000, 1500));
            controlPoints.add(new Vector3(8500, -15500, 1500));

            // level 2
            controlPoints.add(new Vector3(8500, -20000, 4500));
            controlPoints.add(new Vector3(6800, -23000, 5000));
            controlPoints.add(new Vector3(6000, -25500, 6000));
            controlPoints.add(new Vector3(4000, -26700, 6400));
            controlPoints.add(new Vector3(1200, -27500, 5000));

            // level 3
            controlPoints.add(new Vector3(-1700, -24300, 4750));
            controlPoints.add(new Vector3(-4000, -22700, 3600));
            controlPoints.add(new Vector3(-8320, -22100, 2100));
            controlPoints.add(new Vector3(-11480, -20580, 2700));
            controlPoints.add(new Vector3(-16160, -19280, 3500));

            // level 4
            controlPoints.add(new Vector3(-19580, -18320, 3140));
            controlPoints.add(new Vector3(-22510, -15370, 2230));
            controlPoints.add(new Vector3(-22520, -14590, 2320));
            controlPoints.add(new Vector3(-22320, -13730, 2560));
            controlPoints.add(new Vector3(-21090, -12980, 3280));
            controlPoints.add(new Vector3(-19540, -13450, 3450));
            controlPoints.add(new Vector3(-18130, -12780, 3030));
            controlPoints.add(new Vector3(-15450, -9770, 3100));

            // level 5
            controlPoints.add(new Vector3(-11660, -5050, 3080));
            controlPoints.add(new Vector3(-11800, -2750, 2830));
            controlPoints.add(new Vector3(-12050, -2190, 2690));
            controlPoints.add(new Vector3(-9580, 1060, 1780));
            controlPoints.add(new Vector3(-8690, 3770, 710));
            controlPoints.add(new Vector3(-10270, 6000, 880));
            controlPoints.add(new Vector3(-13860, 10270, 2700));

            // level 6
            controlPoints.add(new Vector3(-17750, 15480, 2660));
            controlPoints.add(new Vector3(-19690, 16850, 3620));
            controlPoints.add(new Vector3(-20370, 17680, 4690));
            controlPoints.add(new Vector3(-19990, 18830, 5040));
            controlPoints.add(new Vector3(-18760, 19740, 5110));
            controlPoints.add(new Vector3(-17470, 20860, 4960));
            controlPoints.add(new Vector3(-16490, 21290, 5000));
            controlPoints.add(new Vector3(-15060, 21020, 5870));
            controlPoints.add(new Vector3(-14000, 20030, 5320));
            controlPoints.add(new Vector3(-12920, 19710, 5200));
            controlPoints.add(new Vector3(-11350, 19910, 5150));
            controlPoints.add(new Vector3(-10420, 19660, 4670));
            controlPoints.add(new Vector3(-8670, 17000, 2890));
            controlPoints.add(new Vector3(-7150, 16220, 2830));
            controlPoints.add(new Vector3(-5030, 16810, 3090));
            controlPoints.add(new Vector3(-2780, 18180, 4690));
            controlPoints.add(new Vector3(-1020, 19070, 5150));
            controlPoints.add(new Vector3(1870, 20580, 5800));

            // these take so many time to find... omg

            initiateNewPath(controlPoints, myNoseVector);
        }
    }
}
