package rlbotexample.input.dynamic_data;

import util.vector.Vector3;

public class KinematicPoint {

    private Vector3 position;
    private Vector3 speed;
    private double time;
    private Vector3 spin;

    public KinematicPoint(Vector3 position, Vector3 speed, double gameTime) {
        this.position = position;
        this.speed = speed;
        this.spin = new Vector3();
        this.time = gameTime;
    }

    public KinematicPoint(Vector3 position, Vector3 speed, Vector3 spin, double time) {
        this.position = position;
        this.speed = speed;
        this.spin = spin;
        this.time = time;
    }

    public Vector3 getPosition() {
        return position;
    }

    public Vector3 getSpeed() {
        return speed;
    }

    public double getTime() {
        return time;
    }

    public void setTime(double time) {
        this.time = time;
    }

    public Vector3 getSpin() {
        return this.spin;
    }

    public void setSpin(Vector3 spin) {
        this.spin = spin;
    }
}
