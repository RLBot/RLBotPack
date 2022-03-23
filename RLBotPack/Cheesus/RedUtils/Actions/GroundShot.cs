using System;
using System.Timers;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A ground shot action, where the car runs into the ball without leaving the ground
	/// <para>Can also be used for dribbling</para>
	/// </summary>
	public class GroundShot : Shot
	{
		/// <summary>Whether or not this shot has finished</summary>
		public override bool Finished { get; internal set; }
		/// <summary>Whether or not this shot can be interrupted</summary>
		public override bool Interruptible { get; internal set; }

		/// <summary>The future ball state at which time we are planning to hit the shot</summary>
		public override BallSlice Slice { get; internal set; }
		/// <summary>The exact position we will hit the ball towards</summary>
		public override Vec3 ShotTarget { get; internal set; }
		/// <summary>The final position of the car at the point of collision</summary>
		public override Vec3 TargetLocation { get; internal set; }
		/// <summary>The direction from the car to the ball at the point of collision</summary>
		public override Vec3 ShotDirection { get; internal set; }

		/// <summary>This shot's arrive sub action, which will take us to the ball</summary>
		public Arrive ArriveAction { get; internal set; }

		/// <summary>The amount of boost we have when starting this action</summary>
		private readonly int _startBoostAmount = 0;
		/// <summary>The length between updates to the target location, and shot direction</summary>
		private readonly float _updateInterval = 0.2f;
		/// <summary>Keeps track of the time since the last update</summary>
		private float _updateTimer = 0;
		/// <summary>Whether or not we have left the ground while performing this action</summary>
		private bool _leftGround = false;

		/// <summary>Initializes a new ground shot action, with a specific ball slice and a shot target</summary>
		public GroundShot(Car car, BallSlice slice, Vec3 shotTarget)
		{
			Finished = false;
			Interruptible = true;

			Slice = slice;
			ShotTarget = shotTarget;
			_startBoostAmount = car.Boost;

			SetTargetLocation(car, true);
		}

		/// <summary>Sets the target location and the shot direction based on the velocity of the ball, the position of the car currently, and other factors</summary>
		/// <param name="init">Whether or not this is being run during the initialization of this action</param>
		private void SetTargetLocation(Car car, bool init = false)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Gets the closest surface to the chosen slice, and get that surface's normal
			Surface surface = Field.NearestSurface(Slice.Location);
			Vec3 normal = surface.Normal;

			// Predicts the ball's state after contact
			Ball ballAfterHit = Slice.ToBall();
			Vec3 carFinVel = (((init ? Slice.Location : TargetLocation) - car.Location).Flatten(normal) / timeRemaining).Cap(0, Car.MaxSpeed);
			ballAfterHit.velocity = (carFinVel * 6 + Slice.Velocity) / 7;

			// Predicts how long it will take the ball to hit the target after being hit
			Vec3 directionToScore = Slice.Location.FlatDirection(ShotTarget);
			float velocityDiff = (carFinVel - Slice.Velocity).Length();
			float timeToScore = Slice.Location.FlatDist(ShotTarget) / Utils.Cap(velocityDiff * Utils.ShotPowerModifier(velocityDiff) + ballAfterHit.velocity.Dot(directionToScore), 500, Ball.MaxSpeed);

			// Calculates the shot direction, and target location
			ballAfterHit.velocity = (carFinVel + Slice.Velocity * 2) / 3;
			ShotDirection = ballAfterHit.PredictLocation(timeToScore).Direction(ShotTarget);
			TargetLocation = Slice.Location - ShotDirection * 120;

			// Calculates the height of the target location, and of the chosen slice
			float height = (TargetLocation - surface.Limit(TargetLocation)).Dot(normal);
			float ballHeight = (Slice.Location - surface.Limit(Slice.Location)).Dot(normal);

			// if the target location is too close to the surface, change the shot direction and the target location so it is flatter against the surface
			if (height < 20)
			{
				float angle = MathF.Asin(Utils.Cap((ballHeight - 20) / 120, -1, 1));
				ShotDirection = ShotDirection.FlatNorm(normal) * MathF.Cos(angle) + normal * MathF.Sin(angle);
				TargetLocation = Slice.Location - ShotDirection * 120;
			}

			if (init)
			{
				// If this is during initialization, we need to create the arrive action
				ArriveAction = new Arrive(car, TargetLocation, ShotDirection.FlatNorm(surface.Normal), Slice.Time, true, 0.1f);
				return;
			}
			// Otherwise, just update the arrive action
			ArriveAction.Target = TargetLocation;
			ArriveAction.Direction = ShotDirection.FlatNorm(surface.Normal);
			Finished = height > 20.5f;
		}

		/// <summary>Performs this ground shot</summary>
		public override void Run(RUBot bot)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Drives to the target location
			ArriveAction.Run(bot);

			// This shot is only interruptible when the arrive sub action is
			Interruptible = ArriveAction.Interruptible;
			// Check if we have left the ground
			_leftGround = _leftGround || !bot.Me.IsGrounded;
			// Assuming we drive straight to the target location, how long should it take?
			float eta = ArriveAction.Eta(bot.Me);

			_updateTimer += bot.DeltaTime;
			if (Interruptible && (timeRemaining < 0 || (_leftGround && bot.Me.IsGrounded) || !ShotValid() || bot.Me.Boost > _startBoostAmount ||
				eta > MathF.Max(timeRemaining * 1.05f, timeRemaining + 0.025f) || (eta < timeRemaining - 0.25f && _updateTimer > _updateInterval)))
			{
				// If this shot is no longer valid, or we think it's possible that a better shot exists, we finish this action
				Finished = true;
			}
			else if (_updateTimer > _updateInterval)
			{
				// Updates the target location and shot direction every so often, so this shot is as accurate as possible
				SetTargetLocation(bot.Me);
				_updateTimer = 0;
			}
		}

		/// <summary>Returns whether this ground shot is possible</summary>
		public override bool IsValid(Car car)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Calculates the height of the target
			Surface surface = Field.NearestSurface(TargetLocation);
			float height = (TargetLocation - surface.Limit(TargetLocation)).Dot(surface.Normal);

			// Returns true if we can get there in time, and the ball isn't too high to reach from the ground
			return Drive.GetEta(car, TargetLocation) < timeRemaining && height < 20.5f && ShotDirection.z < 0.9f;
		}
	}
}
