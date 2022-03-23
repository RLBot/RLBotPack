using System;
using System.Drawing;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>An action meant to drive the car to a certain location</summary>
	public class Drive : IAction
	{
		/// <summary>Whether or not we have arrived at our destination</summary>
		public bool Finished { get; private set; }
		/// <summary>Whether or not this action can currently be interrupted</summary>
		public bool Interruptible { get; private set; }

		/// <summary>The destination the car will drive to</summary>
		public Vec3 Target;
		/// <summary>The speed we intend to mantain while driving</summary>
		public float TargetSpeed;
		/// <summary>Whether or not we are going to drive backwards</summary>
		public bool Backwards;
		/// <summary>Whether or not we are going to allow dodges to increase speed</summary>
		public bool AllowDodges;
		/// <summary>Whether or not we are going to use any amount of boost neccesary to mantain our target speed</summary>
		public bool WasteBoost;
		/// <summary>This action's subaction, which could be a dodge, halfflip, speedflip, etc</summary>
		public IAction Action;

		/// <summary>How long we have spent driving on the ground</summary>
		private float timeOnGround = 0;

		/// <summary>How much time until we arrive at our destination</summary>
		public float TimeRemaining { get; private set; }

		/// <summary>Initializes a new drive action</summary>
		/// <param name="target">The destination the car will drive to</param>
		/// <param name="targetSpeed">The speed we intend to mantain while driving</param>
		/// <param name="allowDodges">Whether or not we are going to allow dodges to increase speed</param>
		/// <param name="wasteBoost">>Whether or not we are going to use any amount of boost neccesary to mantain our target speed</param>
		public Drive(Car car, Vec3 target, float targetSpeed = Car.MaxSpeed, bool allowDodges = true, bool wasteBoost = false)
		{
			Interruptible = true;
			Finished = false;

			Target = target;
			TargetSpeed = targetSpeed;

			float forwardsEta = GetEta(car, target, false, false);
			float backwardsEta = GetEta(car, target, true, false);

			// Only go backwards under very specific circumstances, because otherwise the bot goes backwards far too often
			Backwards = backwardsEta + 0.5f < forwardsEta && car.Forward.Dot(car.Velocity) < 500 && car.Forward.FlatAngle(car.Location.Direction(target), car.Up) > MathF.PI * 0.6f;
			AllowDodges = allowDodges;
			WasteBoost = wasteBoost;

			Action = null;
		}

		/// <summary>Drives the car toward the target destination</summary>
		public void Run(RUBot bot)
		{
			// Calculates how much time we have before we should arrive
			TimeRemaining = Distance(bot.Me) / TargetSpeed;

			// Finds the nearest surface to the target for some calculations later
			Surface targetSurface = Field.NearestSurface(Target);

			// When no subaction is set, drive normally and look for a subaction
			if (Action == null)
			{
				if (bot.Me.IsGrounded)
					timeOnGround += bot.DeltaTime;

				// Gets some other relavent surfaces for calculations
				Surface nextSurface = targetSurface;
				Surface mySurface = Field.NearestSurface(bot.Me.Location);

				// Gets some other important values
				float carSpeed = bot.Me.Velocity.Length();
				float forwardSpeed = bot.Me.Velocity.Dot(bot.Me.Forward);

				// Limits the final target to the nearest surface
				Vec3 finalTarget = Field.LimitToNearestSurface(Target);
				// If we are on a differently orientated surface
				if (mySurface.Normal.Dot(targetSurface.Normal) < 0.95f)
				{
					// Finds the next surface we have to drive onto
					nextSurface = FindNextSurface(Field.LimitToNearestSurface(bot.Me.Location), finalTarget);
					finalTarget = nextSurface.Limit(finalTarget);
					Vec3 closestSurfacePoint = mySurface.Limit(finalTarget);
					// Adjust the final target so that the bot drives onto the surface properly
					finalTarget = closestSurfacePoint - nextSurface.Normal.FlatNorm(mySurface.Normal) * MathF.Max(closestSurfacePoint.Dist(finalTarget) - 75, 0);
				}
				if (mySurface.Key != targetSurface.Key)
				{
					// If the target might be around a corner, calculate where to aim so we don't hit a wall
					finalTarget = FindTargetAroundCorner(bot, finalTarget, nextSurface);
				}

				float turnRadius = TurnRadius(MathF.Abs(forwardSpeed));
				// Finds the point of rotation for our bot
				Vec3 nearestTurnCenter = mySurface.Limit(bot.Me.Location) + bot.Me.Right.FlatNorm(mySurface.Normal) * MathF.Sign(bot.Me.Right.Dot(finalTarget - bot.Me.Location)) * turnRadius;
				// Gets info on the landing of our car
				float landingTime = bot.Me.PredictLandingTime();

				if (Field.DistanceBetweenPoints(nearestTurnCenter, Target) > turnRadius - 40 && bot.Me.IsGrounded)
				{
					// If the target isn't within our turn radius, then just drive at our target speed
					bot.Throttle(TargetSpeed, Backwards);
				}
				else if (!bot.Me.IsGrounded)
				{
					// Protects us from errors
					TimeRemaining = float.IsNaN(TimeRemaining) ? 0.01f : TimeRemaining;
					bot.Throttle(Distance(bot.Me) / MathF.Max(TimeRemaining - landingTime, 0.01f));
				}
				else
				{
					// Otherwise, slow dowwn to turn sharper
					bot.Throttle(MathF.Max(SpeedFromTurnRadius(TurnRadius(bot.Me, Target)), 400), Backwards);
				}

				float angleToTarget;
				if (bot.Me.IsGrounded || bot.Me.Velocity.FlatLen() < 500)
				{
					// Aim at the final target assuming we shoukdn't recover
					angleToTarget = bot.AimAt(finalTarget, backwards: Backwards)[0];
				}
				else
				{
					// Otherwise, aim so we have a smooth landing
					Vec3 landingNormal = Field.FindLandingSurface(bot.Me).Normal;
					Vec3 targetDirection = Utils.Lerp(Utils.Cap(landingTime * 1.5f - 0.6f, 0, 0.75f), bot.Me.Velocity.FlatNorm(landingNormal), -Vec3.Up);
					bot.AimAt(bot.Me.Location + targetDirection, landingNormal);
					angleToTarget = bot.Me.Forward.Angle(targetDirection);
				}

				// Only boost when we are facing our target, and when we really need to
				bot.Controller.Boost = bot.Controller.Boost && (angleToTarget < 0.3f || (angleToTarget < 0.8f && !bot.Me.IsGrounded)) && !Backwards && WasteBoost;
				// Drift if the target is behind us, or when we need to turn really sharply
				bot.Controller.Handbrake = (MathF.Abs(angleToTarget) > 2 || (Field.DistanceBetweenPoints(nearestTurnCenter, Target) < turnRadius - 40 && SpeedFromTurnRadius(TurnRadius(bot.Me, Target)) < 400))
											&& mySurface.Normal.Dot(Vec3.Up) > 0.9f && bot.Me.Velocity.Normalize().Dot(bot.Me.Forward) > 0.9f;

				// Draws a debug line to represent the final target
				bot.Renderer.Line3D(finalTarget, finalTarget + Field.NearestSurface(finalTarget).Normal * 200, Color.LimeGreen);

				// Estimates where we'll be after dodging
				Vec3 predictedLocation = bot.Me.LocationAfterDodge();
				// Estimates how much time we have to dodge
				float timeLeft = bot.Me.Location.FlatDist(finalTarget) / MathF.Max(carSpeed + 500, 1410);
				float speedFlipTimeLeft = bot.Me.Location.FlatDist(finalTarget) / MathF.Max(carSpeed + 500 + MathF.Min(bot.Me.Boost, 40) * Car.BoostAccel / 2, 1410);

				if (AllowDodges && Field.InField(predictedLocation, 50) && carSpeed < 2000 && bot.Me.Location.z < 600 && Game.Gravity.z < -500 && MathF.Abs(bot.Me.Velocity.Dot(bot.Me.Up)) < 100)
				{
					// Look for dodges only if we won't hit a wall, and when we actually need to
					if (forwardSpeed > 0)
					{
						if (TargetSpeed > 100 + forwardSpeed)
						{
							// When we're moving forward, and need extra speed, look for dodges, speedflips, and wavedashes
							if (bot.Me.Location.z < 200 && bot.Me.IsGrounded && carSpeed > 1000 && bot.Me.Forward.FlatAngle(bot.Me.Location.Direction(finalTarget)) < 0.1f && timeOnGround > 0.2f)
							{
								// If we are on the ground, we rule out wavedashes, and look at dodges
								Dodge dodge = new Dodge(bot.Me.Location.FlatDirection(Target));

								if (speedFlipTimeLeft > SpeedFlip.Duration && bot.Me.Boost > 0 && Field.InField(predictedLocation, 500) && WasteBoost)
								{ 
									// Only speedflip if we have time, and have boost
									Action = new SpeedFlip(bot.Me.Location.FlatDirection(Target));
								}
								else if (timeLeft > dodge.Duration)
								{
									// Otherwise, dodge if we have time
									Action = dodge;
								}
							}
							else if (bot.Me.Location.z > 100 && !bot.Me.HasDoubleJumped && (!bot.Me.IsGrounded || bot.Me.Velocity.Dot(Vec3.Up) < 200))
							{
								// If we are on the wall, or if we are falling and have a dodge, look for a wavedash
								Wavedash wavedash = new Wavedash(bot.Me.Location.FlatDirection(Target));

								if (timeLeft > wavedash.Duration)
								{
									// Only wavedash if we have time to
									Action = wavedash;
								}
							}
						}
					}
					else if (bot.Me.Location.z < 200 && bot.Me.IsGrounded && carSpeed > 800 && Backwards && (-bot.Me.Forward).FlatAngle(bot.Me.Location.Direction(finalTarget)) < 0.1f && timeOnGround > 0.2f)
					{
						// If we're moving backwards, and are facing the right direction, check if we should halfflip
						if (timeLeft > HalfFlip.Duration)
						{
							// Only halfflip if we have time
							Action = new HalfFlip();
						}
					}
				}
			}
			else if (Action != null && Action.Finished)
			{
				// If our subaction has finished, reset it to null, and reset some other values
				Action = null;
				Backwards = false;
				timeOnGround = 0;
			}
			else if (Action != null)
			{
				// If we currently have a subaction, run it
				Action.Run(bot);
				if (Action is SpeedFlip)
				{
					// If it's a speedflip, add a little extra speed
					bot.Throttle(TargetSpeed + 500, Backwards);
				}
			}

			// Draws a debug line to represent the target
			bot.Renderer.Line3D(Field.LimitToNearestSurface(Target), Field.LimitToNearestSurface(Target) + targetSurface.Normal * 200, Color.LimeGreen);
			
			// Prevents this action from being interrupted during a dodge
			Interruptible = Action == null || Action.Interruptible;

			if (Field.LimitToNearestSurface(bot.Me.Location).Dist(Field.LimitToNearestSurface(Target)) < 100)
			{
				// If we have arrived at our destination, finish this action
				Finished = true;
			}
		}

		/// <summary>Finds the distance left to drive</summary>
		public float Distance(Car car)
		{
			return GetDistance(car, Target, Backwards);
		}

		/// <summary>Estimates the time left before we arrive, assuming we drive as fast as possible</summary>
		public float Eta(Car car)
		{
			return GetEta(car, Target, Backwards, AllowDodges);
		}

		/// <summary>Finds the next driving surface between a start point and a target point</summary>
		private static Surface FindNextSurface(Vec3 start, Vec3 target)
		{
			// Gets a point between the start and target points, then limits it to a surface
			Vec3 middle = Field.LimitToNearestSurface((start + target) / 2);

			// Chooses points along the line between the start and middle points, and then between the middle and target points
			for (float f = 0; f < 2; f += 0.25f)
			{
				// Gets the next position, then limits it to a surface
				Vec3 nextPos = Field.LimitToNearestSurface(start + (middle - start) * Utils.Cap(f, 0, 1) + (target - middle) * Utils.Cap(f - 1, 0, 1));
				if (Field.NearestSurface(nextPos).Normal.Dot(Field.NearestSurface(start).Normal) < 0.95f)
				{
					// return the first surface found that differs from the start surface
					return Field.NearestSurface(nextPos);
				}
			}

			// Otherwise, just give back the target's surface
			return Field.NearestSurface(target);
		}

		/// <summary>Finds target positions so that corners are navigated around nicely</summary>
		private static Vec3 FindTargetAroundCorner(RUBot bot, Vec3 finalTarget, Surface nextSurface)
		{
			Surface mySurface = Field.NearestSurface(bot.Me.Location);

			if (mySurface.Key == "Ground")
			{
				// If we are on the ground, we need to make sure not to hit the post on accident
				Goal goal = Field.Side(bot.Team) == MathF.Sign(finalTarget.y) ? bot.OurGoal : bot.TheirGoal;

				Vec3 enterLeftDirection = bot.Me.Location.Direction(goal.LeftPost - new Vec3(MathF.Sign(goal.LeftPost.x) * 100, MathF.Sign(goal.LeftPost.y) * 50));
				Vec3 enterRightDirection = bot.Me.Location.Direction(goal.RightPost - new Vec3(MathF.Sign(goal.RightPost.x) * 100, MathF.Sign(goal.RightPost.y) * 50));
				Vec3 exitLeftDirection = bot.Me.Location.Direction(goal.LeftPost + new Vec3(MathF.Sign(goal.LeftPost.x) * 60, -MathF.Sign(goal.LeftPost.y) * 50));
				Vec3 exitRightDirection = bot.Me.Location.Direction(goal.RightPost + new Vec3(MathF.Sign(goal.RightPost.x) * 60, -MathF.Sign(goal.RightPost.y) * 50));

				// Clamps the target direction so if the target is in the goal, we enter the goal without hitting the post
				// and if it's not in the goal we make sure we avoid the goal, and the posts
				Vec3 targetDirection = nextSurface.Key.Contains("Goal Ground") ?
									   bot.Me.Location.Direction(finalTarget).Clamp(enterLeftDirection, enterRightDirection, mySurface.Normal) :
									   bot.Me.Location.Direction(finalTarget).Clamp(exitRightDirection, exitLeftDirection, mySurface.Normal);

				// Return the adjusted target
				return bot.Me.Location + targetDirection.Rescale(bot.Me.Location.Dist(finalTarget));
			}
			else if (mySurface.Key.Contains("Goal Ground"))
			{
				// If we are in a goal, we gotta make sure not to hit the posts on our way out
				Goal goal = Field.Side(bot.Team) == MathF.Sign(bot.Me.Location.y) ? bot.OurGoal : bot.TheirGoal;

				Vec3 leftDirection = bot.Me.Location.Direction(goal.LeftPost - new Vec3(MathF.Sign(goal.LeftPost.x) * 100, MathF.Sign(goal.LeftPost.y) * 50));
				Vec3 rightDirection = bot.Me.Location.Direction(goal.RightPost - new Vec3(MathF.Sign(goal.RightPost.x) * 100, MathF.Sign(goal.RightPost.y) * 50));

				// Clamps the target direction between the goal posts, so we don't hit them
				Vec3 targetDirection = bot.Me.Location.Direction(finalTarget).Clamp(rightDirection, leftDirection, mySurface.Normal);

				// Return the adjusted target
				return bot.Me.Location + targetDirection.Rescale(bot.Me.Location.Dist(finalTarget));
			}
			else if (mySurface.Key.Contains("Backboard") || mySurface.Key.Contains("Backwall"))
			{
				// If we are on the backboard, or the backwall, we gotta make sure not to accidentally fall into the goal
				Goal goal = Field.Side(bot.Team) == MathF.Sign(bot.Me.Location.y) ? bot.OurGoal : bot.TheirGoal;

				Vec3 leftDirection;
				Vec3 rightDirection;
				// Depending on which surface we are on, we choose different left and right direction to clamp between
				if (mySurface.Key.Contains("Left Backwall"))
				{
					leftDirection = bot.Me.Location.Direction(goal.TopRightCorner + new Vec3(MathF.Sign(goal.TopRightCorner.x) * 50, 0, 50));
					rightDirection = bot.Me.Location.Direction(goal.BottomRightCorner + new Vec3(MathF.Sign(goal.BottomRightCorner.x) * 50, 0, -50));
				}
				else if (mySurface.Key.Contains("Right Backwall"))
				{
					leftDirection = bot.Me.Location.Direction(goal.BottomLeftCorner + new Vec3(MathF.Sign(goal.BottomLeftCorner.x) * 50, 0, -50));
					rightDirection = bot.Me.Location.Direction(goal.TopLeftCorner + new Vec3(MathF.Sign(goal.TopLeftCorner.x) * 50, 0, 50));
				}
				else
				{
					leftDirection = bot.Me.Location.Direction(goal.TopLeftCorner + new Vec3(MathF.Sign(goal.TopLeftCorner.x) * 50, 0, 50));
					rightDirection = bot.Me.Location.Direction(goal.TopRightCorner + new Vec3(MathF.Sign(goal.TopRightCorner.x) * 50, 0, 50));
				}

				// Clamps the target direction between the directions chosen earlier
				Vec3 targetDirection = bot.Me.Location.Direction(finalTarget).Clamp(leftDirection, rightDirection, mySurface.Normal);

				// Return the adjusted target
				return bot.Me.Location + targetDirection.Rescale(bot.Me.Location.Dist(finalTarget));
			}

			// If none of those apply, just return the target
			return finalTarget;
		}

		/// <summary>Finds the distance the car will travel in order to get to the given target</summary>
		public static float GetDistance(Car car, Vec3 target)
		{
			float forwardsEta = GetEta(car, target, false, false);
			float backwardsEta = GetEta(car, target, true, false);

			bool backwards = backwardsEta + 0.5f < forwardsEta && car.Forward.Dot(car.Velocity) < 500 && car.Forward.FlatAngle(car.Location.Direction(target), car.Up) > MathF.PI * 0.6f;

			return GetDistance(car, target, backwards);
		}

		/// <summary>Finds the distance the car will travel in order to get to the given target</summary>
		/// <param name="backwards">Whether or not we are planning to drive backwards</param>
		public static float GetDistance(Car car, Vec3 target, bool backwards)
		{
			return GetDistance(car, target, backwards, out _, out _);
		}

		/// <summary>Finds the distance the car will travel in order to get to the given target</summary>
		/// <param name="backwards">Whether or not we are planning to drive backwards</param>
		/// <param name="angle",>Gives us the approximate angle of our turn in order to face the target</param>
		/// <param name="radius">Gives us the approximate radius of our turn in order to face the target</param>
		public static float GetDistance(Car car, Vec3 target, bool backwards, out float angle, out float radius)
		{
			// Puts our target on the nearest surface
			target = Field.LimitToNearestSurface(target);
			// Gets the position of the car when it starts driving
			Vec3 carPos = car.PredictLandingPosition();
			// Gets the nearest surface to the car when it starts driving
			Surface carSurface = Field.FindLandingSurface(car);
			Vec3 surfaceNormal = carSurface.Normal;
			// Calculates the forward and right direction for the car when it start driving
			Vec3 carForward = car.IsGrounded ? car.Forward : (car.Velocity.FlatLen() > 500 ? car.Velocity.FlatNorm(surfaceNormal) : car.Location.FlatDirection(target, surfaceNormal));
			Vec3 carRight = carForward.Cross(car.IsGrounded ? -car.Up : -surfaceNormal).Normalize();

			// Grabs the current speed of the car, as well as an estimate of the angle of the next turn
			float currentSpeed = car.Velocity.Dot(carForward);
			angle = (backwards ? -carForward : carForward).FlatAngle(target - carPos, surfaceNormal);
			// Using those values, we estimate the average turn speed of the car, and use that to calculate the average turn radius
			float turnSpeed = backwards ? SpeedAfterTurn(-currentSpeed, angle, 0.4f) : SpeedAfterTurn(currentSpeed, angle, 0.5f);
			radius = TurnRadius(turnSpeed);

			// Finds the point of rotation for our car
			Vec3 nearestTurnCenter = carPos + carRight * MathF.Sign(carRight.Dot(target - carPos)) * radius;
			Vec3 limitedTurnCenter = carSurface.Limit(nearestTurnCenter);
			// If the calculated point of rotation is outside the map, that means the point of rotation is on a different surface from the car
			if (nearestTurnCenter.Dist(limitedTurnCenter) > 1)
			{
				// Calculates the direction up along the wall, towards the actual point of rotation
				Vec3 normal = limitedTurnCenter.Direction(Field.LimitToNearestSurface(nearestTurnCenter + carSurface.Normal * 500));
				// Estimates the actual point of rotaation
				nearestTurnCenter = limitedTurnCenter + normal * nearestTurnCenter.Dist(limitedTurnCenter);
			}

			// Gets the distance between the point of rotation and the target
			float distance = Field.DistanceBetweenPoints(nearestTurnCenter, target);

			if (distance < radius)
			{
				// If we are too closse to the target, adjust our turn radius and point of rotation
				radius = TurnRadius(car, target);
				nearestTurnCenter = carPos + carRight * MathF.Sign(carRight.Dot(target - carPos)) * radius;

				distance = Field.DistanceBetweenPoints(nearestTurnCenter, target);
			}

			// Does some fancy math things that calculates the actual turn angle
			angle = MathF.Abs((carPos - nearestTurnCenter).FlatAngle(target - nearestTurnCenter, surfaceNormal) - ((target - carPos).Dot(backwards ? -carForward : carForward) < 0 ? 2 * MathF.PI : 0));
			angle -= MathF.Acos(Utils.Cap(radius / distance, 0, 1));
			angle = Utils.Cap(angle, 0, 2 * MathF.PI);

			// Returns an estimate of the actual distance needed to drive, including the turn
			return MathF.Sqrt(MathF.Max(MathF.Pow(distance, 2) - MathF.Pow(radius, 2), 0)) + radius * angle;
		}

		/// <summary>Estimates how long it should take do drive to a given target, assuming we drive at max speed</summary>
		public static float GetEta(Car car, Vec3 target)
		{
			float forwardsEta = GetEta(car, target, false, false);
			float backwardsEta = GetEta(car, target, true, false);

			// Only go backwards under very specific circumstances, because otherwise the bot goes backwards far too often
			bool backwards = backwardsEta + 0.5f < forwardsEta && car.Forward.Dot(car.Velocity) < 500 && car.Forward.FlatAngle(car.Location.Direction(target), car.Up) > MathF.PI * 0.6f;

			return GetEta(car, target, backwards, true);
		}

		/// <summary>Estimates how long it should take do drive to a given target, assuming we drive at max speed</summary>
		/// <param name="allowDodges">Whether or not we plan on using dodges to gain speed</param>
		public static float GetEta(Car car, Vec3 target, bool allowDodges)
		{
			float forwardsEta = GetEta(car, target, false, false);
			float backwardsEta = GetEta(car, target, true, false);

			// Only go backwards under very specific circumstances, because otherwise the bot goes backwards far too often
			bool backwards = backwardsEta + 0.5f < forwardsEta && car.Forward.Dot(car.Velocity) < 500 && car.Forward.FlatAngle(car.Location.Direction(target), car.Up) > MathF.PI * 0.6f;

			return GetEta(car, target, backwards, allowDodges);
		}

		/// <summary>Estimates how long it should take do drive to a given target, assuming we drive at max speed</summary>
		/// <param name="allowDodges">Whether or not we plan on using dodges to gain speed</param>
		/// <param name="backwards">Whether or not we are planning to drive backwards</param>
		public static float GetEta(Car car, Vec3 target, bool backwards, bool allowDodges)
		{
			// Gets the distance to drive to the given target, as well and the angle, and radius of the turn we have to make to face the target
			float distance = GetDistance(car, target, backwards, out float angle, out float radius);
			// Seperates the distance from the turn distance
			float turnDistance = angle * radius;
			distance -= turnDistance;

			// Gets the normal of the nearest surface to the car when it starts driving
			Vec3 surfaceNormal = car.IsGrounded ? Field.NearestSurface(car.Location).Normal : Field.FindLandingSurface(car).Normal;
			// Calculates the car's forward direction when it starts driving, and it's velocity in that direction
			Vec3 carForward = car.IsGrounded ? car.Forward : (car.Velocity.FlatLen() > 500 ? car.Velocity.FlatNorm(surfaceNormal) : car.Location.FlatDirection(target, surfaceNormal));
			float currentSpeed = carForward.Dot(car.Velocity);
			float landingTime = car.PredictLandingTime();

			if (backwards)
			{
				// Calculates the speed it will be moving at after the turn
				float speed = MathF.Max(SpeedAfterTurn(-currentSpeed, angle, 0.8f), 1400);
				// Estimates how long it will take to drive to the target backwards
				return landingTime + turnDistance / MathF.Max(SpeedFromTurnRadius(radius), 400) + distance / speed;
			}
			else
			{
				// Calculates the minimum speed of the car after the turn
				float minSpeed = MathF.Max(SpeedAfterTurn(currentSpeed, angle), 1400);
				// Calculates the maximum possible speed of the car after the turn
				float finSpeed = Utils.Cap(minSpeed + Car.BoostAccel * car.Boost / Car.BoostConsumption, 1400, Car.MaxSpeed);
				// Calculates the maximum possible distance covered while boosting
				float distanceWhileBoosting = (MathF.Pow(finSpeed, 2) - MathF.Pow(minSpeed, 2)) / (2 * Car.BoostAccel);

				if (distance < distanceWhileBoosting)
				{
					// Calculates the actual maxmimum speed of the car after the turn
					finSpeed = Utils.Cap(MathF.Sqrt(MathF.Max(MathF.Pow(minSpeed, 2) + 2 * Car.BoostAccel * distance, 0)), 1400, Car.MaxSpeed);
					// Estimates how long it will take to drive to the target while boosting
					return landingTime + turnDistance / MathF.Max(SpeedFromTurnRadius(radius), 400) + distance / ((minSpeed + finSpeed) / 2);
				}
				if (allowDodges && distance / finSpeed > 1.25f)
				{
					// If we have enough time to dodge, then estimate how long it will take to drive to the target while boosting, and then dodging!
					return landingTime + turnDistance / MathF.Max(SpeedFromTurnRadius(radius), 400) + distanceWhileBoosting / ((minSpeed + finSpeed) / 2) + (distance - distanceWhileBoosting) / (finSpeed + 500);
				}

				// Estimates how long it will take to drive to the target
				return landingTime + turnDistance / MathF.Max(SpeedFromTurnRadius(radius), 400) + distanceWhileBoosting / ((minSpeed + finSpeed) / 2) + (distance - distanceWhileBoosting) / finSpeed;
			}
		}

		/// <summary>Estimates the maximum possible turn radius in order to still hit the target</summary>
		public static float TurnRadius(Car car, Vec3 target)
		{
			float distance = Field.DistanceBetweenPoints(car.Location, target);
			return (distance / 2) / (car.Right * MathF.Sign(car.Right.Dot(target - car.Location))).Dot(car.Location.FlatDirection(target, car.Up));
		}

		/// <summary>Returns the turn radius of the car at a given speed</summary>
		public static float TurnRadius(float speed)
		{
			speed = Utils.Cap(speed, 0.01f, Car.MaxSpeed);
			if (speed <= 500)
				return Utils.Lerp(speed / 500, 145, 251);
			if (speed <= 1000)
				return Utils.Lerp((speed - 500) / 500, 251, 425);
			if (speed <= 1500)
				return Utils.Lerp((speed - 1000) / 500, 425, 727);
			if (speed <= 1750)
				return Utils.Lerp((speed - 1500) / 250, 727, 909);
			return Utils.Lerp((speed - 1750) / 550, 909, 1136);
		}

		/// <summary>Returns the speed of the car given a turn radius</summary>
		public static float SpeedFromTurnRadius(float radius)
		{
			radius = Utils.Cap(radius, 145, 1136);
			if (radius <= 251)
				return Utils.Lerp((radius - 145) / 106, 0, 500);
			if (radius <= 425)
				return Utils.Lerp((radius - 251) / 174, 500, 1000);
			if (radius <= 727)
				return Utils.Lerp((radius - 425) / 302, 1000, 1500);
			if (radius <= 909)
				return Utils.Lerp((radius - 727) / 182, 1500, 1750);
			return Utils.Lerp((radius - 909) / 227, 1750, Car.MaxSpeed);
		}

		/// <summary>Estimates the speed of the car after a turn, given the current speed of the car and the angle of the turn</summary>
		public static float SpeedAfterTurn(float currentSpeed, float angle, float modifier = 1)
		{
			return Utils.Cap((1234 * (MathF.Exp(angle * 0.49f * modifier) * angle * 0.49f * modifier * (currentSpeed > 1234 ? 0.2f : 1)) + currentSpeed) / ((MathF.Exp(angle * 0.49f * modifier) * angle * 0.49f * modifier * (currentSpeed > 1234 ? 0.2f : 1)) + 1), 0, Car.MaxSpeed);
		}
	}
}
