using System;
using RedUtils.Math;

namespace RedUtils
{
    /// <summary>An action that will attempt to hit the ball towards a given target
    /// <para>This action doesn't use ball prediction, so it's very imprecise</para>
    /// </summary>
	public class QuickShot : IAction
	{
        /// <summary>Whether or not this action has finished</summary>
        public bool Finished { get; private set; }
        /// <summary>Whether or not this action can be interrupted</summary>
        public bool Interruptible { get; private set; }

        /// <summary>The location we're going to shoot at</summary>
        public Vec3 Target;
        /// <summary>This action's arrive sub action, which will take us to the ball</summary>
        public Arrive ArriveAction;

        /// <summary>Keeps track of the last time the ball was touched</summary>
        private float _latestTouchTime = -1;

        /// <summary>Initializes a new quick shot</summary>
        public QuickShot(Car car, Vec3 target)
        {
            Interruptible = true;

            Target = target;
            ArriveAction = new Arrive(car, target, car.Location.Direction(target));
        }

        /// <summary>Performs this quick shot</summary>
		public void Run(RUBot bot)
		{
            // Updates latest touch time with the last time the ball was hit
            if (_latestTouchTime < 0 && Ball.LatestTouch != null)
                _latestTouchTime = Ball.LatestTouch.Time;

            // Calculates the direction we should shoot in
            Vec3 shotDirection = Ball.Location.Direction(Target);
            // Gets the normal of the surface closest to the ball
            Vec3 surfaceNormal = Field.NearestSurface(Ball.Location).Normal;

            // Updates and runs the arrive action
            ArriveAction.Target = Ball.Location;
            ArriveAction.Direction = shotDirection;
            ArriveAction.Run(bot);

            // This action is only interruptible when the arrive action is
            Interruptible = ArriveAction.Interruptible;
            if (Interruptible && Ball.LatestTouch != null && _latestTouchTime != Ball.LatestTouch.Time && Ball.LatestTouch.PlayerIndex == bot.Index)
            {
                // If we have hit the ball, finish this action
                Finished = true;
            }
            else if ((ArriveAction.TimeRemaining < 0.2f || bot.Me.Location.Dist(Ball.Location) < 300) && Interruptible)
            {
                // When we are close enough, dodge into the ball
                bot.Action = new Dodge(bot.Me.Location.FlatDirection(Ball.Location, surfaceNormal));
            }
        }
	}
}
