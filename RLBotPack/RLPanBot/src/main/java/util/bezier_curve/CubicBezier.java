package util.bezier_curve;

import util.vector.Vector3;

import java.util.List;

public class CubicBezier extends BezierCurve implements CurveSegment {

    public CubicBezier(Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3) {
        super(p0, p1, p2, p3);
    }

    @Override
    public Vector3 interpolate(double t) {
        List<Vector3> points = getPoints();
        return points.get(0).scaled((1-t)*(1-t)*(1-t)) .plus(
                points.get(1).scaled(3*t*(1-t)*(1-t))) .plus(
                points.get(2).scaled(3*t*t*(1-t))) .plus(
                points.get(3).scaled(t*t*t));
    }
}
