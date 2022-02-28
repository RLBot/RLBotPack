using RedUtils;

namespace Phoenix
{
    /// <summary>A factory for creating Targets based on a car and a ball slice</summary>
    public interface ITargetFactory
    {
        public Target GetTarget(Car car, BallSlice slice);
    }
}
