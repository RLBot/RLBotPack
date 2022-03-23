using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>An action meant to drive the car to a certain location, at a certain time and/or facing a certain direction</summary>
	public class Arrive : IAction
	{
		/// <summary>If we have arrived, or ran out of time</summary>
		public bool Finished { get; private set; }
		/// <summary>Whether or not this function is interruptible</summary>
		public bool Interruptible { get; private set; }

		/// <summary>The destination the car will arrive at</summary>
		public Vec3 Target;
		/// <summary>The direction the car will try to face at arrival</summary>
		public Vec3 Direction;
		/// <summary>The time of arrival</summary>
		public float ArrivalTime;
		/// <summary>Whether or not we should flip while driving to the location</summary>
		public bool AllowFlipping;
		/// <summary>How much time we need to drive forward before arriving (mainly used if we plan on jumping/dodging just before arriving)</summary>
		public float RecoveryTime;
		/// <summary>The drive action</summary>
		public Drive Drive;

		/// <summary>How much time is left before we arrive or this action expires</summary>
		public float TimeRemaining { get; private set; }

		/// <summary>Initializes a new arrival action.</summary>
		/// <param name="direction">The direction the car will try to face at the time of arrival. If null, any direction is allowed.</param>
		/// <param name="arrivalTime">The specific time of arrival. If negative, it will not be a specific time and we will not waste boost getting there.</param>
		/// <param name="allowFlipping">Whether or not we are going to allow dodges to increase speed</param>
		/// <param name="recoveryTime">How much time we should give the car to recover before arriving</param>
		public Arrive(Car car, Vec3 target, Vec3? direction = null, float arrivalTime = -1f, bool allowFlipping = true, float recoveryTime = 0f)
		{
			Interruptible = true;
			Finished = false;

			Target = target;
			Direction = direction ?? Vec3.Zero;
			ArrivalTime = arrivalTime;
			AllowFlipping = allowFlipping;
			Drive = new Drive(car, Target, Car.MaxSpeed, AllowFlipping, arrivalTime >= 0f);
			RecoveryTime = recoveryTime;
		}

		/// <summary>Drives the car to a certain location, at a certain time and/or facing a certain direction</summary>
		public void Run(RUBot bot)
		{
			// Calculates various important values
			float distance = Distance(bot.Me);
			float carSpeed = bot.Me.Velocity.Length();

			// Calculates how much time we have before we should arrive
			TimeRemaining = ArrivalTime < 0 ? distance / Car.MaxSpeed : MathF.Max(ArrivalTime - Game.Time, 0.001f);

			// Based on the time remaining, calculate our target speed
			float targetSpeed = distance / TimeRemaining;

			// Predicts (roughly) the location of the car after dodging
			Vec3 predictedLocation = bot.Me.LocationAfterDodge();
			// If we were given a direction, calculate a shifted version of our target so that we face the given direction
			Vec3 shiftedTarget;
			if (Direction.Length() > 0)
			{
				// Gets the surface normal of the surface we should be on at arrival
				Vec3 surfaceNormal = Field.NearestSurface(Target).Normal;
				// Gets the direction to the target, flattened by the surface normal
				Vec3 directionToTarget = bot.Me.Location.FlatDirection(Target, surfaceNormal);

				// Calculates the amount we should shift the current target
				float additionalShift = RecoveryTime * carSpeed;
				float shift = MathF.Min(Field.DistanceBetweenPoints(Target, bot.Me.Location) * 0.6f, Utils.Cap(carSpeed, 1410, Car.MaxSpeed) * 1.5f);
				float turnRadius = Drive.TurnRadius(Utils.Cap(carSpeed, 500, Car.MaxSpeed)) * 1.2f;

				shift *= targetSpeed < 2200 || ArrivalTime < 0 ? Utils.Cap((shift - additionalShift) / turnRadius, 0f, 1f) : 0;

				// Shifts the target such that the direction it is shifted is not on the other side of the final target relative to the car
				Vec3 leftDirection = directionToTarget.Cross(surfaceNormal).Normalize();
				Vec3 rightDirection = directionToTarget.Cross(-surfaceNormal).Normalize();
				shiftedTarget = Field.LimitToNearestSurface(Target - Direction.Clamp(leftDirection, rightDirection, surfaceNormal).Normalize() * shift);
			}
			else
			{
				// If we weren't given a direction, just don't shift the target
				shiftedTarget = Target;
			}

			// How much time we have left to flip
			float timeLeft = bot.Me.Location.FlatDist(Target) / MathF.Max(carSpeed + 500, 1410);

			// Only allow dodges if we are sure we won't land too far over, and that we have enough time to recover
			Drive.AllowDodges = MathF.Sign(predictedLocation.FlatDirection(Target).Dot(Direction.Cross())) == MathF.Sign(bot.Me.Location.FlatDirection(Target).Dot(Direction.Cross())) && timeLeft > 1.35f + RecoveryTime;
			Drive.Target = shiftedTarget;
			Drive.TargetSpeed = targetSpeed;
			Drive.Run(bot); // Drive towards the shifted target

			// If the drive sub action isn't interruptible, then this action isn't interruptible either
			Interruptible = Drive.Interruptible;

			// If we have arrived, or we ran out of time, finish this action
			if (Field.LimitToNearestSurface(bot.Me.Location).Dist(Field.LimitToNearestSurface(Target)) < 100 || (ArrivalTime < Game.Time && ArrivalTime > 0))
			{
				Finished = true;
			}
		}

		/// <summary>Finds the distance left to drive</summary>
		public float Distance(Car car)
		{
			return Drive.GetDistance(car, Target);
		}

		/// <summary>Estimates the time left before we arrive, assuming we drive as fast as possible</summary>
		public float Eta(Car car)
		{
			return Drive.GetEta(car, Target);
		}
	}
}
