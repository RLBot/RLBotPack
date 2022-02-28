using System;
using rlbot.flat;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>A car object. Also contains info on the player/bot controlling the car, like their name, score, etc</summary>
	public class Car
	{
		/// <summary>How long you can hold down the jump button during the first jump for extra height</summary>
		public const float JumpMaxDuration = 0.2f;
		/// <summary>The acceleration you get while holding the jump button during the first jump</summary>
		public const float JumpAccel = 1458.333f;
		/// <summary>The instantanous velocity you get when you hit the jump button for both the first and second jump</summary>
		public const float JumpVel = 291.667f;
		/// <summary>The acceleration you get when holding throttle in the air. Automatically gets added when you boost in the air</summary>
		public const float AirThrottleAccel = 66.667f;
		/// <summary>The decceleration you get when you throttle on the ground in the opposite direction of where you're heading</summary>
		public const float BrakeAccel = 3500f;
		/// <summary>The acceleration you get when you boost</summary>
		public const float BoostAccel = 991.667f;
		/// <summary>The rate at which you consume boost</summary>
		public const float BoostConsumption = 33.3f;
		/// <summary>The max speed of the car</summary>
		public const float MaxSpeed = 2300f;
		/// <summary>The acceleration you get when you're on the ground that keeps you on the ground</summary>
		public const float StickyAccel = 325f;
		/// <summary>The maximum angular velocity of the car</summary>
		public const float PitchAngularAccel = 12.46f;
		/// <summary>The maximum angular velocity of the car</summary>
		public const float YawAngularAccel = 9.11f;
		/// <summary>The maximum angular velocity of the car</summary>
		public const float RollAngularAccel = 38.34f;
		/// <summary>The maximum angular velocity of the car</summary>
		public const float MaxAngularVel = 5.5f;

		/// <summary>The car's current position</summary>
		public Vec3 Location;
		/// <summary>The car's current velocity</summary>
		public Vec3 Velocity;
		/// <summary>The car's current angular velocity</summary>
		public Vec3 AngularVelocity;
		/// <summary>The car's current angular velocity in local coordinates</summary>
		public Vec3 LocalAngularVelocity;
		/// <summary>The car's current pitch, yaw, and roll (in that order) stored as a vec3</summary>
		public Vec3 Rotation;
		/// <summary>The car's orientation 3x3 matrix. <para>You can kind of think of it as three vectors, one pointing forwards, one pointing right, and one pointing up</para></summary>
		public Mat3x3 Orientation;

		/// <summary>The car's hitbox</summary>
		public Hitbox Hitbox { get { return new Hitbox(Location, _hitboxDimensions, _hitboxOffset, Orientation); } }
		/// <summary>A normalized vector pointing out the front of the car</summary>
		public Vec3 Forward { get { return Orientation.Forward; } set { Orientation[0] = value; } }
		/// <summary>A normalized vector pointing out to the right of the car</summary>
		public Vec3 Right { get { return Orientation.Right; } set { Orientation[1] = value; } }
		/// <summary>A normalized vector pointing out through the car's roof</summary>
		public Vec3 Up { get { return Orientation.Up; } set { Orientation[2] = value; } }

		/// <summary>The name of the player or bot who controls this car</summary>
		public string Name;
		public int Index;
		/// <summary>The index of the team this car is on (0 for blue, 1 for orange)</summary>
		public int Team;
		/// <summary>How much boost the car currently has</summary>
		public int Boost;
		/// <summary>If the car is controlled by a bot</summary>
		public bool IsBot;
		/// <summary>If all four of the car's wheels are on a surface</summary>
		public bool IsGrounded;
		/// <summary>If the car has executed it's first jump</summary>
		public bool HasJumped;
		/// <summary>If the car has executed it's second jump</summary>
		public bool HasDoubleJumped;
		/// <summary>If the car has been demolished, and hasn't respawned yet</summary>
		public bool IsDemolished;
		/// <summary>If the car is currently supersonic, and therefore can demolish a car</summary>
		public bool IsSupersonic;

		/// <summary>The car's score on the scoreboard</summary>
		public int Score { get; private set; }
		/// <summary>How many goals the car has scored</summary>
		public int Goals { get; private set; }
		/// <summary>How many own goals the car has scored</summary>
		public int OwnGoals { get; private set; }
		/// <summary>How many assists the car has</summary>
		public int Assists { get; private set; }
		/// <summary>How many saves the car has</summary>
		public int Saves { get; private set; }
		/// <summary>How many shots the car has</summary>
		public int Shots { get; private set; }
		/// <summary>How many times the car has demolished another car</summary>
		public int Demolitions { get; private set; }

		private Vec3 _hitboxDimensions;
		private Vec3 _hitboxOffset;

		/// <summary>Initializes an empty car object</summary>
		public Car()
		{
			Location = Vec3.Zero;
			Velocity = Vec3.Zero;
			AngularVelocity = Vec3.Zero;
			LocalAngularVelocity = Vec3.Zero;
			Rotation = Vec3.Zero;
			Orientation = new Mat3x3(Rotation);

			Name = "";
			Index = 0;
			Team = 0;
			Boost = 0;
			IsBot = true;
			IsGrounded = false;
			HasJumped = false;
			HasDoubleJumped = false;
			IsDemolished = false;
			IsSupersonic = false;

			Score = 0;
			Goals = 0;
			OwnGoals = 0;
			Assists = 0;
			Saves = 0;
			Shots = 0;
			Demolitions = 0;

			_hitboxDimensions = Vec3.Zero;
			_hitboxOffset = Vec3.Zero;
		}

		/// <summary>
		/// Copies a car object, so we can use this one freely without worrying about the original being edited as well
		/// <para>PLEASE use this if you plan on manipulating any of the cars in the "Cars" static class</para>
		/// </summary>
		public Car(Car originalCar)
		{
			Location = originalCar.Location;
			Velocity = originalCar.Velocity;
			AngularVelocity = originalCar.AngularVelocity;
			LocalAngularVelocity = originalCar.LocalAngularVelocity;
			Rotation = originalCar.Rotation;
			Orientation = new Mat3x3(Rotation);

			Name = originalCar.Name;
			Index = originalCar.Index;
			Team = originalCar.Team;
			Boost = originalCar.Boost;
			IsBot = originalCar.IsBot;
			IsGrounded = originalCar.IsGrounded;
			HasJumped = originalCar.HasJumped;
			HasDoubleJumped = originalCar.HasDoubleJumped;
			IsDemolished = originalCar.IsDemolished;
			IsSupersonic = originalCar.IsSupersonic;

			Score = originalCar.Score;
			Goals = originalCar.Goals;
			OwnGoals = originalCar.OwnGoals;
			Assists = originalCar.Assists;
			Saves = originalCar.Saves;
			Shots = originalCar.Shots;
			Demolitions = originalCar.Demolitions;

			_hitboxDimensions = originalCar._hitboxDimensions;
			_hitboxOffset = originalCar._hitboxOffset;
		}

		/// <summary>Initializes a new car with data from the packet</summary>
		public Car(int index, PlayerInfo playerInfo)
		{
			Location = playerInfo.Physics.Value.Location.HasValue ? new Vec3(playerInfo.Physics.Value.Location.Value) : Vec3.Zero;
			Velocity = playerInfo.Physics.Value.Velocity.HasValue ? new Vec3(playerInfo.Physics.Value.Velocity.Value) : Vec3.Zero;
			AngularVelocity = playerInfo.Physics.Value.AngularVelocity.HasValue ? new Vec3(playerInfo.Physics.Value.AngularVelocity.Value) : Vec3.Zero;
			Rotation = playerInfo.Physics.Value.Rotation.HasValue ? new Vec3(playerInfo.Physics.Value.Rotation.Value) : Vec3.Zero;
			Orientation = new Mat3x3(Rotation);
			LocalAngularVelocity = Local(AngularVelocity);

			Name = playerInfo.Name;
			Index = index;
			Team = playerInfo.Team;
			Boost = playerInfo.Boost;
			IsBot = playerInfo.IsBot;
			IsGrounded = playerInfo.HasWheelContact;
			HasJumped = playerInfo.Jumped;
			HasDoubleJumped = playerInfo.DoubleJumped;
			IsDemolished = playerInfo.IsDemolished;
			IsSupersonic = playerInfo.IsSupersonic;

			Score = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Score : 0;
			Goals = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Goals : 0;
			OwnGoals = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.OwnGoals : 0;
			Assists = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Assists : 0;
			Saves = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Saves : 0;
			Shots = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Shots : 0;
			Demolitions = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Demolitions : 0;

			_hitboxDimensions = playerInfo.Hitbox.HasValue ? new Vec3(playerInfo.Hitbox.Value.Length, playerInfo.Hitbox.Value.Width, playerInfo.Hitbox.Value.Height) : Vec3.Zero;
			_hitboxOffset = playerInfo.HitboxOffset.HasValue ? new Vec3(playerInfo.HitboxOffset.Value) : Vec3.Zero;
		}

		/// <summary>Updates the car with data from the packet</summary>
		public void Update(PlayerInfo playerInfo)
		{
			Location = playerInfo.Physics.Value.Location.HasValue ? new Vec3(playerInfo.Physics.Value.Location.Value) : Location;
			Velocity = playerInfo.Physics.Value.Velocity.HasValue ? new Vec3(playerInfo.Physics.Value.Velocity.Value) : Velocity;
			AngularVelocity = playerInfo.Physics.Value.AngularVelocity.HasValue ? new Vec3(playerInfo.Physics.Value.AngularVelocity.Value) : AngularVelocity;
			Rotation = playerInfo.Physics.Value.Rotation.HasValue ? new Vec3(playerInfo.Physics.Value.Rotation.Value) : Rotation;
			Orientation = new Mat3x3(Rotation);
			LocalAngularVelocity = Local(AngularVelocity);

			Boost = playerInfo.Boost;
			IsBot = playerInfo.IsBot;
			IsGrounded = playerInfo.HasWheelContact;
			HasJumped = playerInfo.Jumped;
			HasDoubleJumped = playerInfo.DoubleJumped;
			IsDemolished = playerInfo.IsDemolished;
			IsSupersonic = playerInfo.IsSupersonic;

			Score = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Score : Score;
			Goals = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Goals : Goals;
			OwnGoals = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.OwnGoals : OwnGoals;
			Assists = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Assists : Assists;
			Saves = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Saves : Saves;
			Shots = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Shots : Shots;
			Demolitions = playerInfo.ScoreInfo.HasValue ? playerInfo.ScoreInfo.Value.Demolitions : Demolitions;

			_hitboxDimensions = playerInfo.Hitbox.HasValue ? new Vec3(playerInfo.Hitbox.Value.Length, playerInfo.Hitbox.Value.Width, playerInfo.Hitbox.Value.Height) : _hitboxDimensions;
			_hitboxOffset = playerInfo.HitboxOffset.HasValue ? new Vec3(playerInfo.HitboxOffset.Value) : _hitboxOffset;
		}

		/// <summary>Gives the vector back in local coordinates relative to the car. 
		/// <para>x is now towards where the car is facing, y is towards the right of the car, and z is where the roof of the car is facing</para>
		/// </summary>
		public Vec3 Local(Vec3 vec)
		{
			return Orientation.Dot(vec);
		}

		/// <summary>Predicts when the car is going to land. returns 0 if it is on the ground already</summary>
		public float PredictLandingTime()
		{
			if (IsGrounded)
				return 0; 

			// How much time before the car lands on the ground
			float groundLandingTime = Utils.Quadratic(Game.Gravity.z / 2, Velocity.z, Location.z - 15)[1];
			// How much time before the car lands on the ceiling. -1 if the car isn't going to land on the ceiling
			float ceilingLandingTime = Utils.Quadratic(Game.Gravity.z / 2, Velocity.z, Location.z + 15 - Field.Height)[1];
			// How long until the car lands on the ceiling/floor
			float landingTime = ceilingLandingTime < 0 ? groundLandingTime : ceilingLandingTime;
			// The location where the car will land, on either the ground or the ceiling
			Vec3 landingPos = PredictLocation(landingTime);

			if (!Field.InField(landingPos, 150))
			{
				// If the landing position if outside of the field, we are going to be landing on a wall
				Surface landingSurface = Field.FindLandingSurface(this);
				landingTime = MathF.Max((Location - landingSurface.Limit(Location)).Dot(landingSurface.Normal) / Velocity.Dot(-landingSurface.Normal), 0);
			}

			return landingTime;
		}

		/// <summary>Predicts where the car is going to land. returns it's current position if it is on the ground already</summary>
		public Vec3 PredictLandingPosition()
		{
			return PredictLocation(PredictLandingTime());
		}

		/// <summary>Predicts the location and velocity of the car after a certain amount of time</summary>
		public Car Predict(float time)
		{
			return new Car(this) { Location = Location + Velocity * time + Game.Gravity * 0.5f * time * time, Velocity = Velocity + Game.Gravity * time };
		}

		/// <summary>Predicts the location of the car after a certain amount of time</summary>
		public Vec3 PredictLocation(float time)
		{
			return Location + Velocity * time + Game.Gravity * 0.5f * time * time;
		}

		/// <summary>Predicts the velocity of the car after a certain amount of time</summary>
		public Vec3 PredictVelocity(float time)
		{
			return Velocity + Game.Gravity * time;
		}

		/// <summary>Estimates the location of the car after dodging in the same direction that the car is going in</summary>
		public Vec3 LocationAfterDodge()
		{
			return Location + (Velocity + Velocity.FlatNorm() * 500).Cap(0, Car.MaxSpeed) * 1.3f;
		}

		/// <summary>Predicts the location of the car after jumping</summary>
		/// <param name="elapsed">The amount of time we have already been jumping. 0 if we haven't started jumping</param>
		public Vec3 LocationAfterJump(float time, float elapsed)
		{
			float jumpTimeRemaining = Utils.Cap(JumpMaxDuration - elapsed, 0, JumpMaxDuration);
			float stickTimeRemaining = Utils.Cap(0.05f - elapsed, 0, 0.05f);
			return Location + Velocity * time + Game.Gravity * 0.5f * MathF.Pow(time, 2) +
				(IsGrounded ? (Up * JumpVel * time) : Vec3.Zero) +
				Up * JumpAccel * jumpTimeRemaining * (time - 0.5f * jumpTimeRemaining) -
				Up * StickyAccel * stickTimeRemaining * (time - 0.5f * stickTimeRemaining);
		}

		/// <summary>Predicts the location of the car after double jumping</summary>
		/// <param name="elapsed">The amount of time we have already been jumping. 0 if we haven't started jumping</param>
		public Vec3 LocationAfterDoubleJump(float time, float elapsed)
		{
			float jumpTimeRemaining = Utils.Cap(JumpMaxDuration - elapsed, 0, JumpMaxDuration);
			float stickTimeRemaining = Utils.Cap(0.05f - elapsed, 0, 0.05f);
			return Location + Velocity * time + Game.Gravity * 0.5f * MathF.Pow(time, 2) +
				(IsGrounded ? (Up * JumpVel * time) : Vec3.Zero) +
				Up * JumpAccel * jumpTimeRemaining * (time - 0.5f * jumpTimeRemaining) -
				Up * StickyAccel * stickTimeRemaining * (time - 0.5f * stickTimeRemaining) +
				(!HasDoubleJumped ? Up * JumpVel * (time - jumpTimeRemaining) : Vec3.Zero);
		}

		/// <summary>Predicts the velocity of the car after jumping</summary>
		/// <param name="elapsed">The amount of time we have already been jumping. 0 if we haven't started jumping</param>
		public Vec3 VelocityAfterJump(float time, float elapsed)
		{
			float jumpTimeRemaining = Utils.Cap(JumpMaxDuration - elapsed, 0, JumpMaxDuration);
			float stickTimeRemaining = Utils.Cap(0.05f - elapsed, 0, 0.05f);
			return Velocity + Game.Gravity * time + Up * (IsGrounded ? JumpVel : 0) + Up * JumpAccel * jumpTimeRemaining - Up * StickyAccel * stickTimeRemaining;
		}

		/// <summary>Predicts the velocity of the car after double jumping</summary>
		/// <param name="elapsed">The amount of time we have already been jumping. 0 if we haven't started jumping</param>
		public Vec3 VelocityAfterDoubleJump(float time, float elapsed)
		{
			float jumpTimeRemaining = Utils.Cap(JumpMaxDuration - elapsed, 0, JumpMaxDuration);
			float stickTimeRemaining = Utils.Cap(0.05f - elapsed, 0, 0.05f);
			return Velocity + Game.Gravity * time + Up * JumpVel * (IsGrounded ? 2 : 1) + Up * JumpAccel * jumpTimeRemaining - Up * StickyAccel * stickTimeRemaining;
		}
	}
}