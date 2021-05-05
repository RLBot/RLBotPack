package util.game_situation;

import rlbot.gamestate.*;
import util.timer.FrameTimer;
import util.timer.Timer;

public class SimpleGroundShot1 extends GameSituation {

    public SimpleGroundShot1() {
        super(new FrameTimer(10*30));
    }

    @Override
    public void loadGameState() {
        GameState gameState = getCurrentGameState();
        gameState.withBallState(new BallState(new PhysicsState().withLocation(new DesiredVector3(0f, -2000f, 93f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withRotation(new DesiredRotation(0f, 0f, 0f))
                        .withVelocity(new DesiredVector3(0f, 0f, 0f))));

        gameState.withCarState(0, new CarState()
                        .withPhysics(new PhysicsState()
                                .withRotation(new DesiredRotation(0f, (float)-Math.PI/2, 0f))
                                .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                                .withLocation(new DesiredVector3(0f, 0f, 0f))
                                .withVelocity(new DesiredVector3(0f, 0f, 0f)))
                        .withBoostAmount(100f));

        applyGameState(gameState);
    }
}
