package rlbotexample.input.geometry;

import util.game_constants.RlConstants;
import util.shapes.Sphere;
import util.vector.Vector3;

public class StandardMap extends MapMeshGeometry {

    private static final double WIDTH_OF_SQUARE_THAT_DIAGONAL_WALLS_ARE_PART_OF = 5702.109083;
    private static final Vector3 VECTOR_OF_45_DEGREE_ANGLE_XY = new Vector3(1, 1, 0);
    private static final double GOAL_POST_POSITION_X = 892.755;
    private static final double GOAL_POST_POSITION_Y = 5120;
    private static final double GOAL_CROSSBAR_POSITION_Z = 642.775;

    private static final Vector3 GROUND_HIT_NORMAL = new Vector3(0, 0, -1);
    private static final Vector3 CEILING_HIT_NORMAL = new Vector3(0, 0, 1);
    private static final Vector3 POSITIVE_WALL_X_HIT_NORMAL = new Vector3(1, 0, 0);
    private static final Vector3 NEGATIVE_WALL_X_HIT_NORMAL = new Vector3(-1, 0, 0);
    private static final Vector3 POSITIVE_WALL_Y_HIT_NORMAL = new Vector3(0, 1, 0);
    private static final Vector3 NEGATIVE_WALL_Y_HIT_NORMAL = new Vector3(0, -1, 0);

    @Override
    public Vector3 getCollisionNormalOrElse(final Sphere sphere, final Vector3 defaultValue) {
        final Vector3 globalPoint = sphere.center;
        final double bevel = sphere.radius;

        // basic ceiling and ground
        if(globalPoint.plus(GROUND_HIT_NORMAL.scaled(bevel)).z < 0) {
            return GROUND_HIT_NORMAL;
        }
        else if(globalPoint.plus(CEILING_HIT_NORMAL.scaled(bevel)).z > RlConstants.CEILING_HEIGHT) {
            return CEILING_HIT_NORMAL;
        }

        // basic wall x
        if(globalPoint.plus(POSITIVE_WALL_X_HIT_NORMAL.scaled(bevel)).x > RlConstants.WALL_DISTANCE_X) {
            return POSITIVE_WALL_X_HIT_NORMAL;
        }
        else if(globalPoint.plus(NEGATIVE_WALL_X_HIT_NORMAL.scaled(bevel)).x < -RlConstants.WALL_DISTANCE_X) {
            return NEGATIVE_WALL_X_HIT_NORMAL;
        }

        // basic wall y
        if(!isInNet(globalPoint, bevel)) {
            if (globalPoint.plus(POSITIVE_WALL_Y_HIT_NORMAL.scaled(bevel)).y > RlConstants.WALL_DISTANCE_Y) {
                return POSITIVE_WALL_Y_HIT_NORMAL;
            } else if (globalPoint.plus(NEGATIVE_WALL_Y_HIT_NORMAL.scaled(bevel)).y < -RlConstants.WALL_DISTANCE_Y) {
                return NEGATIVE_WALL_Y_HIT_NORMAL;
            }
        }

        // basic 4 diagonal walls (corners?)
        if(!isInNet(globalPoint, bevel)) {
            // (RIGHT AND LEFT BY LOOKING TOWARDS THE ORANGE NET)
            // orange right
            if(globalPoint.minusAngle(VECTOR_OF_45_DEGREE_ANGLE_XY).x + bevel > WIDTH_OF_SQUARE_THAT_DIAGONAL_WALLS_ARE_PART_OF) {
                return new Vector3(1, 1, 0).normalized();
            }
            // blue left
            else if(globalPoint.minusAngle(VECTOR_OF_45_DEGREE_ANGLE_XY).x - bevel < -WIDTH_OF_SQUARE_THAT_DIAGONAL_WALLS_ARE_PART_OF) {
                return new Vector3(-1, -1, 0).normalized();
            }
            // orange left
            if(globalPoint.minusAngle(VECTOR_OF_45_DEGREE_ANGLE_XY).y + bevel > WIDTH_OF_SQUARE_THAT_DIAGONAL_WALLS_ARE_PART_OF) {
                return new Vector3(-1, 1, 0).normalized();
            }
            // blue right
            else if(globalPoint.minusAngle(VECTOR_OF_45_DEGREE_ANGLE_XY).y - bevel < -WIDTH_OF_SQUARE_THAT_DIAGONAL_WALLS_ARE_PART_OF) {
                return new Vector3(1, -1, 0).normalized();
            }
        }

        return defaultValue;
    }

    private boolean isInNet(Vector3 globalPoint, double bevel) {
        return (globalPoint.x + bevel < GOAL_POST_POSITION_X && globalPoint.x - bevel > -GOAL_POST_POSITION_X)
                && (globalPoint.y - bevel > GOAL_POST_POSITION_Y || globalPoint.y + bevel < -GOAL_POST_POSITION_Y)
                && (globalPoint.z + bevel < GOAL_CROSSBAR_POSITION_Z);
    }
}
