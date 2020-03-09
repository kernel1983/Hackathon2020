from __future__ import print_function

import time
import uuid
import hashlib
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
import database

from ecdsa.util import string_to_number

certain_value = "0"
certain_value = certain_value + 'f'*(64-len(certain_value))

# working = False
system_view = None
current_view = None
current_view_no = 0
view_transactions = {}
view_confirms = {}

root_jump = {}
def lastest_block(root_hash):
    global root_jump

    chains = []
    prev_hashs = []
    if root_hash in root_jump:
        recent_hash = root_jump[root_hash]
        chains.append([recent_hash])
        prev_hashs.append(recent_hash)

    else:
        roots = database.connection.query("SELECT * FROM graph"+tree.current_port+" WHERE from_block = %s OR to_block = %s ORDER BY nonce", root_hash, root_hash)

        for root in roots:
            # print(root.id)
            chains.append([root.hash])
            prev_hashs.append(root.hash)

    while True:
        if prev_hashs:
            prev_hash = prev_hashs.pop(0)
        else:
            break

        leaves = database.connection.query("SELECT * FROM graph"+tree.current_port+" WHERE from_block = %s AND sender = %s ORDER BY nonce", prev_hash, root_hash)
        if len(leaves) > 0:
            for leaf in leaves:
                # print(leaf.id)
                for c in chains:
                    if c[-1] == prev_hash:
                        chain = c.copy()
                        chain.append(leaf.hash)
                        chains.append(chain)
                        break
                if leaf.hash not in prev_hashs and leaf.hash:
                    prev_hashs.append(leaf.hash)

        leaves = database.connection.query("SELECT * FROM graph"+tree.current_port+" WHERE to_block = %s AND receiver = %s ORDER BY nonce", prev_hash, root_hash)
        if len(leaves) > 0:
            for leaf in leaves:
                # print(leaf.id)
                for c in chains:
                    if c[-1] == prev_hash:
                        chain = c.copy()
                        chain.append(leaf.hash)
                        chains.append(chain)
                        break
                if leaf.hash not in prev_hashs and leaf.hash:
                    prev_hashs.append(leaf.hash)

    longest = []
    for i in chains:
        if not longest:
            longest = i
        if len(longest) < len(i):
            longest = i
    # print(longest)
    if len(longest) > 3:
        root_jump[root_hash] = longest[-3]
    return longest


def new_tx_block(seq):
    global messages
    msg_header, transaction, timestamp, msg_id = seq

    txid = transaction["transaction"]["txid"]
    sender = transaction["transaction"]["sender"]
    receiver = transaction["transaction"]["receiver"]
    amount = transaction["transaction"]["amount"]
    timestamp = transaction["transaction"]["timestamp"]

    signature = transaction["signature"]
    block_hash = transaction["block_hash"]
    nonce = transaction["nonce"]
    from_block = transaction["from_block"]
    to_block = transaction["to_block"]

    related_block = True
    if setting.NODE_DIVISION:
        sender_bytes = base64.b64decode(sender.encode('utf8'))
        sender_binary = bin(string_to_number(sender_bytes))[2:]
        # print(tree.current_port, "sender", sender_binary)
        receiver_bytes = base64.b64decode(receiver.encode('utf8'))
        receiver_binary = bin(string_to_number(receiver_bytes))[2:]
        # print(tree.current_port, "receiver", receiver_binary)
        if not sender_binary.startswith(tree.current_nodeid) and not receiver_binary.startswith(tree.current_nodeid):
            related_block = False

    try:
        if related_block:
            sql = "INSERT INTO graph"+tree.current_port+" (msgid, timestamp, hash, from_block, to_block, sender, receiver, nonce, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            database.connection.execute(sql, txid, int(timestamp), block_hash, from_block, to_block, sender, receiver, nonce, tornado.escape.json_encode(transaction))

        if sender in locked_accounts:
            locked_accounts.remove(sender)
        if receiver in locked_accounts:
            locked_accounts.remove(receiver)

        # for tx in messages:
        #     if tx["transaction"]["txid"] == txid:
        #         messages.remove(tx)
        #         break
    except:
        pass


def new_msg_block(seq):
    global messages
    msg_header, block, timestamp, msg_id = seq

    msgid = block["message"]["msgid"]
    sender = block["message"]["sender"]
    receiver = block["message"]["receiver"]
    # amount = block["message"]["amount"]
    timestamp = block["message"]["timestamp"]

    signature = block["signature"]
    block_hash = block["block_hash"]
    nonce = block["nonce"]
    from_block = block["from_block"]
    to_block = block["to_block"]

    related_block = True
    if setting.NODE_DIVISION:
        sender_bytes = base64.b64decode(sender.encode('utf8'))
        sender_binary = bin(string_to_number(sender_bytes))[2:]
        # print(tree.current_port, "sender", sender_binary)
        receiver_bytes = base64.b64decode(receiver.encode('utf8'))
        receiver_binary = bin(string_to_number(receiver_bytes))[2:]
        # print(tree.current_port, "receiver", receiver_binary)
        if not sender_binary.startswith(tree.current_nodeid) and not receiver_binary.startswith(tree.current_nodeid):
            related_block = False

    try:
        if related_block:
            sql = "INSERT INTO graph"+tree.current_port+" (msgid, timestamp, hash, from_block, to_block, sender, receiver, nonce, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            database.connection.execute(sql, msgid, int(timestamp), block_hash, from_block, to_block, sender, receiver, nonce, tornado.escape.json_encode(block))

        if sender in locked_accounts:
            locked_accounts.remove(sender)
        if receiver in locked_accounts:
            locked_accounts.remove(receiver)
    except:
        pass


def forward(seq):
    # global processed_message_ids

    # msg_id = seq[-1]
    # if msg_id in processed_message_ids:
    #     return
    # processed_message_ids.add(msg_id)
    msg = tornado.escape.json_encode(seq)

    for leader_node in LeaderHandler.leader_nodes:
        leader_node.write_message(msg)

    for leader_connector in LeaderConnector.leader_nodes:
        leader_connector.conn.write_message(msg)


# connect point from leader node
class LeaderHandler(tornado.websocket.WebSocketHandler):
    leader_nodes = set()

    def check_origin(self, origin):
        return True

    def open(self):
        self.from_host = self.get_argument("host")
        self.from_port = self.get_argument("port")
        self.from_id = self.get_argument("id")
        self.from_pk = self.get_argument("pk")
        # self.remove_node = True
        # if False: #temp disable force disconnect
        #     print(tree.current_port, "leader force disconnect")
        #     self.remove_node = False
        #     self.close()
        #     return

        print(tree.current_port, "leader attached from", self.from_port)
        if self not in LeaderHandler.leader_nodes:
            LeaderHandler.leader_nodes.add(self)

    def on_close(self):
        print(tree.current_port, "leader disconnected")
        if self in LeaderHandler.leader_nodes: # and self.remove_node
            LeaderHandler.leader_nodes.remove(self)
        # self.remove_node = True

    @tornado.gen.coroutine
    def on_message(self, msg):
        global current_view_no
        seq = tornado.escape.json_decode(msg)
        # print(tree.current_port, "on message from leader connector", seq)

        if seq[0] == "NEW_CHAIN_BLOCK":
            miner.new_block(seq)

        elif seq[0] == "PBFT_O":
            # print(tree.current_port, "PBFT_O get message", seq[1])
            view = seq[1]
            view_no = seq[2]
            # view's no should be continuous
            block = seq[3]
            msgid = block["transaction"]["txid"] if "transaction" in block else block["message"]["msgid"]
            # gen block
            block_hash = block["block_hash"]
            k = "%s_%s"%(int(view), int(view_no))
            view_transactions[k] = block
            forward(["PBFT_P", view, view_no, msgid, block_hash])
            return

        elif seq[0] == "PBFT_P":
            view = seq[1]
            view_no = seq[2]
            msgid = seq[3]
            block_hash = seq[4]
            # verify blockhash with own blockhash for msgid
            forward(["PBFT_C", view, view_no, msgid, current_view])
            return

        elif seq[0] == "PBFT_C":
            view = seq[1]
            view_no = seq[2]
            msgid = seq[3]
            confirm_view = seq[4]

            k = "%s_%s"%(int(view), int(view_no))
            block = view_transactions.get(k)
            view_confirms.setdefault(k, set())
            confirms = view_confirms[k]
            if confirm_view not in confirms:
                confirms.add(confirm_view)
                # print(tree.current_port, current_view, confirms, block)
                if block and len(confirms)==2:
                    print(tree.current_port, "NEW BLOCK", msgid)
                    if "transaction" in block:
                        message = ["NEW_TX_BLOCK", block, time.time(), uuid.uuid4().hex]
                    else:
                        message = ["NEW_MSG_BLOCK", block, time.time(), uuid.uuid4().hex]
                    tree.forward(message)
            return

        elif seq[0] == "PBFT_V":
            pass

        forward(seq)


# connector to leader node
class LeaderConnector(object):
    """Websocket Client"""
    leader_nodes = set()

    def __init__(self, nodeid, nodepk):
        self.id = nodeid
        self.pk = nodepk
        self.probe()

    @tornado.gen.coroutine
    def probe(self):
        http_client = tornado.httpclient.AsyncHTTPClient()
        host, port = tree.current_host, tree.current_port
        while True:
            print('======', self.id, self.pk)
            try:
                response = yield http_client.fetch("http://%s:%s/get_node?nodeid=%s" % (host, port, self.id), request_timeout=300)
            except:
                break
            result = tornado.escape.json_decode(response.body)
            host, port = result['address']
            if self.id == result['current_nodeid']:
                break
            print('result >>>>>', result)

        self.host = host
        self.port = port
        self.ws_uri = "ws://%s:%s/leader?host=%s&port=%s&id=%s&pk=%s" % (self.host, self.port, tree.current_host, tree.current_port, self.id, self.pk)
        # self.branch = None
        self.remove_node = False
        self.conn = None
        self.connect()

    def connect(self):
        tornado.websocket.websocket_connect(self.ws_uri,
                                callback = self.on_connect,
                                on_message_callback = self.on_message,
                                connect_timeout = 1000.0)

    def close(self):
        self.remove_node = True
        if self in LeaderConnector.leader_nodes:
            LeaderConnector.leader_nodes.remove(self)
        self.conn.close()

    def on_connect(self, future):
        print(tree.current_port, "leader connect to", self.port)

        try:
            self.conn = future.result()
            if self not in LeaderConnector.leader_nodes:
                LeaderConnector.leader_nodes.add(self)
        except:
            print(tree.current_port, "reconnect to leader", self.host, self.port)
            tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)


    def on_message(self, msg):
        if msg is None:
            if not self.remove_node:
                print(tree.current_port, "reconnect leader on message...")
                # self.ws_uri = "ws://%s:%s/leader?host=%s&port=%s" % (self.host, self.port, tree.current_host, tree.current_port)
                tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)
            return

        seq = tornado.escape.json_decode(msg)
        # print(tree.current_port, "on message from leader", seq)

        if seq[0] == "NEW_CHAIN_BLOCK":
            miner.new_block(seq)

        elif seq[0] == "PBFT_O":
            # print(tree.current_port, "PBFT_O get message", seq[1])
            view = seq[1]
            view_no = seq[2]
            # view's no should be continuous
            block = seq[3]
            msgid = block["transaction"]["txid"] if "transaction" in block else block["message"]["msgid"]
            # gen block
            block_hash = block["block_hash"]
            k = "%s_%s"%(int(view), int(view_no))
            view_transactions[k] = block
            forward(["PBFT_P", view, view_no, msgid, block_hash])
            return

        elif seq[0] == "PBFT_P":
            view = seq[1]
            view_no = seq[2]
            msgid = seq[3]
            block_hash = seq[4]
            # verify blockhash with own blockhash for msgid
            forward(["PBFT_C", view, view_no, msgid, current_view])
            return

        elif seq[0] == "PBFT_C":
            view = seq[1]
            view_no = seq[2]
            msgid = seq[3]
            confirm_view = seq[4]

            k = "%s_%s"%(int(view), int(view_no))
            block = view_transactions.get(k)
            view_confirms.setdefault(k, set())
            confirms = view_confirms[k]
            if confirm_view not in confirms:
                confirms.add(confirm_view)
                # print(tree.current_port, current_view, confirms, block)
                if block and len(confirms)==2:
                    print(tree.current_port, "NEW BLOCK", msgid)
                    if "transaction" in block:
                        message = ["NEW_TX_BLOCK", block, time.time(), uuid.uuid4().hex]
                    else:
                        message = ["NEW_MSG_BLOCK", block, time.time(), uuid.uuid4().hex]
                    tree.forward(message)
            return

        forward(seq)

messages = []
locked_accounts = set()
# block_to_confirm = {}
# block_to_reply = {}
# @tornado.gen.coroutine
def mining():
    # global working
    global messages
    global locked_accounts
    global current_view_no
    global view_transactions
    global leader_connector_new

    tornado.ioloop.IOLoop.instance().call_later(0.1, mining)
    if leader_connector_new:
        leader_info = leader_connector_new.pop(0)
        LeaderConnector(*leader_info)
    # if not working:
    #     return
    if current_view is None:
        return

    if messages:
        # print(tree.current_port, "I'm the leader", current_view, "of leader view", system_view)
        seq = messages.pop(0)
        block = seq[1]
        if "transaction" in block:
            msgid = block["transaction"]["txid"]
            if current_view != system_view:
                tx = database.connection.get("SELECT * FROM graph"+tree.current_port+" WHERE msgid = %s LIMIT 1", msgid)
                if not tx:
                    messages.append(seq)
                return
            sender = block["transaction"]["sender"]
            receiver = block["transaction"]["receiver"]
            amount = block["transaction"]["amount"]
            timestamp = block["transaction"]["timestamp"]
            signature = block["signature"]

        else:
            msgid = block["message"]["msgid"]
            if current_view != system_view:
                msg = database.connection.get("SELECT * FROM graph"+tree.current_port+" WHERE msgid = %s LIMIT 1", msgid)
                if not msg:
                    messages.append(seq)
                return
            sender = block["message"]["sender"]
            receiver = block["message"]["receiver"]
            timestamp = block["message"]["timestamp"]
            signature = block["signature"]

        if sender in locked_accounts or receiver in locked_accounts:
            messages.append(seq)
            print(tree.current_port, "put msg back", msgid, len(messages))
            return
        locked_accounts.add(sender)
        locked_accounts.add(receiver)
        # print(tree.current_port, "locked_accounts", locked_accounts)

        sender_blocks = lastest_block(sender)
        receiver_blocks = lastest_block(receiver)

        from_block = sender_blocks[-1] if sender_blocks else sender
        to_block = receiver_blocks[-1] if receiver_blocks else receiver
        block["from_block"] = from_block
        block["to_block"] = to_block

        nonce = 0
        data = tornado.escape.json_encode(block) + str(tree.current_port)
        block_hash = hashlib.sha256((data + str(nonce)).encode('utf8')).hexdigest()
        block["block_hash"] = block_hash
        block["nonce"] = nonce

        current_view_no += 1
        k = "%s_%s"%(int(current_view), int(current_view_no))
        view_transactions[k] = block
        message = ["PBFT_O", current_view, current_view_no, block]
        forward(message)


current_leaders = set()
previous_leaders = set()
leader_connector_new = []
def update(leaders):
    global current_leaders
    global previous_leaders
    # global working
    global messages
    global leader_connector_new

    current_leaders = leaders
    nodeno = str(tree.nodeid2no(tree.current_nodeid))
    nodepk = base64.b32encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8")
    # print(tree.current_port, nodeno, pk)
    # print(tree.current_port, leaders, previous_leaders)
    if (nodeno, nodepk) in leaders - previous_leaders:
        for no, pk in leaders:
            connected = set([(i.id, i.pk) for i in LeaderConnector.leader_nodes]) |\
                        set([(i.from_id, i.from_pk) for i in LeaderHandler.leader_nodes]) |\
                        set([(nodeno, nodepk)])
            # print(tree.current_port, connected)
            if (no, pk) not in connected:
                nodeid = tree.nodeno2id(int(no))
                # print(tree.current_port, other_leader_addr, connected)
                leader_connector_new.append((nodeid, pk))

        # if not working:
        #     tornado.ioloop.IOLoop.instance().add_callback(mining)
        #     working = True

    nodes_to_close = set()
    for node in LeaderConnector.leader_nodes:
        if (node.id, node.pk) not in leaders:
            nodes_to_close.add(node)

    # print(tree.current_port, "nodes_to_close", len(nodes_to_close))
    # while nodes_to_close:
    #     nodes_to_close.pop().close()

    if (nodeno, nodepk) not in leaders:
        # working = False
        messages = []

        # while LeaderConnector.leader_nodes:
        #     LeaderConnector.leader_nodes.pop().close()

    previous_leaders = leaders

# @tornado.gen.coroutine
# def main():
#     tornado.ioloop.IOLoop.instance().call_later(1, looping)

if __name__ == '__main__':
    # main()
    print("run python node.py pls")
