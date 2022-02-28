using System;
using RedUtils;

namespace Phoenix
{
    /// <summary>TargetFactory for targets that do not depend on the car or the ball slice</summary>
    public class StaticTargetFactory : ITargetFactory
    {
        public readonly Target target;

        public StaticTargetFactory(Target target)
        {
            this.target = target ?? throw new ArgumentException("Static target is null");
        }

        public Target GetTarget(Car car, BallSlice slice)
        {
            return target;
        }
    }
}
