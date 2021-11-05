# Supercharged Bots

## Config

### help_blue_team

Set to `true` to enable the blue team, and `false` to disable.

### help_orange_team

Set to `true` to enable the orange team, and `false` to disable.

### bots_only

Set to `true` to only enable for bots, and `false` to also enable for humans.

### bonus_boost_accel_percent

The **bonus** acceleration when boosting and not steering. Set to any positive number.

Example: `150` would be a *bonus* of 150% acceleration, meaning that the boost strength is actually 2.5x or 250%.

### bonus_boost_tank

The **bonus** boost in a car's tank. Set to any positive number.

Example: `900` would be a *bonus* of 900 boost, meaning that there's actually 1000 boost in the tank. Boost is consumed at 33.333 boost per second, so that's 30 seconds of boost.

NOTE: The amount that you get from boost pads doesn't change! This means that pads give you 12% of your total tank and pills give you 100% of your total tank.

NOTE 2: The boost meter that you see on screen is in percents, so it goes from 0% to 100% full.

### minimum_boost

The minimum % of boost for cars to have. Set to any integer between (and including) `0` to `100`.

### bonus_hit_percent

The % bonus velocity that will be added when a car touches the ball.

### demo_helper

Set to `true` to enable demo-on-enemy-contact, and `false` to disable.

## Bots with no support

By default, no bots actually supports Supercharged bots. With this in mind, I've tuned this to not interfere with bots and actually help them.

When on the ground, the extra boost acceleration is only applied when the bot's boosting and `steer` is less than or equal to `0.2`.

When in the air, the extra boost acceleration is only applied when the bot's boosting and `yaw` as well as `pitch` are less than or equal to `0.2`.

When the ball is touched, the x/y velocity gets the % bonus, but the z velocity gets the inverse of that bonus. (so 100% (aka 2x) will halve the z velocity.) This is done so make the ball approach the same destination faster, and alter the final destination as little as possible.

## Supporting Supercharged bots

Every 0.1 seconds, a packet is sent through the matchcomms system containing the names of the cars that are supercharged. It also contains information on the current configuration.

Example packet (2 Kamael + Human vs 3 Kamael, bots only, blue team only):

```json
{
    "supercharged_bots": [
        "Kamael",
        "Kamael (1)"
    ],
    "supercharged_config": {
        "bonus_boost_accel_percent": 150,
        "bonus_boost_tank": 900,
        "minimum_boost": 1,
        "bonus_hit_percent": 15,
        "demo_helper": true,
    }
}
```

Once you've added support for your bot being Supercharged, you can add the tag `supports-supercharged-bots` in the `[Details]` section of your bot's config!
