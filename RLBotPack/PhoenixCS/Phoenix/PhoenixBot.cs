using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using RedUtils;
using RedUtils.Math;

/* 
 * This is the main file. It contains your bot class. Feel free to change the name!
 * An instance of this class will be created for each instance of your bot in the game.
 * Your bot derives from the "RedUtilsBot" class, contained in the Bot file inside the RedUtils project.
 * The run function listed below runs every tick, and should contain the custom strategy code (made by you!)
 * Right now though, it has a default ball chase strategy. Feel free to read up and use anything you like for your own strategy.
*/
namespace Phoenix
{
    // Your bot class! :D
    public class PhoenixBot : RUBot
    {
        private KickOffPicker _kickOffPicker = new KickOffPicker();
        private DribbleDetector _dribbleDetector = new DribbleDetector();

        public List<ITargetFactory> WallReflectTargetFactories { get; }
        
        public PhoenixBot(string botName, int botTeam, int botIndex) : base(botName, botTeam, botIndex)
        {
            WallReflectTargetFactories = new List<ITargetFactory>
            {
                new WallReflectTargetFactory(Field.Side(Team) * Vec3.X,
                    new Vec3(-Field.Side(Team) * Field.Width / 2, Field.Side(Team) * 4000),
                    new Vec3(-Field.Side(Team) * Field.Width / 2, 3700)), // Left wall
                new WallReflectTargetFactory(-Field.Side(Team) * Vec3.X,
                    new Vec3(Field.Side(Team) * Field.Width / 2, 3700),
                    new Vec3(Field.Side(Team) * Field.Width / 2, Field.Side(Team) * 4000)), // Right wall
                new WallReflectTargetFactory(new Vec3(Field.Side(Team), Field.Side(Team)).Normalize(),
                    new Vec3(-Field.Side(Team) * 3900, -Field.Side(Team) * 4164),
                    new Vec3(-Field.Side(Team) * 3200, -Field.Side(Team) * 4864)), // Enemy left corner wall
                new WallReflectTargetFactory(new Vec3(-Field.Side(Team), Field.Side(Team)).Normalize(),
                    new Vec3(Field.Side(Team) * 3200, -Field.Side(Team) * 4864),
                    new Vec3(Field.Side(Team) * 3900, -Field.Side(Team) * 4164)), // Enemy right corner wall
                new WallReflectTargetFactory(new Vec3(Field.Side(Team), -Field.Side(Team)).Normalize(),
                    new Vec3(-Field.Side(Team) * 3200, Field.Side(Team) * 4864),
                    new Vec3(-Field.Side(Team) * 3900, Field.Side(Team) * 4164)), // Our left corner wall, artificially extended for better clears
                new WallReflectTargetFactory(new Vec3(-Field.Side(Team), -Field.Side(Team)).Normalize(),
                    new Vec3(Field.Side(Team) * 3900, Field.Side(Team) * 4164),
                    new Vec3(Field.Side(Team) * 3200, Field.Side(Team) * 4864)), // Our right corner wall, artificially extended for better clears
            };
        }

        // Runs every tick. Should be used to find an Action to execute
        public override void Run()
        {
            //GameAnalysis.Update(this);
            //BoostNetwork.FindPath(Me, OurGoal.Location, Renderer);
            _kickOffPicker.Evaluate(this);
            //_kickOffPicker.DrawSummary(Renderer);

            // Prints out the current action to the screen, so we know what our bot is doing
            String actionStr = Action != null ? Action.ToString() : "null";
            Renderer.Text2D($"{Name}: {actionStr}", new Vec3(30, 400 + 18 * Index), 1, Color.White);

            Renderer.Color = Color.Yellow;
            var factories = new List<ITargetFactory> { new ForwardTargetFactory() }.Concat(WallReflectTargetFactories);
            foreach (var factory in factories)
            {
                Target target = factory.GetTarget(Me, BallSlice.Now());
                if (target == null) continue;
                Vec3 topRight = target.BottomRight.WithZ(target.TopLeft.z);
                Vec3 bottomLeft = target.TopLeft.WithZ(target.BottomRight.z);
                Renderer.Line3D(target.TopLeft, topRight, Color.Coral);
                Renderer.Line3D(topRight, target.BottomRight);
                Renderer.Line3D(target.BottomRight, bottomLeft);
                Renderer.Line3D(bottomLeft, target.TopLeft);
            }
            
            Car dribbler = _dribbleDetector.GetDribbler(DeltaTime);
            
            if (IsKickoff && Action == null)
            {
                Action = _kickOffPicker.PickKickOffAction(this);
            }
            else if (dribbler != null && dribbler.Team != Team && _dribbleDetector.Duration() > 0.4f && (Action == null || Action is Drive || Action.Interruptible))
            {
                // An enemy is dribbling. Tackle them!
                if (Action is not Drive)
                {
                    Action = new Drive(Me, dribbler.Location, wasteBoost: true);
                }
                
                // Predict location
                float naiveEta = Drive.GetEta(Me, dribbler.Location, true);
                Vec3 naiveLoc = dribbler.Location + naiveEta * dribbler.Velocity;
                float okayEta = Drive.GetEta(Me, naiveLoc, true);
                Vec3 okayLoc = dribbler.Location + okayEta * dribbler.Velocity;
                float eta = Drive.GetEta(Me, okayLoc, true);
                Vec3 loc = dribbler.Location + eta * dribbler.Velocity;;

                ((Drive)Action).Target = loc;
                Renderer.Rect3D(loc, 14, 14, color: Color.DarkOrange);
                Renderer.Rect3D(dribbler.Location, 20, 20, color: Color.Red);
            }
            else if (Action == null || ((Action is Drive || Action is BoostCollectingDrive) && Action.Interruptible))
            {
                Shot shot = null;
                // search for the first available shot using NoAerialsShotCheck
                CheapNoAerialShotCheck.Next(Me);
                List<ITargetFactory> goalTargetFactories = Field.Side(Me.Team) == MathF.Sign(Ball.Location.y)
                    ? new List<ITargetFactory> { new StaticTargetFactory(new(OurGoal, true)), new StaticTargetFactory(new(TheirGoal)) }
                    : new List<ITargetFactory> { new StaticTargetFactory(new Target(TheirGoal)) };
                Shot directShot = FindShot(CheapNoAerialShotCheck.ShotCheck, goalTargetFactories);
                Shot forwardShot = FindShot(CheapNoAerialShotCheck.ShotCheck, new ForwardTargetFactory());
                Shot reflectShot = FindShot(CheapNoAerialShotCheck.ShotCheck, WallReflectTargetFactories);

                if (directShot != null && reflectShot != null && reflectShot.Slice.Time + 0.02f < directShot.Slice.Time)
                {
                    // Early reflect shot is possible
                    shot = reflectShot;
                }
                else
                {
                    shot = directShot ?? reflectShot;
                }
                if (shot != null && forwardShot != null && forwardShot.Slice.Time + 0.02f < shot.Slice.Time)
                {
                    // Early forward shot is possible
                }
                else
                {
                    shot = directShot ?? forwardShot;
                }

                // Shot is too far away to be concerned about?
                if (shot != null && shot.Slice.Location.Dist(Me.Location) >= 5000)
                {
                    shot = null;
                }
                
                if (shot != null)
                {
                    // If the shot happens in a corner, special rules apply
                    if (MathF.Abs(shot.Slice.Location.x) + MathF.Abs(shot.Slice.Location.y) >= 5700)
                    {
                        if (MathF.Sign(shot.Slice.Location.y) != Field.Side(Team))
                        {
                            // Enemy corner. Never go for these
                            shot = null;
                        }
                        else
                        {
                            // Our corner. Only go if we are approaching for the middle or if all enemies are far away
                            if (MathF.Abs(shot.Slice.Location.x) - MathF.Abs(Me.Location.x) <= 0 &&
                                Cars.AllLivingCars.Any(car => car.Team != Me.Team && car.Location.Dist(OurGoal.Location) < 2500))
                                shot = null;
                        }
                    }
                }
                
                IAction alternative = Action is BoostCollectingDrive ? Action : null;
                Vec3 shadowLocation = Utils.Lerp(0.35f, Ball.Location, OurGoal.Location);
                bool onOurSideOfShadowLocation = (shadowLocation.y - Me.Location.y) * Field.Side(Me.Team) >= 0;
                
                if (shot == null && alternative == null)
                {
                    if (Ball.Location.y * -Field.Side(Team) >= 3000)
                    {
                        // Ball is far from our goal

                        // Collect boost
                        if (Me.Boost <= 20)
                        {
                            List<Boost> boosts = Field.Boosts.FindAll(boost =>
                                boost.IsLarge && (boost.Location.y - Me.Location.y) * Field.Side(Me.Team) >= 0);
                            alternative = new GetBoost(Me, boosts);
                        }
                    }
                    else if (Me.Boost <= 50 && !onOurSideOfShadowLocation)
                    {
                        // Get back but also collect boost
                        alternative = new BoostCollectingDrive(Me,
                            0.83f * OurGoal.Location + new Vec3(0.6f * Me.Location.x, 0));
                    }
                    else if (Me.Boost >= 50 && !onOurSideOfShadowLocation)
                    {
                        // Get back!
                        alternative = new Drive(Me, 0.83f * OurGoal.Location + new Vec3(0.6f * Me.Location.x, 0), wasteBoost: true);
                    }
                    else if (Me.Boost <= 50 && onOurSideOfShadowLocation)
                    {
                        // Collect boost on defence
                        alternative = new BoostCollectingDrive(Me,
                            0.83f * OurGoal.Location - new Vec3(0.8f * Me.Location.x, 0));
                    }
                    else
                    {
                        // Approach
                        alternative = new BoostCollectingDrive(Me, shadowLocation);
                    }
                }

                // if a shot is found, go for the shot. Otherwise, if there is an Action to execute, execute it. If none of the others apply, drive back to goal.
                Action = shot ?? alternative ??
                    Action ?? new BoostCollectingDrive(Me, shadowLocation);
            }
        }
    }
}
