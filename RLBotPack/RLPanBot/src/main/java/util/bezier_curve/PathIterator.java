package util.bezier_curve;

import util.vector.Vector2;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;


public class PathIterator {

    private static final int INVERSE_BEZIER_CURVE_RESOLUTION = 10000;

    private double lengthIncrement;
    private CurveSegment path;
    private double currentT;
    private double precision;
    private List<Vector2> bezierFuncDataPoints; // P(arclength; t)

    public PathIterator(CurveSegment path, double lengthIncrement, double precision) {
        this.path = path;
        this.lengthIncrement = lengthIncrement;
        this.precision = precision;
        this.currentT = 0;
        bezierFuncDataPoints = new ArrayList<>();
    }


    // previous implementation
    public Vector3 next() {
        if (!hasNext()) throw new IndexOutOfBoundsException("Cannot get the next element!");

        double divisor = (1 - currentT) / 2;
        double newT = currentT + divisor;
        double currentSegmentLength = 0;

        while (Math.abs(currentSegmentLength - lengthIncrement) > precision / 2) {
            divisor /= 2;
            currentSegmentLength = path.segmentLength(currentT, newT, 100);

            if (currentSegmentLength < lengthIncrement) {
                newT += divisor;
            } else {
                newT -= divisor;
            }
        }

        currentT = newT;

        return path.interpolate(currentT);
    }

    public void pathLengthIncreased(int numberOfAddedPaths, int numberOfPaths) {
        // updating the t variable in the path composite
        currentT = (currentT * numberOfPaths) / (numberOfPaths + numberOfAddedPaths);
    }

    public boolean hasNext() {
        return path.segmentLength(currentT, 1, 100) > lengthIncrement;
    }

    public void setLengthIncrement(double lengthIncrement) {
        this.lengthIncrement = lengthIncrement;
    }

    public double getT() { return currentT; }
    public void setT(double newT) { currentT = newT; }
}
