using System;
using RedUtils;
using RedUtils.Math;

namespace Phoenix
{
    /// <summary>A TargetFactory that creates targets that will lead to reflect/mirror shots into the enemy goal</summary>
    public class WallReflectTargetFactory : ITargetFactory
    {
        private const float MIN_Z = 190;
        private const float MAX_Z = 1800;
        
        private Vec3 _normal;
        private Vec3 _wallLeft;
        private Vec3 _wallRight;

        public WallReflectTargetFactory(Vec3 normal, Vec3 wallLeft, Vec3 wallRight)
        {
            _normal = normal.Normalize();
            _wallLeft = wallLeft;
            _wallRight = wallRight;
        }

        public Target GetTarget(Car car, BallSlice slice)
        {
            Vec3 a = _wallLeft;
            Vec3 b = _wallRight;

            float ballToGoalDist = slice.Location.Dist(Field.Goals[1 - car.Team].Location);
            float targetSemiWidth = MathF.Max(Utils.Lerp(0.1f + ballToGoalDist / 5500 - 1f * MathF.Abs(slice.Location.x) / Field.Width, 0, 333), 90);
            
            Vec3 a2B = a.Direction(b);

            Vec3 ballOnA2B = a + a2B * (slice.Location - a).Dot(a2B);
            float ballDistA2B = (slice.Location - a).Dot(_normal);

            Vec3 goalOnA2B = a + a2B * (Field.Goals[1 - car.Team].Location - a).Dot(a2B);
            float goalDistA2B = (Field.Goals[1 - car.Team].Location - a).Dot(_normal);

            Vec3 reflectPoint = Utils.Lerp(ballDistA2B / (ballDistA2B + goalDistA2B), ballOnA2B, goalOnA2B);
            float reflectT = (slice.Location - a).Dot(a2B);

            if (reflectT < 0 || a.Dist(b) < reflectT || slice.Location.FlatDist(reflectPoint) > 3000) return null;
            
            Target target = new Target(
                reflectPoint - a2B * targetSemiWidth + Vec3.Z * MAX_Z,
                reflectPoint + a2B * targetSemiWidth + Vec3.Z * MIN_Z
            );

            return target;
        }
    }
}
