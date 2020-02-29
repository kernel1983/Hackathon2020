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
nonce = 0
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
def thread(n):
    global position
    global nonce
    global m
    global r
    # position2 = position
    while True:
        d = sha256(pk_bytes)
        # lock.acquire()
        nonce += 1
        nonce2 = nonce
        # lock.release()

        d.update(util.number_to_string(position, 2**64-1))
        d.update(util.number_to_string(nonce2, 2**64-1))
        if util.string_to_number(d.digest()) < m:
            m = util.string_to_number(d.digest())
            print(n, d.hexdigest(), nonce2, position, position/(time.time() - t0))
        if nonce2 % 10000000 == 0:
            print(time.time() - t0, nonce2, position, position/(time.time() - t0))
        if d.digest()[-1] == r:
            # out.write("\n"+str(position)+' '+str(nonce2)+' '+str(n)+' '+str(r))
            results.append([position, nonce2, n, r])
            if not messages:
                break
            # lock.acquire()
            position += 1
            r = messages.pop(0)
            # lock.release()

ts = []
for i in range(4):
    t=threading.Thread(target=thread, args=(i,))
    ts.append(t)
for t in ts:
    t.start()
for t in ts:
    t.join()

print(time.time() - t0)
for position, nonce2, n, r in results:
    out.write("\n"+str(position)+' '+str(nonce2)+' '+str(n)+' '+str(r))

