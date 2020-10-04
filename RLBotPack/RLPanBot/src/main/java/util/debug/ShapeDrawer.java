package util.debug;

import rlbot.render.Renderer;
import util.shapes.Circle;
import util.vector.Vector2;
import util.vector.Vector3;

import java.awt.*;

public class ShapeDrawer {

    private static final int CIRCLE_RESOLUTION = 32;

    private Renderer renderer;

    public ShapeDrawer(Renderer renderer) {
        this.renderer = renderer;
    }

    public void draw(Circle circle, Color color) {
        double angleResolution = 2*Math.PI/CIRCLE_RESOLUTION;
        Vector2 rotationResolution = new Vector2(Math.cos(angleResolution), Math.sin(angleResolution));
        Vector2 firstRadius;
        Vector2 secondRadius = new Vector2(circle.getRadius(), 0);

        for(int i = 0; i < CIRCLE_RESOLUTION; i++) {
            firstRadius = secondRadius;
            secondRadius = secondRadius.plusAngle(rotationResolution);
            renderer.drawLine3d(color, new Vector3(circle.getCenter().plus(firstRadius), 0), new Vector3(circle.getCenter().plus(secondRadius), 0));
        }
    }
}
