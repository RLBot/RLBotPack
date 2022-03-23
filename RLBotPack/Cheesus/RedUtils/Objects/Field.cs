using System;
using System.Linq;
using System.Collections.Generic;
using rlbot.flat;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>Contains static properties related to the field, like boost pads, goals, etc</summary>
	public static class Field
	{
		/// <summary>The length of the field, from one goal to the other</summary>
		public const float Length = 10240;
		/// <summary>The width of the field, from one side wall to the other</summary>
		public const float Width = 8192;
		/// <summary>The total height of the field</summary>
		public const float Height = 1950;

		/// <summary>The corner planes intersect the axes at ±8064</summary>
		public const float CornerIntersection = 8064;
		/// <summary>The wall length of the corners</summary>
		public const float CornerLength = 1629;
		/// <summary>The length of the corners on the x axis or y axis</summary>
		public const float CornerWidth = 1152;

		/// <summary>The blue goal, and the orange goal (in that order)</summary>
		public static Goal[] Goals { get; private set; }
		/// <summary>The blue team's goal</summary>
		public static Goal BlueGoal => Goals[0];
		/// <summary>The orange team's goal</summary>
		public static Goal OrangeGoal => Goals[1];

		/// <summary>All of the big and small boost pads on the field</summary>
		public static List<Boost> Boosts { get; private set; }

		/// <summary>All of the surfaces in the arena</summary>
		public static Dictionary<string,Surface> Surfaces { get; private set; }
		/// <summary>All of the drivable surfaces in the arena</summary>
		public static Dictionary<string, Surface> DrivableSurfaces { get; private set; }

		static Field()
		{
			Goals = new Goal[] { new Goal(0), new Goal(1) };
			Boosts = new List<Boost>();

			Surfaces = new Dictionary<string, Surface>
			{
				{ "Ground", new Surface("Ground", new Vec3(0, 0, 0), Vec3.Up, new Vec3(Width, Length), Vec3.X, Vec3.Y) },
				{ "Ceiling", new Surface("Ceiling", new Vec3(0, 0, Height), -Vec3.Up, new Vec3(Width, Length), Vec3.X, Vec3.Y) },
				{ "Orange Backboard", new Surface("Orange Backboard", new Vec3(0, Length / 2, Height / 2 + Goal.Height / 2), new Vec3(0, -1, 0), new Vec3(Goal.Width, Height - Goal.Height), Vec3.X, Vec3.Z) },
				{ "Orange Right Backwall", new Surface("Orange Right Backwall", new Vec3(Width / 4 + Goal.Width / 2 - CornerWidth + 200, Length / 2, Height / 2), new Vec3(0, -1, 0), new Vec3(Width / 2 - Goal.Width / 2 - CornerWidth, Height), Vec3.X, Vec3.Z) },
				{ "Orange Left Backwall", new Surface("Orange Left Backwall", new Vec3(-Width / 4 - Goal.Width / 2 + CornerWidth - 200, Length / 2, Height / 2), new Vec3(0, -1, 0), new Vec3(Width / 2 - Goal.Width / 2 - CornerWidth, Height), Vec3.X, Vec3.Z) },
				{ "Blue Backboard", new Surface("Blue Backboard", new Vec3(0, -Length / 2, Height / 2 + Goal.Height / 2), new Vec3(0, 1, 0), new Vec3(Goal.Width, Height - Goal.Height), Vec3.X, Vec3.Z) },
				{ "Blue Right Backwall", new Surface("Blue Right Backwall", new Vec3(-Width / 4 - Goal.Width / 2 + CornerWidth - 200, -Length / 2, Height / 2), new Vec3(0, 1, 0), new Vec3(Width / 2 - Goal.Width / 2 - CornerWidth, Height), Vec3.X, Vec3.Z) },
				{ "Blue Left Backwall", new Surface("Blue Left Backwall", new Vec3(Width / 4 + Goal.Width / 2 - CornerWidth + 200, -Length / 2, Height / 2), new Vec3(0, 1, 0), new Vec3(Width / 2 - Goal.Width / 2 - CornerWidth, Height), Vec3.X, Vec3.Z) },
				{ "Right Orange Sidewall", new Surface("Right Orange Sidewall", new Vec3(Width / 2, 0, Height / 2), new Vec3(-1, 0, 0), new Vec3(Height, Length), Vec3.Z, Vec3.Y) },
				{ "Right Blue Sidewall", new Surface("Right Blue Sidewall", new Vec3(-Width / 2, 0, Height / 2), new Vec3(1, 0, 0), new Vec3(Height, Length), Vec3.Z, Vec3.Y) },
				{
					"Right Orange Corner",
					new Surface("Right Orange Corner",new Vec3(Width / 2 - CornerWidth / 2, Length / 2 - CornerWidth / 2, Height / 2), new Vec3(-MathF.Sqrt(2) / 2, -MathF.Sqrt(2) / 2, 0),
				new Vec3(CornerLength, Height), new Vec3(-MathF.Sqrt(2) / 2, MathF.Sqrt(2) / 2, 0), Vec3.Z)
				},
				{
					"Left Orange Corner",
					new Surface("Left Orange Corner", new Vec3(-Width / 2 + CornerWidth / 2, Length / 2 - CornerWidth / 2, Height / 2), new Vec3(MathF.Sqrt(2) / 2, -MathF.Sqrt(2) / 2, 0),
				new Vec3(CornerLength, Height), new Vec3(MathF.Sqrt(2) / 2, MathF.Sqrt(2) / 2, 0), Vec3.Z)
				},
				{
					"Right Blue Corner",
					new Surface("Right Blue Corner", new Vec3(-Width / 2 + CornerWidth / 2, -Length / 2 + CornerWidth / 2, Height / 2), new Vec3(MathF.Sqrt(2) / 2, MathF.Sqrt(2) / 2, 0),
				new Vec3(CornerLength, Height), new Vec3(MathF.Sqrt(2) / 2, -MathF.Sqrt(2) / 2, 0), Vec3.Z)
				},
				{
					"Left Blue Corner",
					new Surface("Left Blue Corner", new Vec3(Width / 2 - CornerWidth / 2, -Length / 2 + CornerWidth / 2, Height / 2), new Vec3(-MathF.Sqrt(2) / 2, MathF.Sqrt(2) / 2, 0),
				new Vec3(CornerLength, Height), new Vec3(-MathF.Sqrt(2) / 2, -MathF.Sqrt(2) / 2, 0), Vec3.Z)
				},
				{ "Orange Goal Ground", new Surface("Orange Goal Ground", new Vec3(0, Length / 2 + Goal.Depth / 2, 0), Vec3.Up, new Vec3(Goal.Width, Goal.Depth), Vec3.X, Vec3.Y) },
				{ "Blue Goal Ground", new Surface("Blue Goal Ground", new Vec3(0, -Length / 2 - Goal.Depth / 2, 0), Vec3.Up, new Vec3(Goal.Width, Goal.Depth), Vec3.X, Vec3.Y) }
			};

			DrivableSurfaces = new Dictionary<string, Surface>(Surfaces);
			DrivableSurfaces.Remove("Ceiling");
		}

		/// <summary>Initializes the boost pads with data from the FieldInfo struct, provided by our bot</summary>
		public static void Initialize(FieldInfo fieldInfo)
		{
			for (int i = 0; i < fieldInfo.BoostPadsLength; i++)
			{
				if (fieldInfo.BoostPads(i).HasValue)
				{
					Boosts.Add(new Boost(i, fieldInfo.BoostPads(i).Value));
				}
				else
				{
					// Sometimes the bot isn't given the boost pads initially, but we still want to initialize them all in case they become avaliable again
					Boosts.Add(new Boost(i));
				}
			}
		}

		/// <summary>Updates the boost pads with data from the packet</summary>
		public static void Update(GameTickPacket packet)
		{
			for (int i = 0; i < packet.BoostPadStatesLength; i++)
			{
				if (packet.BoostPadStates(i).HasValue)
				{
					Boosts[i].Update(packet.BoostPadStates(i).Value);
				}
			}
		}

		/// <summary>Returns the side of the field which belongs to the team given. (-1 for blue, 1 for orange)</summary>
		public static int Side(int team)
		{
			return 2 * team - 1;
		}

		/// <summary>Whether or not a sphere resides within the field</summary>
		/// <param name="pos">The center of the sphere</param>
		/// <param name="radius">The radius of the sphere</param>
		public static bool InField(Vec3 pos, float radius)
		{
			Vec3 point = Vec3.Abs(pos);
			if (point.x > Width / 2 - radius)
			{
				return false;
			}
			if (point.y > Length / 2 + Goal.Depth - radius)
			{
				return false;
			}
			if ((point.x > Goal.Width / 2 - radius || point.z > Goal.Height - radius) && point.y > Length / 2 - radius)
			{
				return false;
			}
			if (point.x + point.y > CornerIntersection - radius)
			{
				return false;
			}
			return true;
		}

		/// <summary>Whether or not any part of a sphere resides within a goal</summary>
		/// <param name="pos">The center of the sphere</param>
		/// <param name="radius">The radius of the sphere</param>
		public static bool InGoal(Vec3 pos, float radius)
		{
			Vec3 point = Vec3.Abs(pos);

			return point.x < Goal.Width / 2 + radius && point.y > Length / 2 - radius && point.y < Length / 2 + Goal.Depth + radius && point.z < Goal.Height + radius;
		}

		/// <summary>Returns the closest drivable surface to a given point 
		/// <para>Excludes the ceiling, since it isn't a drivable surface. If you want to include the ceiling, use the overload where you can exclude surfaces, and pass in an empty surfaces array</para>
		/// </summary>
		public static Surface NearestSurface(Vec3 pos)
		{
			Surface closestSurface = DrivableSurfaces.First().Value;
			foreach (Surface surface in DrivableSurfaces.Values)
			{
				if (pos.Dist(closestSurface.Limit(pos)) > pos.Dist(surface.Limit(pos)))
				{
					closestSurface = surface;
				}
			}

			return closestSurface;
		}

		/// <summary>Returns the closest surface to a given point</summary>
		/// <param name="excludedSurfaces">A list of surfacaes you don't want to check</param>
		public static Surface NearestSurface(Vec3 pos, Surface[] excludedSurfaces)
		{
			List<Surface> filteredSurfaces = new List<Surface>(Surfaces.Values);
			foreach (Surface surface in excludedSurfaces) filteredSurfaces.Remove(surface);

			Surface closestSurface = filteredSurfaces.First();
			foreach (Surface surface in filteredSurfaces)
			{
				if (pos.Dist(closestSurface.Limit(pos)) > pos.Dist(surface.Limit(pos)))
				{
					closestSurface = surface;
				}
			}

			return closestSurface;
		}

		/// <summary>Returns the surface that the car will land on</summary>
		public static Surface FindLandingSurface(Car car)
		{
			if (car.IsGrounded)
				return NearestSurface(car.Location, Array.Empty<Surface>()); // If the car is already on the ground, return the nearest surface

			// How much time before the car lands on the ground
			float groundLandingTime = Utils.Quadratic(Game.Gravity.z / 2, car.Velocity.z, car.Location.z - 15)[1];
			// How much time before the car lands on the ceiling. -1 if the car isn't going to land on the ceiling
			float ceilingLandingTime = Utils.Quadratic(Game.Gravity.z / 2, car.Velocity.z, car.Location.z + 15 - Height)[1];
			// Gets the landing surface and time, for either the ground or ceiling (depending on which we land on first)
			Surface landingSurface = ceilingLandingTime < 0 ? Surfaces["Ground"] : Surfaces["Ceiling"];
			float landingTime = ceilingLandingTime < 0 ? groundLandingTime : ceilingLandingTime;
			// The location where the car will land, on either the ground or the ceiling
			Vec3 groundLanding = car.PredictLocation(landingTime);

			if (!InField(groundLanding, 150))
			{
				// If the landing position if outside of the field, we are going to be landing on a wall
				foreach (Surface surface in DrivableSurfaces.Values)
				{
					// Loop through every drivable surface, except for the ground (we already accounted for that)
					if (surface.Key == "Ground")
						continue;

					// Calculate how much time until we land on the surface
					float surfaceLandingTime = car.Location.Dist(surface.Limit(car.Location)) / car.Velocity.Dot(-surface.Normal);
					if (surfaceLandingTime > 0 && surfaceLandingTime < landingTime)
					{
						// Sets this as the next landing time
						landingTime = surfaceLandingTime;
						landingSurface = surface;
					}
				}
			}

			// Returns the nearest surface to the location at which we are going to land soonest
			return landingSurface;
		}

		/// <summary>Returns the closest point on any drivable surface
		/// <para>Excludes the ceiling, since it isn't a drivable surface. If you want to include the ceiling, use the overload where you can exclude surfaces, and pass in an empty surfaces array</para>
		/// </summary>
		public static Vec3 LimitToNearestSurface(Vec3 pos)
		{
			return NearestSurface(pos).Limit(pos);
		}

		/// <summary>Returns the closest point on any surface</summary>
		/// <param name="excludedSurfaces">A list of surfacaes you don't want to check</param>
		public static Vec3 LimitToNearestSurface(Vec3 pos, Surface[] excludedSurfaces)
		{
			return NearestSurface(pos, excludedSurfaces).Limit(pos);
		}

		/// <summary>Returns the surface distance between two points</summary>
		public static float DistanceBetweenPoints(Vec3 pos1, Vec3 pos2)
		{
			Surface startSurface = NearestSurface(pos1);
			Vec3 startPos = startSurface.Limit(pos1);
			Surface targetSurface = NearestSurface(pos2);
			Vec3 targetPos = targetSurface.Limit(pos2);
			Surface middleSurface = NearestSurface((startPos + targetPos) / 2);
			Vec3 middlePos = middleSurface.Limit((startPos + targetPos) / 2);

			return startPos.Dist(startSurface.Limit(middlePos)) + startSurface.Limit(middlePos).Dist(middleSurface.Limit(targetPos)) + middleSurface.Limit(targetPos).Dist(targetPos);
		}
	}

	/// <summary>A surface object</summary>
	public class Surface
	{
		/// <summary>The name of the surface</summary>
		public string Key
		{ get; private set; }
		/// <summary>The surface normal. Points out away from the surface</summary>
		public Vec3 Normal
		{ get; private set; }
		/// <summary>The center point of the surface</summary>
		public Vec3 Location
		{ get; private set; }
		/// <summary>The 2D size of the surface</summary>
		public Vec3 Size
		{ get; private set; }
		/// <summary>A vector pointing from the left to the right of the surface (or from the right to the left)</summary>
		public Vec3 Xdirection
		{ get; private set; }
		/// <summary>A vector pointing from the top to the bottom of the surface (or from the bottom to the top)</summary>
		public Vec3 Ydirection
		{ get; private set; }

		/// <summary>Initiliazes a new surface</summary>
		public Surface(string key, Vec3 location, Vec3 normal, Vec3 size, Vec3 xDirection, Vec3 yDirection)
		{
			Key = key;
			Location = location;
			Normal = normal;
			Size = size;
			Xdirection = xDirection;
			Ydirection = yDirection;
		}

		/// <summary>Returns the closest point on this surface to the position given</summary>
		public Vec3 Limit(Vec3 pos)
		{
			Vec3 posToSurace = pos - Location;

			return Location + Xdirection * Utils.Cap(Xdirection.Dot(posToSurace), -Size.x / 2, Size.x / 2) + Ydirection * Utils.Cap(Ydirection.Dot(posToSurace), -Size.y / 2, Size.y / 2);
		}
	}
}
