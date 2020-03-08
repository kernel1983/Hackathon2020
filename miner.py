from __future__ import print_function

import time
import uuid
import hashlib
import copy
import base64
import urllib.request

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
frozen_chain = ['0'*64]
frozen_nodes_in_chain = {}
highest_block_hash = None
recent_longest = []
nodes_in_chain = {}
def longest_chain(from_hash = '0'*64):
    roots = database.connection2.query("SELECT * FROM chain"+tree.current_port+" WHERE prev_hash = %s ORDER BY nonce", from_hash)

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

        leaves = database.connection2.query("SELECT * FROM chain"+tree.current_port+" WHERE prev_hash = %s ORDER BY nonce", prev_hash)
        n += 1
        if len(leaves) > 0:
            if leaves[0]['height'] % 1000 == 0:
                print('longest height', leaves[0]['height'])
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
    # print(tree.current_port, "query time", t1-t0, n)

    longest = []
    for i in chains:
        # print(i)
        if not longest:
            longest = i
        if len(longest) < len(i):
            longest = i
    return longest

messages_out = []
def looping():
    global messages_out
    while messages_out:
        message = messages_out.pop(0)
        tree.forward(message)
    tornado.ioloop.IOLoop.instance().call_later(1, looping)

@tornado.gen.coroutine
def new_block(seq):
    global frozen_block_hash
    msg_header, block_hash, prev_hash, height, nonce, difficulty, identity, data, timestamp, msg_id = seq

    try:
        database.connection.execute("INSERT INTO chain"+tree.current_port+" (hash, prev_hash, height, nonce, difficulty, identity, timestamp, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", block_hash, prev_hash, height, nonce, difficulty, identity, timestamp, tornado.escape.json_encode(data))
    except Exception as e:
        print("Error: %s" % e)

    if prev_hash != '0'*64:
        prev_block = database.connection.get("SELECT * FROM chain"+tree.current_port+" WHERE hash = %s", prev_hash)
        if not prev_block:
            worker_thread_mining = False

    # longest = longest_chain(frozen_block_hash)
    # if longest:
    #     update_leader(longest)

    print(tree.current_port, "current view", leader.current_view, "system view", leader.system_view)

def update_leader(longest):
    height = longest[-1].height
    leaders = set([tuple(i.identity.split(":")) for i in longest[-setting.LEADERS_NUM-setting.ELECTION_WAIT:-setting.ELECTION_WAIT]])
    leader.update(leaders)
    # this method to wake up leader to work, is not as good as the timestamp way

    for i in longest[-setting.LEADERS_NUM-setting.ELECTION_WAIT:-setting.ELECTION_WAIT]:
        if i.identity == "%s:%s" % (tree.nodeid2no(tree.current_nodeid), base64.b32encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8")):
            leader.current_view = i.height
            break

    if height - (setting.LEADERS_NUM+setting.ELECTION_WAIT-1) > 0:
        leader.system_view = height - (setting.LEADERS_NUM+setting.ELECTION_WAIT-1)


class GetHighestBlockHandler(tornado.web.RequestHandler):
    def get(self):
        global highest_block_hash
        self.finish({"hash": highest_block_hash})

class GetBlockHandler(tornado.web.RequestHandler):
    def get(self):
        block_hash = self.get_argument("hash")
        block = database.connection.get("SELECT * FROM chain"+tree.current_port+" WHERE hash = %s", block_hash)
        self.finish({"block": block})


def fetch_chain(host, port):
    try:
        response = urllib.request.urlopen("http://%s:%s/get_highest_block" % (host, port))
    except:
        return
    result = tornado.escape.json_decode(response.read())
    block_hash = result['hash']
    if not block_hash:
        return
    print("get highest block", block_hash)
    while block_hash != '0'*64:
        block = database.connection2.get("SELECT * FROM chain"+tree.current_port+" WHERE hash = %s", block_hash)
        if block:
            if block['height'] % 1000 == 0:
                print('block height', block['height'])
            block_hash = block['prev_hash']
            continue
        try:
            response = urllib.request.urlopen("http://%s:%s/get_block?hash=%s" % (host, port, block_hash))
        except:
            continue
        result = tornado.escape.json_decode(response.read())
        block = result["block"]
        # if block['height'] % 1000 == 0:
        print("block fetch", block['height'])
        block_hash = block['prev_hash']
        try:
            database.connection2.execute("INSERT INTO chain"+tree.current_port+" (hash, prev_hash, height, nonce, difficulty, identity, timestamp, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                block["hash"], block["prev_hash"], block["height"], block["nonce"], block["difficulty"], block["identity"], block["timestamp"], block["data"])
        except Exception as e:
            print("Error: %s" % e)

nonce = 0
def mining():
    global nonce
    global frozen_block_hash
    global frozen_chain
    global frozen_nodes_in_chain
    global recent_longest
    global nodes_in_chain
    global highest_block_hash
    global messages_out

    longest = longest_chain(frozen_block_hash)
    if longest:
        highest_block_hash = longest[-1].hash
        update_leader(longest)
    if len(longest) > setting.FROZEN_BLOCK_NO:
        frozen_block_hash = longest[-setting.FROZEN_BLOCK_NO].prev_hash
        frozen_longest = longest[:-setting.FROZEN_BLOCK_NO]
        recent_longest = longest[-setting.FROZEN_BLOCK_NO:]
    else:
        frozen_longest = []
        recent_longest = longest

    for i in frozen_longest:
        print("frozen_longest", i.height)
        data = tornado.escape.json_decode(i.data)
        frozen_nodes_in_chain.update(data.get("nodes", {}))
        if i.hash not in frozen_chain:
            frozen_chain.append(i.hash)

    nodes_in_chain = copy.copy(frozen_nodes_in_chain)
    for i in recent_longest:
        data = tornado.escape.json_decode(i.data)
        # for j in data.get("nodes", {}):
        #     print("recent_longest", i.height, j, data["nodes"][j])
        nodes_in_chain.update(data.get("nodes", {}))

    # if tree.current_nodeid not in nodes_in_chain and tree.parent_node_id_msg:
    #     tree.forward(tree.parent_node_id_msg)
    #     print(tree.current_port, 'parent_node_id_msg', tree.parent_node_id_msg)

    now = int(time.time())
    last_synctime = now - now % setting.NETWORK_SPREADING_SECONDS - setting.NETWORK_SPREADING_SECONDS
    nodes_to_update = {}
    for nodeid in tree.nodes_pool:
        if tree.nodes_pool[nodeid][1] < last_synctime:
            if nodeid not in nodes_in_chain or nodes_in_chain[nodeid][1] < tree.nodes_pool[nodeid][1]:
                # print("nodes_to_update", nodeid, nodes_in_chain[nodeid][1], tree.nodes_pool[nodeid][1], last_synctime)
                nodes_to_update[nodeid] = tree.nodes_pool[nodeid]

    # nodes_in_chain.update(tree.nodes_pool)
    # tree.nodes_pool = nodes_in_chain
    # print(tree.nodes_pool)
    # print(nodes_to_update)

    # print(frozen_block_hash, longest)
    if longest:
        prev_hash = longest[-1].hash
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
        # print(tree.control_port, "new difficulty", new_difficulty, "height", height)

        if "%s:%s"%(tree.current_host, tree.current_port) in [i.identity for i in longest[-6:]]:
            # this is a good place to wake up leader by timestamp
            # tornado.ioloop.IOLoop.instance().call_later(1, mining)
            # return
            pass

    else:
        prev_hash, height, difficulty, new_difficulty, data, identity = '0'*64, 0, 1, 1, {}, ":"

    # data = {"nodes": {k:list(v) for k, v in tree.nodes_pool.items()}}
    data["nodes"] = nodes_to_update
    data_json = tornado.escape.json_encode(data)

    # new_identity = "%s@%s:%s" % (tree.current_nodeid, tree.current_host, tree.current_port)
    new_identity = "%s:%s" % (tree.nodeid2no(tree.current_nodeid), base64.b32encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8"))
    new_timestamp = time.time()
    for i in range(100):
        block_hash = hashlib.sha256((prev_hash + data_json + str(new_timestamp) + str(difficulty) + new_identity + str(nonce)).encode('utf8')).hexdigest()
        if int(block_hash, 16) < int("1" * (256-difficulty), 2):
            if longest:
                print(tree.current_port, 'height', height, 'nodeid', tree.current_nodeid, 'nonce_init', tree.nodeid2no(tree.current_nodeid), 'timecost', longest[-1].timestamp - longest[0].timestamp)

            message = ["NEW_CHAIN_BLOCK", block_hash, prev_hash, height+1, nonce, new_difficulty, new_identity, data, new_timestamp, uuid.uuid4().hex]
            messages_out.append(message)
            # print(tree.current_port, "mining", nonce, block_hash)
            nonce = 0
            break

        nonce += 1

worker_thread_mining = False
def worker_thread():
    global frozen_block_hash
    global frozen_chain
    global frozen_nodes_in_chain
    global nodes_in_chain
    global highest_block_hash
    global worker_thread_mining

    while True:
        if worker_thread_mining:
            mining()
            time.sleep(1)
            continue

        print('chain checking')
        if int(tree.current_port) > 8001:
            fetch_chain(tree.parent_host, tree.parent_port)

        longest = longest_chain()
        if len(longest) >= setting.FROZEN_BLOCK_NO:
            frozen_block_hash = longest[-setting.FROZEN_BLOCK_NO].prev_hash
            frozen_longest = longest[:-setting.FROZEN_BLOCK_NO]
        #     recent_longest = longest[-setting.FROZEN_BLOCK_NO:]
        else:
            frozen_longest = []
        #     recent_longest = longest

        if longest:
            highest_block_hash = longest[-1].hash
        else:
            highest_block_hash = '0'*64
        worker_thread_mining = True

        for i in frozen_longest:
            if i.height % 1000 == 0:
                print("frozen longest", i.height)
            data = tornado.escape.json_decode(i.data)
            frozen_nodes_in_chain.update(data.get("nodes", {}))
            if i.hash not in frozen_chain:
                frozen_chain.append(i.hash)
        time.sleep(1)

    # mining_task = tornado.ioloop.PeriodicCallback(mining, 1000) # , jitter=0.5
    # mining_task.start()
    # print(tree.current_port, "miner")


# @tornado.gen.coroutine
def main():
    tornado.ioloop.IOLoop.instance().call_later(1, looping)

if __name__ == '__main__':
    print("run python node.py pls")
