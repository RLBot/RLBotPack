using System;
using rlbot.flat;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>An object representing one of the two goals on the field</summary>
	public class Goal
	{
		/// <summary>The total width of the goal, from post to post</summary>
		public const float Width = 1780;
		/// <summary>The total height of the goal, from ground to crossbar</summary>
		public const float Height = 640;
		/// <summary>The total depth of the goal</summary>
		public const float Depth = 850;

		/// <summary>The team this goal belongs to</summary>
		public readonly int Team;
		/// <summary>The center of the goal, on the ground</summary>
		public readonly Vec3 Location;
		/// <summary>The center of the left post</summary>
		public readonly Vec3 LeftPost;
		/// <summary>The center of the right post</summary>
		public readonly Vec3 RightPost;
		/// <summary>The top left corner of the goal</summary>
		public readonly Vec3 TopLeftCorner;
		/// <summary>The top right corner of the goal</summary>
		public readonly Vec3 TopRightCorner;
		/// <summary>The bottom left corner of the goal</summary>
		public readonly Vec3 BottomLeftCorner;
		/// <summary>The bottom right corner of the goal</summary>
		public readonly Vec3 BottomRightCorner;
		/// <summary>The center of the crossbar</summary>
		public readonly Vec3 Crossbar;

		/// <summary>Initializes this goal with a given team id (0 for blue, 1 for orange)</summary>
		public Goal(int team)
		{
			Team = team;
			Location = new Vec3(0, Field.Length / 2 * Field.Side(Team), 0);
			LeftPost = new Vec3(Width / 2 * Field.Side(Team), Field.Length / 2 * Field.Side(Team), Height / 2);
			RightPost = new Vec3(Width / 2 * -Field.Side(Team), Field.Length / 2 * Field.Side(Team), Height / 2);
			TopLeftCorner = new Vec3(Width / 2 * Field.Side(Team), Field.Length / 2 * Field.Side(Team), Height);
			TopRightCorner = new Vec3(Width / 2 * -Field.Side(Team), Field.Length / 2 * Field.Side(Team), Height);
			BottomLeftCorner = new Vec3(Width / 2 * Field.Side(Team), Field.Length / 2 * Field.Side(Team), 0);
			BottomRightCorner = new Vec3(Width / 2 * -Field.Side(Team), Field.Length / 2 * Field.Side(Team), 0);
			Crossbar = new Vec3(0, Field.Length / 2 * Field.Side(Team), Height);
		}
	}
}
