package util.controllers;

public class ThrottleController {

    private static final double CRUISE_VALUE = 0.01;
    private static final double SOFT_BREAK_VALUE = 0;
    private static final double HARD_BREAK_VALUE = -1;

    public static double process(double accelerationRatio) {
        if(accelerationRatio > 0) {
            return accelerationRatio;
        }
        else if(accelerationRatio == 0) {
            return CRUISE_VALUE;
        }
        else if(accelerationRatio > -1) {
            return SOFT_BREAK_VALUE;
        }
        else {
            return HARD_BREAK_VALUE;
        }
    }


}
