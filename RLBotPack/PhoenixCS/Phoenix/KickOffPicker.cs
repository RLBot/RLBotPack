using System;
using System.Collections.Generic;
using System.Linq;
using RedUtils;
using RedUtils.Actions.KickOffs;
using RedUtils.Math;

namespace Phoenix
{
    /// <summary>
    /// A strategy helper class that picks kick offs and evaluates if they are successful or not. Based on this we
    /// update the probabilities of choosing each kick off type. 
    /// </summary>
    public class KickOffPicker
    {
        private const float EvalDuration = 15f;
        private const float DirectionalReward = 0.035f;

        /// <summary>
        /// Holds a factory to create kick off actions and their weight of how likely we are to pick this option
        /// </summary>
        class KickOffOption
        {
            public string Name;
            public float Weight;
            public readonly Func<KickOffType, IAction> Factory;

            public KickOffOption(string name, float weight, Func<KickOffType, IAction> factory)
            {
                Name = name;
                Weight = weight;
                Factory = factory;
            }
        }

        /// <summary>
        /// Our kick off options and their weight
        /// </summary>
        private Dictionary<KickOffType, List<KickOffOption>> _kickOffOptions = new()
        {
            {
                KickOffType.FarBack, new List<KickOffOption>
                {
                    new("Fake", 2f, type => new FakeKickOff(type)),
                    new("Speed", 1f, type => new SpeedKickOff(type)),
                    new("Beast", 1f, type => new BeastKickOff(type)),
                }
            },
            {
                KickOffType.BackSide, new List<KickOffOption>
                {
                    new("Speed", 1f, type => new SpeedKickOff(type)),
                    new("Beast", 1f, type => new BeastKickOff(type)),
                }
            },
            {
                KickOffType.Diagonal, new List<KickOffOption>
                {
                    new("Speed", 1f, type => new SpeedKickOff(type)),
                    new("Beast", 1f, type => new BeastKickOff(type)),
                }
            }
        };

        private KickOffOption _latest;
        private float _latestTime;
        private bool _evaluateDone;

        public IAction PickKickOffAction(RUBot bot)
        {
            // Use left-goes protocol
            Car kicker = Cars.AllCars
                .FindAll(car => car.Team == bot.Me.Team)
                .OrderBy(car => car.Location.Length() + MathF.Sign(car.Location.x * Field.Side(car.Team)))
                .FirstOrDefault();

            if (kicker != bot.Me)
            {
                _latest = null;
                // Get boost instead
                return new GetBoost(bot.Me, interruptible: false);
            }

            // Find the available options
            KickOffType spawn = KickOffs.GetKickOffTypeFromLoc(bot.Me.Location);
            List<KickOffOption> options = _kickOffOptions[spawn];

            // Roll the rng
            Random rng = new Random();
            float totalWeight = options.Select(option => option.Weight).Sum();
            float rngResult = rng.NextFloat() * totalWeight;

            // Find the hit option
            KickOffOption picked = null;
            foreach (KickOffOption option in options)
            {
                if (option.Weight >= rngResult)
                {
                    picked = option;
                    break;
                }

                rngResult -= option.Weight;
            }

            _latest = picked;
            _latestTime = Game.Time;
            _evaluateDone = false;
            return picked.Factory.Invoke(spawn);
        }

        public void Evaluate(RUBot bot)
        {
            if (_latest == null || !Game.IsRoundActive) return;

            float timePassed = Game.Time - _latestTime;
            if (timePassed >= EvalDuration) return;

            // 1 on their side, -1 on our side
            float loc11 = -Field.Side(bot.Me.Team) * 2f * Ball.Location.y / Field.Length;
            _latest.Weight *= (1f + DirectionalReward * loc11 * bot.DeltaTime * (1f - 2 * MathF.Abs(Ball.Location.x) / Field.Width));

            if (!_evaluateDone && MathF.Abs(Ball.Location.y) > Field.Length / 2f - 100 && MathF.Abs(Ball.Location.x) <= Goal.Width / 2f)
            {
                // Basically a goal
                _evaluateDone = true;
                float multiplier10 = 1f - MathF.Max( timePassed / EvalDuration, 0.20f);
                _latest.Weight *= (1f - multiplier10 * Field.Side(bot.Me.Team) * MathF.Sign(Ball.Location.y));
            }
        }

        /// <summary>Renders the current state of the KickOffPicker for debugging</summary>
        public void DrawSummary(ExtendedRenderer draw)
        {
            float x = 200;
            float y = 40;
            float dy = 18;
            float dx = 30;

            foreach (var (spawn, options) in _kickOffOptions)
            {
                draw.Text2D($"{spawn}:", new Vec3(x, y));
                y += dy;
                foreach (var option in options)
                {
                    draw.Text2D($"{option.Name}: {option.Weight}", new Vec3(x + dx, y));
                    y += dy;
                }
            }
        }
    }
}
