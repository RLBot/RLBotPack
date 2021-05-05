package util.math;

public class NewtonianApproximation {

    private static final double H_DERIVATIVE_APPROXIMATE_LIMIT = 0.00001;
    private static final double PRECISION = 1000;

    public static double process(double startingXValue) {
        double x = startingXValue;

        for(int i = 0; i < PRECISION; i++) {
            double y = yourFunctionHere(x);
            double a = derivativeAt(x);
            double b = y - (a*x);
            double newX = -b/a;
            x = newX;
        }

        return x;
    }

    private static double derivativeAt(double someXValue) {
        //         f(x+h) - f(x)
        // f'(x) = -------------
        //               h

        double result =  yourFunctionHere(someXValue + H_DERIVATIVE_APPROXIMATE_LIMIT) - yourFunctionHere(someXValue);
        result /= H_DERIVATIVE_APPROXIMATE_LIMIT;

        return result;
    }

    private static double yourFunctionHere(double potatoe) {
        // just get rid of that and put your function here or replace it in the code or do a lambda or etc.
        return Math.PI*/*fancy stuff*/potatoe;
    }
}
