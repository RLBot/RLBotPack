using System;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A bunch of various helpful math and physics utilities</summary>
	public static class Utils
	{
		/// <summary>Limits the given float value between given minimum and maximum values</summary>
		/// <param name="value">The float being capped</param>
		/// <param name="min">The minimum float value</param>
		/// <param name="max">The maximum float value</param>
		public static float Cap(float value, float min, float max)
		{
			return (value < min) ? min : (value > max) ? max : value;
		}

		/// <summary>Limits the given integer value between given minimum and maximum values</summary>
		/// <param name="value">The integer being capped</param>
		/// <param name="min">The minimum integer value</param>
		/// <param name="max">The maximum integer value</param>
		public static int Cap(int value, int min, int max)
		{
			return (value < min) ? min : (value > max) ? max : value;
		}

		/// <summary>Linerally interpolates between values a and b, using value t
		/// <para>For instance, if t == 0, a is returned. If t == 1, b is returned</para>
		/// </summary>
		public static float Lerp(float t, float a, float b)
		{
			return (b - a) * t + a;
		}

		/// <summary>Linerally interpolates between vectors a and b, using value t
		/// <para>For instance, if t == 0, a is returned. If t == 1, b is returned</para>
		/// </summary>
		public static Vec3 Lerp(float t, Vec3 a, Vec3 b)
		{
			return (b - a) * t + a;
		}

		/// <summary>Inverse linerally interpolates between values a and b, using value v
		/// <para>For instance, if v == a, 0 is returned. If v == b, 1 is returned. And if v is half way between a and b, 0.5 is returned</para>
		/// </summary>
		public static float Invlerp(float v, float a, float b)
		{
			return (v - a) / (b - a);
		}

		/// <summary>Solves the quadratic formula</summary>
		/// <returns>The two roots of the quadratic</returns>
		public static float[] Quadratic(float a, float b, float c)
		{
			float inside = MathF.Sqrt((b * b) - (4 * a * c));
			if (a != 0 && !float.IsNaN(inside))
			{
				return new float[2] { (-b + inside) / (2 * a), (-b - inside) / (2 * a) };
			}
			return new float[2] { -1, -1 };
		}

		/// <summary>Calculates how long it will take to jump a certain height</summary>
		/// <param name="up">The direction your roof is facing when you jump</param>
		/// <param name="height">How high you need to jump (a height less than 15.2 may be slightly inaccurate)</param>
		/// <param name="doubleJump">Whether or not you're going to double jump as soon as your first jump is done</param>
		public static float TimeToJump(Vec3 up, float height, bool doubleJump = false)
		{
			float gravity = up.Dot(Game.Gravity) != 0 ? up.Dot(Game.Gravity) : -0.001f;
			float heightAfterJump = Car.JumpVel * Car.JumpMaxDuration +
				Car.JumpAccel * Car.JumpMaxDuration * Car.JumpMaxDuration / 2 -
				Car.StickyAccel * 0.05f * (Car.JumpMaxDuration - 0.025f) +
				gravity * Car.JumpMaxDuration * Car.JumpMaxDuration / 2;
			float doubleJumpMultiplier = doubleJump ? 2 : 1;

			float intVelAfterJump = Car.JumpVel * doubleJumpMultiplier - 16.25f + (gravity + Car.JumpAccel) * Car.JumpMaxDuration;
			float finVelAfterJump = MathF.Sqrt(MathF.Max(MathF.Pow(intVelAfterJump, 2) + 2 * gravity * (height - heightAfterJump), 0));

			if (height < heightAfterJump)
			{
				float finVel = MathF.Sqrt(MathF.Max(MathF.Pow(Car.JumpVel - 16.25f, 2) + 2 * (gravity + Car.JumpAccel) * height, 0));
				return (finVel - Car.JumpVel + 16.25f) / (gravity + Car.JumpAccel);
			}
			return Car.JumpMaxDuration + (finVelAfterJump - intVelAfterJump) / gravity;
		}

		/// <summary>Calculates how far the car could rotate given a certain amount of time</summary>
		public static float PredictRotation(float acceleration, float time)
		{
			if (acceleration * time > Car.MaxAngularVel)
			{
				float timeToReachMax = Car.MaxAngularVel / acceleration;

				return (acceleration / 2) * MathF.Pow(timeToReachMax, 2) + Car.MaxAngularVel * (time - timeToReachMax);
			}

			return (acceleration / 2) * MathF.Pow(time, 2);
		}

		public static float ShotPowerModifier(float value)
		{
			value = Cap(value, 0, 4600);
			if (value <= 500)
			{
				return 0.65f;
			}
			else if (value <= Car.MaxSpeed)
			{
				return Lerp((value - 500) / 1800, 0.65f, 0.55f);
			}
			return Lerp((value - Car.MaxSpeed) / 4600, 0.55f, 0.3f);
		}
	}
}
