package util.timer;

public class TimeInterpolater {

    private double initialValue;
    private double finalValue;
    private long durationOfInterpolation;
    private long startingTime;

    public TimeInterpolater(double initialValue, double finalValue, long durationOfInterpolation) {
        this.initialValue = initialValue;
        this.finalValue = finalValue;
        this.durationOfInterpolation = durationOfInterpolation;
    }

    public void start() {
        startingTime = System.currentTimeMillis();
    }

    public double getValue() {
        return Math.min(
                initialValue +
                        ((finalValue - initialValue) * (((double)(System.currentTimeMillis()-startingTime))/durationOfInterpolation)),
                finalValue);
    }

    public boolean isFinished() {
        return (System.currentTimeMillis()-startingTime)/(double)durationOfInterpolation > 1;
    }
}
