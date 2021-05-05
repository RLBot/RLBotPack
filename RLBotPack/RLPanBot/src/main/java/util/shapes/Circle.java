package util.shapes;

import util.vector.Vector2;

public class Circle {

    private Vector2 center;
    private double radius;

    public Circle(Vector2 center, double radius) {
        this.center = center;
        this.radius = radius;
    }

    public Vector2 getCenter() {
        return center;
    }

    public double getRadius() {
        return radius;
    }

    public boolean contains(Vector2 point) {
        return point.minus(center).magnitudeSquared() < radius * radius;
    }
}
