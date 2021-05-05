package util.game_situation;

import util.timer.FrameTimer;
import util.timer.Timer;

public class UnhandledGameState extends GameSituation {

    public UnhandledGameState() {
        super(new FrameTimer(0));
    }

    @Override
    public void loadGameState() {}
}
