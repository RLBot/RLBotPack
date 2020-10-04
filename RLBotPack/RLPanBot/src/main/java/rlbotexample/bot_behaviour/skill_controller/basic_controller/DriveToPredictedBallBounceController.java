package rlbotexample.bot_behaviour.skill_controller.basic_controller;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.path.EnemyNetPositionPath;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense.Dribble;
import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.bezier_curve.PathComposite;
import util.controllers.PidController;
import util.controllers.ThrottleController;
import util.vector.Vector3;

import java.util.List;

public class DriveToPredictedBallBounceController extends SkillController {

    final private BotBehaviour bot;
    final private AerialOrientationHandler aerialOrientationHandler;
    double speedToReach;
    GroundOrientationController groundOrientationController;
    DrivingSpeedController drivingSpeedController;

    PathHandler enemyNetPositionPath;
    Dribble dribbleController;
    Vector3 ballDestination;

    public DriveToPredictedBallBounceController(BotBehaviour bot) {
        this.bot = bot;
        this.aerialOrientationHandler = new AerialOrientationHandler(bot);
        speedToReach = 1410;
        groundOrientationController = new GroundOrientationController(bot);
        drivingSpeedController = new DrivingSpeedController(bot);
        CarDestination carDestination = new CarDestination();
        enemyNetPositionPath = new EnemyNetPositionPath(carDestination);
        dribbleController = new Dribble(carDestination, bot);
        ballDestination = new Vector3();
    }

    public void setDestination(Vector3 ballDestination) {
        this.ballDestination = ballDestination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        final BotOutput output = bot.output();
        final List<Double> timeOfBallBounces = input.ballPrediction.ballBounceTimes();
        final BallData futureBall;

        double actualTimeOfBallBounce = Double.MAX_VALUE;
        for(Double timeOfBallBounce: timeOfBallBounces) {
            if(timeOfBallBounce < actualTimeOfBallBounce && input.ballPrediction.ballAtTime(timeOfBallBounce).position.minus(input.car.position).magnitude()/timeOfBallBounce < 2300) {
                actualTimeOfBallBounce = timeOfBallBounce;
            }
        }

        futureBall = input.ballPrediction.ballAtTime(actualTimeOfBallBounce);
        /*
        if(Math.abs(input.ball.velocity.z) > 80) {
            futureBall = input.ballPrediction.ballAtTime(actualTimeOfBallBounce);
        }
        else {
            //System.out.println("ground prediction");
            futureBall = input.ballPrediction.ballAtTime(input.car.position.minus(input.ball.position).magnitude()/input.car.velocity.minus(input.ball.velocity).magnitude());
        }*/
        final CarData futureCar = input.ballPrediction.carsAtTime(actualTimeOfBallBounce).get(input.playerIndex);

        Vector3 futureDestination = futureBall.position.plus(futureBall.position.minus(ballDestination).scaledToMagnitude(85));

        groundOrientationController.setDestination(futureDestination);
        groundOrientationController.updateOutput(input);

        speedToReach = input.car.position.minus(futureDestination).magnitude()/actualTimeOfBallBounce;
        drivingSpeedController.setSpeed(speedToReach);
        drivingSpeedController.updateOutput(input);

        if(speedToReach > 1400) {
            final double carSpeed = input.car.velocity.magnitude();
            // output.boost(carSpeed > 1300 && carSpeed < speedToReach && speedToReach < 2300);
        }

        output.boost(speedToReach > 1410 && input.car.velocity.magnitude() < speedToReach && input.car.orientation.noseVector.dotProduct(ballDestination) > 0);

        if(input.car.position.minus(input.ball.position).magnitude() < 180) {
            enemyNetPositionPath.updateDestination(input);
            dribbleController.updateOutput(input);
        }

        aerialOrientationHandler.setRollOrientation(new Vector3(0, 0, 10000));
        aerialOrientationHandler.setDestination(input.ball.position);
        aerialOrientationHandler.updateOutput(input);

        //System.out.println(timeOfBallBounce);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
