from __future__ import print_function

import math
import time
import socket
import subprocess
import argparse
import uuid
import functools
import base64
import random

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.httpclient
import tornado.gen
import tornado.escape

import setting
import miner
import leader
import database
import msg

from ecdsa import SigningKey, VerifyingKey, NIST256p

control_port = 0

current_host = None
current_port = None
current_branch = None
current_nodeid = None
node_sk = None

available_branches = set()

node_neighborhoods = dict()
node_parents = dict()
nodes_pool = dict()
parent_node_id_msg = None

processed_message_ids = set()

def forward(seq):
    # global processed_message_ids

    message_id = seq[-1]
    if message_id in processed_message_ids:
        return
    processed_message_ids.add(message_id)
    message = tornado.escape.json_encode(seq)

    for child_node in NodeHandler.child_nodes.values():
        # if not child_node.stream.closed:
        child_node.write_message(message)

    if NodeConnector.node_parent:
        NodeConnector.node_parent.conn.write_message(message)

def nodeid2no(nodeid):
    if not nodeid:
        return 1
    return 2**len(str(nodeid)) + int(nodeid, 2)

def nodeno2id(nodeno):
    if nodeno < 2:
        return ''
    no = int(math.log(nodeno, 2))
    return bin(nodeno - 2**no)[2:].zfill(no)

def node_distance(a, b):
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            break
        i += 1
    return len(a)+len(b)-i*2

def sign_msg(message):
    global node_sk
    if not node_sk:
        raise
    message_json = tornado.escape.json_encode(message)
    signature = node_sk.sign(message_json.encode("utf8"))
    message.append(base64.b32encode(signature).decode("utf8"))
    print(current_port, "signature", message)

# connect point from child node
class NodeHandler(tornado.websocket.WebSocketHandler):
    child_nodes = dict()

    def check_origin(self, origin):
        return True

    def open(self):
        global node_parents

        self.branch = self.get_argument("branch")
        self.from_host = self.get_argument("host")
        self.from_port = self.get_argument("port")
        self.pk = base64.b32decode(self.get_argument("pk"))
        # print(self.pk, len(self.pk))
        node_pk = VerifyingKey.from_string(self.pk, curve=NIST256p)
        self.sig = base64.b32decode(self.get_argument("sig"))
        # print(self.sig, len(self.sig))
        # print(b"%s%s%s%s" % (self.branch.encode("utf8"), self.from_host.encode("utf8"), self.from_port.encode("utf8"), self.pk))
        node_pk.verify(self.sig, b"%s%s%s%s" % (self.branch.encode("utf8"), self.from_host.encode("utf8"), self.from_port.encode("utf8"), self.pk))
        self.remove_node = True
        if self.branch in NodeHandler.child_nodes:
            print(current_port, "force disconnect")
            self.remove_node = False
            self.close()

            message = ["DISCARDED_BRANCHES", [[current_host, current_port, self.branch]], uuid.uuid4().hex]
            forward(message)
            return

        print(current_port, "child connected branch", self.branch)
        if self.branch not in NodeHandler.child_nodes:
            NodeHandler.child_nodes[self.branch] = self

        if tuple([current_host, current_port, self.branch]) in available_branches:
            available_branches.remove(tuple([current_host, current_port, self.branch]))

        message = ["DISCARDED_BRANCHES", [[current_host, current_port, self.branch]], uuid.uuid4().hex]
        forward(message)

        # message = ["NODE_ID", self.branch, [ip, port], timestamp, current_nodeid, sig]
        timestamp = time.time()
        message = ["NODE_ID", base64.b32encode(self.pk).decode("utf8"), self.branch,
                    base64.b32encode(node_sk.get_verifying_key().to_string()).decode("utf8"), current_nodeid, timestamp]
        sign_msg(message)
        self.write_message(tornado.escape.json_encode(message))
        # miner.nodes_to_fetch.append(self.branch)
        # miner.worker_thread_mining = False

        message = ["NODE_PARENTS", node_parents, uuid.uuid4().hex]
        self.write_message(tornado.escape.json_encode(message))

    def on_close(self):
        print(current_port, "child disconnected from parent")
        if self.branch in NodeHandler.child_nodes and self.remove_node:
            del NodeHandler.child_nodes[self.branch]
        self.remove_node = True

        available_branches.add(tuple([current_host, current_port, self.branch]))

        message = ["AVAILABLE_BRANCHES", [[current_host, current_port, self.branch]], uuid.uuid4().hex]
        forward(message)

        if tuple([self.from_host, self.from_port, self.branch+"0"]) in available_branches:
            available_branches.remove(tuple([self.from_host, self.from_port, self.branch+"0"]))
        if tuple([self.from_host, self.from_port, self.branch+"1"]) in available_branches:
            available_branches.remove(tuple([self.from_host, self.from_port, self.branch+"1"]))

        message = ["DISCARDED_BRANCHES", [[self.from_host, self.from_port, self.branch+"0"], [self.from_host, self.from_port, self.branch+"1"]], uuid.uuid4().hex]
        forward(message)

        message = ["NODE_ID", None, self.branch, None, current_nodeid, time.time()]
        sign_msg(message)
        forward(message)

    @tornado.gen.coroutine
    def on_message(self, message):
        global current_nodeid
        global node_neighborhoods
        global nodes_pool

        yield tornado.gen.sleep(random.random())
        seq = tornado.escape.json_decode(message)
        # print(current_port, "on message from child", seq)
        if seq[0] == "DISCARDED_BRANCHES":
            for i in seq[1]:
                branch_host, branch_port, branch = i
                if tuple([branch_host, branch_port, branch]) in available_branches:
                    available_branches.remove(tuple([branch_host, branch_port, branch]))

        elif seq[0] == "AVAILABLE_BRANCHES":
            for i in seq[1]:
                branch_host, branch_port, branch = i
                available_branches.add(tuple([branch_host, branch_port, branch]))

        elif seq[0] == "NODE_ID":
            pk = seq[1]
            nodeid = seq[2]
            parent_pk = seq[3]
            parent_nodeid = seq[4]
            timestamp = seq[5]

            if parent_nodeid == "":
                nodes_pool[parent_nodeid] = [parent_pk, timestamp]
            nodes_pool[nodeid] = [pk, timestamp]
            print(current_port, "NODE_ID", nodeid, pk, parent_nodeid, parent_pk, seq[-1])

        elif seq[0] == "NODE_NEIGHBOURHOODS":
            nodeid = seq[1]
            if current_nodeid is not None and node_distance(nodeid, current_nodeid) > setting.NEIGHBOURHOODS_HOPS:
                return
            node_neighborhoods[nodeid] = tuple(seq[2])
            # print(current_port, "NODE_NEIGHBOURHOODS", current_nodeid, nodeid, node_neighborhoods)

        elif seq[0] == "NEW_CHAIN_BLOCK":
            miner.new_block(seq)
            if control_node:
                control_node.write_message(tornado.escape.json_encode(["BLOCK", current_nodeid, seq]))

        elif seq[0] == "NEW_TX_BLOCK":
            leader.new_tx_block(seq)
            msg.WaitMsgHandler.new_block(seq)

        elif seq[0] == "NEW_TX":
            txid = seq[1]["transaction"]["txid"]
            # if (current_host, current_port) in leader.current_leaders and txid not in processed_message_ids:
            if txid not in processed_message_ids:
                processed_message_ids.add(txid)
                leader.message_queue.append(seq)
                # print(current_port, "tx msg", seq)

        elif seq[0] == "NEW_MSG_BLOCK":
            print(current_port, "NEW_MSG_BLOCK")
            leader.new_msg_block(seq)
            msg.WaitMsgHandler.new_block(seq)

        elif seq[0] == "NEW_MSG":
            msgid = seq[1]["message"]["msgid"]
            if msgid not in processed_message_ids:
                processed_message_ids.add(msgid)
                leader.message_queue.append(seq)

        forward(seq)


# connector to parent node
class NodeConnector(object):
    """Websocket Client"""
    node_parent = None

    def __init__(self, to_host, to_port, branch):
        global node_sk
        self.host = to_host
        self.port = to_port
        self.branch = branch
        self.pk = node_sk.get_verifying_key().to_string()

        # print(self.pk.decode("utf8"))
        # print(b"%s%s%s%s" % (self.branch.encode("utf8"), current_host.encode("utf8"), current_port.encode("utf8"), self.pk))
        sig = node_sk.sign(b"%s%s%s%s" % (self.branch.encode("utf8"), current_host.encode("utf8"), current_port.encode("utf8"), self.pk))
        # print(sig)
        self.ws_uri = "ws://%s:%s/node?branch=%s&host=%s&port=%s&pk=%s&sig=%s" % (self.host, self.port, self.branch, current_host, current_port, base64.b32encode(self.pk).decode("utf8"), base64.b32encode(sig).decode("utf8"))
        self.conn = None
        self.connect()

    def connect(self):
        tornado.websocket.websocket_connect(self.ws_uri,
                                callback = self.on_connect,
                                on_message_callback = self.on_message,
                                connect_timeout = 1000.0,
                                ping_timeout = 600.0
                            )

    def close(self):
        if NodeConnector.node_parent:
            NodeConnector.node_parent = None
        self.conn.close()

    @tornado.gen.coroutine
    def on_connect(self, future):
        print(current_port, "node connect", self.branch)

        try:
            self.conn = future.result()
            if not NodeConnector.node_parent:
                NodeConnector.node_parent = self

            available_branches.add(tuple([current_host, current_port, self.branch+"0"]))
            available_branches.add(tuple([current_host, current_port, self.branch+"1"]))

            message = ["AVAILABLE_BRANCHES", [[current_host, current_port, self.branch+"0"], [current_host, current_port, self.branch+"1"]], uuid.uuid4().hex]
            self.conn.write_message(tornado.escape.json_encode(message))

            if current_nodeid is not None:
                message = ["NODE_NEIGHBOURHOODS", current_nodeid, [current_host, current_port], uuid.uuid4().hex]
                self.conn.write_message(tornado.escape.json_encode(message))

        except:
            print(current_port, "NodeConnector reconnect ...")
            tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)
            # tornado.ioloop.IOLoop.instance().call_later(1.0, bootstrap)
            # tornado.ioloop.IOLoop.instance().call_later(1.0, functools.partial(bootstrap, (self.host, self.port)))
            return

    @tornado.gen.coroutine
    def on_message(self, message):
        global current_branch
        global current_nodeid
        global node_parents
        global node_neighborhoods
        global nodes_pool
        global parent_node_id_msg
        global control_node
        global control_node_msg_queue

        yield tornado.gen.sleep(random.random())
        if message is None:
            print("NodeConnector reconnect2 ...")
            # retry before choose another parent
            # if current_branch in available_branches:
            #     available_branches.remove(current_branch)
            # available_branches = set([tuple(i) for i in branches])
            # branches = list(available_branches)
            # current_branch = tuple(branches[0])
            # branch_host, branch_port, branch = current_branch
            # sig = node_sk.sign(b"%s%s%s%s" % (branch.encode("utf8"), current_host.encode("utf8"), current_port.encode("utf8"), self.pk))
            # print(sig)
            # self.ws_uri = "ws://%s:%s/node?branch=%s&host=%s&port=%s&pk=%s&sig=%s" % (branch_host, branch_port, branch, current_host, current_port, base64.b32encode(self.pk).decode("utf8"), base64.b32encode(sig).decode("utf8"))

            tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)
            return

        seq = tornado.escape.json_decode(message)
        # print(current_port, "on message from parent", seq)
        if seq[0] == "DISCARDED_BRANCHES":
            for i in seq[1]:
                branch_host, branch_port, branch = i
                if tuple([branch_host, branch_port, branch]) in available_branches:
                    available_branches.remove(tuple([branch_host, branch_port, branch]))

            # for node in NodeHandler.child_nodes.values():
            #     node.write_message(message)

        elif seq[0] == "AVAILABLE_BRANCHES":
            for i in seq[1]:
                branch_host, branch_port, branch = i
                available_branches.add(tuple([branch_host, branch_port, branch]))

            # for node in NodeHandler.child_nodes.values():
            #     node.write_message(message)

            message = ["NODE_NEIGHBOURHOODS", current_nodeid, [current_host, current_port], uuid.uuid4().hex]
            forward(message)

        elif seq[0] == "NODE_ID":
            pk = seq[1]
            nodeid = seq[2]
            parent_pk = seq[3]
            parent_nodeid = seq[4]
            timestamp = seq[5]

            if parent_nodeid == "":
                nodes_pool[parent_nodeid] = [parent_pk, timestamp]
            nodes_pool[nodeid] = [pk, timestamp]
            print(current_port, "NODE_ID", nodeid, self.branch, pk, parent_nodeid, parent_pk, seq[-1])
            if self.branch == nodeid:
                current_nodeid = nodeid

                print(current_port, "control_node", control_node)
                if control_node:
                    control_node.write_message(tornado.escape.json_encode(["ADDRESS2", current_host, current_port, current_nodeid]))
                else:
                    print(current_port, "ADDRESS2 queue", current_host, current_port, current_nodeid)
                    control_node_msg_queue.append(["ADDRESS2", current_host, current_port, current_nodeid])

                # print(current_port, "NODE_PARENTS", node_parents[current_nodeid])
                if self.conn and not self.conn.stream.closed:
                    message = ["NODE_NEIGHBOURHOODS", current_nodeid, [current_host, current_port], uuid.uuid4().hex]
                    self.conn.write_message(tornado.escape.json_encode(message))

                parent_node_id_msg = seq
            # return

        elif seq[0] == "NODE_PARENTS":
            node_parents.update(seq[1])
            # print(current_port, "NODE_PARENTS", node_parents)

            for child_node in NodeHandler.child_nodes.values():
                child_node.write_message(message)
            return

        elif seq[0] == "NODE_NEIGHBOURHOODS":
            nodeid = seq[1]
            if current_nodeid is not None and node_distance(nodeid, current_nodeid) > setting.NEIGHBOURHOODS_HOPS:
                return
            node_neighborhoods[nodeid] = tuple(seq[2])
            # print(current_port, "NODE_NEIGHBOURHOODS", current_nodeid, nodeid, node_neighborhoods)

        elif seq[0] == "NEW_CHAIN_BLOCK":
            miner.new_block(seq)
            if control_node:
                control_node.write_message(tornado.escape.json_encode(["BLOCK", current_nodeid, seq]))

        elif seq[0] == "NEW_TX_BLOCK":
            leader.new_tx_block(seq)
            msg.WaitMsgHandler.new_block(seq)

        elif seq[0] == "NEW_TX":
            txid = seq[1]["transaction"]["txid"]
            # if (current_host, current_port) in leader.current_leaders and txid not in processed_message_ids:
            if txid not in processed_message_ids:
                processed_message_ids.add(txid)
                leader.message_queue.append(seq)
                # print(current_port, "tx msg", seq)

        elif seq[0] == "NEW_MSG_BLOCK":
            print(current_port, "NEW_MSG_BLOCK")
            leader.new_msg_block(seq)
            msg.WaitMsgHandler.new_block(seq)

        elif seq[0] == "NEW_MSG":
            msgid = seq[1]["message"]["msgid"]
            # if (current_host, current_port) in leader.current_leaders and msgid not in processed_message_ids:
            if msgid not in processed_message_ids:
                processed_message_ids.add(msgid)
                leader.message_queue.append(seq)

        # else:
        forward(seq)

@tornado.gen.coroutine
def bootstrap(addr):
    global available_branches

    print(current_port, "fetch", addr)
    http_client = tornado.httpclient.AsyncHTTPClient()
    try:
        response = yield http_client.fetch("http://%s:%s/available_branches" % tuple(addr))
    except Exception as e:
        print("Error: %s" % e)
        tornado.ioloop.IOLoop.instance().call_later(1.0, functools.partial(bootstrap, addr))
        return

    result = tornado.escape.json_decode(response.body)
    branches = result["available_branches"]
    branches.sort(key=lambda l:len(l[2]))
    print(current_port, "fetch result", [tuple(i) for i in branches])

    if branches:
        available_branches = set([tuple(i) for i in branches])
        host, port, branch = branches[0]
        current_branch = tuple(branches[0])
        NodeConnector(host, port, branch)
    else:
        tornado.ioloop.IOLoop.instance().call_later(1.0, functools.partial(bootstrap, addr))

# connector to control center
control_node = None
control_node_msg_queue = []
@tornado.gen.coroutine
def control_on_connect(future):
    global control_node
    global control_node_msg_queue

    try:
        control_node = future.result()
        control_node.write_message(tornado.escape.json_encode(["ADDRESS", current_host, current_port]))
        for msg in control_node_msg_queue:
            control_node.write_message(tornado.escape.json_encode(msg))

    except:
        tornado.ioloop.IOLoop.instance().call_later(1.0, connect)

@tornado.gen.coroutine
def control_on_message(msg):
    global current_nodeid
    global available_branches

    if msg is None:
        tornado.ioloop.IOLoop.instance().call_later(1.0, connect)
        return

    seq = tornado.escape.json_decode(msg)
    print(current_port, "node on message", seq)

    if setting.BOOTSTRAP_BY_PORT_NO:
        return

    if seq[0] == "BOOTSTRAP_ADDRESS":
        if not seq[1]:
            # root node
            available_branches.add(tuple([current_host, current_port, "0"]))
            available_branches.add(tuple([current_host, current_port, "1"]))
            current_nodeid = ""

        else:
            bootstrap(seq[1][0])

@tornado.gen.coroutine
def connect():
    global current_nodeid
    global available_branches

    # print("\n\n")
    if control_host:
        print(current_port, "connect control", control_host, "port", control_port)
        tornado.websocket.websocket_connect("ws://%s:%s/control" % (control_host, control_port), callback=control_on_connect, on_message_callback=control_on_message)

    if setting.BOOTSTRAP_BY_PORT_NO:
        if NodeConnector.node_parent:
            return
        if int(current_port) > 8002:
            no = int(current_port) - 8001
            port = (no >> 1) + 8001
            print('Connector', bin(no)[3:], current_port)
            NodeConnector(parent_host, port, bin(no)[3:])

        else:
            available_branches.add(tuple([current_host, current_port, "0"]))
            available_branches.add(tuple([current_host, current_port, "1"]))
            current_nodeid = ""


def main():
    global current_host
    global current_port
    global parent_host
    global parent_port
    global control_host
    global control_port
    global node_sk

    parser = argparse.ArgumentParser(description="node description")
    parser.add_argument('--host', default="127.0.0.1")
    parser.add_argument('--port')
    parser.add_argument('--parent_host', default="127.0.0.1")
    parser.add_argument('--parent_port', default=2018)
    parser.add_argument('--control_host')
    parser.add_argument('--control_port', default=8000)

    args = parser.parse_args()
    current_host = args.host
    current_port = args.port
    parent_host = args.parent_host
    parent_port = args.parent_port
    control_host = args.control_host
    control_port = args.control_port

    if setting.BOOTSTRAP_BY_PORT_NO:
        if int(current_port) > 8002:
            no = int(current_port) - 8001
            parent_port = (no >> 1) + 8001

    database.main()

    # parser.add_argument('--pirvate_key', default=)
    # pirvate_key_file = args.pirvate_key
    node_sk = SigningKey.from_pem(open('data/pk/pk'+current_port).read())
    tornado.ioloop.IOLoop.instance().call_later(int(current_port)-8000, connect)
    # tornado.ioloop.IOLoop.instance().add_callback(connect)

if __name__ == '__main__':
    print("run python node.py pls")
