package rlbotexample.bot_behaviour.car_destination;

import rlbotexample.input.dynamic_data.DataPacket;
import util.bezier_curve.CurveSegment;
import util.bezier_curve.PathComposite;
import util.bezier_curve.QuadraticPath;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;


public class CarDestination {

    private CarDestinationUpdater destinationUpdater;

    private Vector3 throttleDestination;
    private Vector3 previousThrottleDestination;

    private Vector3 steeringDestination;

    public CarDestination() {
        destinationUpdater = new CarDestinationUpdater(this);
        List<Vector3> controlPoints = new ArrayList<>();
        controlPoints.add(new Vector3(0, 0, 0));
        controlPoints.add(new Vector3(0, 0, 1));
        setPath(new QuadraticPath(controlPoints, new Vector3(0, 0, 1)));

        throttleDestination = new Vector3();
        previousThrottleDestination = new Vector3();
        steeringDestination = new Vector3();
    }

    public double getDesiredSpeed() {
        return destinationUpdater.getSpeed();
    }

    public void setDesiredSpeed(double speed) {
        destinationUpdater.setSpeed(speed);
    }

    public void advanceOneStep(DataPacket input) {
        if(hasNext()) {
            next(input);
        }
    }

    public boolean hasNext() {
        return destinationUpdater.hasNextThrottleDestination();
    }

    private void next(DataPacket input) {
        destinationUpdater.nextDestination(input);
    }

    public void pathLengthIncreased(int numberOfAddedPaths, int numberOfPaths) {
        destinationUpdater.pathLengthIncreased(numberOfAddedPaths, numberOfPaths);
    }

    public void setPath(PathComposite path) {
        destinationUpdater.setPath(path);
    }

    public CurveSegment getPath() {
        return destinationUpdater.getPath();
    }

    public Vector3 getThrottleDestination() {
        return throttleDestination;
    }

    public void setThrottleDestination(Vector3 throttleDestination) {
        this.previousThrottleDestination = this.throttleDestination;
        this.throttleDestination = throttleDestination;
    }

    public Vector3 getPreviousThrottleDestination() {
        return previousThrottleDestination;
    }

    public Vector3 getThrottleSpeed() {
        return throttleDestination.minus(previousThrottleDestination);
    }

    public Vector3 getSteeringDestination() {
       return steeringDestination;
    }

    public void setSteeringDestination(Vector3 steeringDestination) {
        this.steeringDestination = steeringDestination;
    }

    public static Vector3 getLocal(Vector3 globalPosition, DataPacket input) {
        Vector3 myPosition = input.car.position;
        Vector3 myNoseVector = input.car.orientation.noseVector;
        Vector3 myRoofVector = input.car.orientation.roofVector;

        return globalPosition.minus(myPosition).toFrameOfReference(myNoseVector, myRoofVector);
    }
}
