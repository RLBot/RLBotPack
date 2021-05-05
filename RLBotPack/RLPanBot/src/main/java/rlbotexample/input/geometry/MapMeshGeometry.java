package rlbotexample.input.geometry;

import util.shapes.Sphere;
import util.vector.Vector3;

public abstract class MapMeshGeometry {
    public abstract Vector3 getCollisionNormalOrElse(final Sphere sphere, final Vector3 defaultValue);
}
