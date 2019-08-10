from __future__ import print_function

import sys
sys.path.append("..")

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
import database

working = False
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
        roots = database.connection.query("SELECT * FROM graph"+current_port+" WHERE from_block = %s OR to_block = %s ORDER BY nonce", root_hash, root_hash)

        for root in roots:
            # print(root.id)
            chains.append([root.hash])
            prev_hashs.append(root.hash)

    while True:
        if prev_hashs:
            prev_hash = prev_hashs.pop(0)
        else:
            break

        leaves = database.connection.query("SELECT * FROM graph"+current_port+" WHERE from_block = %s AND sender = %s ORDER BY nonce", prev_hash, root_hash)
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

        leaves = database.connection.query("SELECT * FROM graph"+current_port+" WHERE to_block = %s AND receiver = %s ORDER BY nonce", prev_hash, root_hash)
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
    global transactions
    msg_header, transaction, timestamp, msg_id = seq
    # print(seq)

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

    sender_bin = bin(int.from_bytes(base64.b64decode(sender), 'big'))[2:].zfill(16)
    receiver_bin = bin(int.from_bytes(base64.b64decode(receiver), 'big'))[2:].zfill(16)
    node_bin = bin(current_view - 1)[2:].zfill(2)
    # print(node_bin, sender_bin, receiver_bin)
    try:
        if sender_bin.endswith(node_bin) or receiver_bin.endswith(node_bin):
            sql = "INSERT INTO graph"+current_port+" (txid, timestamp, hash, from_block, to_block, sender, receiver, nonce, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            database.connection.execute(sql, txid, int(timestamp), block_hash, from_block, to_block, sender, receiver, nonce, tornado.escape.json_encode(transaction))

        if sender in locked_accounts:
            locked_accounts.remove(sender)
        if receiver in locked_accounts:
            locked_accounts.remove(receiver)

        # for tx in transactions:
        #     if tx["transaction"]["txid"] == txid:
        #         transactions.remove(tx)
        #         break
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

t0 = None
# connect point from leader node
class LeaderHandler(tornado.websocket.WebSocketHandler):
    leader_nodes = set()

    def check_origin(self, origin):
        return True

    def open(self):
        self.from_host = self.get_argument("host")
        self.from_port = self.get_argument("port")
        # self.remove_node = True
        # if False: #temp disable force disconnect
        #     print(current_port, "leader force disconnect")
        #     self.remove_node = False
        #     self.close()
        #     return

        print(current_port, "leader connected")
        if self not in LeaderHandler.leader_nodes:
            LeaderHandler.leader_nodes.add(self)

    def on_close(self):
        print(current_port, "leader disconnected")
        if self in LeaderHandler.leader_nodes: # and self.remove_node
            LeaderHandler.leader_nodes.remove(self)
        # self.remove_node = True

    @tornado.gen.coroutine
    def on_message(self, msg):
        global current_view_no
        global t0
        seq = tornado.escape.json_decode(msg)
        # print(current_port, "on message from leader connector", seq)

        if seq[0] == "NEW_TX_BLOCK":
            new_tx_block(seq)
            return

        # elif seq[0] == "TX":
        #     transaction = seq[1]
        #     txid = transaction["transaction"]["txid"]
        #     sender = transaction["transaction"]["sender"]
        #     receiver = transaction["transaction"]["receiver"]
        #     amount = transaction["transaction"]["amount"]
        #     timestamp = transaction["transaction"]["timestamp"]
        #     signature = transaction["signature"]
        #     nonce = transaction["nonce"]
        #     from_block = transaction["from_block"]
        #     to_block = transaction["to_block"]

        #     # sender_blocks = lastest_block(sender)
        #     # receiver_blocks = lastest_block(receiver)

        #     if from_block in locked_blocks or to_block in locked_blocks:
        #         message = ["NAK", txid]
        #         self.write_message(tornado.escape.json_encode(message))
        #     else:
        #         message = ["ACK", txid]
        #         self.write_message(tornado.escape.json_encode(message))
        #     print(current_port, "TX", message)
        #     return

        # elif seq[0] == "ACK":
        #     txid = seq[1]
        #     reply = block_to_reply.get(txid)
        #     if self in reply:
        #         reply.remove(self)
        #     print(current_port, "ACK reply", reply)
        #     if reply:
        #         return

        #     transaction = block_to_confirm.get(txid)
        #     sender = transaction["transaction"]["sender"]
        #     receiver = transaction["transaction"]["receiver"]

        #     block_hash = transaction["block_hash"]
        #     nonce = transaction["nonce"]
        #     from_block = transaction["from_block"]
        #     to_block = transaction["to_block"]
        #     return

        # elif seq[0] == "NAK":
        #     txid = seq[1]
        #     transaction = block_to_confirm.get(txid)
        #     if transaction:
        #         from_block = transaction["from_block"]
        #         to_block = transaction["to_block"]

        #         if from_block in locked_blocks:
        #             locked_blocks.remove(from_block)
        #         if to_block in locked_blocks:
        #             locked_blocks.remove(to_block)
        #         if transaction:
        #             del block_to_confirm[txid]
        #     return

        elif seq[0] == "PBFT_O":
            # print(current_port, "PBFT_O get message", seq[1])
            view = seq[1]
            view_no = seq[2]
            # if view_no % 3 != current_view - system_view - 1:
            #     return
            # view's no should be continuous
            transaction = seq[3]
            txid = transaction["transaction"]["txid"]
            # gen block
            block_hash = transaction["block_hash"]
            k = "%s_%s"%(int(view), int(view_no))
            view_transactions[k] = transaction

            if not t0:
                t0 = time.time()
            if t0:
                print(time.time()-t0)

            forward(["PBFT_P", view, view_no, txid, block_hash])
            return

        elif seq[0] == "PBFT_P":
            view = seq[1]
            view_no = seq[2]
            txid = seq[3]
            block_hash = seq[4]
            # verify blockhash with own blockhash for txid
            forward(["PBFT_C", view, view_no, txid, current_view])
            return

        elif seq[0] == "PBFT_C":
            view = seq[1]
            view_no = seq[2]
            txid = seq[3]
            confirm_view = seq[4]

            k = "%s_%s"%(int(view), int(view_no))
            transaction = view_transactions.get(k)
            view_confirms.setdefault(k, set())
            confirms = view_confirms[k]
            if confirm_view not in confirms:
                confirms.add(confirm_view)
                # print(current_port, current_view, confirms, transaction)
                if transaction and len(confirms)==2:
                    # print(current_port, "NEW_TX_BLOCK", txid)
                    message = ["NEW_TX_BLOCK", transaction, time.time(), uuid.uuid4().hex]
                    forward(message)
            return

        elif seq[0] == "PBFT_V":
            pass

        forward(seq)


# connector to leader node
class LeaderConnector(object):
    """Websocket Client"""
    leader_nodes = set()

    def __init__(self, to_host, to_port):
        self.host = to_host
        self.port = to_port
        self.ws_uri = "ws://%s:%s/leader?host=%s&port=%s" % (self.host, self.port, current_host, current_port)
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
        print(current_port, "leader connect")

        try:
            self.conn = future.result()
            if self not in LeaderConnector.leader_nodes:
                LeaderConnector.leader_nodes.add(self)
        except:
            print(current_port, "reconnect leader on connect ...")
            tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)


    def on_message(self, msg):
        global t0
        if msg is None:
            if not self.remove_node:
                print(current_port, "reconnect leader on message...")
                # self.ws_uri = "ws://%s:%s/leader?host=%s&port=%s" % (self.host, self.port, tree.current_host, current_port)
                tornado.ioloop.IOLoop.instance().call_later(1.0, self.connect)
            return

        seq = tornado.escape.json_decode(msg)
        # print(current_port, "on message from leader", seq)

        if seq[0] == "NEW_TX_BLOCK":
            new_tx_block(seq)
            return

        elif seq[0] == "PBFT_O":
            # print(current_port, "PBFT_O get message", seq[1])
            view = seq[1]
            view_no = seq[2]
            # if view_no % 3 != current_view - system_view - 1:
            #     return
            # view's no should be continuous
            transaction = seq[3]
            txid = transaction["transaction"]["txid"]
            # gen block
            block_hash = transaction["block_hash"]
            k = "%s_%s"%(int(view), int(view_no))
            view_transactions[k] = transaction

            if not t0:
                t0 = time.time()
            if t0:
                print(time.time()-t0)

            forward(["PBFT_P", view, view_no, txid, block_hash])
            return

        elif seq[0] == "PBFT_P":
            view = seq[1]
            view_no = seq[2]
            txid = seq[3]
            block_hash = seq[4]
            # verify blockhash with own blockhash for txid
            forward(["PBFT_C", view, view_no, txid, current_view])
            return

        elif seq[0] == "PBFT_C":
            view = seq[1]
            view_no = seq[2]
            txid = seq[3]
            confirm_view = seq[4]

            k = "%s_%s"%(int(view), int(view_no))
            transaction = view_transactions.get(k)
            view_confirms.setdefault(k, set())
            confirms = view_confirms[k]
            if confirm_view not in confirms:
                confirms.add(confirm_view)
                # print(current_port, current_view, confirms, transaction)
                if transaction and len(confirms)==2:
                    # print(current_port, "NEW_TX_BLOCK", txid)
                    message = ["NEW_TX_BLOCK", transaction, time.time(), uuid.uuid4().hex]
                    forward(message)
            return

        # elif seq[0] == "TX":
        #     transaction = seq[1]
        #     txid = transaction["transaction"]["txid"]
        #     sender = transaction["transaction"]["sender"]
        #     receiver = transaction["transaction"]["receiver"]
        #     amount = transaction["transaction"]["amount"]
        #     timestamp = transaction["transaction"]["timestamp"]
        #     signature = transaction["signature"]
        #     nonce = transaction["nonce"]
        #     from_block = transaction["from_block"]
        #     to_block = transaction["to_block"]

        #     # sender_blocks = lastest_block(sender)
        #     # receiver_blocks = lastest_block(receiver)

        #     if from_block in locked_blocks or to_block in locked_blocks:
        #         message = ["NAK", txid]
        #         self.conn.write_message(tornado.escape.json_encode(message))
        #     else:
        #         message = ["ACK", txid]
        #         self.conn.write_message(tornado.escape.json_encode(message))
        #     print(current_port, "TX", message)
        #     return

        # elif seq[0] == "ACK":
        #     txid = seq[1]
        #     reply = block_to_reply.get(txid)
        #     if self in reply:
        #         reply.remove(self)
        #     print(current_port, "ACK reply", reply)
        #     if reply:
        #         return

        #     transaction = block_to_confirm.get(txid)
        #     sender = transaction["transaction"]["sender"]
        #     receiver = transaction["transaction"]["receiver"]

        #     block_hash = transaction["block_hash"]
        #     nonce = transaction["nonce"]
        #     from_block = transaction["from_block"]
        #     to_block = transaction["to_block"]
        #     data = {}
        #     database.connection.execute("INSERT INTO graph"+current_port+" (hash, from_block, to_block, sender, receiver, nonce, data) VALUES (%s, %s, %s, %s, %s, %s, %s)", block_hash, from_block, to_block, sender, receiver, nonce, tornado.escape.json_encode(data))
        #     return

        # elif seq[0] == "NAK":
        #     txid = seq[1]
        #     transaction = block_to_confirm.get(txid)
        #     if transaction:
        #         from_block = transaction["from_block"]
        #         to_block = transaction["to_block"]

        #         if from_block in locked_blocks:
        #             locked_blocks.remove(from_block)
        #         if to_block in locked_blocks:
        #             locked_blocks.remove(to_block)
        #         if transaction:
        #             del block_to_confirm[txid]
        #     return

        # else:
        forward(seq)

transactions = []
locked_accounts = set()
# block_to_confirm = {}
# block_to_reply = {}
def mining():
    # global working
    # global transactions
    global locked_accounts
    global current_view_no
    global view_transactions
    if working:
        # tornado.ioloop.IOLoop.instance().add_callback(mining)
        tornado.ioloop.IOLoop.instance().call_later(1, mining)

    if transactions:
        # print(current_port, "I'm the leader", current_view, "of leader view", system_view)
        seq = transactions.pop(0)
        transaction = seq[1]
        txid = transaction["transaction"]["txid"]
        if current_view != system_view:
            tx = database.connection.get("SELECT * FROM graph"+current_port+" WHERE txid = %s LIMIT 1", txid)
            if not tx:
                transactions.append(seq)
            return
        sender = transaction["transaction"]["sender"]
        receiver = transaction["transaction"]["receiver"]
        amount = transaction["transaction"]["amount"]
        timestamp = transaction["transaction"]["timestamp"]
        signature = transaction["signature"]

        if sender in locked_accounts or receiver in locked_accounts:
            transactions.append(seq)
            print(current_port, "put tx back", txid, len(transactions))
            return
        locked_accounts.add(sender)
        locked_accounts.add(receiver)
        # print(current_port, "locked_accounts", locked_accounts)

        sender_blocks = lastest_block(sender)
        receiver_blocks = lastest_block(receiver)

        from_block = sender_blocks[-1] if sender_blocks else sender
        to_block = receiver_blocks[-1] if receiver_blocks else receiver

        nonce = 0
        data = txid + sender + receiver + str(amount) + str(timestamp) + signature + from_block + to_block + str(current_port)
        block_hash = hashlib.sha256((data + str(nonce)).encode('utf8')).hexdigest()
        transaction["block_hash"] = block_hash
        transaction["nonce"] = nonce
        transaction["from_block"] = from_block
        transaction["to_block"] = to_block

        current_view_no += 1
        k = "%s_%s"%(int(current_view), int(current_view_no))
        view_transactions[k] = transaction
        message = ["PBFT_O", current_view, current_view_no, transaction]
        forward(message)


class NewTxHandler(tornado.web.RequestHandler):
    def post(self):
        tx = tornado.escape.json_decode(self.request.body)
        msg = ["NEW_TX", tx, time.time(), uuid.uuid4().hex]
        transactions.append(msg)
        self.finish({"txid": tx["transaction"]["txid"]})

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
                    (r"/leader", LeaderHandler),
                    (r"/new_tx", NewTxHandler),
                    ]
        settings = {"debug":True}

        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    LeaderConnector("127.0.0.1", 8001)

if __name__ == '__main__':
    # main()
    # print("run python node.py pls")
    current_host = "127.0.0.1"
    current_port = "8002"
    server = Application()
    server.listen(current_port)
    tornado.ioloop.IOLoop.instance().add_callback(main)
    working = True
    system_view = 1
    current_view = 2
    tornado.ioloop.IOLoop.instance().add_callback(mining)
    tornado.ioloop.IOLoop.instance().start()
