package util.controllers;

public class PidController {

    private double kp;
    private double ki;
    private double kd;
    private double currentError;
    private double previousError;
    private double largeTotalError;
    private double smallTotalError;
    private double integralMaxValue;

    public PidController(double kp, double ki, double kd) {
        this.kp = kp;
        this.ki = ki;
        this.kd = kd;
        this.largeTotalError = 0;
        this.smallTotalError = 0;
        this.integralMaxValue = Double.MAX_VALUE;
    }

    public PidController(double kp, double ki, double kd, double integralMaxValue) {
        this.kp = kp;
        this.ki = ki;
        this.kd = kd;
        this.largeTotalError = 0;
        this.smallTotalError = 0;
        this.integralMaxValue = integralMaxValue;
    }

    public double process(double actualValue, double desiredValue) {
        // getting the error
        double error = actualValue - desiredValue;

        // updating the integral part
        // there are 2 total error variables because adding doubles
        // on a too large scale of magnitude difference does nothing at all
        smallTotalError += error;
        if(Math.abs(smallTotalError) > 10) {
            largeTotalError += smallTotalError;
            smallTotalError = 0;
        }

        largeTotalError = Math.max(largeTotalError, -integralMaxValue);
        smallTotalError = Math.max(smallTotalError, -integralMaxValue);
        largeTotalError = Math.min(largeTotalError, integralMaxValue);
        smallTotalError = Math.min(smallTotalError, integralMaxValue);

        // updating the derivative part
        previousError = currentError;
        currentError = error;

        return kp*currentError + ki*(largeTotalError + smallTotalError) - kd*(previousError - currentError);
    }

    public void resetIntegralValue() {
        largeTotalError = 0;
        smallTotalError = 0;
    }

    public double getProportionnalConstant() {
        return kp;
    }

    public double getIntegralConstant() {
        return ki;
    }

    public double getDerivativeConstant() {
        return kd;
    }

    public double getIntegralAmount() {
        return ki*(largeTotalError + smallTotalError);
    }

    public void transferInternalMemoryTo(PidController valuesToTransfer) {
        valuesToTransfer.currentError = this.currentError;
        valuesToTransfer.previousError = this.previousError;
        valuesToTransfer.largeTotalError = this.largeTotalError;
        valuesToTransfer.smallTotalError = this.smallTotalError;
        valuesToTransfer.integralMaxValue = this.integralMaxValue;
    }
}
