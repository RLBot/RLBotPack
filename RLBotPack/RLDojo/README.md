| [![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/4bHnGBm2Dbw/0.jpg)](https://www.youtube.com/watch?v=4bHnGBm2Dbw) |
|:--:| 
| *Demo video of RLDojo* |

# Overview / TL;DR

Free play, training packs, and custom maps are great - but winning real games requires reading, reacting to, and outplaying your opponents. That’s why, in real sports, practicing specific scenarios against other players is a critical component of training. 

This type of training is sorely missing in Rocket League, so I made RLDojo to let you practice customizable drills against RLBot bots (like Nexto) for the first time.

# Features

### Preset Scenarios

RLDojo comes with a handful of preset / “hardcoded” offensive and defensive setups or “scenarios” which comprise a situation that the player can either play out as the offensive car or the defensive car. 

These presets are designed to be mixed and matched in order to cover a large variety of game-like situations in which you would need to either outplay a defender or defend an attacker. They each have a small amount of randomness baked in to cover more flavors of similar scenarios in game.

These scenarios are timed (to 7 seconds by default), where a point will be awarded to the defender if the attacker does not score before the timeout.

### Custom Scenario Creator

In addition to the preset scenarios, I also built a way for you to create your own scenarios, by manually setting the physics of the cars and ball to start a scenario, similar to making training packs (but more flexible, as you can change the rotation of cars and set their velocity).

### Playlist Mode

Playlists allow you to combine multiple types of scenarios (preset or custom) into… well, playlists. This allows you to group multiple scenarios by theme, e.g. maybe you want to work on a few different types of shadow defense or ground-based offense.

RLDojo comes with a few pre-defined playlists for you to try out, or you can create your own.

Special shoutout: `Open Goal` mode is one of my favorites, which emulates a defender chasing you down as you have a free shot on goal from a variety of positions. As we all know, the open goal is the hardest shot in the game, and this actually does a pretty good job feeling like the real things.

### Race Mode

This mode is a surprise fan-favorite (okay fine there’s just 1 fan - the only other RLDojo alpha user - my buddy Mike).

In Race Mode, the ball will spawn in a random location (seeded so that the sequence is always the same), and the player tries to get to the ball as fast as possible. The ball will spawn elsewhere once touched, which will repeat 100 times (number of trials is selectable).

Your fastest time will be recorded and displayed on future attempts, and it is insanely addicting to try to get this time lower and lower.

While initially created just for fun, it turns out this is an incredible exercise for practical efficiency of movement. Rings maps are great, but Race Mode is much more useful for in-game movement imo.

# Background

As someone who got pretty serious about ranking up a few years ago, I’ve tried out just about every training tool that exists, from training packs to dozens of Bakkesmod plugins and custom maps. 

I’ve also gone deep down the rabbithole of content tailored around improving gamesense (shoutout Flakes and Aircharged), and became obsessed with winning games through an emphasis on defense and decision-making.

Trying to improve at these skills made it glaringly obvious that Rocket League’s existing suite of tools are missing an entire dimension of practice: drilling scenarios repeatedly against other players.

For example:

- How can you practice shadow defense without an opponent attacking?
- How can you get better at taking 50/50s without someone on the other side of the ball?
- How can you react to and save a redirecting shot, if training packs can only send a ball from one point?

The goal of RLDojo is to make these scenarios (and infinitely more) possible to train repeatedly!

# Installation
Installation guide here: https://www.youtube.com/watch?v=1GbHdYeG1cc

To get RLDojo up and running:
1. Install RLBot: [rlbot.org](https://rlbot.org/)
2. In RLBotGUI, go to `+Add` -> `Download Bot Pack` (this will download the 'standard' bots)
3. Download the latest RLDojo release: https://github.com/ecolsen7/RLDojo/releases and extract it
4. In RLBotGUI, go to `+Add` -> `Load Folder` and select the RLDojo folder that you just downloaded/created
5. In RLBotGUI, find `Dojo` under the `Scripts` section
   - If there is a yellow triangle next to `Dojo`, click it to install any needed packages
   - Enable `Dojo` by clicking the toggle
6. In RLBotGUI, click the `Mutators` option at the bottom. Change `Match Length` to "Unlimited", and `Respawn Time` to "Disable Goal Reset"
7. In RLBotGUI, click the `Extras` option at the bottom. Select the following:
8. <img width="421" height="289" alt="image" src="https://github.com/user-attachments/assets/a7c5a078-4c64-409a-a16f-a01658826b1a" />
9. Make sure "Human" is on the Blue team, and add any bot (I recommend starting with `Necto`) to the Orange team.
10. Hit `Launch Rocket League and start match`.
11. Have fun!


# How much does it cost?

It’s free! My motivation for making this is that I love this game, and I want to see it and its competitive community thrive.

If you feel particularly inclined to give back, feel free to follow me on [Twitch](https://www.twitch.tv/smoothrik) and/or [Youtube](https://www.youtube.com/@smooth_rik)! If that’s not enough, you can [buy me a coffee](https://buymeacoffee.com/ecolsen74)
