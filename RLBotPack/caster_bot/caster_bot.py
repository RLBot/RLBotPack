from rlbot.utils.structures.game_interface import GameInterface
from rlbot.utils.structures.game_data_struct import GameTickPacket,FieldInfoPacket
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

def host(_queue,voiceChoice):
    if voiceChoice:
        try:
            from gtts import gTTS
            from playsound import playsound
            googleTalk = True
        except:
            googleTalk = False
    else:
        googleTalk = False
    engine = pyttsx3.init()
    rate = engine.getProperty("rate")
    voices = engine.getProperty('voices')  # list of available voices
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
            for index,_comment in enumerate(best_comments):
                if _comment.time_generated < earliest_time:
                    earliest_comment = index
                    earliest_time = _comment.time_generated
            return earliest_comment
        else:
            return -1




    if len(voices) < 1:
        print("no usable voices found on this pc, exiting")
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
            #removing duplicates in the means below won't work as well when we add better variety
            if last_comment != None:
                if c.comment == last_comment.comment:
                    if c.time_generated - last_comment.time_generated < 10:
                        c.valid = False


        comment_storage = [c for c in comment_storage if c.valid ]
        c_index = pick_best_comment(comment_storage)
        if c_index != -1:
            comment = comment_storage.pop(c_index)
            if googleTalk:
                try:
                    tts = gTTS(comment.comment, lang='en', tld=random.choice(chosen_voices))
                    #absolutely HATE the implementation below
                    first = random.randint(1, 99999999)
                    second = random.randint(1, 99999999)
                    tts.save(f"{first}{second}.mp3")
                    playsound(f"{first}{second}.mp3")
                    os.remove(f"{first}{second}.mp3")
                except Exception as e:
                    print(e)
                    print("switching to offline voice mode")
                    googleTalk = False

            if not googleTalk:
                try:
                    engine.setProperty('voice', voices[comment.voiceID].id)
                except:
                    engine.setProperty('voice', voices[0].id)

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
        self.dangerously = rstring(["alarmingly", "perilously", "precariously", "dangerously"])
        self.RC_Intros = rstring(
            ["Here's a fun fact. ", "Check this out. ", "This is interesting. ", "What do you think about this?",
             "Oh, look at this."])
        self.touch_comments = ["makes contact", "gets a touch", "hits the ball", "gets a piece of the ball"]
        self.touch_commentary = []
        self.ballHistory = []
        self.lastTouches = []
        self.RC_list = [0, 1, 2, 3, 4, 5, 6, 7]
        self.teams = []
        self.zoneInfo = None
        self.joinTimer = 0
        self.packet = GameTickPacket()
        self.f_packet = None #FieldInfoPacket()
        self.ball_predictions = BallPrediction()
        self.lastCommentTime = time.time()
        self.q = Queue(maxsize=200)
        self.host = threading.Thread(target=host, args=(self.q, 1,))
        self.host.start()
        #self.host.join()

    def retire(self):
        with self.q.mutex:
            self.q.queue.clear()
        self.stopHost()
        self.host.join()



    def speak(self, phrase,priority,decayRate):
        if not self.q.full():
            self.q.put(Comment(phrase, random.randint(0, 1),priority,decayRate))
        self.lastCommentTime = time.time()

    def kickOffAnalyzer(self):
        if self.packet.game_info.is_kickoff_pause:
            if not self.KOE.active:
                self.KOE = KickoffExaminer(self.currentTime)

        else:
            if self.KOE.active:
                if len(self.ballHistory) > 0:
                    result = self.KOE.update(self.currentTime,self.ballHistory[-1])
                    if result == 0:
                        self.speak("The kickoff goes in favor of blue",1,3)
                    elif result == 1:
                        self.speak("The kickoff goes in favor of orange",1,3)
                    elif result == 2:
                        self.speak("It's a neutral kickoff.",1,3)


    def randomComment(self):
        if len(self.RC_list) > 0:
            choice = self.RC_list.pop(random.randint(0,len(self.RC_list)-1))
        else:
            self.RC_list = [0, 1, 2, 3, 4, 5, 6, 7]
            choice = self.RC_list.pop(random.randint(0,len(self.RC_list)-1))

        if choice == 0:
            self.speak(f"{self.RC_Intros} blue team's current average boost amount is {int(self.teams[0].getAverageBoost())}.",0,2)
            #blue avg boost

        elif choice == 1:
            self.speak(f"{self.RC_Intros} blue team's average speed this match is {int(self.teams[0].getMatchAverageSpeed())} unreal units per second.",0,2)
            #blue avg speed

        elif choice == 2:
            self.speak(f"{self.RC_Intros} blue team has jumped a total of {int(self.teams[0].getJumpCount())} times so far this match.",0,2)
            #blue jump count

        elif choice == 3:
            self.speak(f"{self.RC_Intros} blue team's average boost level during this match so far has been {int(self.teams[0].getMatchAverageBoost())}.",0,2)
            #blue match avg boost

        elif choice == 4:
            self.speak(f"{self.RC_Intros} orange team's current average boost amount is {int(self.teams[1].getAverageBoost())}.",0,2)
            #orange avg boost

        elif choice == 5:
            self.speak(f"{self.RC_Intros} orange team's average speed this match is {int(self.teams[1].getMatchAverageSpeed())} unreal units per second.",0,2)
            #orange avg speed

        elif choice == 6:
            self.speak(f"{self.RC_Intros} orange team has jumped a total of {int(self.teams[1].getJumpCount())} times so far this match.",0,2)
            #orange jump count

        elif choice == 7:
            self.speak(f"{self.RC_Intros} orange team's average boost level during this match so far has been {int(self.teams[1].getMatchAverageBoost())}.",0,2)
            #orange match avg boost

        else:
            self.speak("Hey, did you know that I'm terrible at making up random comments?", 0, 2)

    def timeCheck(self, newTime):
        if newTime - self.currentTime < -1:
            return True
        self.currentTime = newTime
        return False

    def overtimeCheck(self):
        if not self.overTime:
            if self.packet.game_info.is_overtime:
                self.overTime = True
                self.speak(f"That's the end of regulation time, we're headed into over-time with the score tied at {self.packet.teams[0].score}!",10,3)

    def gameWrapUp(self):
        if self.teams[0].score > self.teams[1].score:
            winner = "Blue"
        else:
            winner = "Orange"

        if abs(self.teams[0].score - self.teams[1].score) >=4:
            self.speak(f"Team {winner} has won today's match with a dominant performance.",10,1)
            #impressive victory
        else:
            #normal win message
            self.speak(f"Team {winner} clinched the victory this match",10,1)

        self.speak("Thank you all for watching today's game and don't forget to subscribe to Impossibum's youtube channel!", 10, 1)

    def stopHost(self):
        while self.q.full():
            pass
        self.speak("exit", 0, 0)

    def handleShotDetection(self):
        if self.shotDetection:
            if len(self.ballHistory) > 0:
                shot,goal = shotDetection(self.ball_predictions,2,self.currentTime)
                if shot:
                    if goal == 0:
                        loc = Vector([0,-5200,0])
                    else:
                        loc = Vector([0,5200,0])


                    if not self.KOE.active: #attempt to limit false positives from kickoffs... ugly solution is ugly
                        if self.lastTouches[-1].team == goal:
                            if not self.q.full():
                                #self.speak(f"That's a potential own goal from {self.lastTouches[-1].player_name}.",5,3)
                                pass
                        else:
                            if not self.q.full():
                                self.speak(f"{stringCleaner(self.lastTouches[-1].player_name)} takes a shot at the enemy net!",5,3)

                        #self.shooter = self.lastTouches[-1].player_index
                        if goal == 0:
                            shotTeam = 1
                        else:
                            shotTeam = 0
                        try:
                            self.shooter = self.teams[shotTeam].lastTouch.player_index
                        except:
                            pass
                            #possibly no touch yet in case of owngoals
                        self.shotDetection = False




    def updateTeamsInfo(self):
        for t in self.teams:
            t.updateMembers(self.packet)

    def updateTouches(self):
        try:
            touch = ballTouch(self.packet.game_ball.latest_touch)
        except Exception as e:
            touch = None
            print(e)

        if touch:
            if len(self.lastTouches) < 1 or self.lastTouches[-1] != touch:
                self.lastTouches.append(touch)
                for team in self.teams:
                    team.update(touch)
                if not self.shotDetection:
                    shot,goal = shotDetection(self.ball_predictions,2,self.currentTime)
                    if not shot:
                        if touch.player_index != self.shooter:
                            validSave = False
                            if goal == 0:
                                if distance2D(self.ballHistory[-1].location,Vector([0,-5200,0])) < 2500:
                                    validSave = True
                            else:
                                if distance2D(self.ballHistory[-1].location, Vector([0, 5200, 0])) < 2500:
                                    validSave = True
                            if validSave:
                                self.speak(f"{stringCleaner(touch.player_name)} makes the save!", 6, 4)

                self.shotDetection = True
                self.touch_commentary.append(f"{stringCleaner(touch.player_name)} {random.choice(self.touch_comments)}")



    def zone_analysis(self,ball_obj):
        corners = [0,1,2,3]
        boxes = [4,5]
        sides = [6,7]
        new_zone = find_current_zone(ball_obj)
        if self.currentZone == None:
            self.currentZone = new_zone
            return



        if new_zone != self.currentZone:
            if self.currentZone in sides:
                if new_zone in sides:
                    #self.speak(f"The ball crosses into {get_team_color_by_zone(new_zone)} territory.",0,1)
                    if self.zoneInfo.timeInZone(self.currentTime) >=20:
                        self.speak(
                            f"After {int(self.zoneInfo.timeInZone(self.currentTime))} seconds, the ball is finally cleared from the {get_team_color_by_zone(self.currentZone)} half.", 2,
                            2)
                    else:
                        #print(self.zoneInfo.timeInZone(self.currentTime))
                        pass

                elif new_zone in boxes:
                    if self.shotDetection:
                        self.speak(f"The ball is {self.dangerously} close to the {get_team_color_by_zone(new_zone)} goal!",2,2)

                elif new_zone in corners:
                    self.speak(
                        f" {stringCleaner(self.lastTouches[-1].player_name)} {self.contactNames} the ball to the {get_team_color_by_zone(new_zone)} corner.",1,2)


            elif self.currentZone in boxes:
                #leaving the box is worth mentioning
                self.speak(f"The ball is cleared out of the {get_team_color_by_zone(self.currentZone)} box by {stringCleaner(self.lastTouches[-1].player_name)}.",2,2)

            elif new_zone in corners:
                self.speak(
                    f" {stringCleaner(self.lastTouches[-1].player_name)} {self.contactNames} the ball to the {get_team_color_by_zone(new_zone)} corner.",1,2)

            elif new_zone in boxes:
                if self.shotDetection:
                    self.speak(f"The ball is {self.dangerously} close to the {get_team_color_by_zone(new_zone)} goal!",2,2)

            self.currentZone = new_zone
            self.zoneInfo.update(new_zone, self.currentTime)



    def updateGameBall(self):
        if self.packet.game_info.is_round_active:
            currentBall = ballObject(self.packet.game_ball)
            self.ballHistory.append(currentBall)
            self.zone_analysis(currentBall)

        if len(self.ballHistory) >1000:
            del self.ballHistory[0]

    def gatherMatchData(self):
        members = [[], []]
        for i in range(self.packet.num_cars):
            _car = Car(self.packet.game_cars[i].name, self.packet.game_cars[i].team, i)
            members[_car.team].append(_car)

        self.teams.append(Team(0, members[0]))
        self.teams.append(Team(1, members[1]))
        self.speak(
            f"Welcome to today's match. On team blue we have {', '.join([stringCleaner(x.name) for x in self.teams[0].members])} ",10,10)
        self.speak(
            f" and representing the orange team we have {', '.join([stringCleaner(x.name) for x in self.teams[1].members])} .",10,10)
        self.speak("Good luck everyone.",10,10)

    def scoreAnnouncement(self,teamIndex):
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
                self.speak(f"{scorer} scores! It barely limped across the goal line at {speed} kilometers per hour, but a goal is a goal.",10,10)

            elif speed >= 100:
                self.speak(f"{scorer} scores on a blazingly fast shot at  {speed} kilometers per hour! What a shot!",10,10)

            else:
                self.speak(f"And {scorer}'s shot goes in at {speed} kilometers per hour!",10,10)
        else:
            print("full q")

        if not self.q.full():
            self.speak(f"That goal brings the score to {self.teams[0].score} blue and {self.teams[1].score} orange.",10,10)
        else:
            print("full q")

    def scoreCheck(self):
        if self.teams[0].score != self.packet.teams[0].score:
            self.teams[0].score = self.packet.teams[0].score
            self.scoreAnnouncement(0)
            self.currentZone = 0

        if self.teams[1].score != self.packet.teams[1].score:
            self.teams[1].score = self.packet.teams[1].score
            self.scoreAnnouncement(1)
            self.currentZone = 0


    def run(self):
        while True:
            self.packet = self.wait_game_tick_packet()
            self.ball_predictions = self.get_ball_prediction_struct()
            if not self.f_packet:
                self.f_packet = self.get_field_info()
            if self.packet.game_info.is_match_ended:
                print("Game is over, exiting.")
                self.gameWrapUp()
                self.stopHost()
                break

            if self.firstIter:
                if self.packet.num_cars >= 1:
                    if self.joinTimer <= 0:
                        self.joinTimer = time.time()
                    if time.time() - self.joinTimer >=1: #arbitrary timer to ensure all cars connected
                        self.firstIter = False
                        self.currentTime = float(self.packet.game_info.seconds_elapsed)
                        self.gatherMatchData()
                        self.zoneInfo = ZoneAnalyst(self.currentZone, self.currentTime)
                        self.KOE = KickoffExaminer(self.currentTime)

            self.timeCheck(float(self.packet.game_info.seconds_elapsed)) #just updates time current
            if not self.firstIter:
                self.updateGameBall()
                self.updateTouches()
                self.updateTeamsInfo()
                self.handleShotDetection()
                self.scoreCheck()
                self.overtimeCheck()
                self.kickOffAnalyzer()
                if self.packet.game_info.is_kickoff_pause:
                    self.zoneInfo.zoneTimer = self.currentTime
                if time.time() - self.lastCommentTime >= 8:
                    self.randomComment()
                if len(self.touch_commentary) > 0:
                    if time.time() - self.lastCommentTime >= 5:
                        self.speak(self.touch_commentary[0], 1, 10)
                    self.touch_commentary = []





if __name__ == "__main__":
    script = Caster()
    script.run()
