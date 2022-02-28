using RedUtils;
using RedUtils.Math;

namespace Phoenix
{
    public static class CheapNoAerialShotCheck
    {
        public static Car Me;

        private static int _shotTypeIndex = 0;
        
        private const int ShotTypeCount = 4;

        public static void Next(Car car)
        {
            Me = car;
            _shotTypeIndex = (_shotTypeIndex + 1) % ShotTypeCount;
        }
        
        /// <summary>The default shot check. Will go for pretty much anything it can except aerials</summary>
        /// <param name="slice">The future moment of the ball we are aiming to hit</param>
        /// <param name="target">The final resting place of the ball after we hit it (hopefully)</param>
        public static Shot ShotCheck(BallSlice slice, Target target)
        {
            if (slice != null) // Check if the slice even exists
            {
                float timeRemaining = slice.Time - Game.Time;

                // Check first if the slice is in the future and if it's even possible to shoot at our target
                if (timeRemaining > 0 && target.Fits(slice.Location))
                {
                    Ball ballAfterHit = slice.ToBall();
                    Vec3 carFinVel = ((slice.Location - Me.Location) / timeRemaining).Cap(0, Car.MaxSpeed);
                    ballAfterHit.velocity = carFinVel + slice.Velocity.Flatten(carFinVel.Normalize()) * 0.8f;
                    Vec3 shotTarget = target.Clamp(ballAfterHit);

                    switch (_shotTypeIndex)
                    {
                        case 0:
                            // Let's try a ground shot
                            GroundShot groundShot = new GroundShot(Me, slice, shotTarget);
                            if (groundShot.IsValid(Me))
                            {
                                return groundShot;
                            }
                            break;
                        
                        case 1:
                            // Otherwise, we'll try a jump shot
                            JumpShot jumpShot = new JumpShot(Me, slice, shotTarget);
                            if (jumpShot.IsValid(Me))
                            {
                                return jumpShot;
                            }
                            break;
                        
                        case 2:
                            // How about a double jump shot
                            DoubleJumpShot doubleJumpShot = new DoubleJumpShot(Me, slice, shotTarget);
                            if (doubleJumpShot.IsValid(Me))
                            {
                                return doubleJumpShot;
                            }
                            break;
                        case 3:
                            if (Me.Boost <= 20) break;
                            if (slice.Location.z < 500) break;
                            // And lastly, an aerial shot
                            AerialShot aerial = new AerialShot(Me, slice, shotTarget);
                            if (aerial.IsValid(Me))
                            {
                                return aerial;
                            }
                            break;
                    }
                }
            }

            return null; // if none of those work, we'll just return null (meaning no shot was found)
        }
    }
}
