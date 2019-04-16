// var UIBase = require("src/views/ui/UIBase.js")
// cc.loader.loadJs("src/views/ui/UIBase.js")
var GameRoomInfoUI = UIBase.extend({
	ctor:function() {
		this._super();
		this.resourceFilename = "res/ui/GameRoomInfoUI.json";
	},

	initUI:function(){
		this.roominfo_panel = this.rootUINode.getChildByName("roominfo_panel");
		var player = h1global.entityManager.player();
		var roomid_label = this.roominfo_panel.getChildByName("roomid_label");
		roomid_label.setString("房间号:" + player.curGameRoom.roomID.toString());
		// var lucky_label = this.roominfo_panel.getChildByName("lucky_label");
		// lucky_label.setString("扎" + player.curGameRoom.luckyTileNum.toString() + "个码");
		// this.round_label = this.roominfo_panel.getChildByName("round_label");
		this.round_label = this.rootUINode.getChildByName("round_panel").getChildByName("round_label");
		this.lefttile_label = this.roominfo_panel.getChildByName("lefttile_label");
		// var roommode_bg_img = this.roominfo_panel.getChildByName("roommode_bg_img");
		this.function_panel = this.rootUINode.getChildByName("function_panel");
		this.time_label = this.function_panel.getChildByName("time_label");
		this.function_panel.getChildByName("communicate_btn").addTouchEventListener(function(sender, eventType){
			if(eventType == ccui.Widget.TOUCH_ENDED){
				// 聊天面板
				h1global.curUIMgr.communicate_ui.show();
			}
		});
		this.function_panel.getChildByName("config_btn").addTouchEventListener(function(sender, eventType){
			if(eventType == ccui.Widget.TOUCH_ENDED){
				h1global.curUIMgr.gameconfig_ui.show();
			}
		});
		this.function_panel.getChildByName("help_btn").addTouchEventListener(function(sender, eventType){
			if(eventType == ccui.Widget.TOUCH_ENDED){
				h1global.curUIMgr.help_ui.show();
			}
		});
		// var voice = {
		// 	localId:"",
		// 	serverId:"",
		// };
		// this.voice = voice;
		// this.record_btn = this.rootUINode.getChildByName("record_btn");
		// var start_record_time = 0;
		// var audioName = ""; // 本地版本記錄語音名稱
		// var self = this;
		// function stopAudioFunc(){
		// 	var record_time = new Date().getTime() - start_record_time;
		// 	if((cc.sys.os == cc.sys.OS_ANDROID && cc.sys.isNative)){
		// 		var fid = cutil.addFunc(function(audioPath){
		// 			// 上傳語音文件
		// 			// self.record_btn.setTouchEnabled(true);
		// 			h1global.curUIMgr.audiorecord_ui.hide();
		// 	         var uploadCBId = cutil.addFunc(function(url){
		// 	         	player.sendAppVoice(url, record_time/1000);
		// 	         	self.record_btn.runAction(cc.Sequence.create(cc.DelayTime.create(0.5), 
		// 	         		cc.CallFunc.create(function(){
		// 	         			self.record_btn.setTouchEnabled(true);
		// 	         		})
		// 	         	));
		// 	         });
		// 	         jsb.reflection.callStaticMethod(switches.package_name + "/AppActivity", "uploadAudioFile", "(Ljava/lang/String;I)V", audioName, uploadCBId);
		// 	         // player.sendAppVoice();
		// 		});
		// 		jsb.reflection.callStaticMethod(switches.package_name + "/AppActivity", "avStopAudioRecord", "(I)F", fid);
		// 	} else if((cc.sys.os == cc.sys.OS_IOS && cc.sys.isNative)){
		// 		var fid = cutil.addFunc(function(audioPath){
		// 			// 上傳語音文件
		// 			// cc.log("uploadVoice##########################################")
		// 			// cc.log(audioPath)
		// 			// self.record_btn.setTouchEnabled(true);
		// 			h1global.curUIMgr.audiorecord_ui.hide();
		// 	         var uploadCBId = cutil.addFunc(function(url){
		// 	         	player.sendAppVoice(url, record_time/1000);
		// 	         	self.record_btn.setTouchEnabled(true);
		// 	         });
		// 	         jsb.reflection.callStaticMethod("UpYunOcBridge", "uploadAudioFile:WithFuncID:", audioName, uploadCBId);
		// 	         // player.sendAppVoice();
		// 		});
		// 		jsb.reflection.callStaticMethod("AudioOcBridge","avStopAudioRecord:", fid);
		// 	} else {
		// 	    wx.stopRecord({
		// 	      	success: function (res) {
		// 	        	voice.localId = res.localId;
		// 	        	// 上传语音
		// 	        	h1global.curUIMgr.audiorecord_ui.hide();
		// 	        	wx.uploadVoice({
		// 			      	localId: voice.localId,
		// 			      	success: function (res) {
		// 			        	// alert('上传语音成功，serverId 为' + res.serverId);
		// 			        	voice.serverId = res.serverId;
		// 			        	player.sendVoice(voice.serverId, record_time/1000);
		// 			        	self.record_btn.setTouchEnabled(true);
		// 			      	},
		// 			      	fail: function (res){
		// 			      		self.record_btn.setTouchEnabled(true);
		// 			      	},
		// 			    });
		// 	      	},
		// 	      	fail: function (res) {
		// 	        	// alert(JSON.stringify(res));
		// 	        	h1global.curUIMgr.audiorecord_ui.hide();
		// 	        	self.record_btn.setTouchEnabled(true);
		// 	      	}
		// 	    });
		// 	}
		// }
		// this.record_btn.addTouchEventListener(function(sender, eventType){
		// 	if(eventType == ccui.Widget.TOUCH_BEGAN){
		// 		h1global.curUIMgr.audiorecord_ui.show();
		// 		start_record_time = new Date().getTime();
		// 		if((cc.sys.os == cc.sys.OS_ANDROID && cc.sys.isNative)){
		// 			audioName = player.uuid.toString() + "_" + parseInt(start_record_time).toString();
		// 			var result = jsb.reflection.callStaticMethod(switches.package_name + "/AppActivity", "avStartAudioRecord", "(Ljava/lang/String;)Z", audioName);
		// 			// cc.log("avStartAudioRecord#################", result)
		// 		} else if((cc.sys.os == cc.sys.OS_IOS && cc.sys.isNative)){
		// 			audioName = player.uuid.toString() + "_" + parseInt(start_record_time).toString();
		// 			var result = jsb.reflection.callStaticMethod("AudioOcBridge","avStartAudioRecord:", audioName);
		// 			// cc.log("avStartAudioRecord#################", result)
		// 		} else {
		// 			wx.startRecord({
		// 		    	cancel: function () {
		// 		        	alert('用户拒绝授权录音');
		// 		    	}
		// 		    });
		// 		}
		// 		sender.runAction(cc.Sequence.create(cc.DelayTime.create(30.0), 
		// 			cc.CallFunc.create(function(){
		// 				// cc.log("LZRTEST:TIME OUT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
		// 				sender.setTouchEnabled(false);
		// 				sender.setBrightStyle(ccui.Widget.BRIGHT_STYLE_NORMAL);
		// 				stopAudioFunc();
		// 			})
		// 		))
		// 	} else if(eventType == ccui.Widget.TOUCH_ENDED || eventType == ccui.Widget.TOUCH_CANCELED){
		// 		sender.stopAllActions();
		// 		sender.setTouchEnabled(false);
		// 		var record_time = new Date().getTime() - start_record_time;
		// 		if(record_time >= 1000){
		// 			stopAudioFunc();
		// 		} else {
		// 			// 錄音不足1s則强制延遲到1s執行
		// 			sender.runAction(cc.Sequence.create(cc.DelayTime.create(1.0), cc.CallFunc.create(function(){
		// 				stopAudioFunc();
		// 			})))
		// 		}
		// 	}
		// })
		this.update_round();
		this.update_lefttile();
		var curDateTime = new Date();
		this.update_curtime(curDateTime);
		this.update_roommode();
		onhookMgr.setCurTime((curDateTime.getTime())/1000);
	},

	update_round:function(){
		if(!this.is_show){
			return;
		}
		// this.round_label.setString(	h1global.entityManager.player().curGameRoom.curRound.toString() + "/" + 
		// 							h1global.entityManager.player().curGameRoom.maxRound.toString() + "局");
		this.round_label.setString("第" + h1global.entityManager.player().curGameRoom.curRound.toString() + "局");
	},

	update_lefttile:function(){
		if(!this.is_show){
			return;
		}
		this.lefttile_label.setString("余" + h1global.entityManager.player().curGameRoom.leftTileNum.toString() + "张");
	},

	update_curtime:function(curDateTime){
		if(!this.is_show){
			return;
		}
		var hour = curDateTime.getHours();
		var min = curDateTime.getMinutes();
		this.time_label.setString((hour<10?"0":"") + hour.toString() + ":" + (min<10?"0":"") + min.toString());
	},

	update_roommode:function(){
		if(!this.is_show){
			return;
		}
		var roommode_bg_img = this.rootUINode.getChildByName("roominfo_panel").getChildByName("roommode_bg_img");
		var roommode_panel = this.rootUINode.getChildByName("roominfo_panel").getChildByName("roommode_panel");
		roommode_bg_img.addTouchEventListener(function(sender, eventType){
			if(eventType == ccui.Widget.TOUCH_ENDED){
				roommode_panel.setVisible(!roommode_panel.isVisible());
			}
		});
		// 更新房间模式的面板
		var createRoomInfoList = h1global.entityManager.player().curGameRoom.createRoomInfoList
		for (var i = 0; i < createRoomInfoList.length; i++) {
			if (i >= 3) {break;}
			var mode_img = roommode_panel.getChildByName("room_mode_" + String(i+1))
			mode_img.ignoreContentAdaptWithSize(true)
			if (i == 0) {
				mode_img.loadTexture("res/ui/GameRoomInfoUI/max_deal_" + createRoomInfoList[i] + ".png")
			} else if (i==1) {
				mode_img.loadTexture("res/ui/GameRoomInfoUI/start_deal_" + createRoomInfoList[i] + ".png")
			} else if (i==2) {
				mode_img.loadTexture("res/ui/GameRoomInfoUI/max_lose_" + createRoomInfoList[i] + ".png")
			}
		}
	},
});