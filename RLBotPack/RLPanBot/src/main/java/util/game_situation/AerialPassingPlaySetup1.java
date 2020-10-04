package util.game_situation;

import rlbot.gamestate.*;
import util.game_situation.GameSituation;
import util.timer.FrameTimer;

public class AerialPassingPlaySetup1 extends GameSituation {

    public AerialPassingPlaySetup1() {
        super(new FrameTimer(6*30));
    }

    @Override
    public void loadGameState() {
        GameState gameState = getCurrentGameState();
        /*
        gameState.withBallState(new BallState(new PhysicsState().withLocation(new DesiredVector3(-3000f, 1000f, 100f))
                .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                .withRotation(new DesiredRotation(0f, 0f, 0f))
                .withVelocity(new DesiredVector3(300f, -500f, 1200f))));

        gameState.withCarState(0, new CarState()
                .withPhysics(new PhysicsState()
                        .withRotation(new DesiredRotation(0f, (float)Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withLocation(new DesiredVector3(-3000f, -1000f, 100f))
                        .withVelocity(new DesiredVector3(0f, 100f, 800f)))
                .withBoostAmount(100f));

        gameState.withCarState(1, new CarState()
                .withPhysics(new PhysicsState()
                        .withRotation(new DesiredRotation(0f, (float)Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withLocation(new DesiredVector3(1000f, -2600f, 0f))
                        .withVelocity(new DesiredVector3(0f, 1000f, 0f)))
                .withBoostAmount(100f));
        */

        gameState.withBallState(new BallState(new PhysicsState().withLocation(new DesiredVector3(-3000f, 1000f, 100f))
                .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                .withRotation(new DesiredRotation(0f, 0f, 0f))
                .withVelocity(new DesiredVector3(300f, -500f, 1200f))));

        gameState.withCarState(0, new CarState()
                .withPhysics(new PhysicsState()
                        .withRotation(new DesiredRotation(0f, (float)Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withLocation(new DesiredVector3(-3000f, -1000f, 100f))
                        .withVelocity(new DesiredVector3(0f, 100f, 800f)))
                .withBoostAmount(100f));

        gameState.withCarState(1, new CarState()
                .withPhysics(new PhysicsState()
                        .withRotation(new DesiredRotation(0f, (float)Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))
                        .withLocation(new DesiredVector3(500f, -1500f, 0f))
                        .withVelocity(new DesiredVector3(0f, 0f, 0f)))
                .withBoostAmount(100f));
        applyGameState(gameState);
    }
}
