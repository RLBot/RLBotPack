package util.controllers;

public class PwmController {

    private int period;
    private int callCounter;
    private int threshold;


    public PwmController(int period) {
        this.period = period;
        this.threshold = 0;
        this.callCounter = 0;
    }

    public boolean process(double dutyCycle) {
        boolean result;
        threshold = (int)(period*dutyCycle);

        result = callCounter < threshold;
        callCounter++;
        callCounter %= period;

        return result;
    }

}
