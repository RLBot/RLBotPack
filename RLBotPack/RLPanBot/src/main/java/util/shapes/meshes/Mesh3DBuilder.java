package util.shapes.meshes;

import util.shapes.Triangle3D;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class Mesh3DBuilder {

    private final List<Vector3> vertexList = new ArrayList<>();
    private final List<Triangle3D> triangleList = new ArrayList<>();

    public Mesh3DBuilder() {
    }

    public Mesh3DBuilder addVertex(Vector3 vertex) {
        vertexList.add(vertex);
        return this;
    }

    public Mesh3DBuilder addTriangle(int vertexIndex0, int vertexIndex1, int vertexIndex2) {
        final Vector3 vertex0 = vertexList.get(vertexIndex0);
        final Vector3 vertex1 = vertexList.get(vertexIndex1);
        final Vector3 vertex2 = vertexList.get(vertexIndex2);
        final Triangle3D triangle = new Triangle3D(vertex0, vertex1, vertex2);
        triangleList.add(triangle);
        return this;
    }

    public Mesh3D build() {
        return new Mesh3D(triangleList);
    }
}
