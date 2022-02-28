using RedUtils.Math;
using rlbot.flat;

namespace RedUtils
{
	/// <summary>Contains info on a collision between the ball and a car</summary>
	public class BallTouch
	{
		/// <summary>The time at which point this collision happened</summary>
		public readonly float Time;
		/// <summary>The location of this collision</summary>
		public readonly Vec3 Location;
		/// <summary>The normal of this collision</summary>
		public readonly Vec3 Normal;
		/// <summary>The name of the player who collided with the ball</summary>
		public readonly string PlayerName;
		/// <summary>The index of the player who collided with the ball</summary>
		public readonly int PlayerIndex;
		/// <summary>The team of the player who collided with the ball</summary>
		public readonly int Team;

		/// <summary>Initializes a new ball touch with data from the packet</summary>
		public BallTouch(Touch touch)
		{
			Time = touch.GameSeconds;
			Location = new Vec3(touch.Location.Value);
			Normal = new Vec3(touch.Normal.Value);
			PlayerName = touch.PlayerName;
			PlayerIndex = touch.PlayerIndex;
			Team = touch.Team;
		}
	}
}
