package util.game_situation;

import rlbot.gamestate.*;
import util.timer.FrameTimer;
import util.timer.Timer;

public class AirDribbleSetup3 extends GameSituation {

    public AirDribbleSetup3() {
        super(new FrameTimer(5*30));
    }

    @Override
    public void loadGameState() {
        GameState gameState = getCurrentGameState();
        gameState.withBallState(new BallState(new PhysicsState().withLocation(new DesiredVector3(0f, 2000f, 500f))
                .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                .withRotation(new DesiredRotation(0f, 0f, 0f))
                .withVelocity(new DesiredVector3(0f, -100f, 500f))));

        gameState.withCarState(0, new CarState()
                .withPhysics(new PhysicsState()
                        .withRotation(new DesiredRotation((float)Math.PI/2, (float)-Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withLocation(new DesiredVector3(0f, 2100f, 300f))
                        .withVelocity(new DesiredVector3(0f, -100f, 500f)))
                .withBoostAmount(100f));

        applyGameState(gameState);
    }
}
