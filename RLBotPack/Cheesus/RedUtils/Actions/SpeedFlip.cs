using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A speed-flip action, where the car turns slightly, then diagonal dodges and then cancels the dodge for maximum speed</summary>
	class SpeedFlip : IAction
	{
		/// <summary>The avergae duration of a speed-flip</summary>
		public const float Duration = 1.35f;

		/// <summary>Speed-flips aren't interruptible, so this will always be false</summary>
		public bool Interruptible
		{ get; set; }
		/// <summary>Whether or not we have finished this speedflip</summary>
		public bool Finished
		{ get; set; }

		/// <summary>The direction we plan to speed-flip in</summary>
		public Vec3 Direction;

		/// <summary>When we started this action</summary>
		private float _startTime = -1;
		/// <summary>The side we are going to dodge in. 1 for right, -1 for left</summary>
		private int _side;

		/// <summary>Initializes a new speed-flip</summary>
		public SpeedFlip(Vec3 direction)
		{
			Interruptible = false;
			Finished = false;
			Direction = direction.Normalize();
		}

		/// <summary>Performs a speed-flip</summary>
		public void Run(RUBot bot)
		{
			// During the entire flip, hold down the throttle
			// Note that we don't hold down boost the entire time. We could, but instead we allow any action using this as a subaction to control when we boost
			bot.Controller.Throttle = 1;

			if (_startTime < 0)
			{
				// During the first frame, calculate the angle we need to turn before dodging
				float angle = 0.06f * bot.Me.Velocity.Dot(bot.Me.Forward) / Drive.TurnRadius(bot.Me.Velocity.Dot(bot.Me.Forward));
				// Generate a left and right vector rotated by that angle for us to aim at
				Vec3 leftVec = Direction.Rotate(angle).Flatten().Normalize();
				Vec3 rightVec = Direction.Rotate(-angle).Flatten().Normalize();

				if (bot.Me.Velocity.Angle(leftVec) < bot.Me.Velocity.Angle(rightVec))
				{
					// If we start to the left of the direction, angle to the left
					bot.AimAt(bot.Me.Location + leftVec);

					if (bot.Me.Velocity.FlatAngle(leftVec) < 0.05f)
					{
						// When we are driving in the right direction, start the flip
						_startTime = Game.Time;
						_side = 1; // Tells us to flip to the right
					}
				}
				else
				{
					// If we start to the right of the direction, angle to the right
					bot.AimAt(bot.Me.Location + rightVec);

					if (bot.Me.Velocity.FlatAngle(rightVec) < 0.05f)
					{
						// When we are driving in the right direction, start the flip
						_startTime = Game.Time;
						_side = -1; // Tells us to flip to the left
					}
				}
			}
			else
			{
				float elapsed = Game.Time - _startTime;

				if (0 < elapsed && elapsed < .1)
				{
					// During the first .1 seconds, jump
					bot.Controller.Jump = true;
				}
				else if (.12 < elapsed && elapsed < .15)
				{
					// After waiting .02 seconds, dodge in the specified direction
					bot.Controller.Jump = true;
					bot.Controller.Pitch = -1;
					bot.Controller.Roll = _side * 0.5f;
				}
				else if (.15 < elapsed && elapsed < .75)
				{
					// Cancel the forward part of the dodge, and continue air rolling
					bot.Controller.Pitch = 1;
					bot.Controller.Roll = _side;
				}
				else if (.75 < elapsed && elapsed < 0.9)
				{
					// Land safely on the ground by turning slightly and holding drift
					bot.Controller.Pitch = 1;
					bot.Controller.Handbrake = true;
					bot.Controller.Roll = _side;
					bot.Controller.Yaw = _side;
				}
				else if (0.9 < elapsed)
				{
					// Finish the speed-flip
					Finished = true;
				}
			}

			// If we are too close to the wall, or are airborne too early, finish this action
			if (!Field.InField(bot.Me.Location, 150) || (_startTime < 0 && !bot.Me.IsGrounded))
			{
				Finished = true;
			}
		}
	}
}
