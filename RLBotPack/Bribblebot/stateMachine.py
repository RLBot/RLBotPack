

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from state.dribble import Dribble
from state.state import State
from state.test import Test
from state.kickoff import Kickoff
from state.celebrationPostGame import CelebrationPostGame
from state.celebrationMidGame import CelebrationMidGame

class StateMachine: 

	def __init__(self, agent: BaseAgent):
		self.agent = agent
		self.currentState = None

		self.lastTick = 0

		self.lastScoreDiff = None

		self.lastAction = None



	def tick(self, packet: GameTickPacket):
		
		# print(f"matchend:\t{packet.game_info.is_match_ended}\tactive:\t{packet.game_info.is_round_active}\tkickoff:\t{packet.game_info.is_kickoff_pause}\tovertime:\t{packet.game_info.is_overtime}\tballCenter:\t{packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0}\ttimeLeft:\t{packet.game_info.game_time_remaining}")
		

		isBallInCenter = packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0
		isNegativeTimeLeft = packet.game_info.game_time_remaining < 0 and not packet.game_info.is_unlimited_time

		# temporary workaround for framework bug, see https://github.com/RLBot/RLBot/issues/481
		# TODO: this fix is still active even when the countdown started and kickoff is over, only important if noone hits the ball.
	

		action = None
		
		ACTION_GAME = 1
		ACTION_KICKOFF = Kickoff
		ACTION_MIDGAMECELEBRATION = CelebrationMidGame
		ACTION_POSTGAMECELEBRATION = CelebrationPostGame

		
		
		teamScores = tuple(map(lambda x: x.score, packet.teams))
		scoreDiff = max(teamScores) - min(teamScores)
		if self.lastScoreDiff == None:
			self.lastScoreDiff = scoreDiff
		if packet.game_info.is_match_ended:
			action = ACTION_POSTGAMECELEBRATION
		elif scoreDiff != self.lastScoreDiff:
			action = ACTION_MIDGAMECELEBRATION
			self.lastScoreDiff = scoreDiff
		elif isBallInCenter:
			action = ACTION_KICKOFF
			self.agent.firstTpsReport = True
		else:
			action = ACTION_GAME


		assert action != None

		if action == ACTION_GAME:




			if self.lastAction != action:
				self.lastTick = self.agent.currentTick


			if self.currentState == None:
				self.selectState(packet)

		elif self.lastAction != action:
			assert issubclass(action, State)
			if self.lastAction != action:
				self.currentState = action(self.agent)

		self.lastAction = action

		# self.agent.draw.text2D(self.currentState.__class__.__name__ if self.currentState else "None", self.agent.index)
		
		if not self.currentState.tick(packet):
			self.selectState(packet)
			assert self.currentState.tick(packet), "State exited without doing tick"

		return



	def changeStateAndContinueTick(self, newState, packet, *args) -> bool:
		
		if self.currentState == None or self.currentState.__class__.__name__ != newState.__name__:
			print(f"[{self.agent.index}] switched state to {newState.__name__}")
			self.currentState = newState(self.agent, *args)
		return self.currentState.tick(packet)


	def changeStateIfDifferent(self, newState):
		if self.currentState == None or self.currentState.__class__.__name__ != newState.__name__:
			print(f"[agent{self.agent.index}] switched state to {newState.__name__}")
			self.currentState = newState(self.agent)


	def selectState(self, packet: GameTickPacket):
		# if packet.game_ball.physics.location.z < 100:
		#     self.currentState = Test(self.agent)
		# else:
		self.currentState = Dribble(self.agent)

	def changeStateMidTick(self, state: State):
		self.currentState = state(self.agent)
		self.stateChanged = True



