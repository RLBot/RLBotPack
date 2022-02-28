using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A half-flip action, meant to turn the car around with a canceled back-flip</summary>
	public class HalfFlip : IAction
	{
		/// <summary>The duration of a half-flip</summary>
		public const float Duration = 1.25f;

		/// <summary>Whether or not the half-flip has benn completed</summary>
		public bool Finished { get; private set; }
		/// <summary>Half-flips aren't interruptible, so this will always be false</summary>
		public bool Interruptible { get; private set; }

		/// <summary>Whether or not we are going to jump before half-flipping</summary>
		private bool _jumping = true;
		/// <summary>When we started this action</summary>
		private float _startTime = -1;
		/// <summary>When we half-flip we have to let go of jump for a few frames. This counts those frames</summary>
		private int _step = 0;

		/// <summary>Initializes a new half-flip action</summary>
		public HalfFlip()
		{
			Interruptible = false;
			Finished = false;
		}

		/// <summary>Performs a half-flip</summary>
		public void Run(RUBot bot)
		{
			// If this is the first time this action is running, initialize some variables
			if (_startTime == -1)
			{
				_startTime = Game.Time;
				_jumping = bot.Me.IsGrounded; // We will only jump if we are currently on the ground
			}
			float elapsed = Game.Time - _startTime;

			if (elapsed < 0.1f && _jumping)
			{
				// Jumps for .1 seconds
				bot.Controller.Jump = true;
			}
			else if (_step < 3 && _jumping)
			{
				// Releases jump 3 frames, so we can dodge properly
				bot.Controller.Jump = false;
				_step++;
			}
			else if (elapsed < (_jumping ? 0.1f : 0) + 0.2f)
			{
				// Dodges backwards
				bot.Controller.Yaw = 0;
				bot.Controller.Pitch = 1;
				bot.Controller.Jump = true;
			}
			else if (elapsed < (_jumping ? 0.1f : 0) + 1f)
			{
				// Cancels the flip, and twists to face the corrent direction
				bot.AimAt(bot.Me.Location + bot.Me.Velocity.Flatten());
			}
			else
			{
				// After that, finish the action
				Finished = true;
			}
		}
	}
}
