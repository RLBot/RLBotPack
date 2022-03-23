using System;
using System.Timers;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>An aerial shot action, where the car flys into the ball</summary>
	public class AerialShot : Shot
	{
		/// <summary>Whether or not this aerial has finished</summary>
		public override bool Finished { get; internal set; }
		/// <summary>Whether or not this aerial can be interrupted</summary>
		public override bool Interruptible { get; internal set; }

		/// <summary>The future ball state at which time we are planning to hit the aerial</summary>
		public override BallSlice Slice { get; internal set; }
		/// <summary>The exact position we will hit the ball towards</summary>
		public override Vec3 ShotTarget { get; internal set; }
		/// <summary>The final position of the car at the point of collision</summary>
		public override Vec3 TargetLocation { get; internal set; }
		/// <summary>The direction from the car to the ball at the point of collision</summary>
		public override Vec3 ShotDirection { get; internal set; }

		/// <summary>The location to drive to</summary>
		public Vec3 DriveLocation { get; internal set; }
		/// <summary>The drive sub action</summary>
		public Drive DriveAction { get; internal set; }
		/// <summary>Whether or not we are going to do a double jump aerial</summary>
		public bool DoubleJumping { get; internal set; }

		/// <summary>Whether or not we should jump immediatly or turn and then jump</summary>
		private readonly bool _jumpImmediatly = false;
		/// <summary>The amount of boost we have when starting this action</summary>
		private readonly int _startBoostAmount = 0;
		/// <summary>Whether or not the car is currently double jumping</summary>
		private bool _currentlyDoubleJumping = false;
		/// <summary>Whether or not the car is no longer turning to face the target</summary>
		private bool _aerialing = false;
		/// <summary>Whether or not we have finished launching for the aerial</summary>
		private bool _jumped = false;
		/// <summary>The amount of time that has passed since the start of the aerial</summary>
		private float _elapsedTime = 0;
		/// <summary>If we need to double jump we have to let go of jump for a few frames and then hold jump for a few frames. This counts those frames/summary>
		private int _step = 0;

		/// <summary>Initializes a new aerial shot, with a specific ball slice and a shot target</summary>
		public AerialShot(Car car, BallSlice slice, Vec3 shotTarget)
		{
			// Initializes some default values
			Finished = false;
			Interruptible = true;

			Slice = slice;
			ShotTarget = shotTarget;
			_startBoostAmount = car.Boost;

			// Sets the target location and shot direction such that we hit the ball towards our target
			SetTargetLocation(car);

			// Figures out whether or not the car should jump immediatly, or wait until the car faces the target
			_jumpImmediatly = car.Velocity.FlatAngle(car.Location.Direction(TargetLocation), car.Up) < 0.6f || car.Velocity.FlatLen(car.Up) < 500 || !car.IsGrounded;

			// Sets up the drive location and action
			DriveLocation = Drive.GetEta(car, TargetLocation.Flatten(), false) <= Drive.GetEta(car, TargetLocation, false) ? TargetLocation.Flatten() : TargetLocation;
			DriveAction = new Drive(car, DriveLocation, Drive.GetDistance(car, DriveLocation) / (Slice.Time - Game.Time));
		}

		/// <summary>Sets the target location and the shot direction based on the velocity of the ball and other factors</summary>
		private void SetTargetLocation(Car car)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			// Predicts the ball's state after contact
			Ball ballAfterHit = Slice.ToBall();
			Vec3 carFinVel = ((Slice.Location - car.Location) / timeRemaining).Cap(0, Car.MaxSpeed);
			ballAfterHit.velocity = (carFinVel * 6 + Slice.Velocity) / 7;

			// Predicts how long it will take the ball to hit the target after being hit
			Vec3 directionToScore = Slice.Location.FlatDirection(ShotTarget);
			float velocityDiff = (carFinVel - Slice.Velocity).Length();
			float timeToScore = Slice.Location.FlatDist(ShotTarget) / Utils.Cap(velocityDiff * Utils.ShotPowerModifier(velocityDiff) + ballAfterHit.velocity.Dot(directionToScore), 500, Ball.MaxSpeed);

			// Calculates the shot direction, and target location
			ballAfterHit.velocity = (carFinVel + Slice.Velocity * 2) / 3;
			ShotDirection = ballAfterHit.PredictLocation(timeToScore).Direction(ShotTarget);
			TargetLocation = Slice.Location - ShotDirection * 155;

			// Gets the surface normal, for the closest surface to the target location
			Vec3 normal = Field.NearestSurface(TargetLocation).Normal;

			// if the target location is too close to the wall, change the shot direction and the target location so it is flatter against the wall
			float distFromSurface = (TargetLocation - Field.LimitToNearestSurface(TargetLocation)).Dot(normal);
			if (distFromSurface < 50)
			{
				float angle = MathF.Asin(Utils.Cap((distFromSurface - 50) / 155, -1, 1));
				ShotDirection = (ShotDirection.FlatNorm(normal) * MathF.Cos(angle) + normal * MathF.Sin(angle)).Normalize();
				TargetLocation = Slice.Location - ShotDirection * 155;
			}
		}

		/// <summary>Perfoms this aerial</summary>
		public override void Run(RUBot bot)
		{
			// How much time until we should hit the ball
			float timeRemaining = Slice.Time - Game.Time;

			if (!_aerialing)
			{
				// When we aren't aerialing, just drive towards the ball
				DriveAction.TargetSpeed = Drive.GetDistance(bot.Me, DriveLocation) / timeRemaining;
				DriveAction.Run(bot);

				// If we don't have boost, or we pick up boost, OR the shot isn't valid, stop the shot
				if (_startBoostAmount < bot.Me.Boost || bot.Me.Boost == 0 || !ShotValid())
				{
					Finished = true;
				}
				else if (_jumpImmediatly || MathF.Abs(bot.Controller.Steer) < 0.2f)
				{
					// Once we are ready to aerial, let's check if we even can
					if (CanHit(bot.Me, out bool doubleJumping))
					{
						// If we can, then we set _aerialing to true, and set DoubleJumping to the out variable through CanHit
						DoubleJumping = doubleJumping;
						_aerialing = true;
					}
					else
					{
						// Otherwise, we stop this aerial
						Finished = true;
					}
				}
			}
			else
			{
				// Now that we are up in the air, we set interruptible to false, as we don't want to be interrupted while aerialing
				Interruptible = false;
				_elapsedTime += bot.DeltaTime;
				_currentlyDoubleJumping = false;

				if (!_jumped)
				{
					if (_elapsedTime <= Car.JumpMaxDuration)
					{
						// Holds the jump button for the first 0.2 seconds, giving us the maximum acceleration possible by that first jump
						bot.Controller.Jump = true;
					}
					else if (_step < 3 && DoubleJumping)
					{
						// Lets go of jump for 3 frames, if we are trying to double jump
						bot.Controller.Jump = false;
						_step++;
					}
					else if (_step < 6 && DoubleJumping)
					{
						// Holds jump for 3 frames, giving us the double jump
						bot.Controller.Jump = true;
						_currentlyDoubleJumping = true;
						_step++;
					}
					else
					{
						// We've finished jumping!
						_jumped = true;
					}
				}

				// The final position of the car at the moment when it should be hitting the ball
				Vec3 finPos = _jumped ? bot.Me.PredictLocation(timeRemaining) : (DoubleJumping ? bot.Me.LocationAfterDoubleJump(timeRemaining, _elapsedTime) : bot.Me.LocationAfterJump(timeRemaining, _elapsedTime));
				// The offset between where the car should be at the time of collision, and where it actually will be
				Vec3 offset = TargetLocation - finPos;
				// The acceleration required to reach the target location in time
				float requiredAccel = 2 * offset.Length() / MathF.Pow(timeRemaining, 2);

				bot.AimAt(bot.Me.Location + offset, _jumped ? bot.Me.Location.Direction(Slice.Location) : Vec3.Up);

				// Boosts and throttles when neccesary
				bot.Controller.Boost = offset.Dot(bot.Me.Forward) / timeRemaining >= (Car.BoostAccel + Car.AirThrottleAccel) * MathF.Max(bot.DeltaTime, 13f / 120f) && offset.Angle(bot.Me.Forward) < 0.4f;
				bot.Controller.Throttle = Utils.Cap(offset.Dot(bot.Me.Forward) / timeRemaining / (Car.AirThrottleAccel * MathF.Max(bot.DeltaTime, 1f / 120f)), -1, 1);

				// If we are currently double jumping, let go of all direction keys so we don't flip on accident
				if (_currentlyDoubleJumping)
				{
					bot.Controller.Steer = 0;
					bot.Controller.Yaw = 0;
					bot.Controller.Pitch = 0;
					bot.Controller.Roll = 0;
				}

				// If the aerial is finished, or is no longer possible, stop it
				if (timeRemaining <= 0f || (_jumped && offset.Length() > 50 && timeRemaining > 0.5f && requiredAccel * 0.8f > Car.AirThrottleAccel && (bot.Me.Boost == 0 || requiredAccel * 0.8f > (Car.BoostAccel + Car.AirThrottleAccel))) || (!ShotValid() && timeRemaining > 0.5f) || (bot.Me.IsGrounded && _jumped))
				{
					Finished = true;
				}
				else if (((!DoubleJumping && _elapsedTime < 1.45f) || (!bot.Me.HasJumped && _jumped)) && timeRemaining < 0.1f && offset.Length() < 100)
				{
					// If it's possible to dodge before hitting the ball, why not do it?
					bot.Action = new Dodge(ShotDirection.FlatNorm(), 0.1f);
				}
				else if (offset.Length() < 50 && !_currentlyDoubleJumping)
				{
					// When we are about to hit the ball, face in the shot direction
					bot.AimAt(bot.Me.Location + ShotDirection, bot.Me.Location.Direction(Slice.Location));
				}
			}
		}

		/// <summary>Returns whether this aerial is possible</summary>
		public override bool IsValid(Car car)
		{
			// if the car is grounded, check if we should turn to face the ball before aerialing
			bool jumpImmediatly = CanHit(car) && _jumpImmediatly;
			bool shouldTurn = car.IsGrounded;
			if (shouldTurn)
			{
				Car carAfterTurn = new Car(car);
				Drive.GetDistance(car, DriveLocation, DriveAction.Backwards, out float angle, out float radius);

				Vec3 normal = Field.NearestSurface(car.Location).Normal;
				Vec3 driveDirection = car.Forward.FlatNorm(normal) * (DriveAction.Backwards ? -1 : 1);
				Vec3 turnSide = car.Right.FlatNorm(normal) * MathF.Sign(car.Right.Dot(DriveLocation - car.Location));

				// Predicts the car's location, orientation, and velocity after turning
				carAfterTurn.Location = car.Location + turnSide * radius * (1 - MathF.Cos(angle)) + driveDirection * MathF.Sin(angle);
				carAfterTurn.Forward = carAfterTurn.Location.FlatDirection(DriveLocation, normal);
				carAfterTurn.Up = normal;
				carAfterTurn.Velocity = carAfterTurn.Forward * Drive.SpeedAfterTurn(car.Velocity.Length(), angle, DriveAction.Backwards ? 0.8f : 1);

				shouldTurn = CanHit(carAfterTurn) && !_jumpImmediatly;
			}

			// Returns true if the target is high enough, and we can get to the ball, either by turning first or jumping immediatly
			return TargetLocation.z > 300 && (jumpImmediatly || shouldTurn);
		}

		/// <summary>Whether or not this aerial is possible</summary>
		private bool CanHit(Car car)
		{
			float jumpBoostEstimate = GetBoostEstimate(car, false);
			float doubleJumpBoostEstimate = GetBoostEstimate(car, true);

			return jumpBoostEstimate >= 0 || doubleJumpBoostEstimate >= 0;
		}

		/// <summary>Whether or not this aerial is possible</summary>
		/// <param name="doubleJumping">Whether or not we should double jump</param>
		private bool CanHit(Car car, out bool doubleJumping)
		{
			float jumpBoostEstimate = GetBoostEstimate(car, false);
			float doubleJumpBoostEstimate = GetBoostEstimate(car, true);

			doubleJumping = doubleJumpBoostEstimate >= 0 && (doubleJumpBoostEstimate < jumpBoostEstimate || jumpBoostEstimate < 0);

			return jumpBoostEstimate >= 0 || doubleJumpBoostEstimate >= 0;
		}

		/// <summary>Returns an estimate for how much boost an aerial takes (returns -1 if the aerial isn't possible)</summary>
		private float GetBoostEstimate(Car car, bool doubleJumping)
		{
			float timeRemaining = Slice.Time - Game.Time;

			Vec3 finPos = car.IsGrounded ? (doubleJumping ? car.LocationAfterDoubleJump(timeRemaining, 0) : car.LocationAfterJump(timeRemaining, 0)) : car.PredictLocation(timeRemaining);
			Vec3 finVel = car.IsGrounded ? (doubleJumping ? car.VelocityAfterDoubleJump(timeRemaining, 0) : car.VelocityAfterJump(timeRemaining, 0)) : car.PredictVelocity(timeRemaining);

			Vec3 deltaX = TargetLocation - finPos;
			Vec3 direction = deltaX.Normalize();
			float angle = direction.Angle(car.Forward);
			angle = Utils.Cap(angle, 0.0001f, angle);
			float turnTime = 0.6f * (2 * MathF.Sqrt(angle / 9));

			float tau1 = turnTime * Utils.Cap(1 - 0.4f / angle, 0, 1);
			float requiredAccel = 2 * deltaX.Length() / MathF.Pow(timeRemaining - tau1, 2);
			float ratio = requiredAccel / (Car.BoostAccel + Car.AirThrottleAccel);
			float tau2 = timeRemaining - (timeRemaining - tau1) * MathF.Sqrt(1 - Utils.Cap(ratio, 0, 1));
			Vec3 velocityEstimate = finVel + (Car.BoostAccel + Car.AirThrottleAccel) * (tau2 - tau1) * direction;
			float boostEstimate = (tau2 - tau1) * Car.BoostConsumption;
			bool enoughBoost = boostEstimate < car.Boost * 0.9f;
			bool enoughTime = MathF.Abs(ratio) < 0.9f;

			return (velocityEstimate.Length() < Car.MaxSpeed * 0.9f && enoughBoost && enoughTime) ? boostEstimate : -1;
		}
	}
}
