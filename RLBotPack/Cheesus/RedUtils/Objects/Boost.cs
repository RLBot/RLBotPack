using rlbot.flat;
using RedUtils.Math;
using System;

namespace RedUtils
{
	/// <summary>A large or small boost pad</summary>
	public class Boost
	{
		public readonly int Index;
		public readonly Vec3 Location;
		public readonly bool IsLarge;

		public bool IsActive { get; private set; }
		/// <summary>How much time until it activates. 0 if it is already activated</summary>
		public float TimeUntilActive { get; private set; }

		/// <summary>Initializes a new empty boost pad object</summary>
		public Boost(int index)
		{
			Index = index;
			Location = Vec3.Zero;
			IsLarge = false;
			IsActive = true;
			TimeUntilActive = 0;
		}

		/// <summary>Initializes a new boost pad object with data from the packet</summary>
		public Boost(int index, BoostPad boostPad)
		{
			Index = index;
			Location = new Vec3(boostPad.Location.Value);
			IsLarge = boostPad.IsFullBoost;
			IsActive = true;
			TimeUntilActive = 0;
		}

		/// <summary>Updates the boost pad with info from the packet</summary>
		public void Update(BoostPadState boost)
		{
			IsActive = boost.IsActive;
			TimeUntilActive = boost.Timer;
		}
	}
}
