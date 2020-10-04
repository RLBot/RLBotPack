package util.bezier_curve;

import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class CubicPath extends BezierCurve implements PathComposite {

    private List<Vector3> controlPoints;
    private List<CubicBezier> fragmentedPath;

    public CubicPath(List<Vector3> controlPoints, Vector3 startingDirection) {
        // making sure parameters are valid before proceeding to the construction of the path
        if(controlPoints.size() < 2) throw new IllegalArgumentException("Cannot construct a path with less than 2 control points!");
        if(startingDirection.isZero()) throw new IllegalArgumentException("Cannot construct a path with no initial direction!");

        this.controlPoints = controlPoints;
        this.fragmentedPath = new ArrayList<>();

        // initializing the first curve so we can use a for loop for the rest of the curves
        fragmentedPath.add(createBezierCurve(startingDirection, 0, 1));

        for(int i = 2; i < controlPoints.size(); i++) {
            // finding the next control point
            Vector3 previousControlPointP2 = fragmentedPath.get(i-2).getPoints().get(2);
            Vector3 previousControlPointP3 = fragmentedPath.get(i-2).getPoints().get(3);
            Vector3 currentControlPointP1 = previousControlPointP3.minus(previousControlPointP2);
            // generating a bezier curve that matches smoothly the end of the previous one
            CubicBezier bezier = createBezierCurve(currentControlPointP1, i-1, i);
            fragmentedPath.add(bezier);
        }
    }

    @Override
    public Vector3 interpolate(double t) {
        double resizedT = t*fragmentedPath.size();
        int i = (int)resizedT;

        return fragmentedPath.get(i).interpolate(resizedT - (double)i);
    }

    private CubicBezier createBezierCurve(Vector3 startingDirection, int i, int j) {
        Vector3 p0 = controlPoints.get(i);
        Vector3 p1 = controlPoints.get(j);

        double distanceBetweenMeAndBall = p0.minus(p1).magnitude();
        double halfDistanceBetweenMeAndBall = distanceBetweenMeAndBall/2;

        // alright this is stupendously complicated for the thing that it does.
        // it only takes a point p and mirrors it through a plane z that can have any desired orientation.
        // this allows for finding symmetrical control points of cubic bezier curves, so that a nice symmetric curve
        // can be generated with only two endpoints (and a starting direction)

        Vector3 controlPoint0 = startingDirection.scaledToMagnitude(halfDistanceBetweenMeAndBall);
        Vector3 unitVectorZ = p1.minus(p0).normalized();
        Vector3 newZCoordinate = unitVectorZ.scaled(-controlPoint0.dotProduct(unitVectorZ));
        Vector3 unitVectorX = newZCoordinate.crossProduct(controlPoint0).normalized();
        Vector3 newXCoordinate = unitVectorX.scaled(controlPoint0.dotProduct(unitVectorX));
        Vector3 unitVectorY = newZCoordinate.crossProduct(unitVectorX).normalized();
        Vector3 newYCoordinate = unitVectorY.scaled(controlPoint0.dotProduct(unitVectorY));
        Vector3 controlPoint1 = newZCoordinate.plus(newXCoordinate).plus(newYCoordinate);

        return new CubicBezier(p0,
                p0.plus(controlPoint0),
                p1.plus(controlPoint1),
                p1);
    }
}
