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
        #example: {"domain":"suprise.com"}
        requestMsg = tornado.escape.json_decode(self.request.body)

        msg = tornado.escape.json_decode(self.request.body)

        self.write("RegNameHandler")

    def get(self):
        msg = self.reg(randomDomain() +".com")
        self.finish({"msgid": msg["message"]["msgid"]})

    def reg(self,domain):
        nodepk = base64.b32encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8")
        msg = {
            "message":{"msgid":uuid.uuid4().hex, "sender":nodepk, "receiver":base64.b32encode(domain), "timestamp": time.time()},
            "signature": base64.b32decode("4".encode("utf8")).decode("utf8")
        }
        tree.forward(["NEW_MSG", msg, time.time(), uuid.uuid4().hex])
        return msg

class GetNameHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("GetNameHandler")

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

