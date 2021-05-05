package rlbotexample.input.dynamic_data;

import rlbotexample.input.prediction.ball.AdvancedBallPrediction;
import util.game_constants.RlConstants;
import util.timer.Timer;
import util.vector.Vector3;

import java.util.ArrayList;
import java.util.List;

public class RlUtils {

    public static final double BALL_PREDICTION_TIME = 5;
    public static final double BALL_PREDICTION_REFRESH_RATE = 120;

    private static Timer ballPredictionReloadTimeout = new Timer(0).start();
    private static AdvancedBallPrediction ballPrediction = new AdvancedBallPrediction(new BallData(new Vector3(), new Vector3(), new Vector3(), 0), new ArrayList<CarData>(), 0, BALL_PREDICTION_REFRESH_RATE);

    public static AdvancedBallPrediction ballPrediction(int playerIndex, BallData ballData, List<CarData> allCars) {
        if(playerIndex == 0 && ballPredictionReloadTimeout.isTimeElapsed()) {
            ballPredictionReloadTimeout = new Timer(0.0333333).start();
            ballPrediction = new AdvancedBallPrediction(ballData, allCars, BALL_PREDICTION_TIME, BALL_PREDICTION_REFRESH_RATE);
        }
        return ballPrediction;
    }

    // good enough approximation of time before aerial hit for now.
    public static double timeToReachAerialDestination(DataPacket input, Vector3 playerDistanceFromDestination, Vector3 playerSpeedFromDestination) {
        // this is the player speed SIGNED (it's the player speed, but it's negative if it's going away from the destination...)
        double signedPlayerSpeedFromBall = playerSpeedFromDestination.dotProduct(playerDistanceFromDestination)
                / playerDistanceFromDestination.magnitude();
        double a = -(RlConstants.ACCELERATION_DUE_TO_BOOST)/3.5 /*+ (input.car.orientation.noseVector.dotProduct(new Vector3(0, 0, 1))*RlConstants.NORMAL_GRAVITY_STRENGTH/2)*/;
        double b = signedPlayerSpeedFromBall;
        double c = playerDistanceFromDestination.magnitude();
        double timeBeforeReachingBall = -b - Math.sqrt(b*b - 4*a*c);
        timeBeforeReachingBall /= 2*a;

        // player never has more than 3 seconds to boost in air, so we cap it here.
        // not sure if this is necessary though. It works fine with it
        /*if(timeBeforeReachingBall > 3) {
            timeBeforeReachingBall = 3;
        }*/

        return timeBeforeReachingBall;
    }
}
