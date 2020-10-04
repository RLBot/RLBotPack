package util.bezier_curve;

import util.vector.Vector3;

import java.util.List;

public interface CurveSegment {

    Vector3 interpolate(double t);
    double segmentLength(double t0, double t1, int resolution);
    double curveLength(int resolution);
    double findTFromNearest(Vector3 point, double offsetT, double lengthIncrement, double resolution);
    List<Vector3> getPoints();
    void addPoints(Vector3... newPoint);
}
