package util.timer;

public class Timer
{
    private double secondsToCount;
    private long timeOfStartMillis;

    public Timer(double secondsToCount) {
        this.secondsToCount = secondsToCount;
    }

    public Timer start()
    {
        timeOfStartMillis = System.currentTimeMillis();
        return this;
    }

    public boolean isTimeElapsed()
    {
        return (System.currentTimeMillis() - timeOfStartMillis)/(double)1000 >= secondsToCount;
    }

    public float timeRemaining()
    {
        return (float)(secondsToCount - (System.currentTimeMillis() - timeOfStartMillis)/1000.0);
    }

    public float timeElapsed()
    {
        return ((float)secondsToCount) - timeRemaining();
    }

    public double getSecondsToCount()
    {
        return secondsToCount;
    }
}
