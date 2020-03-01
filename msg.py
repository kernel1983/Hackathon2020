from __future__ import print_function

import sys
import os
import time
import socket
import subprocess
import argparse
import uuid
import hashlib
import base64

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.options
import tornado.httpserver
import tornado.escape
import tornado.gen

import ecdsa #import VerifyingKey, NIST384p

import setting
import tree
import miner
import leader
import database


class GetChatHandler(tornado.web.RequestHandler):
    def get(self):
        user_pk = self.get_argument("user_pk")
        chats = database.connection.query("SELECT * FROM graph"+tree.current_port+" WHERE sender = %s OR receiver = %s", user_pk, user_pk)
        chats_data = [tornado.escape.json_decode(chat["data"]) for chat in chats]
        self.finish({"chat":[chat["message"] for chat in chats_data if "message" in chat and chat["message"]["type"] == "chat_msg"]})


class NewMsgHandler(tornado.web.RequestHandler):
    def get(self):
        msg = {
            "message":{"msgid":uuid.uuid4().hex, "sender":"1", "receiver":"2", "timestamp":"3"},
            "signature": "4"
        }

        tree.forward(["NEW_MSG", msg, time.time(), uuid.uuid4().hex])
        self.finish({"msgid": msg["message"]["msgid"]})

    def post(self):
        msg = tornado.escape.json_decode(self.request.body)

        tree.forward(["NEW_MSG", msg, time.time(), uuid.uuid4().hex])
        self.finish({"msgid": msg["message"]["msgid"]})


class GetMsgHandler(tornado.web.RequestHandler):
    def get(self):
        user_pk = self.get_argument("user_pk")


class WaitMsgHandler(tornado.websocket.WebSocketHandler):
    clients = set()

    # def data_received(self, chunk):
    #     print("data received")

    def check_origin(self, origin):
        return True

    def open(self):
        print("wait msg: client connected")
        if self not in self.clients:
            self.clients.add(self)
        # print('123', len(self.clients))

    def on_close(self):
        print("wait msg: client disconnected")
        if self in self.clients:
            self.clients.remove(self)
        # print('234', len(self.clients))

    # def send_to_client(self, msg):
    #     print("send message: %s" % msg)
    #     self.write_message(msg)

    @tornado.gen.coroutine
    def on_message(self, msg):
        seq = tornado.escape.json_decode(msg)
        print("wait msg got message", seq)

    @classmethod
    def new_block(cls, seq):
        # global WaitMsgHandler
        # print('456', len(cls.clients))
        for w in cls.clients:
            print("new_block", seq)
            w.write_message(tornado.escape.json_encode(seq))


def main():
    print(tree.current_port, "msg")
    # mining_task = tornado.ioloop.PeriodicCallback(mining, 1000) # , jitter=0.5
    # mining_task.start()

if __name__ == '__main__':
    # main()
    print("run python node.py pls")
