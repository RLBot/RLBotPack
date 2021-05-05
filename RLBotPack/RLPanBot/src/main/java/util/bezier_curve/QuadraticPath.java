package util.bezier_curve;

import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class QuadraticPath extends BezierCurve implements PathComposite {

    private static final int MAXIMUM_NUMBER_OF_CURVE_INSTANCE = 100;

    public List<CurveSegment> fragmentedPath;
    private Vector3 startingDirection;
    private Vector3 nextControlPoint;

    public QuadraticPath(List<Vector3> controlPoints, Vector3 startingDirection) {
        this.startingDirection = startingDirection;
        Vector3[] points = new Vector3[controlPoints.size()];
        super.setPoints(controlPoints.toArray(points));

        buildPath();
    }

    @Override
    public Vector3 interpolate(double t) {
        // Finding the actual t. t can be between 0 and n, n = number of curves, instead of only 1.
        // This transformation is due to the fact that we still want to get a position on the curve
        // from 0 < t < 1, but our internal variables are actually coping with 0 < t < n.
        double resizedT = t*fragmentedPath.size();
        // Finding the curve index (or curve number) is the same as flooring the resized t.
        int i = (int)resizedT;

        // The only edge case is when we plot t > 1 in the function, in which case
        // i = n, and so it gets it throws out of bound when we try to get from the curve list.
        // That's why, when t >= 1, we need to clamp it.
        if(t >= 1.0) {
            i = fragmentedPath.size()-1;
        }
        // same goes for the following, but with the lower bound clamping.
        else if(t < 0.0) {
            i = 0;
        }

        // return the interpolated point on one of the curves
        return fragmentedPath.get(i).interpolate(resizedT - (double)i);
    }

    @Override
    public void addPoints(Vector3... newPoints) {
        for(Vector3 newPoint: newPoints) {
            super.addPoints(newPoint);
            addPath(super.getPoints().size() - 1);
        }
        while(fragmentedPath.size() >= MAXIMUM_NUMBER_OF_CURVE_INSTANCE) {
            getPoints().remove(0);
            fragmentedPath.remove(0);
        }
    }

    private void buildPath() {
        // making sure parameters are valid before proceeding to the construction of the path
        if(this.getPoints().size() < 2) throw new IllegalArgumentException("Cannot construct a path with less than 2 control points!");

        fragmentedPath = new ArrayList<>();

        nextControlPoint = startingDirection.scaledToMagnitude(this.getPoints().get(0).minus(this.getPoints().get(1)).magnitude()/4);
        fragmentedPath.add(createBezierCurve(nextControlPoint, 0, 1));
        for(int i = 2; i < this.getPoints().size(); i++) {
            addPath(i);
        }
    }

    private QuadraticBezier createBezierCurve(Vector3 controlPoint, int i, int j) {
        Vector3 p0 = this.getPoints().get(i);
        Vector3 p1 = this.getPoints().get(j);

        return new QuadraticBezier(p0,
                p0.plus(controlPoint),
                p1);
    }

    private void addPath(int i) {
        // finding the next control point
        nextControlPoint = this.getPoints().get(i-1).minus(fragmentedPath.get(i-2).getPoints().get(1)).scaledToMagnitude(this.getPoints().get(i-1).minus(this.getPoints().get(i)).magnitude()/2);
        // generating a bezier curve that matches smoothly the end of the previous one
        QuadraticBezier bezier = createBezierCurve(nextControlPoint, i-1, i);
        fragmentedPath.add(bezier);
    }
}