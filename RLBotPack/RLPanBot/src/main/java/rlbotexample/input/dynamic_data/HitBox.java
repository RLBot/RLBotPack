package rlbotexample.input.dynamic_data;

import rlbot.flat.BoxShape;
import util.vector.Vector3;

public class HitBox {
    public final Vector3 centerPosition;
    public final Vector3 cornerPosition;
    public final Vector3 frontOrientation;
    public final Vector3 roofOrientation;

    public HitBox(Vector3 centerPosition, rlbot.flat.Vector3 centerOfMassOffset, BoxShape boxShape, Vector3 frontOrientation, Vector3 roofOrientation) {
        this.centerPosition = centerPosition.plus(new Vector3(centerOfMassOffset).scaled(-1, 1, 1).matrixRotation(frontOrientation, roofOrientation));
        this.cornerPosition = new Vector3(boxShape.length(), boxShape.width(), boxShape.height()).scaled(0.5);
        this.frontOrientation = frontOrientation;
        this.roofOrientation = roofOrientation;
    }

    public HitBox(Vector3 centerPosition, Vector3 boxSize) {
        this.centerPosition = centerPosition;
        this.cornerPosition = boxSize;
        this.frontOrientation = new Vector3(1, 0, 0);
        this.roofOrientation = new Vector3(0, 0, 1);
    }

    private HitBox(Vector3 centerPosition, Vector3 boxSize, Orientation orientation) {
        this.centerPosition = centerPosition;
        this.cornerPosition = boxSize;
        this.frontOrientation = orientation.getNose();
        this.roofOrientation = orientation.getRoof();
    }

    public HitBox generateHypotheticalHitBox(Vector3 hypotheticalPosition, Orientation hypotheticalOrientation) {
        return new HitBox(hypotheticalPosition, cornerPosition, hypotheticalOrientation);
    }

    public HitBox generateHypotheticalHitBox(Vector3 hypotheticalPosition) {
        return new HitBox(hypotheticalPosition, cornerPosition, new Orientation(roofOrientation, cornerPosition));
    }

    public Vector3 projectPointOnSurface(Vector3 pointToProject) {
        Vector3 localPointToProject = getLocal(pointToProject);

        double newXCoordinate = localPointToProject.x;
        if(localPointToProject.x > cornerPosition.x) {
            newXCoordinate = cornerPosition.x;
        }
        else if(localPointToProject.x < -cornerPosition.x) {
            newXCoordinate = -cornerPosition.x;
        }

        double newYCoordinate = -localPointToProject.y;
        if(localPointToProject.y > cornerPosition.y) {
            newYCoordinate = -cornerPosition.y;
        }
        else if(localPointToProject.y < -cornerPosition.y) {
            newYCoordinate = cornerPosition.y;
        }

        double newZCoordinate = localPointToProject.z;
        if(localPointToProject.z > cornerPosition.z) {
            newZCoordinate = cornerPosition.z;
        }
        else if(localPointToProject.z < -cornerPosition.z) {
            newZCoordinate = -cornerPosition.z;
        }

        return getGlobal(new Vector3(newXCoordinate, newYCoordinate, newZCoordinate));
    }

    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof HitBox)) {
            return false;
        }
        return ((HitBox)obj).centerPosition.minus(this.centerPosition).magnitudeSquared() < 0.1
        && ((HitBox)obj).cornerPosition.minus(this.cornerPosition).magnitudeSquared() < 0.1
        && ((HitBox)obj).frontOrientation.minus(this.frontOrientation).magnitudeSquared() < 0.1
        && ((HitBox)obj).roofOrientation.minus(this.roofOrientation).magnitudeSquared() < 0.1;
    }

    @Override
    public int hashCode() {
        return centerPosition.hashCode()
                + cornerPosition.hashCode()
                + frontOrientation.hashCode()
                + roofOrientation.hashCode();
    }

    private Vector3 getLocal(Vector3 globalPoint) {
        return globalPoint.minus(centerPosition).toFrameOfReference(frontOrientation, roofOrientation);
    }

    private Vector3 getGlobal(Vector3 localPoint) {
        return localPoint.matrixRotation(frontOrientation, roofOrientation).plus(centerPosition);
    }
}
