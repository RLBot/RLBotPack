package util.machine_learning_models.evaluators;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;

public class AirDribbleEvaluator extends BotEvaluator {

    public AirDribbleEvaluator(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void updateEvaluation(DataPacket input) {
        // gotta find a way to evaluate air dribbles
        double currentEvaluation = 0;

        currentEvaluation -= input.ball.velocity.minus(input.car.velocity).magnitude();
        currentEvaluation -= input.ball.position.minus(input.car.position).magnitude();
        currentEvaluation += 7*input.ball.position.z;
        currentEvaluation -= super.getDesiredDestination().getThrottleSpeed().minus(input.ball.velocity).magnitude();
        currentEvaluation -= super.getDesiredDestination().getThrottleDestination().minus(input.ball.position).magnitude();

        setEvaluation(currentEvaluation/1000 + getEvaluation());
    }
}
