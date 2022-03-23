using System;
using System.Timers;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A double jump shot action, where the car double jumps into the ball</summary>
	public class DoubleJumpShot : Shot
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

		/// <summary>This shot's arrive sub action, which will take us to the ball before double jumping</summary>
		public Arrive ArriveAction { get; internal set; }

		/// <summary>The amount of boost we have when starting this action</summary>
		private readonly int _startBoostAmount = 0;
		/// <summary>The length between updates to the target location, and shot direction</summary>
		private readonly float _updateInterval = 0.2f;
		/// <summary>Keeps track of the time since the last update</summary>
		private float _updateTimer = 0;
		/// <summary>Whether or not we have started jumping</summary>
		private bool _jumped = false;
		/// <summary>Whether or not we have left the ground while performing this action</summary>
		private bool _leftGround = false;
		/// <summary>The amount of time since we have started jumping</summary>
		private float _jumpElapsed = 0;
		/// <summary>Keeps track of the last time the ball was touched</summary>
		private float _latestTouchTime = -1;
		/// <summary>When we double jump we have to let go of jump for a few frames and then hold jump for a few frames. This counts those frames</summary>
		private int _step = 0;

		/// <summary>Initializes a new double jump action, with a specific ball slice and a shot target</summary>
		public DoubleJumpShot(Car car, BallSlice slice, Vec3 shotTarget)
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

			// Predicts the ball's state after contact
			Ball ballAfterHit = Slice.ToBall();
			Vec3 carFinVel = (((init ? Slice.Location : TargetLocation) - car.Location) / timeRemaining).Cap(0, Car.MaxSpeed);
			ballAfterHit.velocity = (carFinVel * 6 + Slice.Velocity) / 7;

			// Predicts how long it will take the ball to hit the target after being hit
			Vec3 directionToScore = Slice.Location.FlatDirection(ShotTarget);
			float velocityDiff = (carFinVel - Slice.Velocity).Length();
			float timeToScore = Slice.Location.FlatDist(ShotTarget) / Utils.Cap(velocityDiff * Utils.ShotPowerModifier(velocityDiff) + ballAfterHit.velocity.Dot(directionToScore), 500, Ball.MaxSpeed);

			// Calculates the shot direction, and target location
			ballAfterHit.velocity = (carFinVel + Slice.Velocity * 2) / 3;
			ShotDirection = ballAfterHit.PredictLocation(timeToScore).Direction(ShotTarget);
			float angle = MathF.Min(MathF.Asin(ShotDirection.z), MathF.PI * 0.35f);
			ShotDirection = ShotDirection.FlatNorm() * MathF.Cos(angle) + Vec3.Up * MathF.Sin(angle);
			TargetLocation = Slice.Location - ShotDirection * 160;

			// Gets the closest surface to the target location, and get that surface's normal
			Surface surface = Field.NearestSurface(Slice.Location);
			Vec3 normal = surface.Normal;

			// if the target location is too close to the surface, change the shot direction and the target location so it is flatter against the surface
			float distFromSurface = surface.Limit(TargetLocation).Dist(TargetLocation);
			if (distFromSurface < 50)
			{
				angle = MathF.Asin(Utils.Cap((distFromSurface - 50) / 160, -1, 1));
				ShotDirection = ShotDirection.FlatNorm(normal) * MathF.Cos(angle) + normal * MathF.Sin(angle);
				TargetLocation = Slice.Location - ShotDirection * 160;
			}

			if (init)
			{
				// If this is during initialization, we need to create the arrive action
				ArriveAction = new Arrive(car, TargetLocation.Flatten(), ShotDirection.FlatNorm(), Slice.Time, true, Utils.TimeToJump(Vec3.Up, TargetLocation.z - 17, true));
				return;
			}
			// Otherwise, just update the arrive action
			ArriveAction.Target = TargetLocation.Flatten();
			ArriveAction.Direction = ShotDirection.FlatNorm();
			ArriveAction.RecoveryTime = Utils.TimeToJump(Vec3.Up, TargetLocation.z - 17, true);
		}

		/// <summary>Performs this double jump shot</summary>
		public override void Run(RUBot bot)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Updates latest touch time with the last time the ball was hit
			if (_latestTouchTime < 0 && Ball.LatestTouch != null)
				_latestTouchTime = Ball.LatestTouch.Time;

			if (!_jumped)
			{
				// Before we jump, we gotta approach the ball
				ArriveAction.Run(bot);

				// While approaching, this shot is interrutpible only if the arrive action is
				Interruptible = ArriveAction.Interruptible;
				// Check if we have left the ground
				_leftGround = _leftGround || !bot.Me.IsGrounded;

				// How much time it should take to jump up to the target height
				float timeToJump = MathF.Max(Utils.TimeToJump(Vec3.Up, TargetLocation.z - 17, true), 0.2f);
				// Assuming we drive straight to the target location, how long should it take?
				float eta = ArriveAction.Eta(bot.Me);

				_updateTimer += bot.DeltaTime;
				if (Interruptible && (timeRemaining < timeToJump - 0.05f || (_leftGround && bot.Me.IsGrounded) || !ShotValid() || bot.Me.Boost > _startBoostAmount ||
					eta > MathF.Max(timeRemaining * 1.05f, timeRemaining + 0.025f) || (eta < timeRemaining - 0.25f && bot.Me.Boost > 10 && _updateTimer > _updateInterval)))
				{
					// If this shot is no longer valid, or we think it's possible that a better shot exists, we finish this action
					Finished = true;
				}
				else if (_updateTimer > _updateInterval && timeRemaining > timeToJump)
				{
					// Updates the target location and shot direction every so often, so this shot is as accurate as possible
					SetTargetLocation(bot.Me);
					_updateTimer = 0;
				}
				else
				{
					// The location of the car at the target time if we were to double jump now
					Vec3 finPos = bot.Me.LocationAfterDoubleJump(timeRemaining, 0);

					// If we think we would hit the ball if we jump now, then jump!
					if (timeRemaining < timeToJump && finPos.FlatDist(TargetLocation) < 40 && Interruptible)
					{
						_jumped = true;
					}
				}
			}
			else
			{
				// Now that we are up in the air, we set interruptible to false, as we don't want to be interrupted while jumping
				Interruptible = false;
				_jumpElapsed += bot.DeltaTime;

				if (timeRemaining < 0 || (Ball.LatestTouch != null && _latestTouchTime != Ball.LatestTouch.Time && Ball.LatestTouch.PlayerIndex != bot.Index && Ball.Location.Dist(bot.Me.Location) > 200))
				{
					// If the target time has passed, or someone else hits the ball before us, then we stop this action
					Finished = true;
				}
				else if (_jumpElapsed < Car.JumpMaxDuration)
				{
					// Holds the jump button for the first 0.2 seconds, giving us the maximum acceleration possible by that first jump
					bot.Controller.Jump = true;
				}
				else if (_step < 3)
				{
					// Lets go of jump for 3 frames, so we can double jump
					bot.Controller.Jump = false;
					_step++;
				}
				else if (_step < 6)
				{
					// Holds jump for 3 frames, giving us the double jump
					bot.Controller.Jump = true;
					_step++;
				}
				else
				{
					// Calculates the offset between the cars predicted position and where it should be
					Vec3 finPos = bot.Me.PredictLocation(timeRemaining);
					Vec3 offset = TargetLocation - finPos;

					// Based on those values, we boost and throttle so we get as close to the target location as possible
					bot.Controller.Boost = offset.Dot(bot.Me.Forward) / timeRemaining >= (Car.BoostAccel + Car.AirThrottleAccel) * MathF.Max(bot.DeltaTime, 13f / 120f) && offset.Normalize().Dot(bot.Me.Forward) > 0.75f;
					bot.Controller.Throttle = offset.Normalize().Dot(bot.Me.Forward) > 0.5f ? 1 : 0;

					// Aim in the shot direction
					bot.AimAt(bot.Me.Location + ShotDirection);
				}
			}
		}

		/// <summary>Returns whether this double jump shot is possible</summary>
		public override bool IsValid(Car car)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Returns true if the height of the ball is not to low, or to high, and we can get there in time
			return Drive.GetEta(car, TargetLocation.Flatten()) < timeRemaining && TargetLocation.z >= 300 && TargetLocation.z < 510 && timeRemaining > Utils.TimeToJump(Vec3.Up, TargetLocation.z, true);
		}
	}
}
