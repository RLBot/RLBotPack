using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A dodge/flip action</summary>
	public class Dodge : IAction
	{
		/// <summary>Whether or not we have finished flipping/dodging</summary>
		public bool Finished { get; private set; }
		/// <summary>Dodges aren't interruptible, so this will always be false</summary>
		public bool Interruptible { get; private set; }

		/// <summary>The direction we want to dodge in</summary>
		public Vec3 Direction { get; set; }
		/// <summary>How much time we spend jumping before dodging, if we start on the ground</summary>
		public float JumpTime { get; set; }
		/// <summary>How long this dodge should last</summary>
		public float Duration { get { return JumpTime + 1.15f; } }

		/// <summary>Whether or not we are going to jump before dodging</summary>
		private bool _jumping = true;
		/// <summary>When we started this action</summary>
		private float _startTime = -1;
		/// <summary>The inputs for the dodge direction</summary>
		private Vec3 _input = Vec3.Zero;
		/// <summary>When we dodge we have to let go of jump for a few frames. This counts those frames/summary>
		private int _step = 0;

		/// <summary>Initialize a new dodge action</summary>
		/// <param name="jumpTime">How much time we spend jumping before dodging, if we start on the ground</param>
		public Dodge(Vec3 direction, float jumpTime = 0.1f)
		{
			Interruptible = false;
			Finished = false;

			Direction = direction;
			JumpTime = jumpTime;
		}

		/// <summary>Runs this dodge action</summary>
		public void Run(RUBot bot)
		{
			// If this action hasn't started yet
			if (_startTime == -1)
			{
				// Set start time, and whether or not we should jump
				_startTime = Game.Time;
				_jumping = bot.Me.IsGrounded;
			}
			float elapsed = Game.Time - _startTime;

			if (bot.Me.IsGrounded && elapsed > (_jumping ? JumpTime : 0) + 0.1f)
			{
				// If we have landed too soon, stop this action
				Finished = true;
			}
			else if (elapsed < JumpTime && _jumping)
			{
				// If we should still be jumping, jump
				bot.Controller.Jump = true;
			}
			else if (_step < 3 && _jumping)
			{
				// Release jump for a few frames, after jumping
				bot.Controller.Jump = false;
				_step++;
			}
			else if (elapsed < (_jumping ? JumpTime : 0) + 0.6f)
			{
				// If the directional input hasn't been set
				if (_input.Length() == 0)
				{
					// Find the local direction
					Vec3 localDirection = new Vec3(-bot.Me.Forward.FlatNorm().Cross().Dot(Direction), -bot.Me.Forward.FlatNorm().Dot(Direction));

					// Calculates some special values that we need to know for getting the correct input
					float forwardVel = bot.Me.Forward.Dot(bot.Me.Velocity);
					float s = MathF.Abs(forwardVel) / Car.MaxSpeed;
					bool backwardsDodge = MathF.Abs(forwardVel) < 100 ? (localDirection[0] < 0) : (localDirection[0] >= 0) != (forwardVel > 0);

					// Manipulate the local direction by some special values, so we are dodging in the right direction
					localDirection[0] /= backwardsDodge ? (16f / 15f) * (1 + 1.5f * s) : 1;
					localDirection[1] /= (1 + 0.9f * s);

					localDirection = localDirection.Normalize();

					// Sets the input
					_input = localDirection;
				}

				// Dodges in the specified direction
				bot.Controller.Yaw = _input[0];
				bot.Controller.Pitch = _input[1];
				bot.Controller.Jump = true;
			}
			else
			{
				// Finish the action after dodging
				Finished = true;
			}
		}
	}
}
