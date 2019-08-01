from __future__ import print_function

import os
import subprocess
import time
import socket
import argparse
import random
import uuid
import base64
import hashlib
import urllib

import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.options
import tornado.httpserver
import tornado.gen
import tornado.escape

# from ecdsa import SigningKey, NIST384p
# from umbral import pre, keys, signing

incremental_port = 8000

class Application(tornado.web.Application):
    def __init__(self):
        settings = {
            "debug":True,
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
        }
        handlers = [(r"/new_node", NewNodeHandler),
                    (r"/static/(.*)", tornado.web.StaticFileHandler, dict(path=settings['static_path'])),
                    ]

        tornado.web.Application.__init__(self, handlers, **settings)

class NewNodeHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.count = int(self.get_argument("n", "1"))
        tornado.ioloop.IOLoop.instance().call_later(1, self.add)

    def add(self):
        global incremental_port
        if self.count <= 0:
            self.finish()
            return
        self.count -= 1
        incremental_port += 1
        subprocess.Popen(["python", "node.py", "--host=%s"%current_host, "--port=%s"%incremental_port, "--control_host=%s"%control_host, "--control_port=%s"%control_port], shell=False)
        self.write("new node %s\n" % incremental_port)
        tornado.ioloop.IOLoop.instance().call_later(2, self.add)


def main():
    global current_host
    global current_port
    global control_host
    global control_port
    global incremental_port

    parser = argparse.ArgumentParser(description="control description")
    parser.add_argument('--host')
    parser.add_argument('--port', default=8000)
    parser.add_argument('--control_host')
    parser.add_argument('--control_port', default=8000)

    args = parser.parse_args()
    current_host = args.host
    current_port = args.port
    control_host = args.control_host
    control_port = args.control_port
    incremental_port = int(current_port)

    server = Application()
    server.listen(current_port)
    # tornado.ioloop.IOLoop.instance().add_callback(connect)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
