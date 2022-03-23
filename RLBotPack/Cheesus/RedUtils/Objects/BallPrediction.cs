using rlbot.flat;
using System;
using System.Collections.Generic;

namespace RedUtils
{
    /// <summary>
    /// Processed version of the <see cref="rlbot.flat.BallPrediction"/> that uses sane data structures.
    /// </summary>
    public struct BallPrediction
    {
        public BallSlice this[int index] { get { return Slices[index]; } }

        /// <summary>A list of all of the future ball slices</summary>
        public BallSlice[] Slices;
        public int Length => Slices.Length;

        public BallPrediction(rlbot.flat.BallPrediction ballPrediction)
        {
            Slices = new BallSlice[ballPrediction.SlicesLength];
            for (int i = 0; i < ballPrediction.SlicesLength; i++)
                Slices[i] = new BallSlice(ballPrediction.Slices(i).Value);
        }

        /// <summary>Finds the first ball slice that fits the given predicate 
        /// <para>This function is more effecient then the normal "Find" function, and accounts for scoring</para>
        /// </summary>
        public BallSlice Find(Predicate<BallSlice> predicate)
        {
            if (Length > 0)
            {
                for (int i = 6; i < Length; i += 6)
                {
                    if (predicate(Slices[i]))
                    {
                        for (int j = i - 6; j < i; j++)
                        {
                            if (MathF.Abs(Slices[j].Location.y) > 5250) break;
                            if (predicate(Slices[j]))
                            {
                                return Slices[j];
                            }
                        }
                    }
                    else if (MathF.Abs(Slices[i].Location.y) > 5250) break;
                }
            }

            return null;
        }
        
        /// <summary>Finds the first ball slice that is scoring in favor of the parameter team </summary>
        public BallSlice FindGoal(int team)
        {
            int otherSide = -Field.Side(team);
            if (Length > 0)
            {
                for (int i = 6; i < Length; i += 6)
                {
                    if (Slices[i].Location.y * otherSide > 5250)
                    {
                        for (int j = i - 6; j < i; j++)
                        {
                            if (Slices[j].Location.y * otherSide > 5250) 
                                return Slices[j];
                        }
                    }
                }
            }

            return null;
        }
    }
}
