package util.machine_learning_models.evaluators;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;

public class AirDribbleEvaluator2 extends BotEvaluator {

    public AirDribbleEvaluator2(CarDestination desiredDestination) {
        super(desiredDestination);
    }

    @Override
    public void updateEvaluation(DataPacket input) {
        // gotta find a way to evaluate air dribbles
        double currentEvaluation = 0;

        currentEvaluation -= input.ball.position.minus(input.car.position).magnitude();
        currentEvaluation += 2*input.ball.position.z;
        currentEvaluation -= 4*getDesiredDestination().getThrottleDestination().minus(input.ball.position).magnitude();


        setEvaluation(currentEvaluation/1000 + getEvaluation());
    }
}
