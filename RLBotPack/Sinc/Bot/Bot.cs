using System;
using System.Threading;
using System.Drawing;
using RedUtils;
using RedUtils.Math;
using System.Numerics;
using rlbot.flat;
/* 
* This is the main file. It contains your bot class. Feel free to change the name!
* An instance of this class will be created for each instance of your bot in the game.
* Your bot derives from the "RedUtilsBot" class, contained in the Bot file inside the RedUtils project.
* The run function listed below runs every tick, and should contain the custom strategy code (made by you!)
* Right now though, it has a default ball chase strategy. Feel free to read up and use anything you like for your own strategy.
*/
namespace Bot
{
    // Your bot class! :D
    public class SincBot : RUBot
    {
        // We want the constructor for our Bot to extend from RUBot, but feel free to add some other initialization in here as well.
        public SincBot(string botName, int botTeam, int botIndex) : base(botName, botTeam, botIndex) { }

        public bool KickoffGetBoost { get; private set; }
        public int OpponentsTeamlol { get; private set; }
        public int NearestTileDist { get; private set; }
        public object NearestTileObj { get; private set; }
        public object BallSliceOp { get; private set; }
        public object BallSliceSinc { get; private set; }

        public override void Run()
        {
            // Prints out the current action to the screen, so we know what our bot is doing
            MatchSettings matchSettings = GetMatchSettings();
            foreach (Car opponent in Opponents)
            {
                OpponentsTeamlol = opponent.Team;
            }
            BallSliceOp = Ball.Prediction.FindGoal(Team);
            BallSliceSinc = Ball.Prediction.FindGoal(OpponentsTeamlol);

            if (IsKickoff && Action == null)
            {
                if (Teammates.Count == 1)
                {
                    foreach (Car teammate in Teammates)
                    {
                        // if any teammates are closer to the ball, then don't go for kickoff
                        if (Me.Location.Dist(Ball.Location) < teammate.Location.Dist(Ball.Location))
                        {
                            Action = new Kickoff();
                        }
                        else if (Me.Location.Dist(Ball.Location) > teammate.Location.Dist(Ball.Location))
                        {
                            Action = new GetBoost(Me, interruptible: false);
                        }
                        else if (Me.Location.Dist(Ball.Location) == teammate.Location.Dist(Ball.Location))
                        {
                            if (teammate.IsBot)
                            {
                                if (Teammates.Count == 1)
                                {
                                    if (teammate.Name == "Sinc")
                                    {
                                        Action = new GetBoost(Me, interruptible: false);
                                    }
                                    else
                                    {
                                        Action = new Kickoff();
                                    }
                                }
                            }
                            else
                            {
                                Action = new GetBoost(Me, interruptible: false);
                            }
                        }
                    }
                }
                else if (Teammates.Count == 0)
                {
                    Action = new Kickoff();
                }
                else if (Teammates.Count == 2)
                {
                    bool goingForKickoff = true; // by default, go for kickoff
                    foreach (Car teammate in Teammates)
                    {
                        // if any teammates are closer to the ball, then don't go for kickoff
                        goingForKickoff = goingForKickoff && Me.Location.Dist(Ball.Location) <= teammate.Location.Dist(Ball.Location);
                    }

                    Action = goingForKickoff ? new Kickoff() : new GetBoost(Me, interruptible: false); // if we aren't going for the kickoff, get boost
                }
            }
            else if (Action == null || (Action is Drive && Action.Interruptible))
            {
                Shot shot = null;
                if (Teammates.Count == 1)
                {
                    var ArrayOfTeammates = Teammates.ToArray();
                    var Teammate1 = ArrayOfTeammates[0];
                    if (Me.Location.Dist(Ball.Location) < Teammate1.Location.Dist(Ball.Location))
                    {
                        shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                        foreach (Boost boost in Field.Boosts)
                        {
                            if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 600 && Me.Boost < 100)
                            {
                                if (boost.Location.Dist(Me.Location) < 450)
                                {
                                    Action = new GetBoost(Me, interruptible: true);
                                }
                            }
                        }
                    }
                    else if (Me.Location.Dist(Ball.Location) > Teammate1.Location.Dist(Ball.Location))
                    {
                        if (Ball.Location.Dist(OurGoal.Location) >= 5120)
                        {
                            if (Me.Team == 0)
                            {
                                var IntX = (int)0;
                                var IntY = (int)-2816;
                                Action = new Arrive(Me, new Vec3((float)IntX, (float)IntY, 0));
                            }
                            else
                            {
                                var IntX = (int)0;
                                var IntY = (int)2816;
                                Action = new Arrive(Me, new Vec3((float)IntX, (float)IntY, 0));
                            }
                            if (Me.Boost < 41)
                            {
                                Action = new GetBoost(Me);
                            }
                        }
                        else
                        {
                            shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                            foreach (Boost boost in Field.Boosts)
                            {
                                if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 2000 && Me.Boost < 100)
                                {
                                    if (boost.Location.Dist(Me.Location) < 150)
                                    {
                                        Action = new GetBoost(Me, interruptible: true);
                                    }
                                }
                            }
                        }
                    }
                }
                if (Teammates.Count == 2)
                {
                    var ArrayOfTeammates = Teammates.ToArray();
                    var TeamMidPos = new Vec3(500, 500, 500);
                    if (Me.Team == 0)
                    {
                        TeamMidPos = new Vec3(8192, -5120, 70);
                    }
                    else
                    {
                        TeamMidPos = new Vec3(8192, 5120, 70);
                    }
                    var Teammate1 = ArrayOfTeammates[0];
                    var Teammate2 = ArrayOfTeammates[1];
                    if (Me.Location.Dist(Ball.Location) < Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) < Teammate2.Location.Dist(Ball.Location))
                    {
                        shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                        foreach (Boost boost in Field.Boosts)
                        {
                            if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 400 && Me.Boost < 100)
                            {
                                if (boost.Location.Dist(Me.Location) < 450)
                                {
                                    Action = new GetBoost(Me, interruptible: true);
                                }
                            }
                        }
                    }
                    else if (Me.Location.Dist(Ball.Location) < Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) > Teammate2.Location.Dist(Ball.Location) || Me.Location.Dist(Ball.Location) > Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) < Teammate2.Location.Dist(Ball.Location))
                    {
                        var Attacker = Me;
                        if (Me.Location.Dist(Ball.Location) < Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) > Teammate2.Location.Dist(Ball.Location))
                        {
                            Attacker = Teammate2;
                        }
                        else if (Me.Location.Dist(Ball.Location) > Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) < Teammate2.Location.Dist(Ball.Location))
                        {
                            Attacker = Teammate1;
                        }
                        if (Ball.Location.Dist(TheirGoal.Location) <= 5120)
                        {
                            if (Me.Team == 0)
                            {
                                var IntX = (int)Attacker.Location.x;
                                var IntY = (int)Attacker.Location.y - 2500;
                                Action = new Arrive(Me, new Vec3((float)IntX, (float)IntY, 0));
                            }
                            else
                            {
                                var IntX = (int)Attacker.Location.x;
                                var IntY = (int)Attacker.Location.y + 2500;
                                Action = new Arrive(Me, new Vec3((float)IntX, (float)IntY, 0));
                            }
                        }
                        else if (Ball.Location.Dist(TheirGoal.Location) > 5120)
                        {
                            shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                        }
                        foreach (Boost boost in Field.Boosts)
                        {
                            if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 400 && Me.Boost < 100)
                            {
                                if (boost.Location.Dist(Me.Location) < 325)
                                {
                                    Action = new GetBoost(Me, interruptible: true);
                                }
                            }
                        }
                    }
                    else if (Me.Location.Dist(Ball.Location) > Teammate1.Location.Dist(Ball.Location) && Me.Location.Dist(Ball.Location) > Teammate2.Location.Dist(Ball.Location))
                    {
                        Action = new Arrive(Me, OurGoal.Location);
                        if (Me.Boost < 50 && Ball.Location.FlatDist(OurGoal.Location) > 2500)
                        {
                            Action = new GetBoost(Me, interruptible: true);
                        }
                        if (OurGoal.Location.Dist(Ball.Location) < 2500 || BallSliceSinc != null)
                        {
                            Action = null;
                            shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                        }
                    }
                }
                if (Teammates.Count == 0)
                {
                    if (Me.Boost >= 10)
                    {
                        shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                        foreach (Boost boost in Field.Boosts)
                        {
                            if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 400 && Me.Boost < 100)
                            {
                                if (boost.Location.Dist(Me.Location) < 110)
                                {
                                    if (Me.Boost < 75)
                                    {
                                        Action = new GetBoost(Me, interruptible: true);
                                    }
                                }
                            }
                        }
                    }
                    else
                    {
                        if (Ball.Location.FlatDist(OurGoal.Location) < 1700 || BallSliceSinc != null)
                        {
                            if (Me.Location.FlatDist(OurGoal.Location) < 1700)
                            {
                                shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                            }
                            else
                            {
                                Action = new Arrive(Me, OurGoal.Location, direction: Me.Location.Direction(Ball.Location));
                            }
                        }
                        else
                        {
                            foreach (Car Opponent in Opponents)
                            {
                                if (BallSliceSinc != null && Opponent.Location.FlatDist(Ball.Location) < 1500)
                                {
                                    shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                                }
                                else
                                {
                                    var GrabbingBoost = false;
                                    foreach (Boost boost in Field.Boosts)
                                    {
                                        if (boost.IsActive && boost.IsLarge && Ball.Location.Dist(OurGoal.Location) > 1200 && Me.Boost < 100)
                                        {
                                            if (boost.Location.Dist(Me.Location) < 110)
                                            {
                                                if (Me.Boost < 75)
                                                {
                                                    Action = new GetBoost(Me, interruptible: true);
                                                    GrabbingBoost = true;
                                                }
                                            }
                                        }
                                    }
                                    if (GrabbingBoost == false)
                                    {
                                        shot = FindShot(DefaultShotCheck, new Target(TheirGoal));
                                    }
                                }
                            }
                        }
                    }
                }
                if (Teammates.Count == 1 || Teammates.Count == 2)
                {
                    if (Me.Boost > 30)
                    {
                        Action = shot ?? Action;
                    }
                    else
                    {
                        Action = shot ?? Action;

                    }
                }
                else if (Teammates.Count == 0)
                {
                    Action = shot ?? Action ?? new Drive(Me, OurGoal.Location);

                }
            }
            
        }
    }
}
