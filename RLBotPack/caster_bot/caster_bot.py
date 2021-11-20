from rlbot.utils.structures.game_interface import GameInterface
from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
from rlbot.utils.structures.ball_prediction_struct import BallPrediction
from caster_utils import *
from rlbot.agents.base_script import BaseScript
import pyttsx3
from queue import Queue
import threading
import random
import time
import math
import os


def host(_queue, voiceChoice):
    if voiceChoice:
        try:
            from gtts import gTTS
            from playsound import playsound
            from io import BytesIO

            googleTalk = True
        except:
            googleTalk = False
    else:
        googleTalk = False

    engine = pyttsx3.init()
    rate = engine.getProperty("rate")
    voices = engine.getProperty("voices")  # list of available voices
    comment_storage = []
    accepting = True

    possible_voices = ["com.au", "co.uk", "com", "ca", "co.in", "ie"]
    chosen_voices = random.sample(possible_voices, 2)

    def pick_best_comment(comment_list):
        current_highest = 0
        best_comments = []

        for index, _comment in enumerate(comment_list):
            if _comment.priority > current_highest:
                best_comments.clear()
                current_highest = _comment.priority
                best_comments.append(_comment)
            elif _comment.priority == current_highest:
                best_comments.append(_comment)

        if len(best_comments) > 0:
            earliest_time = math.inf
            earliest_comment = 0
            for index, _comment in enumerate(best_comments):
                if _comment.time_generated < earliest_time:
                    earliest_comment = index
                    earliest_time = _comment.time_generated
            return earliest_comment
        else:
            return -1

    if len(voices) < 1:
        print("no usable voices found on this pc, exiting caster script")
        return

    last_comment = None
    while accepting or len(comment_storage) > 0:

        while not _queue.empty() and accepting:
            c = _queue.get()
            if c.comment != "exit":
                comment_storage.append(c)
            else:
                comment_storage.clear()
                accepting = False

        for c in comment_storage:
            c.update()
            # removing duplicates in the means below won't work as well when we add better variety
            if last_comment != None:
                if c.comment == last_comment.comment:
                    if c.time_generated - last_comment.time_generated < 10:
                        c.valid = False

        comment_storage = [c for c in comment_storage if c.valid]
        c_index = pick_best_comment(comment_storage)
        if c_index != -1:
            comment = comment_storage.pop(c_index)
            if googleTalk:
                try:
                    tts = gTTS(
                        comment.comment, lang="en", tld=random.choice(chosen_voices)
                    )
                    # absolutely HATE the implementation below but all packages that play audio from bytes require more complicated installs
                    file_name = f"{time.perf_counter()}.mp3"
                    tts.save(file_name)
                    playsound(file_name)
                    os.remove(file_name)
                except Exception as e:
                    print(e)
                    print("switching to offline voice mode")
                    googleTalk = False

            if not googleTalk:
                try:
                    engine.setProperty("voice", voices[comment.voiceID].id)
                except:
                    engine.setProperty("voice", voices[0].id)

                engine.say(comment.comment)
                engine.runAndWait()
            last_comment = comment

    print("Exiting announcer thread.")


class Caster(BaseScript):
    def __init__(self):
        super().__init__("Caster")
        print("Caster created")
        self.touchTimer = 0
        self.currentTime = 0
        self.firstIter = True
        self.overTime = False
        self.shotDetection = True
        self.shooter = None
        self.currentZone = None
        self.KOE = None
        self.contactNames = rstring(["hits", "touches", "moves"])
        self.dominantNames = rstring(["dominant", "commanding", "powerful"])
        self.dangerously = rstring(
            ["alarmingly", "perilously", "precariously", "dangerously"]
        )
        self.RC_Intros = rstring(
            [
                "Here's a fun fact. ",
                "Check this out. ",
                "This is interesting. ",
                "What do you think about this?",
                "Oh, look at this.",
            ]
        )
        self.touch_comments = [
            "makes contact",
            "gets a touch",
            "hits the ball",
            "gets a piece of the ball",
        ]
        self.touch_commentary = []
        self.ballHistory = []
        self.lastTouches = []
        self.RC_list = [0, 1, 2, 3, 4, 5, 6, 7]
        self.teams = []
        self.zoneInfo = None
        self.joinTimer = 0
        self.packet = GameTickPacket()
        self.f_packet = None  # FieldInfoPacket()
        self.ball_predictions = BallPrediction()
        self.lastCommentTime = 0
        self.comment_ids = [x + 1 for x in range(18)]
        self.make_touch_comment = False
        self.summary_count = 0
        self.game_length = -1
        self.clock_time = 0
        self.q = Queue(maxsize=200)
        self.random_lockout = time.perf_counter()
        self.host = threading.Thread(
            target=host,
            args=(
                self.q,
                0,
            ),
        )
        self.host.start()

    def retire(self):
        with self.q.mutex:
            self.q.queue.clear()
        self.stopHost()
        self.host.join()

    def demo_check(self):
        # must be run before cars are updated!
        for t in self.teams:
            for c in t.members:
                if self.packet.game_cars[c.index].is_demolished and not c.demolished:
                    # find closest enemy to c
                    enemy_team = 1 if c.team == 0 else 0
                    attacker = self.teams[enemy_team].members[0]
                    closest = math.inf
                    for e in self.teams[enemy_team].members:
                        dist = findDistance(c.position, e.position)
                        if dist < closest:
                            closest = dist
                            attacker = e
                    self.speak(
                        f"{stringCleaner(attacker.name)} gets the demolish on {stringCleaner(c.name)}",
                        5,
                        2,
                    )
                    self.teams[enemy_team].demos += 1

    def match_clock_handler(self):
        if self.game_length == -1:
            self.game_length = self.packet.game_info.game_time_remaining

        self.clock_time = self.game_length - self.packet.game_info.game_time_remaining

    def speak(self, phrase, priority, decayRate):
        if not self.q.full():
            self.q.put(Comment(phrase, random.randint(0, 1), priority, decayRate))
        self.lastCommentTime = self.currentTime * 1

    def kickOffAnalyzer(self):
        if self.packet.game_info.is_kickoff_pause:
            if not self.KOE.active:
                self.KOE = KickoffExaminer(self.currentTime)

        else:
            if self.KOE.active:
                if len(self.ballHistory) > 0:
                    result = self.KOE.update(self.currentTime, self.ballHistory[-1])
                    if result == 0:
                        self.speak("The kickoff goes in favor of blue", 5, 3)
                    elif result == 1:
                        self.speak("The kickoff goes in favor of orange", 5, 3)
                    elif result == 2:
                        self.speak("It's a neutral kickoff.", 5, 3)

    def mid_game_summary(self):
        # give a score comparisan "we're 2 minutes into the match and blue already has a commanding lead of 3:1"
        minutes = int(self.clock_time / 60)
        if minutes > self.summary_count and minutes != int(
            (self.game_length + 10) / 60
        ):

            tied = self.teams[0].score == self.teams[1].score
            if tied:
                self.speak(
                    f"We're now {minutes} {'minute' if minutes == 1 else 'minutes'} into this game and the score is tied up at "
                    f"{self.teams[0].score}",
                    4,
                    5,
                )

            else:
                self.speak(
                    f"We're now {minutes} {'minute' if minutes == 1 else 'minutes'} into this match and "
                    f"{'blue' if self.teams[0].score > self.teams[1].score else 'orange'} has a {abs(self.teams[0].score - self.teams[1].score)} goal lead.",
                    6,
                    8,
                )
            self.summary_count += 1

    def overtime_prelude(self):
        # compare shots taken, saves and boost averages, etc
        shots_taken = [self.teams[0].getShotCount(), self.teams[1].getShotCount()]
        if shots_taken[0] == shots_taken[1]:
            avg_speeds = [
                self.teams[0].getMatchAverageSpeed(),
                self.teams[1].getMatchAverageSpeed(),
            ]
            self.speak(
                f"We're headed into over-time with the score tied at {self.packet.teams[0].score}! "
                f"{'Blue' if avg_speeds[0] > avg_speeds[1] else 'Orange'} has been the faster team so far this match with an average speed of {speedConversion(avg_speeds[0]) if avg_speeds[0] > avg_speeds[1] else speedConversion(avg_speeds[1])} kilometers per hour compared to {speedConversion(avg_speeds[0]) if avg_speeds[0] < avg_speeds[1] else speedConversion(avg_speeds[1])} from their opposition",
                10,
                10,
            )
        else:
            self.speak(
                f"We're headed into over-time with the score tied at {self.packet.teams[0].score}! "
                f"{'Blue' if shots_taken[0] > shots_taken[1] else 'Orange'} has been more aggressive with {shots_taken[0] if shots_taken[0] > shots_taken[1] else shots_taken[1]} shots on target compared to {shots_taken[0] if shots_taken[0] < shots_taken[1] else shots_taken[1]} from their opposition",
                10,
                10,
            )

    def randomComment(self):
        c_time = time.perf_counter()

        # randomComment() was being called multiple times in successtion for some reason, so added a small lockout window.
        if c_time - self.random_lockout < 1:
            return
        else:
            self.random_lockout = c_time

        if len(self.comment_ids) == 0:
            self.comment_ids = [x + 1 for x in range(18)]
        choice = random.sample(self.comment_ids, 1)[0]
        self.comment_ids.remove(choice)
        priority = 1
        decay = 1

        if choice <= 10:
            if not self.make_touch_comment:
                self.make_touch_comment = True
            else:
                self.comment_ids.append(choice)

        elif choice == 11:
            shot_totals = [self.teams[0].getShotCount(), self.teams[1].getShotCount()]
            if shot_totals[0] == shot_totals[1]:
                self.speak(
                    f"Both teams are evenly matched on shots taken so far with each having {shot_totals[0]}.",
                    priority,
                    decay,
                )

            else:
                self.speak(
                    f"{'Blue' if shot_totals[0] > shot_totals[1] else 'Orange'} is ahead on shots taken so far with {shot_totals[0] if shot_totals[0] > shot_totals[1] else shot_totals[1]} this match.",
                    priority,
                    decay,
                )

        elif choice == 12:
            # match avg boost
            team_boosts = [
                self.teams[0].getAverageBoost(),
                self.teams[1].getAverageBoost(),
            ]
            if team_boosts[0] == team_boosts[1]:
                self.speak(
                    f"Neither team at finding a boost advantage right now as both sides are at {int(team_boosts[0])} boost.",
                    priority,
                    decay,
                )
            else:
                self.speak(
                    f"{'Blue' if team_boosts[0] > team_boosts[1] else 'Orange'} currently has the boost advantage. Let's see what they can do with it.",
                    priority,
                    decay,
                )

        elif choice == 13:
            # match avg speed
            team_speeds = [
                self.teams[0].getMatchAverageSpeed(),
                self.teams[1].getMatchAverageSpeed(),
            ]
            self.speak(
                f"{'Blue' if team_speeds[0] > team_speeds[1] else 'Orange'} has been the faster team so far in this match with an average speed of {speedConversion(team_speeds[0]) if team_speeds[0] > team_speeds[1] else speedConversion(team_speeds[1])} kilometers per hour.",
                priority,
                decay,
            )

        elif choice == 14:
            if self.teams[0].demos == 0:
                self.speak(
                    f"{self.RC_Intros} blue team has jumped a total of {int(self.teams[0].getJumpCount())} times so far this match.",
                    priority,
                    decay,
                )
            else:
                self.speak(
                    f"{self.RC_Intros} blue team has total of {int(self.teams[0].demos)} demos so far this match.",
                    priority,
                    decay,
                )

        elif choice == 15:
            if self.teams[1].demos == 0:
                self.speak(
                    f"{self.RC_Intros} orange team has jumped a total of {int(self.teams[1].getJumpCount())} times so far this match.",
                    priority,
                    decay,
                )
            else:
                self.speak(
                    f"{self.RC_Intros} orange team has total of {int(self.teams[1].demos)} demos so far this match.",
                    priority,
                    decay,
                )

        elif choice == 16:
            own_goal_info = [
                self.teams[0].getOwnGoalCount(),
                self.teams[1].getOwnGoalCount(),
            ]
            if sum(own_goal_info) == 0:
                self.speak(
                    "Surprisingly there's been no own goals yet this match.",
                    priority,
                    decay,
                )
            else:
                if own_goal_info[0] == own_goal_info[1]:
                    self.speak(
                        f"Both teams have the honor of being tied for most own goals at {own_goal_info[0]}",
                        priority,
                        decay,
                    )

                else:
                    self.speak(
                        f"{'Orange' if own_goal_info[1] > own_goal_info[0] else 'Blue'} is currently leading in own goals with a total of {own_goal_info[1] if own_goal_info[1] > own_goal_info[0] else own_goal_info[0]}",
                        priority,
                        decay,
                    )

        elif choice == 17:
            save_info = [self.teams[0].getSaveCount(), self.teams[1].getSaveCount()]
            if sum(save_info) == 0:
                self.speak(
                    "There's been no defensive heroism yet as both sides are still at 0 saves",
                    priority,
                    decay,
                )
            else:
                if save_info[0] == save_info[1]:
                    self.speak(
                        f"Both teams have made {save_info[0]} saves so far this match.",
                        priority,
                        decay,
                    )

                else:
                    self.speak(
                        f"{'Orange' if save_info[1] > save_info[0] else 'Blue'} has been making more saves this match with a total of {save_info[1] if save_info[1] > save_info[0] else save_info[0]}.",
                        priority,
                        decay,
                    )

        elif choice == 18:
            # which player has the most shots?
            most_shots = 0
            player_team = 0
            player_names = []
            for t in self.teams:
                for m in t.members:
                    shots = m.getShots()
                    if shots > most_shots:
                        most_shots = shots
                        player_team = m.team
                        player_names = [stringCleaner(m.name)]

                    elif shots == most_shots:
                        player_names.append(stringCleaner(m.name))

            if most_shots == 0:
                self.speak(
                    f"We're {int(self.clock_time)} seconds in and still no shots fired on either net.",
                    priority,
                    decay,
                )

            elif len(player_names) > 1:
                self.speak(
                    f"{', '.join(player_names)} are currently tied for most shots on net with {most_shots} each",
                    priority,
                    decay,
                )

            else:
                self.speak(
                    f" {player_names[0]} on {'blue' if player_team == 0 else 'orange'} is leading the pack with {most_shots} shots on net so far.",
                    priority,
                    decay,
                )

    def timeCheck(self, newTime):
        if newTime - self.currentTime < -1:
            return True
        self.currentTime = newTime
        return False

    def overtimeCheck(self):
        if not self.overTime:
            if self.packet.game_info.is_overtime:
                self.overTime = True
                self.overtime_prelude()
                self.make_touch_comment = False
                # self.speak(f"That's the end of regulation time, we're headed into over-time with the score tied at {self.packet.teams[0].score}!",10,3)

    def gameWrapUp(self):
        if self.teams[0].score > self.teams[1].score:
            winner = "Blue"
        else:
            winner = "Orange"

        if abs(self.teams[0].score - self.teams[1].score) >= 3:
            self.speak(
                f"Team {winner} has won today's match with a dominant performance.",
                10,
                10,
            )
            # impressive victory
        else:
            # normal win message
            self.speak(f"Team {winner} clinched the victory this match", 10, 10)

        self.speak(
            "Thank you all for watching and don't forget to subscribe to Impossibum on youtube!",
            10,
            10,
        )

    def stopHost(self):
        while self.q.full():
            pass
        self.speak("exit", 0, 0)

    def handleShotDetection(self):
        if self.shotDetection:
            if len(self.ballHistory) > 0:
                shot, goal = shotDetection(self.ball_predictions, 4, self.currentTime)
                if shot:
                    if goal == 0:
                        loc = Vector([0, -5200, 0])
                    else:
                        loc = Vector([0, 5200, 0])

                    if (
                        not self.KOE.active
                    ):  # attempt to limit false positives from kickoffs... ugly solution is ugly
                        if self.lastTouches[-1].team == goal:
                            if not self.q.full():
                                # self.speak(f"That's a potential own goal from {self.lastTouches[-1].player_name}.",5,3)
                                pass
                        else:
                            if not self.q.full():
                                self.speak(
                                    f"{stringCleaner(self.lastTouches[-1].player_name)} takes a shot at the enemy net!",
                                    5,
                                    3,
                                )

                        # self.shooter = self.lastTouches[-1].player_index
                        if goal == 0:
                            shotTeam = 1
                        else:
                            shotTeam = 0
                        try:
                            self.shooter = self.teams[shotTeam].lastTouch.player_index
                        except:
                            pass
                            # possibly no touch yet in case of owngoals
                        self.shotDetection = False

    def updateTeamsInfo(self):
        for t in self.teams:
            t.updateMembers(self.packet)

    def updateTouches(self):
        try:
            touch = ballTouch(self.packet.game_ball.latest_touch)
        except Exception as e:
            touch = None

        if touch:
            if len(self.lastTouches) < 1 or self.lastTouches[-1] != touch:
                self.lastTouches.append(touch)
                for team in self.teams:
                    team.update(touch)
                if not self.shotDetection:
                    shot, goal = shotDetection(
                        self.ball_predictions, 2, self.currentTime
                    )
                    if not shot:
                        if touch.player_index != self.shooter:
                            validSave = False
                            if goal == 0:
                                if (
                                    distance2D(
                                        self.ballHistory[-1].location,
                                        Vector([0, -5200, 0]),
                                    )
                                    < 2500
                                ):
                                    validSave = True
                            else:
                                if (
                                    distance2D(
                                        self.ballHistory[-1].location,
                                        Vector([0, 5200, 0]),
                                    )
                                    < 2500
                                ):
                                    validSave = True
                            if validSave:
                                self.speak(
                                    f"{stringCleaner(touch.player_name)} makes the save!",
                                    8,
                                    6,
                                )

                self.shotDetection = True
                toucher = stringCleaner(touch.player_name)
                if toucher.replace(" ", "") != "":
                    if self.make_touch_comment:
                        self.speak(
                            f"{toucher} {random.choice(self.touch_comments)}", 3, 2
                        )
                        self.make_touch_comment = False

    def zone_analysis(self, ball_obj):
        corners = [0, 1, 2, 3]
        boxes = [4, 5]
        sides = [6, 7]
        new_zone = find_current_zone(ball_obj)
        if self.currentZone == None:
            self.currentZone = new_zone
            return

        if new_zone != self.currentZone:
            if self.currentZone in sides:
                if new_zone in sides:
                    # self.speak(f"The ball crosses into {get_team_color_by_zone(new_zone)} territory.",0,1)
                    if self.zoneInfo.timeInZone(self.currentTime) >= 20:
                        self.speak(
                            f"After {int(self.zoneInfo.timeInZone(self.currentTime))} seconds, the ball is finally cleared from the {get_team_color_by_zone(self.currentZone)} half.",
                            2,
                            2,
                        )
                    else:
                        pass

                elif new_zone in boxes:
                    if self.shotDetection:
                        self.speak(
                            f"The ball is {self.dangerously} close to the {get_team_color_by_zone(new_zone)} goal!",
                            1,
                            1,
                        )

                elif new_zone in corners:
                    self.speak(
                        f" {stringCleaner(self.lastTouches[-1].player_name)} {self.contactNames} the ball to the {get_team_color_by_zone(new_zone)} corner.",
                        1,
                        1,
                    )

            elif self.currentZone in boxes:
                # leaving the box is worth mentioning
                self.speak(
                    f"The ball is cleared out of the {get_team_color_by_zone(self.currentZone)} box by {stringCleaner(self.lastTouches[-1].player_name)}.",
                    2,
                    2,
                )

            elif new_zone in corners:
                self.speak(
                    f" {stringCleaner(self.lastTouches[-1].player_name)} {self.contactNames} the ball to the {get_team_color_by_zone(new_zone)} corner.",
                    1,
                    2,
                )

            elif new_zone in boxes:
                if self.shotDetection:
                    self.speak(
                        f"The ball is {self.dangerously} close to the {get_team_color_by_zone(new_zone)} goal!",
                        2,
                        2,
                    )

            self.currentZone = new_zone
            self.zoneInfo.update(new_zone, self.currentTime)

    def updateGameBall(self):
        if self.packet.game_info.is_round_active:
            currentBall = ballObject(self.packet.game_ball)
            self.ballHistory.append(currentBall)
            self.zone_analysis(currentBall)

        if len(self.ballHistory) > 1000:
            del self.ballHistory[0]

    def gatherMatchData(self):
        members = [[], []]
        for i in range(self.packet.num_cars):
            _car = Car(self.packet.game_cars[i].name, self.packet.game_cars[i].team, i)
            members[_car.team].append(_car)

        self.teams.append(Team(0, members[0]))
        self.teams.append(Team(1, members[1]))
        self.speak(
            f"On blue we have {', '.join([stringCleaner(x.name) for x in self.teams[0].members])} ",
            10,
            10,
        )
        self.speak(
            f" and orange is comprised of {', '.join([stringCleaner(x.name) for x in self.teams[1].members])} .",
            10,
            10,
        )
        self.speak("Good luck!", 10, 10)

    def scoreAnnouncement(self, teamIndex):
        try:
            scorer = stringCleaner(self.teams[teamIndex].lastTouch.player_name)
        except:
            if teamIndex == 0:
                scorer = "Blue Team"
            else:
                scorer = "Orange Team"
        speed = self.ballHistory[-1].getRealSpeed()
        if not self.q.full():
            if speed <= 20:
                self.speak(
                    f"{scorer} scores! It barely limped across the goal line at {speed} kilometers per hour, but a goal is a goal.",
                    10,
                    10,
                )

            elif speed >= 100:
                self.speak(
                    f"{scorer} scores on a blazingly fast shot at  {speed} kilometers per hour! What a shot!",
                    10,
                    10,
                )

            else:
                self.speak(
                    f"And {scorer}'s shot goes in at {speed} kilometers per hour!",
                    10,
                    10,
                )
        else:
            print("full q")

        if not self.q.full():
            self.speak(
                f"That goal brings the score to {self.teams[0].score} blue and {self.teams[1].score} orange.",
                10,
                10,
            )
        else:
            print("full q")

    def scoreCheck(self):
        if self.teams[0].score != self.packet.teams[0].score:
            self.teams[0].score = self.packet.teams[0].score
            self.scoreAnnouncement(0)
            self.make_touch_comment = False
            self.currentZone = 0

        if self.teams[1].score != self.packet.teams[1].score:
            self.teams[1].score = self.packet.teams[1].score
            self.scoreAnnouncement(1)
            self.make_touch_comment = False
            self.currentZone = 0

    def run(self):
        while True:
            self.packet = self.wait_game_tick_packet()
            self.ball_predictions = self.get_ball_prediction_struct()
            if not self.f_packet:
                self.f_packet = self.get_field_info()
            if self.packet.game_info.is_match_ended:
                print("Game is over, exiting caster script.")
                self.gameWrapUp()
                break

            if self.firstIter:
                if self.packet.num_cars >= 1:
                    if self.joinTimer <= 0:
                        self.joinTimer = time.time()
                    # arbitrary timer to ensure all cars connected
                    if time.time() - self.joinTimer >= 1:
                        self.firstIter = False
                        self.currentTime = float(self.packet.game_info.seconds_elapsed)
                        self.gatherMatchData()
                        self.zoneInfo = ZoneAnalyst(self.currentZone, self.currentTime)
                        self.KOE = KickoffExaminer(self.currentTime)

            self.timeCheck(float(self.packet.game_info.seconds_elapsed))
            self.match_clock_handler()
            if not self.firstIter:

                self.updateGameBall()
                self.updateTouches()
                self.demo_check()
                self.updateTeamsInfo()
                self.handleShotDetection()
                self.scoreCheck()
                self.overtimeCheck()
                self.kickOffAnalyzer()
                self.mid_game_summary()
                if self.packet.game_info.is_kickoff_pause:
                    self.zoneInfo.zoneTimer = self.currentTime
                if self.currentTime - self.lastCommentTime >= 8:
                    self.randomComment()


if __name__ == "__main__":
    script = Caster()
    script.run()
