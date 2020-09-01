import configparser
import tkinter
from pathlib import Path
from tkinter import simpledialog

from rlbot_twitch_broker_client.defaults import STANDARD_TWITCH_BROKER_PORT

from twitchbroker.twitch_broker import TwitchAuth, MutableBrokerSettings, TwitchBroker

if __name__ == '__main__':

    # Follow https://dev.twitch.tv/docs/irc/guide/ to get an oauth token, and just save it in a file
    # in this same directory.
    twitch_login_file = Path(__file__).parent / 'personal_settings.cfg'
    config = configparser.ConfigParser()

    if twitch_login_file.exists():
        config.read(twitch_login_file)
        channel = config['Twitch']['channel']
        oauth = config['Twitch']['oauth']
    else:
        application_window = tkinter.Tk()
        application_window.withdraw()
        channel = simpledialog.askstring("Twitch Channel", "What's your twitch channel name?", parent=application_window)
        oauth = simpledialog.askstring("OAuth", "What's your OAuth token for connecting to twitch?", parent=application_window)
        application_window.destroy()
        config['Twitch'] = {
            'channel': channel,
            'oauth': oauth
        }
        with open(twitch_login_file, 'w') as f:
            config.write(f)

    if oauth is None:
        raise ValueError("oauth token is missing!")

    auth = TwitchAuth(channel, oauth, f'#{channel}')

    num_old_menus_to_honor = 2
    pause_on_menu = False

    if 'BrokerConfig' in config:
        brokerconf = config['BrokerConfig']
        if 'num_old_menus_to_honor' in brokerconf:
            num_old_menus_to_honor = brokerconf.getint('num_old_menus_to_honor')
        if 'pause_on_menu' in brokerconf:
            pause_on_menu = brokerconf.getboolean('pause_on_menu')

    # Require multiple people from twitch chat to attempt the same command before firing it, to nerf disruptive ones.
    # Configured by entity name, a.k.a. section header.
    votes_needed = {}
    if 'VotesNeeded' in config:
        vote_conf = config['VotesNeeded']
        for key, value in vote_conf.items():
            votes_needed[key] = int(value)

    vote_scales = {}
    if 'VotesNeededWhenOneVotePerSecond' in config:
        vote_conf = config['VotesNeededWhenOneVotePerSecond']
        for key, value in vote_conf.items():
            vote_scales[key] = int(value)

    settings = MutableBrokerSettings(num_old_menus_to_honor=num_old_menus_to_honor, pause_on_menu=pause_on_menu,
                                     min_votes_needed=votes_needed, votes_needed_when_one_vote_per_second=vote_scales)

    # Open up http://127.0.0.1:7307/static/chat_form.html if you want to send test commands without
    # connecting to twitch.
    # Open the overlay (the html file in overlay_folder to see what actions you can enter in chat.
    # You can open it via IntelliJ's html preview, or an OBS scene, both of these start a little mini server
    # so it can access the json successfully. Opening the overlay file directly in a web browser won't work.
    twitch_broker = TwitchBroker(Path(__file__).parent / 'overlay', auth, settings)
    twitch_broker.run_loop_with_chat_buffer(STANDARD_TWITCH_BROKER_PORT)
