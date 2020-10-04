package rlbotexample.input.prediction.player;

import rlbotexample.input.dynamic_data.BallData;
import rlbotexample.input.dynamic_data.CarData;
import rlbotexample.input.dynamic_data.HitBox;
import util.game_constants.RlConstants;
import util.vector.Ray3;
import util.vector.Vector3;

public class CarBounce {


    private static final double CAR_MASS = 180;
    
    private static final double CAR_BOUNCE_RESTITUTION = 0.2;

    // WTF is this anyway???? dunno how to solve for this for now
    // edit: oh yeah I think this is the friction coefficient. I'll try the same value as the ball for now
    private static final double CAR_MU_CONSTANT = 2;

    private final Vector3 initialPosition;
    private final Vector3 initialVelocity;
    private final Vector3 spin;
    private final HitBox initialHitBox;
    private final double initialBoostAmount;
    private final Ray3 rayNormal;
    private final Vector3 surfaceVelocity;
    private final Vector3 parallelVelocityComponent;
    private final Vector3 perpendicularVelocityComponent;
    private final double initialCarDynamicRadius;
    private final double carIntertia;


    // best execution up to now
    // (still a lot of glitches, but it seems to work for like 99% of bounces.
    // Only high-speed bounces on curved walls seem to put a lot of noise into the predicted ball path)

    public CarBounce(final CarData carData, final Ray3 rayNormal) {
        this.initialPosition = carData.position;
        this.initialVelocity = carData.velocity;
        this.spin = carData.spin;
        this.initialHitBox = carData.hitBox;
        this.initialBoostAmount = carData.boost;
        this.rayNormal = rayNormal;
        this.surfaceVelocity = carData.surfaceVelocity(rayNormal.direction.scaled(-1));
        this.parallelVelocityComponent = initialVelocity.projectOnto(rayNormal.direction);
        this.perpendicularVelocityComponent = initialVelocity.minus(parallelVelocityComponent);

        this.initialCarDynamicRadius = initialHitBox.projectPointOnSurface(rayNormal.offset).minus(initialPosition).magnitude();

        // !!!!!! NOT RIGHT !!! NOT RIGHT !!!
        carIntertia = 0.4 * CAR_MASS * initialCarDynamicRadius * initialCarDynamicRadius;
    }

    public CarData compute(final double deltaTime) {
        if(parallelVelocityComponent.magnitude() > 200) {
            return computeBounces();
        }
        else {
            return computeBounces();
        }
    }

    public CarData computeRoll(final double deltaTime) {
        Vector3 p = rayNormal.offset;
        Vector3 n = rayNormal.direction;

        Vector3 L = p.minus(initialPosition);

        double m_reduced = 1.0 / ((1.0 / CAR_MASS) + (L.dotProduct(L) / carIntertia));

        Vector3 v_perp = n.scaled(Math.min(initialVelocity.dotProduct(n), 0));
        Vector3 v_para = initialVelocity.minus(v_perp.minus(L.crossProduct(spin)));

        double ratio = v_perp.magnitude() / Math.max(v_para.magnitude(), 0.0001);

        Vector3 J_perp = v_perp.scaled(-(1.0 + CAR_BOUNCE_RESTITUTION) * CAR_MASS);
        Vector3 J_para = v_para.scaled(-Math.min(1.0, CAR_MU_CONSTANT * ratio) * m_reduced);

        Vector3 J = J_perp.plus(J_para);

        Vector3 newSpin = spin.minus(L.crossProduct(J).scaled(1.0 / carIntertia));
        Vector3 newVelocity = initialVelocity.plus(J.scaled(1.0 / CAR_MASS).plus(initialVelocity));
        Vector3 newPosition = initialPosition.plus(newVelocity.scaled(deltaTime));

        double penetration = initialCarDynamicRadius - (newPosition.minus(p)).dotProduct(n);
        if (penetration > 0.0) {
            newPosition = newPosition.plus(n.scaled(1.001 * penetration));
        }

        newSpin = newSpin.scaled(Math.min(1.0, RlConstants.BALL_MAX_SPIN / newSpin.magnitude()));
        newVelocity = newVelocity.scaled(Math.min(1.0, RlConstants.CAR_MAX_SPEED / newVelocity.magnitude()));

        return new CarData(newPosition, newVelocity, newSpin, initialBoostAmount, initialHitBox.generateHypotheticalHitBox(newPosition), 0);
    }


    public CarData computeBounces() {
        // WORKING CODE (but not when wall sliding upward from the ground)
        final Vector3 slipSpeed = perpendicularVelocityComponent.minus(surfaceVelocity);
        final double surfaceSpeedRatio = parallelVelocityComponent.magnitude()/slipSpeed.magnitude();

        final Vector3 projectedHitPointOnHitBox = initialHitBox.projectPointOnSurface(initialHitBox.centerPosition.plus(rayNormal.direction.scaledToMagnitude(10000))).minus(initialHitBox.centerPosition);
        final double bounceAlignmentRatio = rayNormal.direction.dotProduct(projectedHitPointOnHitBox)/projectedHitPointOnHitBox.magnitude();
        final Vector3 newParallelVelocity = parallelVelocityComponent.scaled(-CAR_BOUNCE_RESTITUTION).scaled(bounceAlignmentRatio);
        Vector3 perpendicularDeltaVelocity = slipSpeed.scaled(-Math.min(1.0, 2*surfaceSpeedRatio) * 0.285);

        Vector3 newVelocity = newParallelVelocity.plus(perpendicularVelocityComponent.plus(perpendicularDeltaVelocity));

        final Vector3 deltaSpin = perpendicularDeltaVelocity.crossProduct(rayNormal.direction).scaled(0.0003 * initialCarDynamicRadius);
        final Vector3 newSpin = spin.minus(deltaSpin);

        Vector3 newPosition = initialPosition;

        Vector3 p = rayNormal.offset;
        Vector3 n = rayNormal.direction;
        double penetration = initialCarDynamicRadius - (newPosition.minus(p)).dotProduct(n);
        if (penetration > 0.0) {
            newPosition = newPosition.plus(n.scaled(1.001 * penetration));
        }

        return new CarData(newPosition, newVelocity, newSpin, initialBoostAmount, initialHitBox.generateHypotheticalHitBox(newPosition), 0);
    }

}
