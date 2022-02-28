using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A wavedash action</summary>
	public class Wavedash : IAction
	{
		/// <summary>Whether or not this action has finished</summary>
		public bool Finished { get; private set; }
		/// <summary>Wavedashes aren't interruptible, so this will always be false</summary>
		public bool Interruptible { get; private set; }

		/// <summary>The direction we plan to wavedash in</summary>
		public Vec3 Direction;
		/// <summary>How much time we spend jumping, if we start on the ground</summary>
		public float JumpTime;
		/// <summary>The total duration of the wavedash</summary>
		public float Duration { get { return JumpTime * 4 + 0.8f; } }

		/// <summary>Whether or not we are going to jump</summary>
		private bool _jumping = true;
		/// <summary>When we started this action</summary>
		private float _startTime = -1;
		/// <summary>The inputs for the dodge direction</summary>
		private Vec3 _input = Vec3.Zero;

		/// <summary>Initialize a new wavedash action</summary>
		/// <param name="direction">The direction which we will attempt to dash in.
		/// If null, we will dash in the direction we are already going.</param>
		/// <param name="jumpTime">How much time we spend jumping before dodging, if we start on the ground</param>
		public Wavedash(Vec3? direction = null, float jumpTime = 0.05f)
		{
			Interruptible = false;
			Finished = false;

			Direction = direction ?? Vec3.Zero;
			JumpTime = jumpTime;
		}

		/// <summary>Runs this wavedash action</summary>
		public void Run(RUBot bot)
		{
			// If this action hasn't started yet
			if (_startTime == -1)
			{
				// Set the start time, and whether or not we should jump
				_startTime = Game.Time;
				_jumping = bot.Me.IsGrounded;
			}
			float elapsed = Game.Time - _startTime;

			// If we should be jumping, jump
			if (elapsed < JumpTime && _jumping)
			{
				bot.Controller.Jump = true;
			}
			else if (!bot.Me.IsGrounded && bot.Me.Location.z < 40 && bot.Me.Velocity.z < -100)
			{
				// If we are about to hit the ground, dodge!
				if (_input.Length() == 0)
				{
					// If the input hasn't been set, set the input according to the given direction. If no direction is given, just dodge forward
					_input = Direction.Length() > 0 ?
							new Vec3(bot.Me.Local(Direction)[1], -bot.Me.Local(Direction)[0]) :
							new Vec3(bot.Me.Local(bot.Me.Velocity).Normalize()[1], -bot.Me.Local(bot.Me.Velocity).Normalize()[0]);
				}

				// Dodges using the input set earlier
				bot.Controller.Yaw = _input[0];
				bot.Controller.Pitch = _input[1];
				bot.Controller.Jump = true;
			}
			else if (!bot.Me.IsGrounded)
			{
				// Aim slightly above the ground, in the direction given
				Vec3 landingNormal = Field.FindLandingSurface(bot.Me).Normal;
				bot.AimAt(bot.Me.Location + (Direction.Length() > 0 ? Direction.FlatNorm(landingNormal) : bot.Me.Velocity.FlatNorm(landingNormal)) + landingNormal * 0.2f, landingNormal);
			}
			else
			{
				Finished = true;
			}
		}
	}
}
