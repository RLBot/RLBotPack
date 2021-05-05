package rlbotexample.input.dynamic_data;

import util.vector.Vector3;

public class Orientation {
    private final Vector3 nose;
    private final Vector3 roof;

    public Orientation() {
        this.nose = new Vector3(1, 0, 0);
        this.roof = new Vector3(0, 0, 1);
    }

    public Orientation(Vector3 nose, Vector3 roof) {
        this.nose = nose;
        this.roof = roof;
    }

    public Vector3 getNose() {
        return nose;
    }

    public Vector3 getRoof() {
        return roof;
    }
}
