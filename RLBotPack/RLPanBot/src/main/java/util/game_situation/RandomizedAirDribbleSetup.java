package util.game_situation;

import rlbot.gamestate.*;
import util.game_situation.GameSituation;
import util.timer.FrameTimer;
import util.timer.Timer;

public class RandomizedAirDribbleSetup extends GameSituation {

    public RandomizedAirDribbleSetup() {
        super(new FrameTimer(20*30));
    }

    @Override
    public void loadGameState() {

        float basePositionX = randomRange(-2000, 2000);
        float basePositionY = randomRange(-3000, 3000);
        float basePositionZ = randomRange(800, 1500);
        float baseSpeedX = randomRange(-800, 800);
        float baseSpeedY = randomRange(-800, 800);
        float baseSpeedZ = randomRange(0, 500);

        float deltaPositionX = randomRange(0, 0);
        float deltaPositionY = randomRange(0, 0);
        float deltaPositionZ = randomRange(-400, -600);
        float deltaSpeedX = randomRange(-100, 100);
        float deltaSpeedY = randomRange(-100, 100);
        float deltaSpeedZ = randomRange(200, 300);

        GameState gameState = getCurrentGameState();
        gameState.withBallState(new BallState(new PhysicsState()
                .withLocation(new DesiredVector3(basePositionX, basePositionY, basePositionZ))
                .withVelocity(new DesiredVector3(baseSpeedX, baseSpeedY, baseSpeedZ))
                .withRotation(new DesiredRotation(0f, 0f, 0f))
                .withAngularVelocity(new DesiredVector3(0f, 0f, 0f))));

        gameState.withCarState(0, new CarState()
                .withPhysics(new PhysicsState()
                        .withLocation(new DesiredVector3(basePositionX+deltaPositionX, basePositionY+deltaPositionY, basePositionZ+deltaPositionZ))
                        .withVelocity(new DesiredVector3(baseSpeedX+deltaSpeedX, baseSpeedY+deltaSpeedY, baseSpeedZ+deltaSpeedZ))
                        .withRotation(new DesiredRotation((float)Math.PI/2, (float)-Math.PI/2, 0f))
                        .withAngularVelocity(new DesiredVector3(0f, 0f, 0f)))
                .withBoostAmount(100f));

        applyGameState(gameState);
    }

    private float randomRange(double min, double max) {
        return (float)(((max-min)*Math.random()) + min);
    }
}
