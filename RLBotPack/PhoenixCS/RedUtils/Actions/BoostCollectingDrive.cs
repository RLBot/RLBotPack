using System;
using System.Drawing;
using System.Linq;
using RedUtils.Math;
using RLBotDotNet;

namespace RedUtils
{
    public class BoostCollectingDrive : IAction
    {
        /// <summary>Whether or not this action is finished</summary>
        public bool Finished { get; set; }

        /// <summary>Whether or not this action can be interrupted</summary>
        public bool Interruptible { get; set; }

        /// <summary>The boost pad we are going to grab next</summary>
        public Boost ChosenBoost;

        /// <summary>The boost pad we are going to grab after the next</summary>
        public Boost ChosenBoost2;

        /// <summary>The location of ChosenBoost, but shifted a bit to make the driving smoother</summary>
        private Vec3 LoosenedLocation;

        /// <summary>This action's drive subaction</summary>
        public Arrive ArriveAction;

        public readonly Vec3 FinalDestination;

        private int _tick = 0;

        /// <summary>Whether or not this action was initially set as interruptible</summary>
        private readonly bool _initiallyInterruptible;

        public BoostCollectingDrive(Car car, Vec3 finalDestination, bool interruptible = true)
        {
            FinalDestination = finalDestination;
            _initiallyInterruptible = interruptible;

            ArriveAction = new Arrive(car, finalDestination);
        }

        public void Run(RUBot bot)
        {
            float distToTarget = bot.Me.Location.Dist(FinalDestination);

            _tick++;
            if (_tick >= 20 || (ChosenBoost != null && ChosenBoost.TimeUntilActive >= 2.8f))
            {
                _tick = 0;
                
                var prevBoost1 = ChosenBoost;
                var prevBoost2 = ChosenBoost2;

                if (bot.Me.Velocity.Dot(bot.Me.Location.Direction(FinalDestination)) < 400)
                {
                    // Some speed towards the final destination is required before we consider picking up boosts
                    ChosenBoost = null;
                    ChosenBoost2 = null;
                }
                else
                {
                    // Repick boost
                    ChosenBoost = Field.Boosts.FindAll(boost =>
                        {
                            float distToBoost = boost.Location.Dist(bot.Me.Location);
                            return (boost.IsActive || distToBoost / boost.TimeUntilActive > bot.Me.Velocity.Length()) &&
                                   distToBoost + boost.Location.Dist(FinalDestination) < 1.2f * distToTarget &&
                                   boost.Location.Dist(FinalDestination) < distToTarget - 100;
                        })
                        .OrderBy(boost => (boost == prevBoost1 ? 0.8 : 1.0) * (
                            1.2f * boost.Location.Dist(bot.Me.Location) +
                            1.0f * boost.Location.Dist(FinalDestination) +
                            1.0f * MathF.Abs(bot.Me.Right.Dot(boost.Location - bot.Me.Location))))
                        .FirstOrDefault();

                    if (ChosenBoost == null) ChosenBoost2 = null;
                    else
                    {
                        ChosenBoost2 = Field.Boosts.FindAll(boost =>
                            {
                                float boostToBoostDist = boost.Location.Dist(ChosenBoost.Location);
                                return boost != ChosenBoost &&
                                       (boost.IsActive ||
                                        (ChosenBoost.Location.Dist(bot.Me.Location) + boostToBoostDist) /
                                        boost.TimeUntilActive > bot.Me.Velocity.Length()) &&
                                       boostToBoostDist + boost.Location.Dist(FinalDestination) < 1.2f * distToTarget &&
                                       boost.Location.Dist(FinalDestination) < distToTarget - 100;
                            })
                            .OrderBy(boost => (ChosenBoost == prevBoost1 && boost == prevBoost2 ? 0.9 : 1.0) * (
                                1.2f * boost.Location.Dist(ChosenBoost.Location) +
                                1.0f * boost.Location.Dist(FinalDestination) +
                                1.1f * MathF.Abs(ChosenBoost.Location.Direction(FinalDestination)
                                    .Rotate(MathF.PI / 2f).Dot(boost.Location - bot.Me.Location))))
                            .FirstOrDefault();
                    }
                }

                // Update Drive sub action
                if (ChosenBoost != prevBoost1 || ChosenBoost2 != prevBoost2)
                {
                    if (ChosenBoost == null)
                    {
                        LoosenedLocation = FinalDestination;
                    }
                    else
                    {
                        Vec3 loc2 = ChosenBoost2?.Location ?? FinalDestination;
                        Vec3 looseDir = ((bot.Me.Location - ChosenBoost.Location) + (loc2 - ChosenBoost.Location)).Normalize();
                        LoosenedLocation = ChosenBoost.Location + looseDir * 110; // Radius of small pads are 144
                    }
                    
                    ArriveAction.Target = LoosenedLocation;
                    ArriveAction.Direction = ChosenBoost2 != null
                        ? Utils.Lerp(0.9f, bot.Me.Forward, bot.Me.Location.Direction(ChosenBoost2.Location - 100 * ChosenBoost2.Location.Direction(FinalDestination))).FlatNorm()
                        : Utils.Lerp(0.9f, bot.Me.Forward, bot.Me.Location.Direction(FinalDestination)).FlatNorm();
                }
                ArriveAction.Drive.WasteBoost = bot.Me.Velocity.Length() < MathF.Min(distToTarget / 4, 1400);
            }

            if (ChosenBoost != null)
            {
                bot.Renderer.Line3D(bot.Me.Location, LoosenedLocation.WithZ(20f), Color.GreenYellow);
                bot.Renderer.Line3D(LoosenedLocation.WithZ(20f), ChosenBoost.Location.WithZ(20f), Color.Green);
            }
            if (ChosenBoost != null && ChosenBoost2 != null)
                bot.Renderer.Line3D(LoosenedLocation.WithZ(20f), ChosenBoost2.Location.WithZ(20f),
                    Color.GreenYellow);

            ArriveAction.Run(bot);

            Interruptible = _initiallyInterruptible && ArriveAction.Interruptible;
            Finished = bot.Me.Boost > 65 || bot.Me.Location.Dist(FinalDestination) < 100;
        }
    }
}
