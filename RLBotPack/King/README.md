# RedUtilities

A set of utitilies for making rocket league bots in C#

## Usage Instructions

### Prerequisites
Make sure you've installed [.NET SDK 5.0 x64](https://dotnet.microsoft.com/download) or newer,  
AND make sure you've installed [Python 3.7 64 bit](https://www.python.org/ftp/python/3.7.3/python-3.7.3-amd64.exe) or newer. During installation:
   - Select "Add Python to PATH"
   - Make sure pip is included in the installation
   
Set up RLBotGUI
1. Set up and install the RLBotGUI, by following this along with this [video](https://www.youtube.com/watch?v=oXkbizklI2U&t=0s).
1. Use Add -> Load folder in RLBotGUI on the current directory. This bot should appear in the list.


### Using Visual Studio
1. Install Visual Studio 2019 16.8 or newer.
1. Open Bot.sln in Visual Studio.
1. Edit the code as you see fit, and then compile 
1. In RLBotGUI, put the bot on a team and start the match.

### Using Rider
1. Install Rider. If you do not have Visual Studio installed alongside Rider, follow [this article](https://rider-support.jetbrains.com/hc/en-us/articles/207288089-Using-Rider-under-Windows-without-Visual-Studio-prerequisites) to set up Rider.
1. Open Bot.sln in Rider.
1. Edit the code as you see fit, and then compile
1. In RLBotGUI, put the bot on a team and start the match.

## Upgrades

This project uses a package manager called NuGet to keep track of the RLBot framework.
The framework will get updates periodically, and you'll probably want them, especially if you want to make sure
your bot will work right in the next tournament!

### Upgrading in Visual Studio
1. In Visual Studio, right click on the Bot C# project and choose "Manage NuGet Packages..."
1. Click on the "Installed" tab. You should see a package called "RLBot.Framework".
1. If an upgrade is available, it should say so and give you the option to upgrade.

### Upgrading in Rider
1. In Rider, right click on the Bot C# project and choose "Manage NuGet Packages".
1. In the "Installed Packages" section, click on the package called "RLBot.Framework".
1. If the "Version" dropdown contains a higher version than what your project currently has, you can select that version and click the Upgrade button next to the dropdown to upgrade.

## Notes

- Bot name, description, etc, is configured by `Bot.cfg`
- Bot strategy is controlled by `Bot/Bot.cs`
- Bot appearance is controlled by `Loadouts/loadout_generator.py`
- To make your bot run as fast as possible, build it in release mode, and then change the "executable_path" in `Bot.cfg` to `./Bot/bin/Release/net5.0/Bot.exe`
- See the [wiki](https://github.com/RLBot/RLBotCSharpExample/wiki) for tips to improve your programming experience.
- If you'd like to keep up with bot strategies and bot tournaments, join our [Discord server](https://discord.gg/q9pbsWz). It's the heart of the RLBot community!


## Overview of how the C# bot interacts with Python

The C# bot executable is a server that listens for Python clients.
When `python_run_file.py` is started by the RLBot framework, it connects to the C# bot server and tells it its info.
Then, the C# bot server controls the bot through the `RLBot_Core_Interface` DLL.

## Credit

-  [ddthj/GoslingUtils](https://github.com/ddthj/GoslingUtils) for inspiration on some of the structure and code (which I ported to c#)
-  [VirxEC/VirxERLU](https://github.com/VirxEC/VirxERLU) for the basis of my aerial code (which I ported to c#)
-  [Darxeal/BotimusPrime](https://github.com/Darxeal/BotimusPrime) for inspiration on some of the structure and driving code (which I ported to c#)
