using rlbot.flat;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A predicted state of the ball in the future</summary>
	public class BallSlice
	{
		/// <summary>The location of the ball at this future point in time</summary>
		public readonly Vec3 Location;
		/// <summary>The velocity of the ball at this future point in time</summary>
		public readonly Vec3 Velocity;
		/// <summary>The angular velocity of the ball at this future point in time</summary>
		public readonly Vec3 AngularVelocity;
		/// <summary>The time in the future that this slice predicts</summary>
		public readonly float Time;

		/// <summary>Initializes a new ball slice</summary>
		public BallSlice(PredictionSlice slice)
		{
			Location = new Vec3(slice.Physics.Value.Location.Value);
			Velocity = new Vec3(slice.Physics.Value.Velocity.Value);
			AngularVelocity = new Vec3(slice.Physics.Value.AngularVelocity.Value);
			Time = slice.GameSeconds;
		}

		public BallSlice(Vec3 location, Vec3 velocity, Vec3 angularVelocity, float time)
		{
			Location = location;
			Velocity = velocity;
			AngularVelocity = angularVelocity;
			Time = time;
		}

		/// <summary>Converts this ball slice to a ball</summary>
		public Ball ToBall()
		{
			return new Ball(Location, Velocity, AngularVelocity);
		}
		
		
		/// <summary>Initializes a new ball slice from the current situation.
		/// Useful if the Ball prediction is not available.</summary>
		public static BallSlice Now()
		{
			return new BallSlice(Ball.Location, Ball.Velocity, Ball.AngularVelocity, Game.Time);
		}
	}
}
