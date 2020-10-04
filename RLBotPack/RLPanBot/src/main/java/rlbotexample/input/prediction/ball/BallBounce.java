package rlbotexample.input.prediction.ball;

import rlbotexample.input.dynamic_data.BallData;
import util.game_constants.RlConstants;
import util.vector.Ray3;
import util.vector.Vector3;

public class BallBounce {

    private static final double BALL_MASS = 30;
    private static final double BALL_INERTIA = 0.4 * BALL_MASS * RlConstants.BALL_RADIUS * RlConstants.BALL_RADIUS;
    private static final double BALL_BOUNCE_RESTITUTION = 0.6;
    private static final double BALL_MU_CONSTANT = 2;

    private final Vector3 initialPosition;
    private final Vector3 initialVelocity;
    private final Vector3 spin;
    private final Ray3 rayNormal;
    private final Vector3 surfaceVelocity;
    private final Vector3 parallelVelocityComponent;
    private final Vector3 perpendicularVelocityComponent;


    // best execution up to now
    // (still a lot of glitches, but it seems to work for like 99% of bounces.
    // Only high-speed bounces on curved walls seem to put a lot of noise into the predicted ball path)

    public BallBounce(final BallData ballData, final Ray3 rayNormal) {
        this.initialPosition = ballData.position;
        this.initialVelocity = ballData.velocity;
        this.spin = ballData.spin;
        this.rayNormal = rayNormal;
        this.surfaceVelocity = ballData.surfaceVelocity(rayNormal.direction.scaled(-1));
        this.parallelVelocityComponent = initialVelocity.projectOnto(rayNormal.direction);
        this.perpendicularVelocityComponent = initialVelocity.minus(parallelVelocityComponent);
    }

    public BallData compute(final double deltaTime) {
        if(parallelVelocityComponent.magnitude() > 200) {
            return computeBounces();
        }
        else {
            return computeRoll(deltaTime);
        }
    }

    public BallData computeRoll(final double deltaTime) {
        Vector3 p = rayNormal.offset;
        Vector3 n = rayNormal.direction;

        Vector3 L = p.minus(initialPosition);

        double m_reduced = 1.0 / ((1.0 / BALL_MASS) + (L.dotProduct(L) / BALL_INERTIA));

        Vector3 v_perp = n.scaled(Math.min(initialVelocity.dotProduct(n), 0));
        Vector3 v_para = initialVelocity.minus(v_perp.minus(L.crossProduct(spin)));

        double ratio = v_perp.magnitude() / Math.max(v_para.magnitude(), 0.0001);

        Vector3 J_perp = v_perp.scaled(-(1.0 + BALL_BOUNCE_RESTITUTION) * BALL_MASS);
        Vector3 J_para = v_para.scaled(-Math.min(1.0, BALL_MU_CONSTANT * ratio) * m_reduced);

        Vector3 J = J_perp.plus(J_para);

        Vector3 newSpin = spin.minus(L.crossProduct(J).scaled(1.0 / BALL_INERTIA));
        Vector3 newVelocity = initialVelocity.plus(J.scaled(1.0 / BALL_MASS).plus(initialVelocity.scaled(-RlConstants.BALL_AIR_DRAG_COEFFICIENT * deltaTime)));
        Vector3 newPosition = initialPosition.plus(newVelocity.scaled(deltaTime));

        double penetration = RlConstants.BALL_RADIUS - (newPosition.minus(p)).dotProduct(n);
        if (penetration > 0.0) {
            newPosition = newPosition.plus(n.scaled(1.001 * penetration));
        }

        newSpin = newSpin.scaled(Math.min(1.0, RlConstants.BALL_MAX_SPIN / newSpin.magnitude()));
        newVelocity = newVelocity.scaled(Math.min(1.0, RlConstants.BALL_MAX_SPEED / newVelocity.magnitude()));

        return new BallData(newPosition, newVelocity, newSpin, 0);
    }


    public BallData computeBounces() {
        // WORKING CODE (but not when wall sliding upward from the ground)
        final Vector3 slipSpeed = perpendicularVelocityComponent.minus(surfaceVelocity);
        final double surfaceSpeedRatio = parallelVelocityComponent.magnitude()/slipSpeed.magnitude();

        final Vector3 newParallelVelocity = parallelVelocityComponent.scaled(-BALL_BOUNCE_RESTITUTION);
        Vector3 perpendicularDeltaVelocity = slipSpeed.scaled(-Math.min(1.0, 2*surfaceSpeedRatio) * 0.285);

        Vector3 newVelocity = newParallelVelocity.plus(perpendicularVelocityComponent.plus(perpendicularDeltaVelocity));

        final Vector3 deltaSpin = perpendicularDeltaVelocity.crossProduct(rayNormal.direction).scaled(0.0003 * RlConstants.BALL_RADIUS);
        final Vector3 newSpin = spin.minus(deltaSpin);

        Vector3 newPosition = initialPosition;

        return new BallData(newPosition, newVelocity, newSpin, 0);
    }

}
