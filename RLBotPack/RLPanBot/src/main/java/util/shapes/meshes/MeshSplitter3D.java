package util.shapes.meshes;

import rlbotexample.input.dynamic_data.HitBox;
import util.game_constants.RlConstants;
import util.shapes.Sphere;
import util.shapes.Triangle3D;
import util.vector.Ray3;
import util.vector.Vector3;
import util.vector.Vector3Int;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class MeshSplitter3D {

    public static final double SPLIT_SIZE = 100;
    public static final double OFFSET_POSITION_X = 2*RlConstants.WALL_DISTANCE_X;
    public static final double OFFSET_POSITION_Y = 1.2*RlConstants.WALL_DISTANCE_Y;
    public static final double OFFSET_POSITION_Z = 1000;
    public static final Vector3 OFFSET_POSITION = new Vector3(OFFSET_POSITION_X, OFFSET_POSITION_Y, OFFSET_POSITION_Z);

    private final Mesh3D initialMesh;
    private final Mesh3D[][][] meshArray;
    private static final List<Mesh3D> meshRegions = new ArrayList<>();

    public MeshSplitter3D(Mesh3D mesh) {
        this.initialMesh = mesh;
        int lengthX = (int)(4*RlConstants.WALL_DISTANCE_X/SPLIT_SIZE);
        int lengthY = (int)(6*RlConstants.WALL_DISTANCE_Y/SPLIT_SIZE);
        int lengthZ = (int)(2*RlConstants.CEILING_HEIGHT/SPLIT_SIZE);
        meshArray = new Mesh3D[lengthX][lengthY][lengthZ];
        split(mesh);
    }

    public Ray3 collideWith(Sphere sphere) {
        Ray3 resultingRay = new Ray3();
        meshRegions.clear();

        // rasterize a sphere with voxels
        int searchSize = (int)(sphere.radius*2/SPLIT_SIZE);
        int offset = 1;
        List<Vector3> indexToTest = new ArrayList<>();
        for(int i = -offset-1; i < searchSize + offset+1; i++) {
            for(int j = -offset-1; j < searchSize + offset+1; j++) {
                for(int k = -offset-1; k < searchSize + offset+1; k++) {
                    if(i*i + j*j + k*k < (sphere.radius/SPLIT_SIZE)*(sphere.radius/SPLIT_SIZE)*(1.5 * 1.5)) {
                        indexToTest.add(new Vector3(i, j, k));
                    }
                }
            }
        }

        // add all regions that have been rasterized
        for(Vector3 index3D: indexToTest) {
            final Vector3 centerOffset = new Vector3(1, 1, 1).scaled(SPLIT_SIZE/1.8);
            final Mesh3D meshRegion = queryMeshRegion(sphere.center.plus(centerOffset).plus(index3D.scaled(SPLIT_SIZE)));

            meshRegions.add(meshRegion);
        }

        // remove duplicate triangles from the calculations because hey, this is expensive, you know?
        Set<Triangle3D> removedTriangleDuplicates = new HashSet<>();
        for(Mesh3D mesh: meshRegions) {
            if(mesh != null) {
                removedTriangleDuplicates.addAll(mesh.triangleList);
            }
        }

        // do an average of all the ray normals that collide with the sphere
        int numberOfCollidingTriangles = 0;
        for(Triangle3D triangle : removedTriangleDuplicates) {
            final Vector3 n = triangle.getNormal();
            final Vector3 p = triangle.getCenterPosition();
            final Vector3 pr = sphere.center.projectOnto(triangle);
            final double separation = sphere.center.minus(p).dotProduct(n);
            final Vector3 ballVectorFromTriangle = sphere.center.minus(pr);
            if(ballVectorFromTriangle.magnitude() <= sphere.radius
                    && separation <= sphere.radius) {
                numberOfCollidingTriangles++;
                resultingRay.offset = resultingRay.offset.plus(sphere.center.minus(n.scaled(separation)));
                resultingRay.direction = resultingRay.direction.plus(n.scaled(sphere.radius - separation));
            }
        }

        // finish the average
        if(numberOfCollidingTriangles > 0) {
            resultingRay.offset = resultingRay.offset.scaled(1.0/numberOfCollidingTriangles);
            resultingRay.direction = resultingRay.direction.normalized();
        }

        return resultingRay;
    }

    // very ugly method duplicate, there is a better way to do this...
    public Ray3 collideWith(HitBox hitBox) {
        Ray3 resultingRay = new Ray3();
        meshRegions.clear();

        // rasterize a sphere with voxels
        final double hitBoxMaxRadius = hitBox.cornerPosition.magnitude();
        final Vector3 hitBoxCenter = hitBox.centerPosition;
        int searchSize = (int)(hitBoxMaxRadius*2/SPLIT_SIZE);
        int offset = 1;
        List<Vector3> indexToTest = new ArrayList<>();
        for(int i = -offset-1; i < searchSize + offset+1; i++) {
            for(int j = -offset-1; j < searchSize + offset+1; j++) {
                for(int k = -offset-1; k < searchSize + offset+1; k++) {
                    if(i*i + j*j + k*k < (hitBoxMaxRadius/SPLIT_SIZE)*(hitBoxMaxRadius/SPLIT_SIZE)*(1.5 * 1.5)) {
                        indexToTest.add(new Vector3(i, j, k));
                    }
                }
            }
        }

        // add all regions that have been rasterized
        for(Vector3 index3D: indexToTest) {
            final Vector3 centerOffset = new Vector3(1, 1, 1).scaled(SPLIT_SIZE/1.8);
            final Mesh3D meshRegion = queryMeshRegion(hitBoxCenter.plus(centerOffset).plus(index3D.scaled(SPLIT_SIZE)));

            meshRegions.add(meshRegion);
        }

        // remove duplicate triangles from the calculations because hey, this is expensive, you know?
        Set<Triangle3D> removedTriangleDuplicates = new HashSet<>();
        for(Mesh3D mesh: meshRegions) {
            if(mesh != null) {
                removedTriangleDuplicates.addAll(mesh.triangleList);
            }
        }

        // do an average of all the ray normals that collide with the sphere
        int numberOfCollidingTriangles = 0;
        for(Triangle3D triangle : removedTriangleDuplicates) {
            final Vector3 p = triangle.getCenterPosition();
            final Vector3 pr = hitBoxCenter.projectOnto(triangle);
            final Vector3 hitPointOnHitBox = hitBox.projectPointOnSurface(pr.plus(pr.minus(hitBoxCenter).scaledToMagnitude(10000)));
            final Vector3 n = triangle.getNormal();
            final double separation = hitBoxCenter.minus(p).dotProduct(n);
            final Vector3 hitBoxVectorFromTriangle = hitBoxCenter.minus(pr);

            final double hitBoxDynamicRadius = hitPointOnHitBox.minus(hitBoxCenter).magnitude();
            if(hitBoxVectorFromTriangle.magnitude() <= hitBoxDynamicRadius
                    && separation <= hitBoxDynamicRadius) {
                numberOfCollidingTriangles++;
                resultingRay.offset = resultingRay.offset.plus(hitBoxCenter.minus(n.scaled(separation)));
                resultingRay.direction = resultingRay.direction.plus(n.scaled(hitBoxDynamicRadius - separation));
            }
        }

        // finish the average
        if(numberOfCollidingTriangles > 0) {
            resultingRay.offset = resultingRay.offset.scaled(1.0/numberOfCollidingTriangles);
            resultingRay.direction = resultingRay.direction.normalized();
        }

        return resultingRay;
    }

    public Mesh3D queryMeshRegion(Vector3 globalPosition) {
        final Vector3 offsetPosition = globalPosition.plus(OFFSET_POSITION);
        final Vector3 indexVector = offsetPosition.scaled(1/SPLIT_SIZE);
        final Vector3Int index = new Vector3Int((int)indexVector.x, (int)indexVector.y, (int)indexVector.z);

        return meshArray[index.x][index.y][index.z];
    }

    private void split(Mesh3D mesh) {
        for(Triangle3D triangle: mesh.triangleList) {
            final List<Vector3Int> voxelIndexes = rasterizeTriangle3D(triangle);
            for(Vector3Int indexVector: voxelIndexes) {
                if (meshArray[indexVector.x][indexVector.y][indexVector.z] == null) {
                    meshArray[indexVector.x][indexVector.y][indexVector.z] = new Mesh3D();
                }
                meshArray[indexVector.x][indexVector.y][indexVector.z].addTriangleToMesh(triangle);
            }
        }
    }

    // a single triangle can be situated in many indexes at the same time
    // (like pixels, but here it's actually voxels in a sense),
    // so that's why we rasterize here
    // Watch out, this returns INDEXES, and not positions.
    // Duh, we're talking about voxels...
    private List<Vector3Int> rasterizeTriangle3D(Triangle3D triangle) {
        List<Vector3Int> voxels = new ArrayList<>();

        final double smallestPositionX = Math.min(Math.min(triangle.point0.x, triangle.point1.x), triangle.point2.x);
        final double smallestPositionY = Math.min(Math.min(triangle.point0.y, triangle.point1.y), triangle.point2.y);
        final double smallestPositionZ = Math.min(Math.min(triangle.point0.z, triangle.point1.z), triangle.point2.z);
        final double biggestPositionX = Math.max(Math.max(triangle.point0.x, triangle.point1.x), triangle.point2.x);
        final double biggestPositionY = Math.max(Math.max(triangle.point0.y, triangle.point1.y), triangle.point2.y);
        final double biggestPositionZ = Math.max(Math.max(triangle.point0.z, triangle.point1.z), triangle.point2.z);

        final int smallestIndexX = (int)((smallestPositionX+OFFSET_POSITION_X)/SPLIT_SIZE);
        final int smallestIndexY = (int)((smallestPositionY+OFFSET_POSITION_Y)/SPLIT_SIZE);
        final int smallestIndexZ = (int)((smallestPositionZ+OFFSET_POSITION_Z)/SPLIT_SIZE);
        final int biggestIndexX = (int)((biggestPositionX+OFFSET_POSITION_X)/SPLIT_SIZE);
        final int biggestIndexY = (int)((biggestPositionY+OFFSET_POSITION_Y)/SPLIT_SIZE);
        final int biggestIndexZ = (int)((biggestPositionZ+OFFSET_POSITION_Z)/SPLIT_SIZE);

        for(int i = smallestIndexX; i < biggestIndexX+2; i++) {
            for(int j = smallestIndexY; j < biggestIndexY+2; j++) {
                for(int k = smallestIndexZ; k < biggestIndexZ+2; k++) {
                    final Vector3 boxCenterPosition = new Vector3(i, j, k).scaled(SPLIT_SIZE).minus(OFFSET_POSITION);
                    final HitBox voxelHitBox = new HitBox(boxCenterPosition, new Vector3(SPLIT_SIZE/2, SPLIT_SIZE/2, SPLIT_SIZE/2));
                    final Vector3 projectedPointOnTriangle = boxCenterPosition.projectOnto(triangle);
                    final Vector3 projectedPointOnVoxel = voxelHitBox.projectPointOnSurface(projectedPointOnTriangle);
                    if(projectedPointOnTriangle.minus(projectedPointOnVoxel).magnitude() < 1) {
                        voxels.add(new Vector3Int(i, j, k));
                    }
                }
            }
        }

        return voxels;
    }
}
