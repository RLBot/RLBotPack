package util.timer;

public class AutoCorrectingLapse {
    private double secondsToLapse;
    private double elapsedTime;
    private long lastTime;
    private long numberOfLapseToDo;

    public AutoCorrectingLapse(double secondsToLapse) {
        this.secondsToLapse = secondsToLapse;
        this.elapsedTime = 0;
        this.lastTime = System.currentTimeMillis();
        this.numberOfLapseToDo = 0;
    }

    public void update() {
        elapsedTime += (System.currentTimeMillis() - lastTime)*0.001;
        lastTime = System.currentTimeMillis();
        if(elapsedTime > secondsToLapse) {
            elapsedTime -= secondsToLapse;
            numberOfLapseToDo++;
        }
    }

    public boolean isTimeElapsed() {
        return numberOfLapseToDo > 0;
    }
    public void lapse() {
        numberOfLapseToDo--;
    }

    private long round(double x) {
        return (long)(x+0.5);
    }
}
