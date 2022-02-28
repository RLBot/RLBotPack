using System;
using System.Linq;
using RedUtils.Math;

namespace RedUtils.Actions.KickOffs
{
    public class BeastKickOff : IAction
    {
        private const float DODGE_DIST = 250f;
        private const float MIDDLE_OFFSET = 430f;

        /// <summary>Kickoffs aren't interruptible, so this will always be false</summary>
        public bool Interruptible
        { get; set; } = false;
        /// <summary>Whether or not the kickoff period has ended</summary>
        public bool Finished
        { get; set; } = false;

        /// <summary>Which type of kickoff spawn location it is</summary>
        private readonly KickOffType _type;

        private Dodge _dodge = null;
        private Drive _drive = null;

        public BeastKickOff(KickOffType type)
        {
            _type = type;
        }

        public void Run(RUBot bot)
        {
            // Resolve dodge
            if (_dodge != null && !_dodge.Finished)
            {
                _dodge.Run(bot);
                return;
            }
            _dodge = null;

            Vec3 myLoc = bot.Me.Location;
            float dist = myLoc.Length();
            float velTowardsBall = bot.Me.Velocity.Dot(-myLoc.Normalize());

            // Kick off parameters
            Vec3 target = new Vec3(0, Field.Side(bot.Me.Team) * (dist / 2.6f - MIDDLE_OFFSET), 0);
            float speed = 2300;

            // Does the opponent go for a kick off?
            Car closestOpponent = Cars.AllCars
                .FindAll(car => car.Team != bot.Me.Team)
                .OrderBy(car => car.Location.Length())
                .FirstOrDefault();
            bool oppPerformsKick = closestOpponent != null && closestOpponent.Location.Length() < dist + 600;

            // If not, adjust parameters
            if (!oppPerformsKick)
            {
                speed = 2210;
                target = new Vec3(35f * MathF.Sign(myLoc.x), Field.Side(bot.Me.Team) * (dist / 2.05f - MIDDLE_OFFSET), 0);
            }
            
            if (dist - DODGE_DIST < velTowardsBall * 0.3f && oppPerformsKick)
            {
                // Dodge when close to ball - but only if the opponent also goes for kick off
                _dodge = new Dodge(myLoc.Direction(target));
            }
            else if (dist > 3640 && velTowardsBall > 1200 && !oppPerformsKick)
            {
                // Make two dodges when spawning far back
                _dodge = new Dodge(myLoc.Direction(target));
            }
            else if (MathF.Abs(myLoc.x) > 180 && MathF.Abs(myLoc.y) > 2780)
            {
                // Pick up boost when spawning back right/left by driving a bot towards the middle boost pad first
                target.y = Field.Side(bot.Me.Team) * 2790;
            }
            
            // Drive
            if (_drive == null)
                _drive = new Drive(bot.Me, target, speed, false, true);
            else
            {
                _drive.Target = target;
                _drive.TargetSpeed = speed;
            }
            _drive.Run(bot);
            
            Finished = Ball.Location.x != 0 || Ball.Location.y != 0 || !Game.IsKickoffPause;
        }
    }
}
