package util.vector;

public class Ray3 {
    public Vector3 offset;
    public Vector3 direction;

    public Ray3() {
        this.offset = new Vector3();
        this.direction = new Vector3();
    }

    public Ray3(Vector3 offset, Vector3 direction) {
        this.offset = offset;
        this.direction = direction;
    }
}
