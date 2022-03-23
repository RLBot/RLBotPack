using System.Collections;
using System.Collections.Generic;
using RedUtils.Math;

namespace RedUtils
{
	/// <summary>An action for driving to grab a boost pad</summary>
	public class GetBoost : IAction
	{
		/// <summary>Whether or not this action is finished</summary>
		public bool Finished { get; set; }
		/// <summary>Whether or not this action can be interrupted</summary>
		public bool Interruptible { get; set; }

		/// <summary>The index of the boost pad we are going to grab</summary>
		public int BoostIndex = 0;
		/// <summary>This action's drive subaction</summary>
		public Drive DriveAction;
		public Boost ChosenBoost;
		public float Eta = 0;

		/// <summary>Whether or not this action was initially set as interruptible</summary>
		private readonly bool _initiallyInterruptible = true;

		/// <summary>Initializes a GetBoost.</summary>
		/// <param name="boostIndex">Index of boost pad to go for. If set to -1 it will attempt to find the best big boost pad automatically</param>
		/// <param name="interruptible">Whether or not this shot can be interrupted</param>
		public GetBoost(Car car, int boostIndex = -1, bool interruptible = true)
		{
			Finished = false;
			Interruptible = interruptible;
			_initiallyInterruptible = interruptible;

			if (boostIndex == -1)
			{
				float fastestEta = 999;
				// Loop through all large boost pads, and finds the one we can get to soonest
				foreach (Boost boost in Field.Boosts)
				{
					if (!boost.IsLarge)
						continue;

					// Calculates how long it will take to get the boost
					float eta = Drive.GetEta(car, boost.Location);
					// If we can get there fastest, and it will be active when we get there, we choose it as our new fastest!
					if (eta < fastestEta && (boost.IsActive || boost.TimeUntilActive < eta))
					{
						fastestEta = eta;
						boostIndex = boost.Index;
					}
				}
			}

			BoostIndex = boostIndex;
			ChosenBoost = Field.Boosts[BoostIndex];
			DriveAction = new Drive(car, ChosenBoost.Location, Car.MaxSpeed, true, ChosenBoost.IsLarge);
		}

		/// <summary>Initializes a GetBoost action which will go for the soonest reachable boost of the supplied boosts</summary>
		/// <param name="boosts">Which boosts to consider</param>
		/// <param name="interruptible">Whether or not this action can be interrupted</param>
		public GetBoost(Car car, IEnumerable<Boost> boosts, bool interruptible = true)
		{
			Finished = false;
			Interruptible = interruptible;
			_initiallyInterruptible = interruptible;

			float fastestEta = 999;
			// Loop through the given boost pads, and finds the one we can get to soonest
			foreach (Boost boost in boosts)
			{
				// Calculates how long it will take to get the boost
				float eta = Drive.GetEta(car, boost.Location);
				// If we can get there fastest, and it will be active when we get there, we choose it as our new fastest!
				if (eta < fastestEta && (boost.IsActive || boost.TimeUntilActive < eta))
				{
					fastestEta = eta;
					BoostIndex = boost.Index;
				}
			}

			ChosenBoost = Field.Boosts[BoostIndex];
			DriveAction = new Drive(car, ChosenBoost.Location, Car.MaxSpeed, true, ChosenBoost.IsLarge);
		}

		/// <summary>Drives to the chosen boost pad</summary>
		public void Run(RUBot bot)
		{
			// Drive to the boost
			DriveAction.Run(bot);

			// Gets info on the chosen boost
			ChosenBoost = Field.Boosts[BoostIndex];
			Eta = Drive.GetEta(bot.Me, ChosenBoost.Location);

			// This action can only be interrupted if it was initially set as interruptuble, and if its sub action is also interruptible
			Interruptible = _initiallyInterruptible && DriveAction.Interruptible;
			// When we arrive at the boost's location, we finish this action
			Finished = (!ChosenBoost.IsActive && (ChosenBoost.TimeUntilActive > Drive.GetEta(bot.Me, ChosenBoost.Location) || DriveAction.Finished)) || bot.Me.Boost > 90;
		}
	}
}
