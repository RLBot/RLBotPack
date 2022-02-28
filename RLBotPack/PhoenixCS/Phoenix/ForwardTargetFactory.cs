using System;
using RedUtils;
using RedUtils.Math;

namespace Phoenix
{
    /// <summary>A TargetFactory that creates a target that will just move the ball away from our goal and closer to enemy goal</summary>
    public class ForwardTargetFactory : ITargetFactory
    {
        private const float SemiWidth = 350f;
        private const float SemiHeight = 350f;
        private const float Offset = 650f;
        
        public Target GetTarget(Car car, BallSlice slice)
        {
            Vec3 flow = Field.FlowDir(slice.Location, car.Team);
            Vec3 center = slice.Location + flow * Offset;
            Vec3 left = flow.FlatNorm().Rotate(MathF.PI / 2f);
            Vec3 topLeft = center + left * SemiWidth + Vec3.Up * SemiHeight;
            Vec3 bottomRight = center - left * SemiWidth - Vec3.Up * SemiHeight;
            return new Target(topLeft, bottomRight);
        }
    }
}
