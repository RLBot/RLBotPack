package util.machine_learning_models.evaluators;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;

public abstract class BotEvaluator {

    private CarDestination desiredDestination;
    private double bestEvaluation;

    BotEvaluator(CarDestination desiredDestination) {
        this.desiredDestination = desiredDestination;
        bestEvaluation = 0;
    }

    // called every frame.
    // it adds evaluations frame after frame.
    // At the end, the highest evaluation, the best
    // (hopefully, I can find a good function that can
    // evaluate well the behaviours I'm trying to implement...)
    public abstract void updateEvaluation(DataPacket input);

    CarDestination getDesiredDestination() {
        return desiredDestination;
    }

    public double getEvaluation() {
        return bestEvaluation;
    }

    void setEvaluation(double newEvaluation) {
        this.bestEvaluation = newEvaluation;
    }

    public void resetEvaluation() {
        bestEvaluation = 0;
    }
}
