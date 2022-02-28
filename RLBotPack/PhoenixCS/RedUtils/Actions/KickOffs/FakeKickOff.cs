using System;
using RedUtils.Math;

namespace RedUtils.Actions.KickOffs
{
    public class FakeKickOff : IAction
    {
        /// <summary>Kickoffs aren't interruptible, so this will always be false</summary>
		public bool Interruptible
		{ get; set; }
		/// <summary>Whether or not the kickoff period has ended</summary>
		public bool Finished
		{ get; set; }

		/// <summary>A random number close to 0.5</summary>
		private float _rand1;
		/// <summary>A random number close to 0.5</summary>
		private float _rand2;

		/// <summary>The in-game time of the start of the fake</summary>
		private float _beginTime = -1f;
		
		/// <summary>Whether or not we have started moving forward</summary>
		private bool _begunMoving;

		/// <summary>Initializes a new kickoff action</summary>
		public FakeKickOff(KickOffType type)
		{
			Interruptible = false;
			Finished = false;
			if (type != KickOffType.FarBack) throw new ArgumentException("Fakes only works on FarBack kick offs");
			
			Random rng = new Random();
			_rand1 = rng.NextMiddleFloatOf3();
			_rand2 = rng.NextMiddleFloatOf3();
		}

		/// <summary>Performs this kickoff action</summary>
		public void Run(RUBot bot)
		{
			Finished = Ball.Location.x != 0 || Ball.Location.y != 0 || !Game.IsKickoffPause;
			
			if (_beginTime < 0)
			{
				// Begin fake
				_beginTime = Game.Time;
			}
			else if (_begunMoving)
			{
				// Drive forwards until someone hits the ball 
				bot.Controller.Throttle = 1f;
				Finished = Game.Time > _beginTime + 2.7f;
			}
			else if (Game.Time < _beginTime + 0.7f + _rand1 * 0.15f)
			{
				// Creep backwards
				bot.Controller.Throttle = -1f;
			}
			else if (Game.Time > _beginTime + 1.95f + _rand1 * 0.05f + _rand2 * 0.25f)
			{
				// Begin driving forwards
				_begunMoving = true;
			}
		}
    }
}
