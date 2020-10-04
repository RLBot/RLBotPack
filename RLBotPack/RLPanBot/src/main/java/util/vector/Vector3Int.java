package util.vector;

import com.google.flatbuffers.FlatBufferBuilder;
import rlbot.flat.Rotator;

/**
 * A simple 3d vector class with the most essential operations.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can add to it as much
 * as you want, or delete it.
 */
public class Vector3Int {

    public final int x;
    public final int y;
    public final int z;

    public Vector3Int(int x, int y, int z) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    @Override
    public String toString() {
        return "[ x:" + this.x + ", y:" + this.y + ", z:" + this.z + " ]";
    }
}
