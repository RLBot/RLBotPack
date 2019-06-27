These instructions are intended for a tournament organizer. In theory, you're reading this because
you've just extracted a zip file submitted to a tournament. If that's not your situation, go look at README.md
instead.

1. Make sure you've installed Java 8 or newer. Here's the [Java 10 JRE](http://www.oracle.com/technetwork/java/javase/downloads/jre10-downloads-4417026.html).
1. Make sure you've [set the JAVA_HOME environment variable](https://javatutorial.net/set-java-home-windows-10).
1. Run the framework as normal, and point to one of the bot cfg files in this directory.
For an example of running the framework, see the [setup video](https://www.youtube.com/watch?v=UjsQFNN0nSA).
1. ***IF*** you see the message `Can't auto-start java because no executable is configured. Please start java manually!`
 then you will need to double click on the `ReliefBot.bat` file included in the bin directory.
 Doing this once is enough to support all bots in this zip in the whole game.
1. To give ReliefBot the best performance, please do not open the tactical
overlay during important matches.

Advanced:

- It's fine to close and restart `ReliefBot.bat` while runner.py is active.
- You can also run the `.bat` on the command line to see stack traces for debugging purposes.
- If there is a port conflict, you can modify relief_bot.py's get_port method.
