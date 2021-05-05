package rlbotexample.bot_behaviour.metagame.possessions;

import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

public class PossessionEvaluator {

    /*
    public static double possessionRatio(int indexOfPlayer, int indexOfOpponent, DataPacket input) {
        Vector3 playerPosition = input.allCars.get(indexOfPlayer).position;
        Vector3 playerSpeed = input.allCars.get(indexOfPlayer).velocity;
        Vector3 playerNoseOrientation = input.allCars.get(indexOfPlayer).orientation.noseVector;
        Vector3 opponentPosition = input.allCars.get(indexOfOpponent).position;
        Vector3 opponentSpeed = input.allCars.get(indexOfOpponent).velocity;
        Vector3 opponentNoseOrientation = input.allCars.get(indexOfOpponent).orientation.noseVector;
        Vector3 ballPosition = input.ball.position;
        Vector3 ballSpeed = input.ball.velocity;

        double playerPossessionValue = opponentPosition.minus(ballPosition).magnitude();

        double opponentPossessionValue = playerPosition.minus(ballPosition).magnitude();

        return playerPossessionValue - opponentPossessionValue;
    }
    */

    public static double possessionRatio(int indexOfPlayer, int indexOfOpponent, DataPacket input) {
        return singlePlayerPossessionValue(indexOfPlayer, input) - singlePlayerPossessionValue(indexOfOpponent, input);
    }

    private static double singlePlayerPossessionValue(int indexOfPlayer, DataPacket input) {
        Vector3 futurePositionOfBall = input.ballPrediction.ballAtTime(1).position;
        Vector3 futurePositionOfPlayer = input.ballPrediction.carsAtTime(1).get(indexOfPlayer).position;

        Vector3 playerNoseOrientation = input.allCars.get(indexOfPlayer).orientation.noseVector;
        Vector3 goalPosition = new Vector3(0, 5200 * (input.allCars.get(indexOfPlayer).team*2)-1, 500);

        return + (11000 - input.ball.position.minus(input.allCars.get(indexOfPlayer).position).magnitude())*1000        // handle distance from ball
                + input.allCars.get(indexOfPlayer).velocity.minus(input.ball.velocity).normalized()                     // handle speed from ball
                    .dotProduct(input.ball.position.minus(input.allCars.get(indexOfPlayer).position))*900
                + input.allCars.get(indexOfPlayer).position.minus(input.ball.position).normalized()                     // handle too far away ahead player from ball
                    .dotProduct(input.allCars.get(indexOfPlayer).position.minus(goalPosition).normalized())*10
                + playerNoseOrientation.dotProduct(futurePositionOfBall.minus(input.allCars.get(indexOfPlayer).position))*1      // handle orientation of players towards ball
                + playerNoseOrientation.dotProduct(input.car.position.minus(goalPosition).normalized())*200;    // handle orientation of players on the field
    }

    /*public static double possessionRatio(int indexOfPlayer, int indexOfOpponent, DataPacket input) {
        Vector3 aerialKinematicBody = input.allCars.get(indexOfPlayer).position;
        Vector3 playerSpeed = input.allCars.get(indexOfPlayer).velocity;
        Vector3 playerNoseOrientation = input.allCars.get(indexOfPlayer).orientation.noseVector;
        Vector3 opponentPosition = input.allCars.get(indexOfOpponent).position;
        Vector3 opponentSpeed = input.allCars.get(indexOfOpponent).velocity;
        Vector3 opponentNoseOrientation = input.allCars.get(indexOfOpponent).orientation.noseVector;
        Vector3 getNativeBallPrediction = input.getNativeBallPrediction.position;
        Vector3 ballSpeed = input.getNativeBallPrediction.velocity;

        // evaluation = distance + angle from getNativeBallPrediction + speed from getNativeBallPrediction.
        // the bigger the number, the worst it is for the car that has the value.
        // this is why player possession is calculated from opponent possession variables.
        // the output is a number between 0 and a lot (lol).
        double playerPossessionValue = opponentPosition.minus(getNativeBallPrediction).magnitude();
        playerPossessionValue += opponentPosition.minus(getNativeBallPrediction).flatten().correctionAngle(opponentNoseOrientation.flatten());
        playerPossessionValue += ballSpeed.minus(opponentSpeed).dotProduct(getNativeBallPrediction.minus(opponentPosition));

        double opponentPossessionValue = aerialKinematicBody.minus(getNativeBallPrediction).magnitude();
        opponentPossessionValue += aerialKinematicBody.minus(getNativeBallPrediction).flatten().correctionAngle(playerNoseOrientation.flatten());
        opponentPossessionValue += ballSpeed.minus(playerSpeed).dotProduct(getNativeBallPrediction.minus(aerialKinematicBody));

        // If the number is ~1, then each player has somewhat the same possession value. No player has the advantage from the other.
        // If the number is >> 1, then the player definitely has possession over the opponent, and it can take his due time to play.
        // If the number is << 1 (and bigger than 0, so close to 0... the number is strictly positive, remember?), then the opponent definitely has the possession, and so you gotta be careful my dude.

        // so...
        // result = 1 -> equal possession
        // result > 1 -> player has possession
        // result < 1 -> opponent has possession
        return playerPossessionValue/opponentPossessionValue;
    }*/
}
