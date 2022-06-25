# Random Standard

## Description

Script for RLBot which picks a random standard mode (1v1, 2v2, 3v3, 4v4, 5v5) after every kickoff.
It works by teleporting pairs of bots from each team outside the stadium after every goal. Demo video: https://www.youtube.com/watch?v=bzw3wnuuX8g

### Requirements

-Enable State Setting in Extra

-Have exactly 2v2, 3v3, 4v4 or 5v5 setup in RLBot. Anything else will not work, for example, 3v1 or 6v6.


## Config

### Change Probability

You can change the probability of each mode appearing. It works like adding X number of tiles of each game mode to a bag and then selecting a tile after every goal. When higher game modes are not possible, they will be ignored when randomly selecting a mode. The default config is equal chance for every game mode being selected.

```json
ones_prob = 10
twos_prob = 10
threes_prob = 10
fours_prob = 10
fives_prob = 10
```

### Enable Random  or Cycle Mode

Default is random enabled, which follows the probability settings.
```json
random_enabled = 1
```
If it is set to 0, it will disable random mode and instead cycle from the highest possible mode to the lowest. For example, 3v3 then 2v2 then 1v1 then 3v3 then 2v2 etc.
```json
random_enabled = 0
```
### Simulated Kickoff

If goal reset is disabled in mutators, it will teleport bots to kickoff positions after every goal.
```json
simulated_kickoff = 1
```
If simulated kickoff is set to 0, bots won't teleport after a goal. This means that bots that are outside the field will unfreeze and will be able to enter the field or despawn by falling into the void.
```json
simulated_kickoff = 0
```
