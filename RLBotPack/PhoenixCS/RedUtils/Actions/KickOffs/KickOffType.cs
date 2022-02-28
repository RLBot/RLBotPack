using System;
using RedUtils.Math;

namespace RedUtils.Actions.KickOffs
{
    /// <summary>The kick off spawn position type</summary>
    public enum KickOffType
    {
        FarBack,
        BackSide,
        Diagonal,
    }

    public static partial class KickOffs
    {
        /// <summary>Returns the kick off type based on a spawn location</summary>
        public static KickOffType GetKickOffTypeFromLoc(Vec3 location)
        {
            return MathF.Abs(location.y) switch
            {
                <= 3500f => KickOffType.Diagonal,
                <= 4000f => KickOffType.BackSide,
                _ => KickOffType.FarBack,
            };
        } 
    }
}
