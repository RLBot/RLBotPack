package util.timer;

public class Clock {

    private long timeOfStartMillis;
    private double deltaTimeSecs;
    private boolean hasStopped;

    public Clock() { hasStopped = false; }

    public void start()
    {
        timeOfStartMillis = System.currentTimeMillis();
        hasStopped = false;
    }

    public void stop() {
        double lastMillisRead = System.currentTimeMillis();
        deltaTimeSecs = (lastMillisRead - timeOfStartMillis)/1000.0;
        hasStopped = true;
    }

    public double getElapsedSeconds() {
        if(!hasStopped) {
            return (System.currentTimeMillis() - timeOfStartMillis)/1000.0;
        }
        else {
            return deltaTimeSecs;
        }
    }

    private double timeSinceStartSecs() {
        return (System.currentTimeMillis() - timeOfStartMillis)/1000.0;
    }
}
