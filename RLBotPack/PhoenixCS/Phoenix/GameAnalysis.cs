using System.Collections.Generic;
using RedUtils;
using rlbot.flat;
using Color = System.Drawing.Color;

namespace Phoenix
{
    public static class GameAnalysis
    {
        public class CarAnalysis
        {
            public float ToBallEta { get; internal set; }
            public float ToAllyGoalEta { get; internal set; }
            public bool IsCommitted { get; internal set; }
            public bool IsShooting { get; internal set; }
        }

        private static Dictionary<Car, CarAnalysis> _carAnalyses = new();

        public static void Update(RUBot bot)
        {
            foreach (Car car in Cars.AllCars)
            {
                if (!_carAnalyses.ContainsKey(car))
                    _carAnalyses.Add(car, new CarAnalysis());
                _carAnalyses.TryGetValue(car, out var analysis);
                
                analysis.ToBallEta = Drive.GetEta(car, Ball.Location, true);
                analysis.ToAllyGoalEta = Drive.GetEta(car, Field.Goals[car.Team].Location, true);
                
                analysis.IsShooting = analysis.ToBallEta < 0.8f;
                analysis.IsCommitted = analysis.ToAllyGoalEta > 2f; // TODO Ideally commitment should be based on ETA for incoming shots

                if (analysis.IsShooting)
                    bot.Renderer.OrientatedCube(car.Location + car.Orientation.Transpose().Dot(car.Hitbox.Offset), car.Orientation, car.Hitbox.Dimensions, Color.Aqua);
                if (analysis.IsCommitted)
                    bot.Renderer.OrientatedCube(car.Location + car.Orientation.Transpose().Dot(car.Hitbox.Offset), car.Orientation, 0.95f * car.Hitbox.Dimensions, Color.Orange);
            }
        }
    }
}
