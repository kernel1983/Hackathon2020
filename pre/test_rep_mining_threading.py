from __future__ import print_function

import time
import random
import base64
import threading
from hashlib import blake2b
from hashlib import sha1
from hashlib import sha256

import numbertheory
import util

from keys import PrivateKey, PublicKey

lock = threading.Lock()
sk = PrivateKey.generate()
pk_bytes = sk.verifying_key.to_string()

# l160 = 2**160-1
# l192 = 2**192-1
l256 = 2**256-1
# l512 = 2**512-1

print(pk_bytes)
m = l256
nonce = 1
position = 1

out = open('./rep_threading.txt', 'w')
out.write(base64.b16encode(pk_bytes).decode('utf8'))

messages = []
for i in range(2**20):
    r = random.randrange(255)
    messages.append(r)

t0 = time.time()
r = messages.pop(0)
results = []
def thread(n, t):
    global position
    global nonce
    global m
    global r
    nonce2 = nonce+n
    position2 = position
    while True:
        if position2 != position:
            position2 = position
            nonce2 = nonce+n

        d = sha256(pk_bytes)
        # lock.acquire()
        nonce2 += t
        # lock.release()

        d.update(util.number_to_string(position, 2**64-1))
        d.update(util.number_to_string(nonce2, 2**64-1))
        if util.string_to_number(d.digest()) < m:
            m = util.string_to_number(d.digest())
            print(n, d.hexdigest(), nonce2, nonce2/(time.time() - t0 + 0.00000001), position, position/(time.time() - t0 + 0.00000001))
        if nonce % 10000000 == 0:
            print(time.time() - t0, nonce2, nonce2/(time.time() - t0 + 0.00000001), position, position/(time.time() - t0 + 0.00000001))
        if d.digest()[-1] == r:
            # print(position, nonce2, n, r)
            # out.write("\n"+str(position)+' '+str(nonce2)+' '+str(n)+' '+str(r))
            results.append([position, nonce2, n, r])
            if not messages:
                break
            # lock.acquire()
            position += 1
            nonce = nonce2
            # position2 = position
            r = messages.pop(0)
            # lock.release()

ts = []
for i in range(4):
    t=threading.Thread(target=thread, args=(i,4))
    ts.append(t)
for t in ts:
    t.start()
for t in ts:
    t.join()

print(time.time() - t0, nonce/(time.time() - t0), position/(time.time() - t0))
for position, nonce2, n, r in results:
    out.write("\n"+str(position)+' '+str(nonce2)+' '+str(n)+' '+str(r))
