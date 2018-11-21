import json
import random
import re
import socket
import threading
import time
from struct import pack

import requests


class DouyuTV_barrage(object):
    "获取斗鱼弹幕和礼物消息"

    def __init__(self):
        self.headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
        }
        self.HOST = 'openbarrage.douyutv.com'
        self.PORT = 8601
        #斗鱼提供了第三方接入弹幕服务器
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.index = 1000

    def log(self, str):
        now_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        log = now_time + '\t' + str
        print(log)

    def sendMsg(self, data):
        "客户端上服务器发送消息"
        #消息包含五个部分：消息长度（包含自身）+ 消息长度（包含自身）+ 消息类型 + 消息内容 + 结尾的'\0'
        #9=4+4+1
        msg = pack('i', 9 + len(data)) * 2
        # 689表示客户端发送给弹幕服务器
        msg += b'\xb1\x02\x00\x00'
        msg += data.encode('ascii') + b'\x00'
        self.sock.sendall(msg)

    def keepLive(self):
        "心跳消息"
        while True:
            msg = 'type@=mrkl/'
            self.sendMsg(msg)
            #keeplive=self.sock.recv(9999)
            time.sleep(30)

    def getRoominfo(self, url):
        "获取房间信息"
        self.log("请求网页内容...")
        try:
            html = requests.get(url, headers=self.headers).text
        except:
            self.log("请求网页内容失败...")
            exit()
        self.log("获取房间信息...")
        roominfo = {}
        room = re.findall(r'\$ROOM\.(.*);', html)
        #反斜杠后边跟元字符去除特殊功能
        for i in room[0:4]:
            r = json.loads('{"' + i.replace('=', '":"').replace(" ", "") +
                           '"}')
            #将字符串转化为字典；去除字符串中的空格
            roominfo.update(r)
        self.log("房间名:" + roominfo["room_id"] + '\t\t|\t\t主播:' +
                 roominfo["owner_uid"])
        self.rid = roominfo["room_id"]
        if roominfo["show_status"] == 2:
            self.log(roominfo["owner_uid"] + '未开播!正在退出...')
            exit()
        else:
            self.log(roominfo["owner_uid"] + '正在直播!准备获取弹幕...')

    def connectBarrageserver(self):
        "连接弹幕服务器"
        self.log("连接弹幕服务器..." + self.HOST + ':' + str(self.PORT))
        self.sock.connect((self.HOST, self.PORT))
        self.log("连接成功,发送登录请求...")
        data = 'type@=loginreq/roomid@=' + str(self.rid) + '/'
        self.sendMsg(data)
        #服务端返回登录相应消息
        data = self.sock.recv(9999)
        result = re.findall(b'type@=(\w+)/userid', data)[0]
        if result != b'loginres':
            self.log("登录失败,程序退出...")
            exit(0)
        self.log("登录成功")
        #加入房间分组
        data = 'type@=joingroup/rid@=' + str(self.rid) + '/gid@=-9999/'
        self.sendMsg(data)
        self.log("心跳包机制启动...")
        t = threading.Thread(target=self.keepLive)
        #只要还有一个前台线程在运行,这个进程就不会结束,如果一个进程中只有后台线程运行,这个进程会结束.
        t.setDaemon(True)
        t.start()

    def dispalyBarrage(self):
        "输出弹幕和礼物消息"
        self.log("输出弹幕和礼物消息:")
        while self.index:
            try:
                data = self.sock.recv(9999)
                if b"type@=" not in data:
                    pass
                elif b"type@=rss" in data:
                    msg = self.formataData(data)
                    if not self.log(msg['ss']):
                        self.log('主播已下播')
                        exit()
                elif b"type@=chatmsg" in data:
                    msg = self.formataData(data)
                    self.log('<Lv:%s>' % msg.get('level', 'unknown') + '\t' +
                             msg.get('nn', 'unknown') + '\t' +
                             msg.get('txt', 'unknown'))
                elif b"type@=dgb" in data:
                    msg = self.formataData(data)
                    self.log('礼物消息：' + '\t' + msg.get('rid', 'unknown') +
                             '\t' + msg.get('nn', 'unknown') + '\t' +
                             msg.get('gfid', 'unknown') + '\t' +
                             msg.get('hits', 'unknown'))
            except Exception:
                self.log("弹幕内容解析错误")
            self.index -= 1
        self.log("登出...")
        msg = 'type@=logout/'
        self.sendMsg(msg)
        self.sock.close()

    def formataData(self, data):
        "数据序列化"
        msg = re.findall(b'(type@=.*?)\x00', data)[0]
        msg = msg.replace(b'@=', b'":"').replace(b'/', b'","').replace(
            b'@A', b'@').replace(b'@S', b'/')
        msg = json.loads((b'{"' + msg[:-2] + b'}').decode('utf8', 'ignore'))
        return msg


if __name__ == '__main__':
    url = 'https://www.douyu.com/84452'
    barrage = DouyuTV_barrage()
    barrage.getRoominfo(url)
    barrage.connectBarrageserver()
    barrage.dispalyBarrage()
