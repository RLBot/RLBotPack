package util.renderers;

import rlbot.flat.BallPrediction;
import rlbot.flat.PredictionSlice;
import rlbot.render.Renderer;
import util.vector.Vector3;

import java.awt.*;

/**
 * This class can help you get started with getNativeBallPrediction prediction. Feel free to change it as much as you want,
 * this is part of your bot, not part of the framework!
 */
public class NativeBallPredictionRenderer {

    public static void drawTillMoment(BallPrediction ballPrediction, float gameSeconds, Color color, Renderer renderer) {
        Vector3 previousLocation = null;
        for (int i = 0; i < ballPrediction.slicesLength(); i += 4) {
            PredictionSlice slice = ballPrediction.slices(i);
            if (slice.gameSeconds() > gameSeconds) {
                break;
            }
            Vector3 location = new Vector3(slice.physics().location());
            if (previousLocation != null) {
                renderer.drawLine3d(color, previousLocation, location);
            }
            previousLocation = location;
        }
    }
}
