package util.controllers;

public class BoostController {

    private final static PwmController pwmController = new PwmController(4);

    public static boolean process(double accelerationRatio) {
        return pwmController.process(accelerationRatio);
    }

    private static double booelanToDouble(boolean valueToConvert) {
        if(valueToConvert) {
            return 1;
        }
        return 0;
    }
}
