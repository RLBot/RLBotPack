using System;
using rlbot.flat;

namespace RedUtils.Math
{
	/// <summary>Represents a vector in three dimensions</summary>
	public struct Vec3
	{
		public float this[int index]
		{
			get
			{
				return index switch
				{
					0 => x,
					1 => y,
					2 => z,
					_ => float.NaN,
				};
				;
			}
			set 
			{
				switch (index)
				{
					case 0:
						x = value;
						break;
					case 1:
						y = value;
						break;
					case 2:
						z = value;
						break;
					default:
						break;
				}
			}
		}
		/// <summary>The x component of this vector</summary>
		public float x;
		/// <summary>The y component of this vector</summary>
		public float y;
		/// <summary>The z component of this vector</summary>
		public float z;

		#region Properties
		/// <summary>A vector with all zeros</summary>
		public static Vec3 Zero
		{ get { return new Vec3(0, 0, 0); } }
		/// <summary>A vector with the value (0, 0, 1)</summary>
		public static Vec3 Up
		{ get { return new Vec3(0, 0, 1); } }
		/// <summary>A vector with the value (0, 0, 1)</summary>
		public static Vec3 Z
		{ get { return new Vec3(0, 0, 1); } }
		/// <summary>A vector with the value (0, 1, 0)</summary>
		public static Vec3 Y
		{ get { return new Vec3(0, 1, 0); } }
		/// <summary>A vector with the value (1, 0, 1)</summary>
		public static Vec3 X
		{ get { return new Vec3(1, 0, 0); } }
		#endregion

		#region Constructors
		/// <summary>Creates a new vector with the specified values</summary>
		public Vec3(float x, float y, float z)
		{
			this.x = x;
			this.y = y;
			this.z = z;
		}
		/// <summary>Creates a new vector with the specified values (z is 0)</summary>
		public Vec3(float x, float y)
		{
			this.x = x;
			this.y = y;
			this.z = 0;
		}
		/// <summary>Creates a new vector with the first three values in the array
		/// <para>if the list doesn't have enough values, the missing values will be put in as zeros</para>
		/// </summary>
		public Vec3(float[] values)
		{
			if (values.Length > 0) x = values[0]; else x = 0;
			if (values.Length > 1) y = values[1]; else y = 0;
			if (values.Length > 2) z = values[2]; else z = 0;
		}
		/// <summary>Copies a vector (can be used to change an element of a vector within a statment)</summary>
		public Vec3(Vec3 vector)
		{
			x = vector.x;
			y = vector.y;
			z = vector.z;
		}
		/// <summary>Converts <see cref="rlbot.flat.Vector3"/> to a <see cref="Vec3"/></summary>
		public Vec3(Vector3 vector)
		{
			x = vector.X;
			y = vector.Y;
			z = vector.Z;
		}
		/// <summary>Converts <see cref="rlbot.flat.Rotator"/> to a <see cref="Vec3"/></summary>
		public Vec3(Rotator rotator)
		{
			x = rotator.Pitch;
			y = rotator.Yaw;
			z = rotator.Roll;
		}
		#endregion

		#region Arithimatic Operations
		public static Vec3 operator +(Vec3 v1, Vec3 v2)
		{
			return new Vec3(v1.x + v2.x, v1.y + v2.y, v1.z + v2.z);
		}
		public static Vec3 operator -(Vec3 v)
		{
			return new Vec3(-v.x, -v.y, -v.z);
		}
		public static Vec3 operator -(Vec3 v1, Vec3 v2)
		{
			return new Vec3(v1.x - v2.x, v1.y - v2.y, v1.z - v2.z);
		}
		public static Vec3 operator *(Vec3 v1, Vec3 v2)
		{
			return new Vec3(v1.x * v2.x, v1.y * v2.y, v1.z * v2.z);
		}
		public static Vec3 operator *(Vec3 v, float a)
		{
			return new Vec3(v.x * a, v.y * a, v.z * a);
		}
		public static Vec3 operator *(float a, Vec3 v)
		{
			return new Vec3(a * v.x, a * v.y, a * v.z);
		}
		public static Vec3 operator /(Vec3 v1, Vec3 v2)
		{
			return new Vec3(v1.x / v2.x, v1.y / v2.y, v1.z / v2.z);
		}
		public static Vec3 operator /(Vec3 v, float x)
		{
			return new Vec3(v.x / x, v.y / x, v.z / x);
		}
		#endregion

		#region Linear Algebra & Other Operations
		/// <summary>Returns a vector with the absolute value of all of elements in the given vector</summary>
		public static Vec3 Abs(Vec3 vec)
		{
			return new Vec3(MathF.Abs(vec.x), MathF.Abs(vec.y), MathF.Abs(vec.z));
		}
		/// <summary>Returns the dot product between this vector and the given vector</summary>
		public float Dot(Vec3 v)
		{
			return x * v.x + y * v.y + z * v.z;
		}
		/// <summary>Returns the dot product between this vector and the given 3x3 matrix</summary>
		public Vec3 Dot(Mat3x3 m)
		{
			return m.Forward * x + m.Right * y + m.Up * z;
		}
		/// <summary>Returns a 2D cross product 
		/// <para>The equivalent of crossing this vector with the z unit vector</para>
		/// </summary>
		public Vec3 Cross()
		{
			return new Vec3(y, -x, 0);
		}
		/// <summary>Returns the cross product between this vector and the given vector</summary>
		public Vec3 Cross(Vec3 v)
		{
			return new Vec3(y * v.z - z * v.y, z * v.x - x * v.z, x * v.y - y * v.x);
		}
		/// <summary>Returns the legnth/magnitude of this vector</summary>
		public float Length()
		{ 
			return MathF.Sqrt(x * x + y * y + z * z);
		}
		/// <summary>Returns a normalized version of this vector 
		/// <para>In other words, its the same vector, just with a length of 1</para>
		/// </summary>
		public Vec3 Normalize()
		{
			float l = Length();
			return l > 0 ? this / l : this; 
		}
		/// <summary>Returns a flattened, then normalized version of this vector
		/// <para>In other words, its z component is 0, and its length is 1</para>
		/// </summary>
		public Vec3 FlatNorm()
		{
			return this.Flatten().Normalize();
		}
		/// <summary>Returns a flattened, then normalized version of this vector 
		/// <para>In other words, the dot product between it and the given "up" vector is 0, and its length is 1</para>
		/// </summary>
		public Vec3 FlatNorm(Vec3 up)
		{
			return this.Flatten(up).Normalize();
		}
		/// <summary>Returns a flattened version of this vector
		/// <para>In other words, its the same vector, except the z component is 0</para>
		/// </summary>
		public Vec3 Flatten()
		{
			return new Vec3(x, y, 0);
		}
		/// <summary>Returns a flattened version of this vector, along the given "up" direction
		/// <para>In other words, the dot product between it and the "up" vector is 0</para>
		/// </summary>
		public Vec3 Flatten(Vec3 up)
		{
			up = up.Normalize();
			return this - up * Dot(up);
		}
		/// <summary>Returns a normalized vector pointing from this vector to the given vector</summary>
		public Vec3 Direction(Vec3 vec)
        {
            return (vec - this).Normalize();
        }
		/// <summary>Returns a flattened, normalized vector pointing from this vector to the given vector
		/// <para>In other words, its the direction from this vector to the given vector, and its z component is 0</para>
		/// </summary>
		public Vec3 FlatDirection(Vec3 vec)
        {
            return (vec - this).FlatNorm();
        }
		/// <summary>Returns a flattened, normalized vector pointing from this vector to the given vector
		/// <para>In other words, its the direction from this vector to the given vector, and the dot product between it and the "up" vector is now 0</para>
		/// </summary>
		public Vec3 FlatDirection(Vec3 vec, Vec3 up)
        {
            return (vec - this).FlatNorm(up);
        }
		/// <summary>Returns the distance between two vectors</summary>
		public float Dist(Vec3 v)
		{
			return (v - this).Length();
		}
		/// <summary>Returns the flat distance between two vectors
		/// <para>In other words, this vector and the given vector are flattened, and then there distance is measured</para>
		/// </summary>
		public float FlatDist(Vec3 v)
		{
			return (v - this).Flatten().Length();
		}
		/// <summary>Returns the flat distance between two vectors
		/// <para>In other words, this vector and the given vector are flattened in the "up" direction, and then there distance is measured</para>
		/// </summary>
		public float FlatDist(Vec3 v, Vec3 up)
		{
			return (v - this).Flatten(up).Length();
		}
		/// <summary>Returns the flattened length of this vector</summary>
		public float FlatLen()
		{
			return Flatten().Length();
		}
		/// <summary>Returns the length of this vector, flattened in the "up" direction</summary>
		public float FlatLen(Vec3 up)
		{
			return Flatten(up).Length();
		}
		/// <summary>Returns the angle between two vectors</summary>
		public float Angle(Vec3 v)
		{
			return MathF.Acos(MathF.Round(this.Normalize().Dot(v.Normalize()), 4));
		}
		/// <summary>Returns the 2D, flat angle between two vectors</summary>
		public float FlatAngle(Vec3 v)
		{
			return MathF.Acos(MathF.Round(this.Normalize().Flatten().Dot(v.Normalize().Flatten()), 4));
		}
		/// <summary>Returns the 2D, flat angle between two vectors (flattened in the "up" direction)</summary>
		public float FlatAngle(Vec3 v, Vec3 up)
		{
			return MathF.Acos(MathF.Round(this.Normalize().Flatten(up).Dot(v.Normalize().Flatten(up)), 4));
		}
		/// <summary>Returns this vector, with the same direction, just with a new length</summary>
		public Vec3 Rescale(float n)
		{
			return this.Normalize() * n;
		}
		/// <summary>Returns this vector, with the same direction, but the length is capped between a minimum and maximum length</summary>
		public Vec3 Cap(float min, float max)
		{
			return this.Rescale(Utils.Cap(Length(), min, max));
		}
		/// <summary>Clamps the rotation of this vector between a given start and end vector, such that start &lt; this &lt; end in terms of clockwise rotation</summary>
		public Vec3 Clamp(Vec3 start, Vec3 end)
		{
			Vec3 v = Normalize();
			bool right = v.Dot(end.Cross(-Up)) < 0;
			bool left = v.Dot(start.Cross(-Up)) > 0;

			bool isBetween = end.Dot(start.Cross(-Up)) > 0 ? (left && right) : (left || right);

			if (isBetween)
			{
				return this;
			}
			if (start.Dot(v) < end.Dot(v))
			{
				return end.Flatten().Normalize() * Flatten().Length() + Up * z;
			}
			return start.Flatten().Normalize() * Flatten().Length() + Up * z;
		}
		/// <summary>Clamps the rotation of this vector between a given start and end vector, such that start &lt; this &lt; end in terms of clockwise rotation</summary>
		public Vec3 Clamp(Vec3 start, Vec3 end, Vec3 up)
		{
			Vec3 v = Normalize();
			bool right = v.Dot(end.Cross(-up)) < 0;
			bool left = v.Dot(start.Cross(-up)) > 0;

			bool isBetween = end.Dot(start.Cross(-up)) > 0 ? (left && right) : (left || right);

			if (isBetween)
			{
				return this;
			}
			if (start.Dot(v) < end.Dot(v))
			{
				return end.FlatNorm(up) * Flatten(up).Length() + up * Dot(up);
			}
			return start.FlatNorm(up) * Flatten(up).Length() + up * Dot(up);
		}
		/// <summary>Rotates the vector around the z axis in the counter-clockwise direction</summary>
		public Vec3 Rotate(float angle)
		{
			return Flatten(Up) * MathF.Cos(angle) + Flatten(Up).Cross(Up).Rescale(Flatten(Up).Length()) * MathF.Sin(angle) + Up * Dot(Up);
		}

		/// <summary>Rotates the vector around the given axis in the counter-clockwise direction</summary>
		public Vec3 Rotate(float angle, Vec3 rotationAxis)
		{
			return Flatten(rotationAxis) * MathF.Cos(angle) + Flatten(rotationAxis).Cross(rotationAxis).Rescale(Flatten(rotationAxis).Length()) * MathF.Sin(angle) + rotationAxis * Dot(rotationAxis);
		}
		#endregion
		public override string ToString()
		{
			return $"({x}, {y}, {z})";
		}
	}
}
