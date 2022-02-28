using System;

namespace RedUtils
{
    public static class MyExtensions
    {
        /// <summary>
        /// Returns a random float between 0 (inclusive) and 1 (exclusive).
        /// </summary>
        public static float NextFloat(this Random rng)
        {
            return (float)rng.NextDouble();
        }

        /// <summary>
        /// Three random floats between 0 (inclusive) and 1 (exclusive) are rolled. This method returns the middle
        /// value, resulting in a number typically closer to 0.5.
        /// </summary>
        public static float NextMiddleFloatOf3(this Random rng)
        {
            return MathF.Min(MathF.Max(rng.NextFloat(), rng.NextFloat()), rng.NextFloat());
        }
    }
}
