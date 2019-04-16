# -*- coding: utf-8 -*-
import KBEngine
from KBEDebug import *
import const
import utility
import json
import switch
import base64

class iRoomOperation(object):
	""" 玩家游戏相关 """

	def __init__(self):
		self.room = None

	# c2s
	#maxOldDealNum, startOldDealNum, diceAddNum, isSameAdd, maxLoseScore, is_agent=0
	def createRoom(self, createRoomInfoList):
		DEBUG_MSG("create room info list:{0}".format(str(createRoomInfoList)))
		if len(createRoomInfoList) < 4:
			return
		maxOldDealNum, startOldDealNum, diceAddNum, isSameAdd, maxLoseScore, is_agent = utility.getCreateRoomInfo(createRoomInfoList)

		def callback(content):
			content = content.decode()
			try:
				DEBUG_MSG("cards response: {}".format(content))
				if content[0] != '{':
					if getattr(self, 'client', None):
						self.client.createRoomFailed(const.CREATE_FAILED_OTHER)
					return
				data = json.loads(content)
				card_cost, diamond_cost = switch.calc_cost(maxOldDealNum, maxLoseScore)
				if not KBEngine.globalData["GameWorld"].free_play and card_cost > data["card"] and diamond_cost > data["diamond"]:
					if getattr(self, 'client', None):
						self.client.createRoomFailed(const.CREATE_FAILED_NO_ENOUGH_CARDS)
					return
				params = {
					'owner_uid': self.userId,
					'game_round': 999,
					'lucky_tile': 0,
					"maxOldDealNum" : maxOldDealNum,
					"startOldDealNum" : startOldDealNum,
					"diceAddNum" : diceAddNum,
					"isSameAdd"	: isSameAdd,
					"maxLoseScore" : maxLoseScore,
					'is_agent': is_agent,
					"createRoomInfoList" : createRoomInfoList
				}
				KBEngine.createBaseAnywhere("GameRoom", params, self.createRoomCallback)
			except:
				DEBUG_MSG("createRoom callback error:{}".format(content))
				if getattr(self, 'self', None):
					self.client.createRoomFailed(const.CREATE_FAILED_OTHER)
		if switch.DEBUG_BASE:
			callback('{"card":99, "diamond":999}'.encode())
		else:
			utility.get_user_info(self.accountName, callback)


	def createRoomCallback(self, room, err = None):
		if room:
			room.roomID = utility.gen_room_id(room.id)
			if room.is_agent == 1:
				def callback(content):
					try:
						content = content.decode()
						if content[0] != '{':
							DEBUG_MSG(content)
							return
						room.reqEnterRoom(self, True)
						self.room = room
						KBEngine.globalData["GameWorld"].addRoom(room)
						info = room.get_init_client_dict()
						if getattr(self, 'client', None):
							self.client.createRoomSucceed(info)
					except:
						DEBUG_MSG("agent consume callback error:{}".format(content))
				card_cost, diamond_cost = switch.calc_cost(room.maxOldDealNum, room.maxLoseScore)
				if switch.DEBUG_BASE:
					callback('{"card":99, "diamond":999}'.encode())
				else:
					utility.update_card_diamond(self.accountName, -card_cost, -diamond_cost ,callback, "XiaoShanMJ RoomID:{}".format(self.roomID)) # reason 必须为英文
			else:
				room.reqEnterRoom(self, True)
				self.room = room
				KBEngine.globalData["GameWorld"].addRoom(room)
				info = room.get_init_client_dict()
				if getattr(self, 'client', None):
					self.client.createRoomSucceed(info)
		else:
			if getattr(self, 'client', None):
				self.client.createRoomFailed(const.CREATE_FAILED_OTHER)

	# c2s
	def enterRoom(self, roomID):
		KBEngine.globalData["GameWorld"].enterRoom(roomID, self)

	def enterRoomSucceed(self, room, idx):
		self.room = room
		info = room.get_init_client_dict()
		DEBUG_MSG(info)
		# DEBUG_MSG('@' * 30)
		if getattr(self, 'client', None):
			self.client.enterRoomSucceed(idx, info)

	def enterRoomFailed(self, err):
		if getattr(self, 'client', None):
			self.client.enterRoomFailed(err)

	def othersEnterRoom(self, player_info):
		if getattr(self, 'client', None):
			self.client.othersEnterRoom(player_info)

	def othersQuitRoom(self, idx):
		if getattr(self, 'client', None):
			self.client.othersQuitRoom(idx)

	# c2s
	def quitRoom(self):
		if self.room:
			KBEngine.globalData["GameWorld"].quitRoom(self.room.roomID, self)

	def quitRoomSucceed(self):
		DEBUG_MSG('@' * 30)
		DEBUG_MSG('avatar quit room succeed!')
		self.room = None
		if getattr(self, 'client', None):
			self.client.quitRoomSucceed()

	def quitRoomFailed(self, err):
		# DEBUG_MSG('@' * 30)
		# DEBUG_MSG('avatar quit room failed!')
		if getattr(self, 'client', None):
			self.client.quitRoomFailed(err)

	def startGame(self, dealer_idx, tile_list, kingTile, diceList, curOldDealNum, createRoomInfoList):
		if getattr(self, 'client', None):
			self.client.startGame(dealer_idx, tile_list, kingTile, diceList, curOldDealNum, createRoomInfoList)

	def postOperation(self, idx, aid, tile_list):
		if getattr(self, 'client', None):
			self.client.postOperation(idx, aid, tile_list)

	def postMultiOperation(self, idx_list, aid_list, tile_list):
		if getattr(self, 'client', None):
			self.client.postMultiOperation(idx_list, aid_list, tile_list)

	# c2s
	def doOperation(self, aid, tile_list):
		if self.room:
			self.room.doOperation(self, aid, tile_list)

	def doOperationFailed(self, err):
		if getattr(self, 'client', None):
			self.client.doOperationFailed(err)

	def waitForOperation(self, aid, tile_list):
		if getattr(self, 'client', None):
			self.client.waitForOperation(aid, tile_list)

	# c2s
	def confirmOperation(self, aid, tile_list):
		if self.room:
			self.room.confirmOperation(self, aid, tile_list)

	def roundResult(self, round_info):
		if getattr(self, 'client', None):
			self.client.roundResult(round_info)

	def finalResult(self, player_info_list, round_info):
		self.room = None
		if getattr(self, 'client', None):
			self.client.finalResult(player_info_list, round_info)

	# c2s
	def roundEndCallback(self):
		if self.room:
			self.room.roundEndCallback(self)

	def readyForNextRound(self, idx):
		if getattr(self, 'client', None):
			self.client.readyForNextRound(idx)

	def recordRoundResult(self, round_r_dict):
		# 记录玩家房间中每局的记录
		if self.game_history:
			# DEBUG_MSG("recordRoundResult: {}".format(round_r_dict))
			game_record_list = self.game_history[-1]
			game_record_list.append(round_r_dict)
			if getattr(self, 'client', None):
				self.client.pushRoundRecord(round_r_dict)
		else:
			DEBUG_MSG("recordRoundResult failed. round_result = {}".format(round_r_dict))

	def recordGameResult(self, game_record_list):
		# 保存玩家房间牌局战绩, 只保留最近10条记录
		# DEBUG_MSG("game_record_list: {}".format(game_record_list))
		# DEBUG_MSG("game_history: {}".format(self.game_history))
		self.game_history.extend(game_record_list)
		# DEBUG_MSG("recordGameResult: {}".format(self.game_history[-1]))
		length = len(self.game_history)
		if length > const.MAX_HISTORY_RESULT:
			for i in range(length - const.MAX_HISTORY_RESULT):
				self.game_history.pop(0)

		if getattr(self, 'client', None):
			self.client.pushGameRecordList(game_record_list)

	# c2s
	def sendEmotion(self, eid):
		if self.room:
			self.room.sendEmotion(self, eid)

	# c2s
	def sendMsg(self, mid):
		if self.room:
			self.room.sendMsg(self, mid)

	# c2s
	def sendVoice(self, url):
		if self.room:
			self.room.sendVoice(self, url)

	# c2s
	def sendAppVoice(self, url, time):
		if self.room:
			self.room.sendAppVoice(self, url, time)

	def recvEmotion(self, idx, eid):
		if getattr(self, 'client', None):
			self.client.recvEmotion(idx, eid)

	def recvMsg(self, idx, mid):
		if getattr(self, 'client', None):
			self.client.recvMsg(idx, mid)

	def recvVoice(self, idx, url):
		if getattr(self, 'client', None):
			self.client.recvVoice(idx, url)

	def recvAppVoice(self, idx, url, time):
		if getattr(self, 'client', None):
			self.client.recvAppVoice(idx, url, time)

	def process_reconnection(self):
		DEBUG_MSG("iRoomOperation:(%i): client reconnect!" % (self.id))
		if self.room:
			self.room.reqReconnect(self)

	def handle_reconnect(self, rec_room_info):
		if getattr(self, 'client', None):
			self.client.handleReconnect(rec_room_info)

	# c2s
	def applyDismissRoom(self):
		""" 申请解散房间 """
		if self.room:
			self.room.apply_dismiss_room(self)

	def req_dismiss_room(self, idx):
		""" 广播有人申请解散房间 """
		if getattr(self, 'client', None):
			# DEBUG_MSG("call client reqDismissRoom {0}".format(idx))
			self.client.reqDismissRoom(idx)

	# c2s
	def voteDismissRoom(self, vote):
		""" 解散房间投票操作 """
		if self.room:
			self.room.vote_dismiss_room(self, vote)

	def vote_dismiss_result(self, idx, vote):
		""" 广播投票结果 """
		if getattr(self, 'client', None):
			# DEBUG_MSG("call client voteDismissResult {0}->{1}".format(idx, vote))
			self.client.voteDismissResult(idx, vote)

	# s2c
	def notifyPlayerOnlineStatus(self, idx, status):
		""" 玩家上线, 下线通知 """
		DEBUG_MSG("call client notifyPlayerOnlineStatus {0}->{1}".format(idx, status))
		if getattr(self, 'client', None):
			self.client.notifyPlayerOnlineStatus(idx, status)
