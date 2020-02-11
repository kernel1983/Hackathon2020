from __future__ import print_function

import time
import uuid
import hashlib
import copy
import base64

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.httpclient
import tornado.gen
import tornado.escape

import setting
import tree
import node
import leader
import database


frozen_block_hash = '0'*64
def longest_chain(frozen_hash = '0'*64):
    global frozen_block_hash
    roots = database.connection.query("SELECT * FROM chain"+tree.current_port+" WHERE prev_hash = %s ORDER BY nonce", frozen_hash)

    chains = []
    prev_hashs = []
    for root in roots:
        # chains.append([root.hash])
        chains.append([root])
        prev_hashs.append(root.hash)

    t0 = time.time()
    n = 0
    while True:
        if prev_hashs:
            prev_hash = prev_hashs.pop(0)
        else:
            break

        leaves = database.connection.query("SELECT * FROM chain"+tree.current_port+" WHERE prev_hash = %s ORDER BY nonce", prev_hash)
        n += 1
        if len(leaves) > 0:
            for leaf in leaves:
                for c in chains:
                    if c[-1].hash == prev_hash:
                        chain = copy.copy(c)
                        # chain.append(leaf.hash)
                        chain.append(leaf)
                        chains.append(chain)
                        break
                if leaf.hash not in prev_hashs and leaf.hash:
                    prev_hashs.append(leaf.hash)
    t1 = time.time()
    print(tree.current_port, "query time", t1-t0, n)

    longest = []
    for i in chains:
        # print(i)
        if not longest:
            longest = i
        if len(longest) < len(i):
            longest = i
    return longest


nonce = 0
nonce_interval = 0
@tornado.gen.coroutine
def mining():
    global nonce
    global nonce_interval
    global frozen_block_hash

    longest = longest_chain(frozen_block_hash)
    if longest:
        update_leader(longest)
    if len(longest) >= setting.FROZEN_BLOCK_NO:
        frozen_block_hash = longest[-setting.FROZEN_BLOCK_NO].hash

    nodes_in_chain = {}
    for i in longest:
        data = tornado.escape.json_decode(i.data)
        # if data.get("nodes"):print(i.height, data["nodes"])
        nodes_in_chain.update(data.get("nodes", {}))
        # print(' ', nodes)

    nonce_interval = len(nodes_in_chain)
    if nonce == 0:
        nonce = tree.nodeid2no(tree.current_nodeid)
    print(tree.current_port, 'nonce', nonce, 'nonce_interval', nonce_interval)

    if tree.current_nodeid not in nodes_in_chain and tree.parent_node_id_msg:
        tree.forward(tree.parent_node_id_msg)
        print(tree.current_port, 'parent_node_id_msg', tree.parent_node_id_msg)

    now = int(time.time())
    last_synctime = now - now % setting.NETWORK_SPREADING_SECONDS - setting.NETWORK_SPREADING_SECONDS
    nodes_to_update = {}
    for nodeid in tree.nodes_pool:
        if tree.nodes_pool[nodeid][1] < last_synctime:
            if nodeid not in nodes_in_chain or nodes_in_chain[nodeid] != tree.nodes_pool[nodeid]:
                nodes_to_update[nodeid] = tree.nodes_pool[nodeid]

    nodes_in_chain.update(tree.nodes_pool)
    tree.nodes_pool = nodes_in_chain
    # print(tree.nodes_pool)
    # print(nodes_to_update)

    # print(longest)
    if longest:
        longest_hash = longest[-1].hash
        height = longest[-1].height
        difficulty = longest[-1].difficulty
        identity = longest[-1].identity
        data = tornado.escape.json_decode(longest[-1].data)
        recent = longest[-3:]
        # print(recent)
        if len(recent) * setting.BLOCK_INTERVAL_SECONDS > recent[-1].timestamp - recent[0].timestamp:
            new_difficulty = min(255, difficulty + 1)
        else:
            new_difficulty = max(1, difficulty - 1)

        if "%s:%s"%(tree.current_host, tree.current_port) in [i.identity for i in longest[-6:]]:
            # this is a good place to wake up leader by timestamp
            # tornado.ioloop.IOLoop.instance().call_later(1, mining)
            # return
            pass

    else:
        longest_hash, height, difficulty, new_difficulty, data, identity = "0"*64, 0, 1, 1, {}, ""

    # data = {"nodes": {k:list(v) for k, v in tree.nodes_pool.items()}}
    data["nodes"] = nodes_to_update
    data_json = tornado.escape.json_encode(data)

    new_identity = "%s@%s:%s" % (tree.current_nodeid, tree.current_host, tree.current_port)
    new_timestamp = time.time()
    for i in range(10):
        block_hash = hashlib.sha256((longest_hash + data_json + str(new_timestamp) + str(difficulty) + str(nonce)).encode('utf8')).hexdigest()
        if int(block_hash, 16) < int("1" * (256-difficulty), 2):
            if longest:
                print(tree.current_port, 'height', height, 'nodeid', tree.current_nodeid, 'nonce_init', tree.nodeid2no(tree.current_nodeid), 'timecost', longest[-1].timestamp - longest[0].timestamp)

            message = ["NEW_CHAIN_BLOCK", block_hash, longest_hash, height+1, nonce, new_difficulty, new_identity, data, new_timestamp, uuid.uuid4().hex]
            tree.forward(message)
            # print(tree.current_port, "mining", nonce, block_hash)
            nonce = 0
            break

        nonce += nonce_interval

    tornado.ioloop.IOLoop.instance().call_later(1, mining)

def new_block(seq):
    global frozen_block_hash
    msg_header, block_hash, longest_hash, height, nonce, difficulty, identity, data, timestamp, msg_id = seq

    try:
        database.connection.execute("INSERT INTO chain"+tree.current_port+" (hash, prev_hash, height, nonce, difficulty, identity, timestamp, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", block_hash, longest_hash, height, nonce, difficulty, identity, timestamp, tornado.escape.json_encode(data))
    except:
        pass

    longest = longest_chain(frozen_block_hash)
    if longest:
        update_leader(longest)
    if len(longest) >= setting.FROZEN_BLOCK_NO:
        frozen_block_hash = longest[-setting.FROZEN_BLOCK_NO].hash
    print(tree.current_port, "current view", leader.current_view, "system view", leader.system_view)

def update_leader(longest):
    height = longest[-1].height
    leaders = set([tuple(i.identity.split(":")) for i in longest[-setting.LEADERS_NUM-setting.ELECTION_WAIT:-setting.ELECTION_WAIT]])
    leader.update(leaders)
    # this method to wake up leader to work, is not as good as the timestamp way

    for i in longest[-setting.LEADERS_NUM-setting.ELECTION_WAIT:-setting.ELECTION_WAIT]:
        if i.identity == "%s:%s"%(tree.current_host, tree.current_port):
            leader.current_view = i.height
            break

    if height - (setting.LEADERS_NUM+setting.ELECTION_WAIT-1) > 0:
        leader.system_view = height - (setting.LEADERS_NUM+setting.ELECTION_WAIT-1)

class GetChainHandler(tornado.web.RequestHandler):
    def get(self):
        global frozen_block_hash
        chain = [i["hash"] for i in longest_chain(frozen_block_hash)]
        self.finish({'chain': chain})

class GetBlockHandler(tornado.web.RequestHandler):
    def get(self):
        block_hash = self.get_argument("hash")
        block = database.connection.get("SELECT * FROM chain"+tree.current_port+" WHERE hash = %s", block_hash)
        self.finish({"block": block})

@tornado.gen.coroutine
def main():
    print(tree.current_port, "miner")

    # mining_task = tornado.ioloop.PeriodicCallback(mining, 1000) # , jitter=0.5
    # mining_task.start()
    tornado.ioloop.IOLoop.instance().call_later(1, mining)

if __name__ == '__main__':
    print("run python node.py pls")
