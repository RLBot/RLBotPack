package util.shapes.meshes;

import util.shapes.Sphere;
import util.shapes.Triangle3D;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class Mesh3D {

    public final List<Triangle3D> triangleList;

    public Mesh3D(final List<Triangle3D> triangleList) {
        this.triangleList = triangleList;
    }

    public Mesh3D() {
        this.triangleList = new ArrayList<>();
    }

    public Triangle3D getClosestTriangle(final Sphere sphere) {
        final Vector3 sphereCenter = sphere.center;
        Triangle3D closestTriangle = new Triangle3D();
        double bestDistanceWithTriangleSquared = Double.MAX_VALUE;

        for(Triangle3D triangle: triangleList) {
            final Vector3 projectedPointOnTriangle = sphereCenter.projectOnto(triangle);
            if(projectedPointOnTriangle.minus(sphereCenter).magnitudeSquared() < bestDistanceWithTriangleSquared) {
                closestTriangle = triangle;
                bestDistanceWithTriangleSquared = projectedPointOnTriangle.minus(sphereCenter).magnitudeSquared();
            }
        }

        return closestTriangle;
    }

    public void addTriangleToMesh(Triangle3D triangleList) {
        this.triangleList.add(triangleList);
    }
}
