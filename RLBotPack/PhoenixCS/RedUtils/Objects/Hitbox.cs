using System;
using rlbot.flat;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A car's hitbox</summary>
	public class Hitbox
	{
		/// <summary>The location of the car that this hitbox belongs to</summary>
		public Vec3 Location;
		/// <summary>The dimensions of this hitbox</summary>
		public Vec3 Dimensions;
		/// <summary>The local offset between the car and this hitbox</summary>
		public Vec3 Offset;
		/// <summary>The orientation matrix for this hitbox (and the car this hitbox belongs to)</summary>
		public Mat3x3 Orientation;

		/// <summary>The center of this hitbox</summary>
		public Vec3 Center { get { return Location + Offset.Dot(Orientation); } }

		/// <summary>Initializes a new car hitbox</summary>
		public Hitbox(Vec3 location, Vec3 dimensions, Vec3 offset, Mat3x3 orientation)
		{
			Location = location;
			Dimensions = dimensions;
			Offset = offset;
			Orientation = orientation;
		}
	}
}
