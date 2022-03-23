namespace RedUtils
{
	/// <summary>An action to be performed by our bot</summary>
	public interface IAction
	{
		/// <summary>Whether or not the action has finished</summary>
		public bool Finished { get; }
		/// <summary>Whether or not the action can be interrupted</summary>
		public bool Interruptible { get; }

		/// <summary>Performs this action</summary>
		public void Run(RUBot bot);
	}
}
