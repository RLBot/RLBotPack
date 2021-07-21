from maneuvers.collect_boost import CollectClosestBoostManeuver, filter_pads


class RotateOrDefendState:
    def __init__(self):
        pass

    def exec(self, bot):
        if bot.info.my_car.boost < 50:
            bot.maneuver = CollectClosestBoostManeuver(bot, filter_pads(bot, bot.info.boost_pads, big_only=True))
        return bot.drive.home(bot)
