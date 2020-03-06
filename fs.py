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

def mt(filename, algorithm = hashlib.md5):
    f = open(filename, "rb")
    s = os.path.getsize(filename)
    m = s/(1024*1024)
    obj = f.read(1024*1024)

    hash_list = []
    result = []
    start = 0
    offset = 1024*1024
    end = offset
    while obj:
        obj_hash = algorithm(obj).hexdigest()
        # print(obj_hash, len(obj))
        hash_list.append((start, end, obj_hash))

        obj = f.read(1024*1024)
        start = offset
        offset += len(obj)
        end = offset
    result.append(hash_list)

    hash_list = mt_combine(hash_list, algorithm)
    result.append(hash_list)
    while len(hash_list) > 1:
        hash_list = mt_combine(hash_list, algorithm)
        result.append(hash_list)
    return result

def mt_combine(hash_list, algorithm):
    l = len(hash_list)
    m = l % 2
    result = []
    for i in range(0, l - m, 2):
        result.append((hash_list[i][0], hash_list[i+1][1], algorithm((hash_list[i][2] + hash_list[i+1][2]).encode("utf8")).hexdigest()))
    result.extend(hash_list[l-m:])
    return result


def m(n):
    power = math.floor(math.log(n, 2))
    return 2**(power-1)+(n-2**power)

def M(n):
    while n > 2:
        print(n)
        n=m(n)


# transactions = []
# nonce = 0
# def mining():
#     global nonce

#     longest = miner.longest_chain()
#     # print(longest)
#     if longest:
#         longest_hash = longest[-1].hash
#         difficulty = longest[-1].difficulty
#         data = longest[-1].data
#         identity = longest[-1].identity
#         recent = longest[-3:]
#         # print(recent)
#         if len(recent) * setting.BLOCK_INTERVAL_SECONDS > recent[-1].timestamp - recent[0].timestamp:
#             new_difficulty = min(255, difficulty + 1)
#         else:
#             new_difficulty = max(1, difficulty - 1)

#         # if tree.current_port in [i.identity for i in longest[-6:]]:
#         #     return

#     else:
#         longest_hash, difficulty, new_difficulty, data, identity = "0"*64, 1, 1, "", ""

#     if not transactions:
#         return
#     print(transactions)
#     transaction = transactions[0]
#     msg_header, user_id, data, timestamp, msg_id = transaction
#     if msg_id in [i["identity"] for i in longest or []]:
#         transactions.pop(0)
#         return

#     for i in range(100):
#         block_hash = hashlib.sha256((identity + tornado.escape.json_encode(data) + longest_hash + str(difficulty) + str(nonce)).encode('utf8')).hexdigest()
#         if int(block_hash, 16) < int("1" * (256-difficulty), 2):
#             if longest:
#                 print(len(longest), longest[-1].timestamp, longest[0].timestamp, longest[-1].timestamp - longest[0].timestamp)
#             # db.execute("UPDATE chain SET hash = %s, prev_hash = %s, nonce = %s, wallet_address = %s WHERE id = %s", block_hash, longest_hash, nonce, wallet_address, last.id)
#             # database.connection.execute("INSERT INTO chain"+tree.current_port+" (hash, prev_hash, nonce, difficulty, identity, timestamp, data) VALUES (%s, %s, %s, %s, '')", block_hash, longest_hash, nonce, difficulty, str(tree.current_port))

#             message = ["NEW_CHAIN_BLOCK", block_hash, longest_hash, nonce, new_difficulty, msg_id, int(time.time()), data, uuid.uuid4().hex]
#             tree.forward(message)
#             # print(tree.current_port, "mining", nonce, block_hash)
#             nonce = 0
#             transactions.pop(0)
#             break

#         nonce += 1

class ActivateDefaultStoreHandler(tornado.web.RequestHandler):
    def get(self):
        # object_hash = self.get_argument("hash")
        user_id = self.get_argument("user_id")
        # timestamp = self.get_argument("timestamp")
        # signature = self.get_argument("signature")
        # print(user_id)
        vk_bytes = base64.b16decode(user_id)
        # print(vk_bytes)
        vk = ecdsa.VerifyingKey.from_string(vk_bytes, curve=ecdsa.NIST256p)

        # vk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(str(user_id)))
        # sig = signing.Signature.from_bytes(bytes.fromhex(str(signature)))
        # assert sig.verify((object_hash+timestamp).encode("utf8"), vk)

        # capsule = open("data/%s/%s_capsule" % (user_id, object_hash), "rb").read()
        self.finish(vk_bytes)


class NewFileMetaHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        body = '''{"type":"file","blobs":["fd1e1f7378afd9c5e18cb4198f81c9129c5c8d7e0df6dc151bc39ecc0165408d","e9d3ef5f981e371465af217e09d9dfbb6681845a21beb199e62bef433e0369cf"]}'''
        meta = tornado.escape.json_decode(body)

        for blob in meta['blobs']:
            blob_bin = bin(int(blob, 16))
            print('>>>>>', blob, blob_bin[2:])

            http_client = tornado.httpclient.AsyncHTTPClient()
            host, port = tree.current_host, tree.current_port

            # need to cache those query to speed up
            while True:
                # print("fetch chain", block_hash)
                response = yield http_client.fetch("http://%s:%s/get_node?nodeid=%s" % (host, port, blob_bin[2:]), request_timeout=300)
                result = tornado.escape.json_decode(response.body)
                print('result >>>>>', result)
                host, port = result['address']
                if result['nodeid'] == result['current_nodeid']:
                    break

            # target_nodeid = tree.current_nodeid
            # score = None
            # # print(tree.current_port, tree.node_neighborhoods)
            # for j in [tree.node_neighborhoods, tree.node_parents]:
            #     for i in j:
            #         new_score = tree.node_distance(blob_bin[2:], i)
            #         if score is None or new_score < score:
            #             score = new_score
            #             target_nodeid = i
            #             address = j[target_nodeid]
            #         # print(i, new_score)
            # print('>>>>>', target_nodeid, address)

    @tornado.gen.coroutine
    def post(self):
        print(tree.current_nodeid, len(self.request.body), self.request.body)

class NewFileBlobHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def post(self):
        print(tree.current_nodeid, len(self.request.body), self.request.body)

class NewRootHomeHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        object_hash = self.get_argument("hash")
        user_id = self.get_argument("user_id")
        timestamp = self.get_argument("timestamp")
        signature = self.get_argument("signature")

        vk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(str(user_id)))
        sig = signing.Signature.from_bytes(bytes.fromhex(str(signature)))
        assert sig.verify((object_hash+timestamp).encode("utf8"), vk)

        content = open("data/%s/%s" % (user_id, object_hash), "rb").read()
        self.finish(content)

    @tornado.gen.coroutine
    def post(self):
        # object_hash = self.get_argument("hash")
        # user_id = self.get_argument("user_id")
        # timestamp = self.get_argument("timestamp")
        # signature = self.get_argument("signature")

        # vk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(str(user_id)))
        # sig = signing.Signature.from_bytes(bytes.fromhex(str(signature)))
        # assert sig.verify((object_hash+timestamp).encode("utf8"), vk)
        print(tree.current_nodeid, len(self.request.body), self.request.body)

class UserHandler(tornado.web.RequestHandler):
    def get(self):
        user_id = self.get_argument("user_id")
        timestamp = self.get_argument("timestamp")
        signature = self.get_argument("signature")

        vk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(str(user_id)))
        sig = signing.Signature.from_bytes(bytes.fromhex(str(signature)))
        # vk = VerifyingKey.from_string(bytes.fromhex(str(user_id)), curve=NIST384p)
        assert sig.verify(timestamp.encode("utf8"), vk)
        # check database if this user located at current node
        # if not, query to get node id for the user
        # if not existing, query for the replicated

        # res = {"user_id": user_id}
        # user = database.connection.get("SELECT * FROM "+tree.current_port+"users WHERE user_id = %s ORDER BY replication_id ASC LIMIT 1", user_id)
        # if user:
        #     res["user"] = user
        # else:
        #     user_bin = bin(int(user_id[2:], 16))[2:].zfill(64*4)
        #     print(tree.current_port, user_id[2:], user_bin)

        #     nodeids = tree.node_neighborhoods.keys()
        #     distance = 0
        #     for i in nodeids:
        #         new_distance = tree.node_distance(i, user_bin)
        #         if new_distance < distance or not distance:
        #             distance = new_distance 
        #             nodeid = i
        #     print(tree.current_port, tree.current_nodeid, node_id, distance)
        #     res["node"] = [nodeid, tree.node_neighborhoods[node_id]]
        longest = miner.longest_chain() or []
        for block in longest:
            data = tornado.escape.json_decode(block["data"])
            if data["user_id"] == user_id:
                self.finish(data)
                break
        else:
            self.finish({})

    def post(self):
        user_id = self.get_argument("user_id")
        folder_hash = self.get_argument("folder_hash")
        block_size = int(self.get_argument("block_size"))
        folder_size = int(self.get_argument("folder_size"))
        nodeid = self.get_argument("nodeid")
        capsule = self.get_argument("capsule")
        timestamp = self.get_argument("timestamp")
        signature = self.get_argument("signature")

        vk = keys.UmbralPublicKey.from_bytes(bytes.fromhex(str(user_id)))
        sig = signing.Signature.from_bytes(bytes.fromhex(str(signature)))
        assert sig.verify(timestamp.encode("utf8"), vk)

        # print(tree.current_port, len(self.request.body))
        if not os.path.exists("data/%s" % user_id):
            os.mkdir("data/%s" % user_id)
        open("data/%s/%s" % (user_id, folder_hash), "wb").write(self.request.body)
        open("data/%s/%s_capsule" % (user_id, folder_hash), "wb").write(bytes.fromhex(capsule))

        data = {"folder_hash": folder_hash, "block_size":block_size, "folder_size": folder_size, "nodeid": nodeid, "user_id": user_id, "by": tree.current_port}
        tree.forward(["UPDATE_HOME", user_id, data, time.time(), uuid.uuid4().hex])
        self.finish()


def main():
    print(tree.current_port, "fs")
    # mining_task = tornado.ioloop.PeriodicCallback(mining, 1000) # , jitter=0.5
    # mining_task.start()

if __name__ == '__main__':
    # main()
    print("run python node.py pls")
    for i in mt(sys.argv[1]):
        print(i)
