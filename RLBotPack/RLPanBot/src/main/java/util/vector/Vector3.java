package util.vector;

import com.google.flatbuffers.FlatBufferBuilder;
import rlbot.flat.Rotator;
import rlbot.render.Renderer;
import rlbotexample.input.dynamic_data.CarOrientation;
import rlbotexample.input.dynamic_data.Orientation;
import util.shapes.Triangle3D;

import java.awt.*;
import java.util.Objects;

/**
 * A simple 3d vector class with the most essential operations.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can add to it as much
 * as you want, or delete it.
 */
public class Vector3 extends rlbot.vector.Vector3 {

    public static final Vector3 UP_VECTOR = new Vector3(0, 0, 1);

    public Vector3(double x, double y, double z) {
        super((float) x, (float) y, (float) z);
    }

    public Vector3(Vector2 xy, double z) { super((float) xy.x, (float) xy.y, (float) z); }

    public Vector3() {
        this(0, 0, 0);
    }

    public Vector3(Vector3 v) {
        this(v.x, v.y, v.z);
    }

    public Vector3(Rotator rotator) {
        this(rotator.pitch(), rotator.yaw(), rotator.roll());
    }

    public Vector3(rlbot.flat.Vector3 vec) {
        // Invert the X value so that the axes make more sense.
        this(-vec.x(), vec.y(), vec.z());
    }

    public int toFlatbuffer(FlatBufferBuilder builder) {
        // Invert the X value again so that rlbot sees the format it expects.
        return rlbot.flat.Vector3.createVector3(builder, -x, y, z);
    }

    public Vector3 plus(Vector3 other) {
        return new Vector3(x + other.x, y + other.y, z + other.z);
    }

    public Vector3 minus(Vector3 other) {
        return new Vector3(x - other.x, y - other.y, z - other.z);
    }

    public Vector3 scaled(double scale) {
        return new Vector3(x * scale, y * scale, z * scale);
    }

    public Vector3 scaled(double scaleX, double scaleY, double scaleZ) {
        return new Vector3(x * scaleX, y * scaleY, z * scaleZ);
    }

    /**
     * If magnitude is negative, we will return a vector facing the opposite direction.
     */
    public Vector3 scaledToMagnitude(double magnitude) {
        if (isZero()) {
            return new Vector3();
        }
        double scaleRequired = magnitude / magnitude();
        return scaled(scaleRequired);
    }

    public double distance(Vector3 other) {
        double xDiff = x - other.x;
        double yDiff = y - other.y;
        double zDiff = z - other.z;
        return Math.sqrt(xDiff * xDiff + yDiff * yDiff + zDiff * zDiff);
    }

    public double magnitude() {
        return Math.sqrt(magnitudeSquared());
    }

    public double magnitudeSquared() {
        return x * x + y * y + z * z;
    }

    public Vector3 normalized() {

        if (isZero()) {
            return new Vector3();
        }
        return this.scaled(1 / magnitude());
    }

    public double dotProduct(Vector3 other) {
        return x * other.x + y * other.y + z * other.z;
    }

    public boolean isZero() {
        return x == 0 && y == 0 && z == 0;
    }

    public Vector2 flatten() {
        return new Vector2(x, y);
    }

    public double angle(Vector3 v) {
        double mag2 = magnitudeSquared();
        double vmag2 = v.magnitudeSquared();
        double dot = dotProduct(v);
        return Math.acos(dot / Math.sqrt(mag2 * vmag2));
    }

    public Vector3 crossProduct(Vector3 v) {
        double tx = y * v.z - z * v.y;
        double ty = z * v.x - x * v.z;
        double tz = x * v.y - y * v.x;
        return new Vector3(tx, ty, tz);
    }

    public Vector3 projectOnto(Vector3 vectorToProjectOnto) {
        return vectorToProjectOnto.scaled(this.dotProduct(vectorToProjectOnto)/vectorToProjectOnto.magnitudeSquared());
    }

    public double angleWith(Vector3 vector) {
        double cosine = this.dotProduct(vector)/(this.magnitude()*vector.magnitude());
        return Math.acos(cosine);
    }

    /*


     */
    public Vector3 matrixRotation(Vector3 forwardFacingVector, Vector3 roofFacingVector) {
        Vector3 result = new Vector3(this);

        // roll
        Vector3 rotatedRoll = roofFacingVector.minusAngle(forwardFacingVector);
        Vector2 rollProjection = new Vector2(rotatedRoll.z, rotatedRoll.y);
        Vector2 rotatedInRollLocalPointProjection = new Vector2(result.z, result.y).minusAngle(rollProjection).plusAngle(new Vector2(0, 1));
        result = new Vector3(result.x, rotatedInRollLocalPointProjection.x, rotatedInRollLocalPointProjection.y);

        // computing global pitch and yaw
        Vector2 pitchProjection = new Vector2(forwardFacingVector.flatten().magnitude(), -forwardFacingVector.z);
        Vector2 localPointProjection = new Vector2(result.x, result.z);
        Vector2 rotatedLocalPointProjection = localPointProjection.minusAngle(pitchProjection);
        result = new Vector3(rotatedLocalPointProjection.x, result.y, rotatedLocalPointProjection.y);
        result = result.plusAngle(new Vector3(forwardFacingVector.flatten(), 0));

        return result;
    }

    public Vector3 matrixRotation(Orientation orientation) {
        Vector3 result = new Vector3(this);

        // roll
        Vector3 rotatedRoll = orientation.getRoof().minusAngle(orientation.getNose());
        Vector2 rollProjection = new Vector2(rotatedRoll.z, rotatedRoll.y);
        Vector2 rotatedInRollLocalPointProjection = new Vector2(result.z, result.y).minusAngle(rollProjection).plusAngle(new Vector2(0, 1));
        result = new Vector3(result.x, rotatedInRollLocalPointProjection.x, rotatedInRollLocalPointProjection.y);

        // computing global pitch and yaw
        Vector2 pitchProjection = new Vector2(orientation.getNose().flatten().magnitude(), -orientation.getNose().z);
        Vector2 localPointProjection = new Vector2(result.x, result.z);
        Vector2 rotatedLocalPointProjection = localPointProjection.minusAngle(pitchProjection);
        result = new Vector3(rotatedLocalPointProjection.x, result.y, rotatedLocalPointProjection.y);
        result = result.plusAngle(new Vector3(orientation.getNose().flatten(), 0));

        return result;
    }

    public Vector3 matrixRotation(CarOrientation orientation) {
        Vector3 result = new Vector3(this);

        // roll
        Vector3 rotatedRoll = orientation.roofVector.minusAngle(orientation.noseVector);
        Vector2 rollProjection = new Vector2(rotatedRoll.z, rotatedRoll.y);
        Vector2 rotatedInRollLocalPointProjection = new Vector2(result.z, result.y).minusAngle(rollProjection).plusAngle(new Vector2(0, 1));
        result = new Vector3(result.x, rotatedInRollLocalPointProjection.x, rotatedInRollLocalPointProjection.y);

        // computing global pitch and yaw
        Vector2 pitchProjection = new Vector2(orientation.noseVector.flatten().magnitude(), -orientation.noseVector.z);
        Vector2 localPointProjection = new Vector2(result.x, result.z);
        Vector2 rotatedLocalPointProjection = localPointProjection.minusAngle(pitchProjection);
        result = new Vector3(rotatedLocalPointProjection.x, result.y, rotatedLocalPointProjection.y);
        result = result.plusAngle(new Vector3(orientation.noseVector.flatten(), 0));

        return result;
    }

    public Vector3 toFrameOfReference(Vector3 frontDirection, Vector3 topDirection)
    {
        // Calculate the vector without any roll yet (the roll is calculated from the topDirection vector)
        Vector3 frameOfRefWithoutRoll = this.minusAngle(frontDirection);
        // Calculate the roll vector in the frame of ref so we can use it to do a planar projection followed by a rotation later on.
        // Basically, the vector is going to do nothing if it faces upward, and it's going to subtract its angle from
        // that top position if it has any
        Vector3 rollInFrameOfRef = topDirection.minusAngle(frontDirection);

        // Calculating the 2D equivalents in the planar projection
        Vector2 flattenedFrameOfRefWithoutRoll = new Vector2(frameOfRefWithoutRoll.z, frameOfRefWithoutRoll.y);
        Vector2 flattenedRollInFrameOfRef = new Vector2(rollInFrameOfRef.z, rollInFrameOfRef.y);

        // Applying the roll rotation
        Vector2 planarProjectionZyOfResult = flattenedFrameOfRefWithoutRoll.minusAngle(flattenedRollInFrameOfRef);

        // Put back into a coherent form the calculated coordinates and return the vector
        return new Vector3(frameOfRefWithoutRoll.x, planarProjectionZyOfResult.y, planarProjectionZyOfResult.x);
    }

    public Vector3 minusAngle(Vector3 rotationVector) {
        // Rotating the vector in xy beforehand
        Vector3 firstRotatedVector = new Vector3(this.flatten().minusAngle(rotationVector.flatten()), this.z);
        Vector3 firstRotationVector = new Vector3(rotationVector.flatten().magnitude(), 0, rotationVector.z);

        // Then rotating it in xz (the rotating vector in y is 0, thus we now only need to rotate it in xz)
        Vector2 projectedVectorXz = new Vector2(firstRotatedVector.x, firstRotatedVector.z)
                .minusAngle(new Vector2(firstRotationVector.x, firstRotationVector.z));

        // We can now add the x and the z coordinates separately from the firstly calculated y coordinate
        return new Vector3(projectedVectorXz.x, firstRotatedVector.y, projectedVectorXz.y);
    }

    public Vector3 plusAngle(Vector3 rotationVector) {
        // Rotating the vector in xy beforehand
        Vector3 firstRotatedVector = new Vector3(this.flatten().plusAngle(rotationVector.flatten()), this.z);
        Vector3 firstRotationVector = new Vector3(rotationVector.flatten().plusAngle(rotationVector.flatten()), rotationVector.z);

        // Then rotating it in the planar projection of the rotation angle (x, y, 0), (x, y, z)
        Vector2 projectedVectorXyXyz = new Vector2(firstRotatedVector.flatten().magnitude(), firstRotatedVector.z)
                .plusAngle(new Vector2(firstRotationVector.flatten().magnitude(), firstRotationVector.z));

        Vector2 resultXy = firstRotatedVector.flatten().scaledToMagnitude(projectedVectorXyXyz.x);
        // We can now add the x and the z coordinates separately from the firstly calculated y coordinate
        return new Vector3(resultXy.x, resultXy.y, projectedVectorXyXyz.y);
    }

    public Vector3 projectOnto(final Triangle3D triangle) {
        final Vector3 p1 = triangle.point0;
        final Vector3 p2 = triangle.point1;
        final Vector3 p3 = triangle.point2;
        final Vector3 p = this;
        final Vector3 u = p2.minus(p1);
        final Vector3 v = p3.minus(p1);
        final Vector3 n = u.crossProduct(v);
        final Vector3 w = p.minus(p1);
        double Y = (u.crossProduct(w).dotProduct(n)) / n.magnitudeSquared();
        double B = (w.crossProduct(v).dotProduct(n)) / n.magnitudeSquared();

        double a = 1-Y-B;

        if(a >= 0 && a <= 1
                && B >= 0 && B <= 1
                && Y >= 0 && Y <= 1) {
            return p1.scaled(a).plus(p2.scaled(B)).plus(p3.scaled(Y));
        }
        else {
            final Vector3 edgePosition1 = triangleEdgePosition(p1, p2.minus(p1), p);
            final Vector3 edgePosition2 = triangleEdgePosition(p2, p3.minus(p2), p);
            final Vector3 edgePosition3 = triangleEdgePosition(p3, p1.minus(p3), p);

            final double dist1 = edgePosition1.minus(p).magnitude();
            final double dist2 = edgePosition2.minus(p).magnitude();
            final double dist3 = edgePosition3.minus(p).magnitude();

            if(dist1 <= dist2 && dist1 <= dist3) {
                return edgePosition1;
            }
            if(dist2 <= dist1 && dist2 <= dist3) {
                return edgePosition2;
            }
            return edgePosition3;
        }
    }

    private Vector3 triangleEdgePosition(final Vector3 start, final Vector3 dir, final Vector3 p) {
        final double u = clamp(p.minus(start).dotProduct(dir)/dir.dotProduct(dir), 0, 1);
        return start.plus(dir.scaled(u));
    }

    private double clamp(final double valueToClamp, final double min, final double max) {
        return Math.max(min, Math.min(max, valueToClamp));
    }

    @Override
    public String toString() {
        return "[ x:" + this.x + ", y:" + this.y + ", z:" + this.z + " ]";
    }

    @Override
    public int hashCode() {
        return Objects.hash((int)x, (int)y, (int)z);
    }
}
