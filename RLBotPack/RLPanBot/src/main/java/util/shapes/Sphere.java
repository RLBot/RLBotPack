package util.shapes;

import util.vector.Vector3;

public class Sphere {

    public final Vector3 center;
    public final double radius;

    public Sphere(final Vector3 center, final double radius) {
        this.center = center;
        this.radius = Math.abs(radius);
    }

    public boolean isCollidingWith(final Vector3 point) {
        return center.minus(point).magnitudeSquared() < sq(radius);
    }

    private double sq(double x) {
        return x*x;
    }
}
