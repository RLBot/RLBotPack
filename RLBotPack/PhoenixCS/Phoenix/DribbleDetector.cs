using System;
using System.Linq;
using RedUtils;

namespace Phoenix
{
    /// <summary>A strategy helper class that can detect dribbling bots</summary>
    public class DribbleDetector
    {
        private const float DistReq = 165;
        private const float TimeReq = 0.25f; 
        private const float ZReq = 120f;

        private Car _prev;
        private float _duration;
        
        /// <summary>Returns the bot that is currently dribbling, or null if none are</summary>
        public Car GetDribbler(float dt)
        {
            Car dribbler = Cars.AllCars.FindAll(car => !car.IsDemolished)
                .OrderBy(car => car.Location.Dist(Ball.Location)).FirstOrDefault();

            if (dribbler == null || dribbler != _prev || Ball.Location.z < ZReq || dribbler.Location.Dist(Ball.Location) > DistReq) _duration = 0;
            
            _duration += dt;
            _prev = dribbler;

            return _duration >= TimeReq ? dribbler : null;
        }

        /// <summary>Returns the duration of the current dribble</summary>
        public float Duration()
        {
            return _duration;
        }
    }
}
