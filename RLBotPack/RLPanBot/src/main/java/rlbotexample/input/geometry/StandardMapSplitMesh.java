package rlbotexample.input.geometry;

import rlbotexample.input.dynamic_data.HitBox;
import util.parameter_configuration.ObjFileReader;
import util.shapes.Sphere;
import util.shapes.Triangle3D;
import util.shapes.meshes.Mesh3D;
import util.shapes.meshes.MeshSplitter3D;
import util.vector.Ray3;
import util.vector.Vector3;

import java.util.List;

public class StandardMapSplitMesh {

    public static final MeshSplitter3D STANDARD_MAP_MESH = new MeshSplitter3D(ObjFileReader.loadMeshFromFile(ObjFileReader.STANDARD_MAP_MESH_GEOMETRY_PATH));

    public Ray3 getCollisionRayOrElse(final Sphere sphere, final Ray3 defaultRay) {
        final Ray3 collisionRay = STANDARD_MAP_MESH.collideWith(sphere);

        if(collisionRay.direction.magnitude() > 0) {
            return collisionRay;
        }

        return defaultRay;
    }

    public Ray3 getCollisionRayOrElse(final HitBox hitBox, final Ray3 defaultRay) {
        final Ray3 collisionRay = STANDARD_MAP_MESH.collideWith(hitBox);

        if(collisionRay.direction.magnitude() > 0) {
            return collisionRay;
        }

        return defaultRay;
    }
}
