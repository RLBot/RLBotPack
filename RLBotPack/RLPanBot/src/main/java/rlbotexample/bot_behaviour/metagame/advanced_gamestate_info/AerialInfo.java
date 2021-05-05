package rlbotexample.bot_behaviour.metagame.advanced_gamestate_info;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.HitBox;
import rlbotexample.input.dynamic_data.RlUtils;
import util.game_constants.RlConstants;
import util.vector.Vector3;

public class AerialInfo {

    public static boolean isManeuverReachable(int indexOfPlayer, DataPacket input) {
        double approximateTimeToReachDestination = approximateTimeToReachBall(indexOfPlayer, input);
        double availableAirTime = input.allCars.get(indexOfPlayer).boost/33.3333333
                + input.allCars.get(indexOfPlayer).velocity.z/RlConstants.NORMAL_GRAVITY_STRENGTH;

        return approximateTimeToReachDestination < availableAirTime;
    }

    public static boolean isBallConsideredAerial(BallData ballData, HitBox hitBox) {
        return ballData.position.z > 200;// && !isBallReachableFromMapSurfaceWithoutJumping(ballData, hitBox);
    }

    public static boolean isPlayerAllowedToAerial(int indexOfPlayer, DataPacket input) {
        BallData futureBallToReach = input.ballPrediction.ballAtTime(approximateTimeToReachBall(indexOfPlayer, input));
        HitBox playerHitBox = input.allCars.get(indexOfPlayer).hitBox;
        return isManeuverReachable(indexOfPlayer, input) && isBallConsideredAerial(futureBallToReach, playerHitBox);

    }

    private static boolean isBallReachableFromMapSurfaceWithoutJumping(BallData ballData, HitBox hitBox) {
        double offsetFromSurface = RlConstants.BALL_RADIUS + hitBox.cornerPosition.z*2;
        return Math.abs(ballData.position.x) > 4096 - offsetFromSurface
                || Math.abs(ballData.position.y) > 5120 - offsetFromSurface
                || Math.abs(ballData.position.z - 1022) > 1022 - offsetFromSurface;
    }

    private static double approximateTimeToReachBall(int indexOfPlayer, DataPacket input) {
        Vector3 playerDistanceFromDestination = input.ball.position.minus(input.allCars.get(indexOfPlayer).position);
        Vector3 playerSpeedFromDestination = input.ball.velocity.minus(input.allCars.get(indexOfPlayer).velocity);
        return RlUtils.timeToReachAerialDestination(input, playerDistanceFromDestination, playerSpeedFromDestination);
    }
}
