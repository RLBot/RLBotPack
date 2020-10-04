package util.machine_learning_models.binary_search;

public class UntanglingFunction {

    private double period;
    private double decayRate;
    private double startingValue;

    public UntanglingFunction(double period, double decayRate, double startingValue) {
        this.period = period;
        this.decayRate = decayRate;
        this.startingValue = startingValue;
    }

    public double process(int iteration) {
        return (((startingValue/2) * Math.cos(Math.PI * (2/period) * iteration)) + 1) * Math.pow(decayRate, -iteration);
    }
}
