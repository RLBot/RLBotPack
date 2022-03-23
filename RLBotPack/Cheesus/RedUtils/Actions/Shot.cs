using RedUtils.Math;
using System;
using System.Timers;

namespace RedUtils
{
	/// <summary>An action designed to hit the ball towards a target</summary>
	public abstract class Shot : IAction
	{
		/// <summary>Whether or not the shot has finished</summary>
		public abstract bool Finished { get; internal set; }
		/// <summary>Whether or not the shot can be interrupted</summary>
		public abstract bool Interruptible { get; internal set; }

		/// <summary>The future ball state at which time we are planning to hit the shot</summary>
		public abstract BallSlice Slice { get; internal set; }
		/// <summary>The exact position we will hit the ball towards</summary>
		public abstract Vec3 ShotTarget { get; internal set; }
		/// <summary>The final position of the car at the point of collision</summary>
		public abstract Vec3 TargetLocation { get; internal set; }
		/// <summary>The direction from the car to the ball at the point of collision</summary>
		public abstract Vec3 ShotDirection { get; internal set; }

		/// <summary>Defines whether or not we should go for this shot</summary>
		public abstract bool IsValid(Car car);

		/// <summary>Returns whether or not we can still go for this shot</summary>
		internal bool ShotValid(float threshold = 60)
		{
			BallSlice[] slices = Ball.Prediction.Slices;
			int soonest = 0;
			int latest = slices.Length - 1;

			while (latest + 1 - soonest > 2)
			{
				int midpoint = (soonest + latest) / 2;
				if (slices[midpoint].Time > Slice.Time)
					latest = midpoint;
				else
					soonest = midpoint;
			}

			// Preparing to interpolate between the selected slices
			float dt = slices[latest].Time - slices[soonest].Time;
			float timeFromSoonest = Slice.Time - slices[soonest].Time;
			Vec3 slopes = (slices[latest].Location - slices[soonest].Location) * (1 / dt);

			// Determining exactly where the ball will be at the given shot's intercept_time
			Vec3 predictedBallLocation = slices[soonest].Location + (slopes * timeFromSoonest);

			// Comparing predicted location with where the shot expects the ball to be
			return (Slice.Location - predictedBallLocation).Length() < threshold;
		}

		/// <summary>Performs this shot</summary>
		public abstract void Run(RUBot bot);
	}
}
