package rlbotexample.input.boost;


import util.vector.Vector3;

/**
 * Representation of one of the boost pads on the field.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can change it as much
 * as you want, or delete it.
 */
public class BoostPad {

    private final Vector3 location;
    private final boolean isFullBoost;
    private boolean isActive;

    public BoostPad(Vector3 location, boolean isFullBoost) {
        this.location = location;
        this.isFullBoost = isFullBoost;
    }

    public void setActive(boolean active) {
        isActive = active;
    }

    public Vector3 getLocation() {
        return location;
    }

    public boolean isFullBoost() {
        return isFullBoost;
    }

    public boolean isActive() {
        return isActive;
    }
}
