package util.shapes;

import util.vector.Vector3;

public class Triangle3D {
    public final Vector3 point0;
    public final Vector3 point1;
    public final Vector3 point2;

    public Triangle3D() {
        final Vector3 defaultVertex = new Vector3();
        this.point0 = defaultVertex;
        this.point1 = defaultVertex;
        this.point2 = defaultVertex;
    }

    public Triangle3D(final Vector3 point0, final Vector3 point1, final Vector3 point2) {
        this.point0 = point0;
        this.point1 = point1;
        this.point2 = point2;
    }

    public Vector3 getNormal() {
        final Vector3 vectoredEdge0 = point0.minus(point1);
        final Vector3 vectoredEdge1 = point1.minus(point2);
        final Vector3 notNormalizedNormal = vectoredEdge0.crossProduct(vectoredEdge1);

        return notNormalizedNormal.normalized();
    }

    public Vector3 getCenterPosition() {
        return point0.plus(point1).plus(point2).scaled(1.0/3);
    }
}
