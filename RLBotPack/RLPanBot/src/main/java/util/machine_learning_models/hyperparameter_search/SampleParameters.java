package util.machine_learning_models.hyperparameter_search;

import java.util.ArrayList;
import java.util.List;

public class SampleParameters {

    private List<Double> parameters;
    private double rewardValue;

    public SampleParameters(List<Double> parameters, double rewardValue) {
        this.parameters = parameters;
        this.rewardValue = rewardValue;
    }

    public double getRewardValue() {
        return rewardValue;
    }

    public List<Double> makeChild(double searchRangeRatio) {
        double randomNumber;
        List<Double> parameters = new ArrayList<>();

        for(Double parameter: this.parameters) {
            randomNumber = 2*(Math.random()-0.5);
            parameters.add(parameter + parameter*randomNumber*searchRangeRatio);
        }
        return parameters;
    }
}
