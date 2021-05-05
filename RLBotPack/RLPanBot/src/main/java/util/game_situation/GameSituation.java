package util.game_situation;

import rlbot.cppinterop.RLBotDll;
import rlbot.gamestate.GameState;
import util.timer.FrameTimer;
import util.timer.Timer;

public abstract class GameSituation {

    private FrameTimer gameStateDuration;

    public GameSituation(FrameTimer gameStateDuration) {
        this.gameStateDuration = gameStateDuration;
        this.gameStateDuration.start();
        this.loadGameState();
    }

    public void reloadGameState() {
        this.gameStateDuration.start();
        this.loadGameState();
    }

    public abstract void loadGameState();

    public boolean isGameStateElapsed() {
        return gameStateDuration.isTimeElapsed();
    }

    public void frameHappend() {
        gameStateDuration.countFrame();
    }

    public GameState getCurrentGameState() {
        return new rlbot.gamestate.GameState();
    }

    public void applyGameState(GameState gameState) {
        RLBotDll.setGameState(gameState.buildPacket());
    }
}
