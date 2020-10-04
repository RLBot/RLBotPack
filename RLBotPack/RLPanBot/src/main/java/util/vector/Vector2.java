package util.vector;

/**
 * A vector that only knows about x and y components.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can add to it as much
 * as you want, or delete it.
 */
public class Vector2 {

    public final double x;
    public final double y;

    public Vector2(double x, double y) {
        this.x = x;
        this.y = y;
    }

    public Vector2() {
        this.x = 0;
        this.y = 0;
    }

    public Vector2 plus(Vector2 other) {
        return new Vector2(x + other.x, y + other.y);
    }

    public Vector2 minus(Vector2 other) {
        return new Vector2(x - other.x, y - other.y);
    }

    public Vector2 scaled(double scale) {
        return new Vector2(x * scale, y * scale);
    }

    /**
     * If magnitude is negative, we will return a vector facing the opposite direction.
     */
    public Vector2 scaledToMagnitude(double magnitude) {
        if (isZero()) {
           return new Vector2(0, 0);
        }
        double scaleRequired = magnitude / magnitude();
        return scaled(scaleRequired);
    }

    public double distance(Vector2 other) {
        double xDiff = x - other.x;
        double yDiff = y - other.y;
        return Math.sqrt(xDiff * xDiff + yDiff * yDiff);
    }

    /**
     * This is the length of the vector.
     */
    public double magnitude() {
        return Math.sqrt(magnitudeSquared());
    }

    public double magnitudeSquared() {
        return x * x + y * y;
    }

    public Vector2 normalized() {

        if (isZero()) {
            return new Vector2(0, 0);
        }
        return this.scaled(1 / magnitude());
    }

    public double dotProduct(Vector2 other) {
        return x * other.x + y * other.y;
    }

    public Vector2 minusAngle(Vector2 rotationVector) {
        // Prepossessing to subtract the angle when multiplying complex numbers
        Vector2 conjugate = new Vector2(rotationVector.x, -rotationVector.y);
        // Using complex number thing to sub angles
        Vector2 result = new Vector2(conjugate.x * this.x - conjugate.y * this.y,
                conjugate.x * this.y + conjugate.y * this.x);
        // Setting back the 2D magnitude to what it was because now it's all over the place
        result = result.scaledToMagnitude(this.magnitude());

        // Returning the calculated 2D vector with the previous unchanged z coordinate
        return result;
    }

    public Vector2 plusAngle(Vector2 rotationVector) {
        // Using complex number thing to sub angles
        Vector2 result = new Vector2(rotationVector.x * this.x - rotationVector.y * this.y,
                rotationVector.x * this.y + rotationVector.y * this.x);
        // Setting back the 2D magnitude to what it was because now it's all over the place
        result = result.scaledToMagnitude(this.magnitude());

        // Returning the calculated 2D vector with the previous unchanged z coordinate
        return result;
    }

    public boolean isZero() {
        return x == 0 && y == 0;
    }

    /**
     * The correction angle is how many radians you need to rotate this vector to make it line up with the "ideal"
     * vector. This is very useful for deciding which direction to steer.
     */
    public double correctionAngle(Vector2 ideal) {
        double currentRad = Math.atan2(y, x);
        double idealRad = Math.atan2(ideal.y, ideal.x);

        if (Math.abs(currentRad - idealRad) > Math.PI) {
            if (currentRad < 0) {
                currentRad += Math.PI * 2;
            }
            if (idealRad < 0) {
                idealRad += Math.PI * 2;
            }
        }

        return idealRad - currentRad;
    }

    /**
     * Will always return a positive value <= Math.PI
     */
    public static double angle(Vector2 a, Vector2 b) {
        return Math.abs(a.correctionAngle(b));
    }

    @Override
    public String toString() {
        return "[ x:" + this.x + ", y:" + this.y + " ]";
    }
}
