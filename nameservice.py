from __future__ import print_function
from random import randint
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

class RegNameHandler(tornado.web.RequestHandler):
    def post(self):
        #example requestMsg: {"domain":"suprise.com"}
        requestMsg = tornado.escape.json_decode(self.request.body)
        domain = requestMsg.domain
        if len(domain) == 0:
            self.get()
        else:
            self.reg(domain)

    def get(self):
        self.reg(randomDomain() +".com")

    def reg(self,domain):
        nodepk = base64.b32encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8")
        msg = {
            "message":{"msgid":uuid.uuid4().hex, "sender":nodepk, "receiver":base64.b32encode(domain.encode("utf8")), "timestamp": time.time()},
            "signature": base64.b32decode("4".encode("utf8")).decode("utf8")
        }
        tree.forward(["NEW_MSG", msg, time.time(), uuid.uuid4().hex])
        self.finish({"msgid": msg["message"]["msgid"], "msg":msg})

class GetNameHandler(tornado.web.RequestHandler):
    def get(self):
        #example request params:   /...?get=baidu.com
        arg = self.get_query_argument('get', '')
        possibleUrl = base64.b32encode(arg.encode("utf8"))
        roots = database.connection.query("SELECT * FROM graph"+tree.current_port+" WHERE from_block = %s OR to_block = %s ORDER BY nonce", arg, possibleUrl)
        id = ""
        url = ""
        for root in roots:
            id = root.from_block
            url = root.to_block
            break
        if len(id) > 0:
            msg = {"id":id, "url":(base64.b32decode(url)).decode("utf8")}
        else:
            msg = leader.lastest_block(arg)
        self.finish({"msg": msg})

class UpdateNameHandler(tornado.web.RequestHandler):
    def post(self):
        self.write("UpdateNameHandler")

def price(summary, value):
    total = sum([l*a for l, a in summary.items()])
    print(total)
    # weights = [total/l/a for l, a in summary.items()]
    # print(weights)
    weight = sum([total/l for l, a in summary.items()])
    return {l:total/l/a/weight*value for l, a in summary.items()}

def randomDomain():
    return ''.join(chr(97 + randint(0, 25)) for i in range(6))

print(price({1:2, 2:10, 7:60}, 100*12*7))

