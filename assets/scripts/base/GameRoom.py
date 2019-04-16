# -*- coding: utf-8 -*-

import KBEngine
from KBEDebug import *
import time
from datetime import datetime
from interfaces.GameObject import GameObject
from entitymembers.iRoomRules import iRoomRules
from entitymembers.PlayerProxy import PlayerProxy
import const
import random
import switch
import utility

class GameRoom(KBEngine.Base, GameObject, iRoomRules):
	"""
	这是一个游戏房间/桌子类
	该类处理维护一个房间中的实际游戏， 例如：斗地主、麻将等
	该房间中记录了房间里所有玩家的mailbox，通过mailbox我们可以将信息推送到他们的客户端。
	"""
	def __init__(self):
		GameObject.__init__(self)
		iRoomRules.__init__(self)

		self.owner_uid = 0
		self.agent = None
		self.roomID = None

		# 状态0：未开始游戏， 1：某一局游戏中
		self.state = 0

		# 存放该房间内的玩家mailbox
		self.players_dict = {}
		self.players_list = [None] * const.ROOM_PLAYER_NUMBER
		self.origin_players_list = [None] * const.ROOM_PLAYER_NUMBER

		# 上局庄家
		self.last_dealer_idx = 0
		# 庄家index
		self.dealer_idx = 0
		# 当前控牌的玩家index
		self.current_idx = 0
		# 对当前打出的牌可以进行操作的玩家的index, 服务端会限时等待他的操作
		self.wait_idx = None
		self.wait_op = None
		# 房间基础轮询timer
		self._poll_timer = None
		# 玩家操作限时timer
		self._op_timer = None
		# 一局游戏结束后, 玩家准备界面等待玩家确认timer
		self._next_game_timer = None

		#财神
		self.kingTile = 0
		#打出财神的玩家idx
		self.discardKingTileIdx = -2

		self.current_round = 0
		self.all_discard_tiles = []
		# 最后一位出牌的玩家
		self.last_player_idx = -1
		# 房间开局所有操作的记录(aid, src, des, tile)
		self.op_record = []
		# 确认继续的玩家
		self.confirm_next_idx = []

		# 解散房间操作的发起者
		self.dismiss_room_from = -1
		# 解散房间操作开始的时间戳
		self.dismiss_room_ts = 0
		# 解散房间操作投票状态
		self.dismiss_room_state_list = [0, 0, 0, 0]
		self.dismiss_timer = None
		#目前老庄数
		self.curOldDealNum = self.startOldDealNum

		# self.addTimer(const.ROOM_EXIST_TIME, 0, const.TIMER_TYPE_ROOM_EXIST)
		self.roomOpenTime = time.time()

	@property
	def isFull(self):
		count = sum([1 for i in self.players_list if i is not None])
		return count == const.ROOM_PLAYER_NUMBER

	@property
	def isEmpty(self):
		count = sum([1 for i in self.players_list if i is not None])
		return count == 0 and self.agent is None

	@property
	def timeLeft(self):
		roomTimeLeft = const.ROOM_EXIST_TIME - (time.time()-self.roomOpenTime)
		if roomTimeLeft <= 0:
			return 0.0
		return roomTimeLeft

	def getSit(self):
		for i, j in enumerate(self.players_list):
			if j is None:
				return i

	def _reset(self):
		self.state = 0
		self.agent = None
		self.players_list = [None] * const.ROOM_PLAYER_NUMBER
		self.last_dealer_idx = 0
		self.dealer_idx = 0
		self.current_idx = 0
		self._poll_timer = None
		self._op_timer = None
		self._next_game_timer = None
		self.all_discard_tiles = []
		self.kingTile = 0
		self.discardKingTileIdx = -2
		self.current_round = 0
		self.confirm_next_idx = []
		self.dismiss_timer = None
		self.dismiss_room_ts = 0
		self.dismiss_room_state_list = [0, 0, 0, 0]
		self.curOldDealNum = self.startOldDealNum
		KBEngine.globalData["GameWorld"].delRoom(self)

	def throwTheDice(self, idxList):
		diceList = [[0, 0], [0, 0], [0, 0], [0, 0]]
		for idx in idxList:
			for i in range(0,2):
				diceNum = random.randint(1, 6)
				diceList[idx][i] = diceNum
		return diceList

	def getMaxDiceIdx(self, diceList):
		numList = []
		for i in range(len(diceList)):
			numList.append(diceList[i][0] + diceList[i][1])

		idx = 0
		num = 0
		for i in range(len(numList)):
			if numList[i] > num:
				idx = i
				num = numList[i]
		return idx, num

	def setCurOldDealNum(self, addDealNum = 0):
		if self.current_round > 1 and self.dealer_idx == self.last_dealer_idx:
			if self.maxOldDealNum <= 0:
				self.curOldDealNum += 1
			elif self.curOldDealNum < self.maxOldDealNum:
				self.curOldDealNum += 1
		else:
			if self.maxOldDealNum <= 0:
				self.curOldDealNum = self.startOldDealNum + addDealNum
			elif self.startOldDealNum + addDealNum > self.maxOldDealNum:
				self.curOldDealNum = self.maxOldDealNum
			else:
				self.curOldDealNum = self.startOldDealNum + addDealNum

	def deal(self):
		""" 发牌 """
		for i in range(const.INIT_TILE_NUMBER):
			for j in range(const.ROOM_PLAYER_NUMBER):
				self.players_list[j].tiles.append(self.tiles[j])
			# t1, t2, t3, t4 = self.tiles[:4]
			self.tiles = self.tiles[const.ROOM_PLAYER_NUMBER:]
			# self.players_list[0].tiles.append(t1)
			# self.players_list[1].tiles.append(t2)
			# self.players_list[2].tiles.append(t3)
			# self.players_list[3].tiles.append(t4)
		#财神
		self.kingTile = self.tiles[0]
		self.tiles = self.tiles[1:]
		DEBUG_MSG("deal:room kingTile is {}.".format(self.kingTile))
		for i in range(const.ROOM_PLAYER_NUMBER):
			self.players_list[i].tidy(self.kingTile)

	def onTimer(self, id, userArg):
		DEBUG_MSG("Room.onTimer called: id %i, userArg: %i" % (id, userArg))

		if userArg == const.TIMER_TYPE_DISMISS_WAIT:
			self.delTimer(id)
			self.dropRoom()
		# if userArg == const.TIMER_TYPE_ROOM_EXIST:
		# 	self.game_round = self.current_round
		# 	self.delTimer(id)


	def reqEnterRoom(self, avt_mb, first=False):
		"""
		defined.
		客户端调用该接口请求进入房间/桌子
		"""
		if self.isFull:
			avt_mb.enterRoomFailed(const.ENTER_FAILED_ROOM_FULL)
			return

		# 代开房
		if first and self.is_agent == 1:
			self.agent = PlayerProxy(avt_mb, self, -1)
			self.players_dict[avt_mb.userId] = self.agent
			avt_mb.enterRoomSucceed(self, -1)
			return

		for i, p in enumerate(self.players_list):
			if p and p.mb and p.mb.userId == avt_mb.userId:
				p.mb = avt_mb
				avt_mb.enterRoomSucceed(self, i)
				return

		DEBUG_MSG("Room.reqEnterRoom: %s" % (self.roomID))
		idx = self.getSit()
		n_player = PlayerProxy(avt_mb, self, idx)
		self.players_dict[avt_mb.userId] = n_player
		self.players_list[idx] = n_player
		# 确认准备
		# if idx not in self.confirm_next_idx:
		# 	self.confirm_next_idx.append(idx)

		if not first:
			self.broadcastEnterRoom(idx)
			self.check_same_ip()

		if self.isFull:
			self.origin_players_list = self.players_list[:]

		# if self.isFull:
		# 	if self.is_agent == 1 and self.agent and self.agent.mb:
		# 		try:
		# 			self.agent.mb.quitRoomSucceed()
		# 			leave_tips = "您代开的房间已经开始游戏, 您已被请离.\n房间号【{}】".format(self.roomID)
		# 			self.agent.mb.showTip(leave_tips)
		# 		except:
		# 			pass

		# 	self.startGame()
			# self.addTimer(const.START_GAME_WAIT_TIME, 0, const.TIMER_TYPE_START_GAME)

	def reqReconnect(self, avt_mb):
		DEBUG_MSG("GameRoom reqReconnect userid = {}".format(avt_mb.userId))
		if avt_mb.userId not in self.players_dict.keys():
			return

		DEBUG_MSG("GameRoom reqReconnect player is in room".format(avt_mb.userId))
		# 如果进来房间后牌局已经开始, 就要传所有信息
		# 如果还没开始, 跟加入房间没有区别
		player = self.players_dict[avt_mb.userId]
		if self.agent and player.userId == self.agent.userId:
			self.agent.mb = avt_mb
			self.agent.online = 1
			avt_mb.enterRoomSucceed(self, -1)
			return
		
		player.mb = avt_mb
		player.online = 1
		if self.state == 1 or 0 < self.current_round <= self.game_round:
			if self.state == 0:
				# 重连回来直接准备
				self.roundEndCallback(avt_mb)
			rec_room_info = self.get_reconnect_room_dict(player.mb.userId)
			player.mb.handle_reconnect(rec_room_info)
		else:
			sit = 0
			for idx, p in enumerate(self.players_list):
				if p and p.mb:
					if p.mb.userId == avt_mb.userId:
						sit = idx
						break
			avt_mb.enterRoomSucceed(self, sit)

		# self.check_same_ip()

	def reqLeaveRoom(self, player):
		"""
		defined.
		客户端调用该接口请求离开房间/桌子
		"""
		DEBUG_MSG("Room.reqLeaveRoom:{0}, is_agent={1}".format(self.roomID, self.is_agent))
		if player.userId in self.players_dict.keys():
			n_player = self.players_dict[player.userId]
			idx = n_player.idx


			if idx == -1 and self.is_agent == 1:
				self.dropRoom()
			elif idx == 0 and self.is_agent == 0:
				# 房主离开房间, 则解散房间
				self.dropRoom()
			else:
				n_player.mb.quitRoomSucceed()
				self.players_list[idx] = None
				del self.players_dict[player.userId]
				if idx in self.confirm_next_idx:
					self.confirm_next_idx.remove(idx)
				# 通知其它玩家该玩家退出房间
				for i, p in enumerate(self.players_list):
					if i != idx and p and p.mb:
						p.mb.othersQuitRoom(idx)
				if self.agent and self.agent.mb:
					self.agent.mb.othersQuitRoom(idx)

		if self.isEmpty:
			self._reset()

	def dropRoom(self):
		for p in self.players_list:
			if p and p.mb:
				try:
					p.mb.quitRoomSucceed()
				except:
					pass

		if self.agent and self.agent.mb:
			try:
				# # 如果是代开房, 没打完一局返还房卡
				# if self.is_agent == 1 and self.current_round < 2:
				# 	# cost = 2 if self.game_round == 16 else 1
				# 	cost = 1
				# 	self.agent.mb.addCards(cost, "dropRoom")
				self.agent.mb.quitRoomSucceed()
			except:
				pass

		self._reset()

	def startGame(self):
		""" 开始游戏 """
		self.op_record = []
		self.state = 1
		self.current_round += 1
		self.discardKingTileIdx = -2

		diceList = [[0, 0], [0, 0], [0, 0], [0, 0]]

		addDealNum = 0
		if self.current_round <= 1: #首次选庄
			diceList = self.throwTheDice([0,1,2,3])
			idx, num = self.getMaxDiceIdx(diceList)
			self.dealer_idx = idx
			if self.diceAddNum > 0 and num >= self.diceAddNum:
				addDealNum += 1
			elif self.isSameAdd > 0 and diceList[idx][0] == diceList[idx][1]:
				addDealNum += 1	
		else:
			diceList = self.throwTheDice([self.dealer_idx])
			idx, num = self.getMaxDiceIdx(diceList)
			if self.dealer_idx != self.last_dealer_idx:
				if self.diceAddNum > 0 and num >= self.diceAddNum:
					addDealNum += 1
				elif self.isSameAdd > 0 and diceList[idx][0] == diceList[idx][1]:
					addDealNum += 1

		#老庄
		self.setCurOldDealNum(addDealNum)
		DEBUG_MSG("start game,curOldDealNum{0},dealer_idx{1},diceList{2}".format(self.curOldDealNum, self.dealer_idx, str(diceList)))

		# 仅仅在第1局扣房卡, 不然每局都会扣房卡
		def callback(content):
			content = content.decode()
			try:
				if content[0] != '{':
					DEBUG_MSG(content)
					self.dropRoom()
					return
				# 第一局时房间默认房主庄家, 之后谁上盘赢了谁是, 如果臭庄, 最后摸牌的人是庄
				for p in self.players_list:
					p.reset()
				self.initTiles()
				self.deal()
				self.current_idx = self.dealer_idx

				for p in self.players_list:
					if p and p.mb:
						p.mb.startGame(self.dealer_idx, p.tiles, self.kingTile, diceList, self.curOldDealNum, self.createRoomInfoList)

				# 是否起手4个红中就可以胡牌
				# for i, p in enumerate(self.players_list):
				# 	if self.first_hand_win(p.tiles):
				# 		self.winGame(i, const.OP_WIN)
				# 		return

				self.beginRound()
			except:
				DEBUG_MSG("consume failed!")

		if self.current_round == 1 and self.is_agent == 0:
			card_cost, diamond_cost = switch.calc_cost(self.maxOldDealNum, self.maxLoseScore)
			if switch.DEBUG_BASE:
				callback('{"card":99, "diamond":999}'.encode())
			else:
				utility.update_card_diamond(self.players_list[0].mb.accountName, -card_cost, -diamond_cost, callback, "XiaoShanMJ RoomID:{}".format(self.roomID))
			return

		DEBUG_MSG("start Game: Room{0} - Round{1}".format(self.roomID, str(self.current_round)+'/'+str(self.game_round)))

		callback('{"card":99, "diamond":999}'.encode())

	def cutAfterKong(self):
		if not self.can_cut_after_kong():
			return
		if len(self.tiles) <= self.lucky_tile:
			self.drawEnd()
			return

		player = self.players_list[self.current_idx]
		ti = self.tiles[0]
		self.tiles = self.tiles[1:]
		player.cutTile(ti)

	def beginRound(self):
		if len(self.tiles) <= self.lucky_tile:
			self.drawEnd()
			return

		player = self.players_list[self.current_idx]
		ti = self.tiles[0]
		self.tiles = self.tiles[1:]
		player.drawTile(ti)

	def reqStopGame(self, player):
		"""
		客户端调用该接口请求停止游戏
		"""
		DEBUG_MSG("Room.reqLeaveRoom: %s" % (self.roomID))
		self.state = 0
		# self.delTimer(self._poll_timer)
		# self._poll_timer = None


	def drawEnd(self):
		""" 臭庄 """
		self.last_dealer_idx = self.dealer_idx
		self.dealer_idx = (self.current_idx + 4 - 1) % 4

		self.settlementScoreRoundEnd(True)

		info = dict()
		info['lucky_tiles'] = []
		info['op_list'] = [-1]
		info['win_idx_list'] = [-1]
		info["result"] = [0] * 17
		if self.timeLeft <= 0:
			self.game_round = self.current_round
		if self.current_round < self.game_round:
			self.broadcastRoundEnd(info)
		else:
			self.endAll(info)

	def winGame(self, idx, op, multiple, resultList):
		""" 座位号为idx的玩家胡牌 """
		self.last_dealer_idx = self.dealer_idx
		self.dealer_idx = idx
		p = self.players_list[idx]
		# lucky_tiles, hit = self.cal_lucky_tile(p.tiles, self.lucky_tile)
		lucky_tiles, hit =  [], 0
		if self.lucky_tile == 1:
			p.lucky_tile += 1
		else:
			p.lucky_tile += hit
		self.cal_score(idx, op, hit, multiple)

		self.settlementScoreRoundEnd(False)

		info = dict()
		info['lucky_tiles'] = lucky_tiles
		info['op_list'] = [op]
		info['win_idx_list'] = [idx]
		info["result"] = resultList
		if self.timeLeft <= 0:
			self.game_round = self.current_round
		if self.current_round < self.game_round:
			self.broadcastRoundEnd(info)
		else:
			self.endAll(info)

	def settlementScoreRoundEnd(self, isDrawEnd):
		for i in range(len(self.players_list)):
			if self.players_list[i].roundEndSettlement(isDrawEnd):
				self.game_round = self.current_round

	def endAll(self, info):
		""" 游戏局数结束, 给所有玩家显示最终分数记录 """

		# 先记录玩家当局战绩, 会累计总得分
		self.record_round_result()

		info['left_tiles'] = info['left_tiles'] = self.tiles
		info['player_info_list'] = [p.get_round_client_dict() for p in self.players_list if p is not None]
		player_info_list = [p.get_final_client_dict() for p in self.players_list if p is not None]
		# DEBUG_MSG("%" * 30)
		# DEBUG_MSG("FinalEnd info = {}".format(player_info_list))
		for p in self.players_list:
			if p and p.mb:
				p.mb.finalResult(player_info_list, info)

		self._reset()

	def sendEmotion(self, avt_mb, eid):
		""" 发表情 """
		# DEBUG_MSG("Room.Player[%s] sendEmotion: %s" % (self.roomID, eid))
		idx = None
		for i, p in enumerate(self.players_list):
			if p and avt_mb == p.mb:
				idx = i
				break
		else:
			if self.agent and self.agent.userId == avt_mb.userId:
				idx = -1

		if idx is None:
			return

		if self.agent and idx != -1 and self.agent.mb:
			self.agent.mb.recvEmotion(idx, eid)

		for i, p in enumerate(self.players_list):
			if p and i != idx:
				p.mb.recvEmotion(idx, eid)

	def sendMsg(self, avt_mb, mid):
		""" 发消息 """
		# DEBUG_MSG("Room.Player[%s] sendMsg: %s" % (self.roomID, mid))
		idx = None
		for i, p in enumerate(self.players_list):
			if p and avt_mb == p.mb:
				idx = i
				break
		else:
			if self.agent and self.agent.userId == avt_mb.userId:
				idx = -1

		if idx is None:
			return

		if self.agent and idx != -1 and self.agent.mb:
			self.agent.mb.recvMsg(idx, mid)

		for i, p in enumerate(self.players_list):
			if p and i != idx:
				p.mb.recvMsg(idx, mid)

	def sendVoice(self, avt_mb, url):
		# DEBUG_MSG("Room.Player[%s] sendVoice" % (self.roomID))
		idx = None
		for i, p in enumerate(self.players_list):
			if p and avt_mb.userId == p.userId:
				idx = i
				break
		else:
			if self.agent and self.agent.userId == avt_mb.userId:
				idx = -1

		if idx is None:
			return
		if self.agent and idx != -1 and self.agent.mb:
			self.agent.mb.recvVoice(idx, url)

		for i, p in enumerate(self.players_list):
			if p and p.mb:
				p.mb.recvVoice(idx, url)

	def sendAppVoice(self, avt_mb, url, time):
		# DEBUG_MSG("Room.Player[%s] sendVoice" % (self.roomID))
		idx = None
		for i, p in enumerate(self.players_list):
			if p and avt_mb.userId == p.userId:
				idx = i
				break
		else:
			if self.agent and self.agent.userId == avt_mb.userId:
				idx = -1

		if idx is None:
			return
		if self.agent and idx != -1 and self.agent.mb:
			self.agent.mb.recvAppVoice(idx, url, time)

		for i, p in enumerate(self.players_list):
			if p and p.mb:
				p.mb.recvAppVoice(idx, url, time)

	def doOperation(self, avt_mb, aid, tile_list):
		"""
		当前控牌玩家摸牌后向服务端确认的操作
		:param idx: 当前打牌的人的座位
		:param aid: 操作id
		:param tile: 针对的牌
		:return: 确认成功或者失败
		"""
		if self.dismiss_room_ts != 0 and int(time.time() - self.dismiss_room_ts) < const.DISMISS_ROOM_WAIT_TIME:
			# 说明在准备解散投票中,不能进行其他操作
			return

		tile = tile_list[0]
		idx = -1
		for i, p in enumerate(self.players_list):
			if p and p.mb == avt_mb:
				idx = i

		if idx != self.current_idx or self.wait_idx is not None:
			avt_mb.doOperationFailed(const.OP_ERROR_NOT_CURRENT)
			return

		# self.delTimer(self._op_timer)
		p = self.players_list[idx]
		if aid == const.OP_DISCARD and self.can_discard(p.tiles, tile):
			self.all_discard_tiles.append(tile)
			p.discardTile(self.kingTile, tile)
		elif aid == const.OP_CONCEALED_KONG and self.can_concealed_kong(p.tiles, tile):
			p.concealedKong(tile)
		elif aid == const.OP_EXPOSED_KONG and self.can_self_exposed_kong(p, tile):
			p.self_exposedKong(tile)
		elif aid == const.OP_PASS:
			# 自己摸牌的时候可以杠或者胡时选择过, 则什么都不做. 继续轮到该玩家打牌.
			pass
		elif aid == const.OP_WIN:
			resultList = self.can_win(list(p.tiles), idx)
			if sum([1 for i in resultList if i > 0]) > 0:
				DEBUG_MSG("cal_multiple:{0},olderDeal:{1}".format(str(self.cal_multiple(resultList)), str(self.curOldDealNum)))
				multiple = self.cal_multiple(resultList)
				p.win(multiple, resultList)
			else:
				avt_mb.doOperationFailed(const.OP_ERROR_ILLEGAL)
				self.current_idx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
				self.beginRound()
		else:
			avt_mb.doOperationFailed(const.OP_ERROR_ILLEGAL)
			self.current_idx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
			self.beginRound()


	def confirmOperation(self, avt_mb, aid, tile_list):
		""" 被轮询的玩家确认了某个操作 """
		if self.dismiss_room_ts != 0 and int(time.time() - self.dismiss_room_ts) < const.DISMISS_ROOM_WAIT_TIME:
			# 说明在准备解散投票中,不能进行其他操作
			return

		tile = tile_list[0]
		idx = -1
		for i, p in enumerate(self.players_list):
			if p and p.mb == avt_mb:
				idx = i

		if idx != self.wait_idx:
			avt_mb.doOperationFailed(const.OP_ERROR_NOT_CURRENT)
			return
		# 确认要操作的牌是否是最后一张被打的牌
		if aid != const.OP_PASS and tile != self.all_discard_tiles[-1]:
			avt_mb.doOperationFailed(const.OP_ERROR_ILLEGAL)
			return

		# self.delTimer(self._poll_timer)

		self.wait_idx = None
		self.wait_op = None
		p = self.players_list[idx]
		if aid == const.OP_PONG and self.can_pong(p.tiles, tile, idx):
			self.current_idx = idx
			p.pong(tile)
		elif aid == const.OP_EXPOSED_KONG and self.can_exposed_kong(p.tiles, tile, idx):
			self.current_idx = idx
			p.exposedKong(tile)
		elif aid == const.OP_CHOW and self.can_chow_one(p.tiles, tile_list, idx):
			self.current_idx = idx
			p.chow(tile_list)
		else:
			#无任何操作 过牌
			nextIdx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
			nextMb = self.players_list[nextIdx]
			if idx != nextIdx and self.can_chow(nextMb.tiles, self.all_discard_tiles[-1], nextIdx):
				self.wait_idx = nextIdx
				self.wait_op = const.OP_DISCARD
				nextMb.mb.waitForOperation(const.OP_DISCARD, [self.all_discard_tiles[-1],])
			else:
				self.current_idx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
				self.beginRound()

	def broadcastOperation(self, idx, aid, tile_list = None):
		"""
		将操作广播给所有人, 包括当前操作的玩家
		:param idx: 当前操作玩家的座位号
		:param aid: 操作id
		:param tile_list: 出牌的list
		"""
		for i, p in enumerate(self.players_list):
			if p is not None:
				p.mb.postOperation(idx, aid, tile_list)

	def broadcastOperation2(self, idx, aid, tile_list = None):
		""" 将操作广播除了自己之外的其他人 """
		for i, p in enumerate(self.players_list):
			if p and i != idx:
				p.mb.postOperation(idx, aid, tile_list)

	def broadcastMultiOperation(self, idx_list, aid_list, tile_list=None):
		for i, p in enumerate(self.players_list):
			if p is not None:
				p.mb.postMultiOperation(idx_list, aid_list, tile_list)

	def broadcastRoundEnd(self, info):
		# 广播胡牌或者流局导致的每轮结束信息, 包括算的扎码和当前轮的统计数据

		# 先记录玩家当局战绩, 会累计总得分
		self.record_round_result()

		self.state = 0
		info['left_tiles'] = self.tiles
		info['player_info_list'] = [p.get_round_client_dict() for p in self.players_list if p is not None]

		DEBUG_MSG("&" * 30)
		DEBUG_MSG("RoundEnd info = {}".format(info))
		self.confirm_next_idx = []
		for p in self.players_list:
			if p:
				p.mb.roundResult(info)

		# self._next_game_timer = self.addTimer(const.NEXT_GAME_WAIT_TIME, 0, const.TIMER_TYPE_NEXT_GAME)

	def checkDicsardKingTile(self, idx, aid, tile):
		#玩家打出财神
		if aid != const.OP_DISCARD:
			return
		if tile == self.kingTile and self.discardKingTileIdx < 0:	#打出的是财神 （同一圈只有第一张财神有效）
			self.discardKingTileIdx = idx
		elif tile != self.kingTile and self.discardKingTileIdx == idx:	#又轮到出财神玩家出牌（继续出财神则等到下一圈才恢复）
			self.discardKingTileIdx = -2

	def waitForOperation(self, idx, aid, tile):
		#能不能碰和杠
		for i, p in enumerate(self.players_list):
			if p and i != idx:
				if aid == const.OP_DISCARD:
					if self.can_pong(p.tiles, tile, i) or self.can_exposed_kong(p.tiles, tile, i):
						self.wait_idx = i
						self.wait_op = aid
						p.mb.waitForOperation(aid, [tile,])
						break
		else:
			#下家能不能吃
			nextIdx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
			p = self.players_list[nextIdx]
			if self.can_chow(p.tiles, tile, nextIdx) and aid == const.OP_DISCARD:	#能吃
				self.wait_idx = nextIdx
				self.wait_op = aid
				p.mb.waitForOperation(aid, [tile,])
			else:
				self.current_idx = (self.current_idx + 1) % const.ROOM_PLAYER_NUMBER
				self.beginRound()

	#判断是否可以抢杠胡
	# def checkOthersWin(self, idx, tile):
	# 	kong_win = []
	# 	for i, p in enumerate(self.players_list):
	# 		if i == idx:
	# 			continue

	# 		tmp = list(p.tiles)
	# 		tmp.append(tile)
	# 		if self.can_win(tmp):
	# 			kong_win.append(p)
	# 	return kong_win

	#抢杠胡处理
	# def processKongWin(self, win_list, tile):
	# 	""" 处理抢杠胡, 可能有多人胡的情况 """
	# 	if len(win_list) == 1:
	# 		p = win_list[0]
	# 		p.kong_win(tile)
	# 		self.broadcastOperation(p.idx, const.OP_KONG_WIN, [tile,])
	# 		self.winGame(p.idx, const.OP_KONG_WIN)
	# 	else:
	# 		win_idx_list = [mem.idx for mem in win_list]
	# 		op_list = [const.OP_KONG_WIN] * len(win_idx_list)
	# 		self.broadcastMultiOperation(win_idx_list, op_list, [tile,])

	# 		self.dealer_idx = win_idx_list[0]
	# 		all_mem_tiles = []
	# 		for mem in win_list:
	# 			mem.kong_win(tile)
	# 			all_mem_tiles.extend(mem.tiles)
	# 		lucky_tiles, hit = self.cal_lucky_tile(all_mem_tiles, self.lucky_tile)

	# 		last_aid, src, des, tiles = self.op_record[-1]
	# 		des_p = self.players_list[des]
	# 		for mem in win_list:
	# 			if self.lucky_tile == 1:
	# 				mem.lucky_tile += 1
	# 			else:
	# 				mem.lucky_tile += hit

	# 			if self.lucky_tile == 1:
	# 				mem.score += (hit + 2) * 3
	# 				des_p.score -= (hit + 2) * 3
	# 			else:
	# 				mem.score += 2 * (hit + 1) * 3
	# 				des_p.score -= 2 * (hit + 1) * 3

	# 		info = dict()
	# 		info['lucky_tiles'] = lucky_tiles
	# 		info['op_list'] = op_list
	# 		info['win_idx_list'] = win_idx_list
	# 		if self.current_round < self.game_round:
	# 			self.broadcastRoundEnd(info)
	# 		else:
	# 			self.endAll(info)


	def get_init_client_dict(self):
		agent_d = {
			'nickname': "",
			'userId': 0,
			'head_icon': "",
			'ip': '0.0.0.0',
			'sex': 1,
			'idx': -1,
			'uuid': 0,
			'online': 1,
		}
		if self.is_agent and self.agent:
			d = self.agent.get_init_client_dict()
			agent_d.update(d)

		return {
			'roomID': self.roomID,
			'ownerId': self.owner_uid,
			'isAgent': self.is_agent,
			'agentInfo': agent_d,
			'dealerIdx': self.dealer_idx,
			'curRound': self.current_round + 1,
			'maxRound': self.game_round,
			'luckyTileNum': self.lucky_tile,
			'player_info_list': [p.get_init_client_dict() for p in self.players_list if p is not None],
			'createRoomInfoList': self.createRoomInfoList,
			'roomTimeLeft' : self.timeLeft,
			'player_state_list': [1 if i in self.confirm_next_idx else 0 for i in range(const.ROOM_PLAYER_NUMBER)],
		}

	def get_reconnect_room_dict(self, userId):
		dismiss_left_time = int(time.time() - self.dismiss_room_ts)
		if self.dismiss_room_ts == 0 or dismiss_left_time >= const.DISMISS_ROOM_WAIT_TIME:
			dismiss_left_time = 0

		idx = 0
		for p in self.players_list:
			if p and p.userId == userId:
				idx = p.idx
		waitAid = -1
		if self.wait_idx is not None and self.wait_op and idx == self.wait_idx:
			waitAid = self.wait_op

		agent_d = {
			'nickname': "",
			'userId': 0,
			'head_icon': "",
			'ip': '0.0.0.0',
			'sex': 1,
			'idx': -1,
			'uuid': 0,
			'online': 1,
		}
		if self.is_agent and self.agent:
			d = self.agent.get_init_client_dict()
			agent_d.update(d)

		return {
			'roomID': self.roomID,
			'isAgent': self.is_agent,
			'agentInfo': agent_d,
			'curRound': self.current_round,
			'maxRound': self.game_round,
			'luckyTileNum': self.lucky_tile,
			'ownerId': self.owner_uid,
			'dealerIdx': self.dealer_idx,
			'curPlayerSitNum': self.current_idx,
			'isPlayingGame': self.state,
			'player_state_list': [1 if i in self.confirm_next_idx else 0 for i in range(const.ROOM_PLAYER_NUMBER)],
			'lastDiscardTile': 0 if not self.all_discard_tiles else self.all_discard_tiles[-1],
			"lastDrawTile" : self.players_list[idx].last_draw,
			'lastDiscardTileFrom': self.last_player_idx,
			"lastDiscardTileNum" : self.getSerialSameTileNum(),
			"curOldDealNum" : self.curOldDealNum,
			"kingTile" : self.kingTile,
			"discardKingTileIdx" : self.discardKingTileIdx,
			'waitAid': waitAid,
			'leftTileNum': len(self.tiles),
			'applyCloseFrom': self.dismiss_room_from,
			'applyCloseLeftTime': dismiss_left_time,
			'applyCloseStateList': self.dismiss_room_state_list,
			'player_info_list': [p.get_reconnect_client_dict(userId) for p in self.players_list if p is not None],
			'createRoomInfoList': self.createRoomInfoList,
			'roomTimeLeft': self.timeLeft,
		}

	def broadcastEnterRoom(self, idx):
		new_p = self.players_list[idx]

		if self.is_agent == 1:
			if self.agent and self.agent.mb:
				self.agent.mb.othersEnterRoom(new_p.get_init_client_dict())

		for i, p in enumerate(self.players_list):
			if p is None:
				continue
			if i == idx:
				p.mb.enterRoomSucceed(self, idx)
			else:
				p.mb.othersEnterRoom(new_p.get_init_client_dict())

	def cal_win_kong_score(self, winIdx):
		kong_num_list = self.players_list[winIdx].kong_num_list
		if kong_num_list[0] > 0:
			for j in range(kong_num_list[0]):
				self.cal_score(winIdx, const.OP_CONCEALED_KONG)
		if kong_num_list[1] > 0:
			for j in range(kong_num_list[1]):
				self.cal_score(winIdx, const.OP_GET_KONG)
		if kong_num_list[2] > 0:
			for j in range(kong_num_list[2]):
				self.cal_score(winIdx, const.OP_EXPOSED_KONG)

	def cal_score(self, idx, aid, lucky_tile = 0, multiple = 0):
		if aid == const.OP_EXPOSED_KONG:
			winScore = 0
			for i, p in enumerate(self.players_list):
				if i != idx:
					winScore += p.addScore(-1)
			self.players_list[idx].addScore(-winScore)
		elif aid == const.OP_CONCEALED_KONG:
			winScore = 0
			for i, p in enumerate(self.players_list):
				if i != idx:
					winScore += p.addScore(-1)
			self.players_list[idx].addScore(-winScore)
		elif aid == const.OP_POST_KONG:
			pass
		elif aid == const.OP_GET_KONG:
			winScore = 0
			for i, p in enumerate(self.players_list):
				if i != idx:
					winScore += p.addScore(-1)
			self.players_list[idx].addScore(-winScore)
		elif aid == const.OP_WIN:
			self.cal_win_kong_score(idx)
			if idx == self.last_dealer_idx:	# 庄家赢
				winScore = 0
				curVal = pow(2,multiple + self.curOldDealNum)
				for i, p in enumerate(self.players_list):
					if i != idx:
						winScore += p.addScore(-curVal)
				self.players_list[idx].addScore(-winScore)
			else:						# 闲家赢
				winScore = 0
				for i, p in enumerate(self.players_list):
					if i != idx:
						if i == self.last_dealer_idx:
							curVal = pow(2,multiple + self.curOldDealNum)
							winScore += p.addScore(-curVal)
						else:
							curVal = pow(2,multiple)
							winScore += p.addScore(-curVal)
				self.players_list[idx].addScore(-winScore)
		elif aid == const.OP_KONG_WIN:
			pass

	def roundEndCallback(self, avt_mb):
		""" 一局完了之后玩家同意继续游戏 """
		if self.state == 1:
			return
		idx = -1
		for i, p in enumerate(self.players_list):
			if p and p.userId == avt_mb.userId:
				idx = i
				break
		if idx not in self.confirm_next_idx:
			self.confirm_next_idx.append(idx)
			for p in self.players_list:
				if p and p.idx != idx:
					p.mb.readyForNextRound(idx)

		if len(self.confirm_next_idx) == const.ROOM_PLAYER_NUMBER and self.isFull:
			if self.current_round == 0 and self.is_agent == 1 and self.agent:
				try:
					self.agent.mb.quitRoomSucceed()
					leave_tips = "您代开的房间已经开始游戏, 您已被请离.\n房间号【{}】".format(self.roomID)
					self.agent.mb.showTip(leave_tips)
				except:
					pass
			self.startGame()

	def record_round_result(self):
		# 玩家记录当局战绩
		d = datetime.fromtimestamp(time.time())
		round_result_d = {
			'date': '-'.join([str(d.year), str(d.month), str(d.day)]),
			'time': ':'.join([str(d.hour), str(d.minute)]),
			'round_record': [p.get_round_result_info() for p in self.origin_players_list if p],
		}

		# 第一局结束时push整个房间所有局的结构, 以后就增量push
		if self.current_round == 1:
			game_result_l = [[round_result_d]]
			for p in self.players_list:
				if p:
					p.record_all_result(game_result_l)
		else:
			for p in self.players_list:
				if p:
					p.record_round_game_result(round_result_d)

	def check_same_ip(self):
		ip_list = []
		for p in self.players_list:
			if p and p.mb and p.ip != '0.0.0.0':
				ip_list.append(p.ip)
			else:
				ip_list.append(None)

		tips = []
		checked = []
		for i in range(const.ROOM_PLAYER_NUMBER):
			if ip_list[i] is None or i in checked:
				continue
			checked.append(i)
			repeat = []
			repeat.append(i)
			for j in range(i+1, const.ROOM_PLAYER_NUMBER):
				if ip_list[j] is None or j in checked:
					continue
				if ip_list[i] == ip_list[j]:
					repeat.append(j)
			if len(repeat) > 1:
				name = []
				for k in repeat:
					checked.append(k)
					name.append(self.players_list[k].nickname)
				tip = '和'.join(name) + '有相同的ip地址'
				tips.append(tip)
		if tips:
			tips = '\n'.join(tips)
			# DEBUG_MSG(tips)
			for p in self.players_list:
				if p and p.mb:
					p.mb.showTip(tips)

	def apply_dismiss_room(self, avt_mb):
		""" 游戏开始后玩家申请解散房间 """
		self.dismiss_room_ts = time.time()
		src = None
		for i, p in enumerate(self.players_list):
			if p.userId == avt_mb.userId:
				src = p
				break

		# 申请解散房间的人默认同意
		self.dismiss_room_from = src.idx
		self.dismiss_room_state_list[src.idx] = 1

		self.dismiss_timer = self.addTimer(const.DISMISS_ROOM_WAIT_TIME, 0, const.TIMER_TYPE_DISMISS_WAIT)

		for p in self.players_list:
			if p and p.mb and p.userId != avt_mb.userId:
				p.mb.req_dismiss_room(src.idx)

	def vote_dismiss_room(self, avt_mb, vote):
		""" 某位玩家对申请解散房间的投票 """
		src = None
		for p in self.players_list:
			if p and p.userId == avt_mb.userId:
				src = p
				break

		self.dismiss_room_state_list[src.idx] = vote
		for p in self.players_list:
			if p and p.mb:
				p.mb.vote_dismiss_result(src.idx, vote)

		yes = self.dismiss_room_state_list.count(1)
		no = self.dismiss_room_state_list.count(2)
		if yes >= 3:
			self.delTimer(self.dismiss_timer)
			self.dismiss_timer = None
			self.dropRoom()

		if no >= 2:
			self.delTimer(self.dismiss_timer)
			self.dismiss_timer = None
			self.dismiss_room_from = -1
			self.dismiss_room_ts = 0
			self.dismiss_room_state_list = [0,0,0,0]

	def notify_player_online_status(self, userId, status):
		src = -1
		for idx, p in enumerate(self.players_list):
			if p and p.userId == userId:
				p.online = status
				src = idx
				break

		if src == -1:
			return

		for idx, p in enumerate(self.players_list):
			if p and p.mb and p.userId != userId:
				p.mb.notifyPlayerOnlineStatus(src, status)
