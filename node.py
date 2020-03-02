from __future__ import print_function

import time
import socket
import subprocess
import argparse
import uuid
import base64

import tornado.web
# import tornado.websocket
import tornado.ioloop
import tornado.options
import tornado.httpserver
# import tornado.httpclient
import tornado.gen
import tornado.escape

import setting
import tree
import miner
import leader
import database
import fs
import msg

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/node", tree.NodeHandler),
                    (r"/leader", leader.LeaderHandler),
                    (r"/available_branches", AvailableBranchesHandler),
                    (r"/get_chain", miner.GetChainHandler),
                    (r"/get_block", miner.GetBlockHandler),
                    (r"/get_node", GetNodeHandler),
                    (r"/disconnect", DisconnectHandler),
                    (r"/broadcast", BroadcastHandler),
                    (r"/new_tx", NewTxHandler),
                    (r"/dashboard", DashboardHandler),
                    # mtfs
                    # (r"/user", fs.UserHandler),
                    (r"/fs/new_file_meta", fs.NewFileMetaHandler),
                    (r"/fs/new_file_blob", fs.NewFileBlobHandler),
                    (r"/fs/new_root_home", fs.NewRootHomeHandler),
                    # (r"/activate_default_store", fs.ActivateDefaultStoreHandler),
                    (r"/new_msg", msg.NewMsgHandler),
                    (r"/get_msg", msg.GetMsgHandler),
                    (r"/wait_msg", msg.WaitMsgHandler),
                    (r"/get_chat", msg.GetChatHandler),
                    ]
        settings = {"debug":True}

        tornado.web.Application.__init__(self, handlers, **settings)


class AvailableBranchesHandler(tornado.web.RequestHandler):
    def get(self):
        branches = list(tree.available_branches)

        # parent = tree.NodeConnector.parent_node:
        self.finish({"available_branches": branches,
                     #"parent": parent,
                     "nodeid": tree.current_nodeid})

class GetNodeHandler(tornado.web.RequestHandler):
    def get(self):
        nodeid = self.get_argument("nodeid")
        target_nodeid = nodeid
        score = None
        # print(tree.current_port, tree.node_neighborhoods)
        for j in [tree.node_neighborhoods, tree.node_parents]:
            for i in j:
                new_score = tree.node_distance(nodeid, i)
                if score is None or new_score < score:
                    score = new_score
                    target_nodeid = i
                    address = j[target_nodeid]
                # print(i, new_score)

        self.finish({"address": address,
                     "nodeid": target_nodeid,
                     "current_nodeid": tree.current_nodeid})

class DisconnectHandler(tornado.web.RequestHandler):
    def get(self):
        if tree.NodeConnector.parent_node:
            # connector.remove_node = False
            tree.NodeConnector.parent_node.close()

        self.finish({})
        tornado.ioloop.IOLoop.instance().stop()

class BroadcastHandler(tornado.web.RequestHandler):
    def get(self):
        test_msg = ["TEST_MSG", tree.current_nodeid, time.time(), uuid.uuid4().hex]

        tree.forward(test_msg)
        self.finish({"test_msg": test_msg})

class NewTxHandler(tornado.web.RequestHandler):
    def post(self):
        tx = tornado.escape.json_decode(self.request.body)

        tree.forward(["NEW_TX", tx, time.time(), uuid.uuid4().hex])
        self.finish({"txid": tx["transaction"]["txid"]})

class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        branches = list(tree.available_branches)
        branches.sort(key=lambda l:len(l[2]))

        parents = []
        self.write("<br>current_nodeid: %s <br>" % tree.current_nodeid)

        self.write("<br>pk: %s <br>" % base64.b16encode(tree.node_sk.get_verifying_key().to_string()).decode("utf8"))
        # sender = base64.b64encode(sender_vk.to_string()).decode("utf8")
        self.write("<br>parent_node:<br>")
        if tree.NodeConnector.parent_node:
            self.write("%s:%s<br>" %(tree.NodeConnector.parent_node.host, tree.NodeConnector.parent_node.port))

        self.write("<br>node_parents:<br>")
        for nodeid in tree.node_parents:
            host, port = tree.node_parents[nodeid][0]
            self.write("%s %s:%s<br>" %(nodeid, host, port))

        self.write("<br>node_neighborhoods:<br>")
        for nodeid in tree.node_neighborhoods:
            host, port = tree.node_neighborhoods[nodeid]
            self.write("%s %s:%s<br>" %(nodeid, host, port))

        self.write("<br>nodes_pool:<br>")
        for nodeid in tree.nodes_pool:
            pk = tree.nodes_pool[nodeid]
            self.write("%s: %s<br>" %(nodeid, pk))

        self.write("<br>nodes_in_chain:<br>")
        for nodeid in miner.nodes_in_chain:
            pk = miner.nodes_in_chain[nodeid]
            self.write("%s: %s<br>" %(nodeid, pk))

        self.write("<br>frozen_nodes_in_chain:<br>")
        for nodeid in miner.frozen_nodes_in_chain:
            pk = miner.frozen_nodes_in_chain[nodeid]
            self.write("%s: %s<br>" %(nodeid, pk))

        self.write("<br>available_branches:<br>")
        for branch in branches:
            self.write("%s:%s %s <br>" % branch)

        self.write("<br>LeaderHandler:<br>")
        for node in leader.LeaderHandler.leader_nodes:
            self.write("%s:%s<br>" %(node.from_host, node.from_port))

        self.write("<br>LeaderConnector:<br>")
        for node in leader.LeaderConnector.leader_nodes:
            self.write("%s:%s<br>" %(node.host, node.port))

        self.write("<br>frozen chain:<br>")
        for i, h in enumerate(miner.frozen_chain):
            self.write("%s %s<br>" % (i, h))
        self.finish()

def main():
    database.main()
    tree.main()
    miner.main()
    # fs.main()

    server = Application()
    server.listen(tree.current_port, '0.0.0.0')
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()

