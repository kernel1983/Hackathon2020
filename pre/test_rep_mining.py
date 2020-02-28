from __future__ import print_function

import time
import base64
import random
from hashlib import blake2b
from hashlib import sha1
from hashlib import sha256

import numbertheory
import util

from keys import PrivateKey, PublicKey

sk = PrivateKey.generate()
pk_bytes = sk.verifying_key.to_string()

# l160 = 2**160-1
# l192 = 2**192-1
l256 = 2**256-1
# l512 = 2**512-1

print(pk_bytes)
# t0 = time.time()
m = l256
nonce = 0
position = 0

out = open('./rep.txt', 'w')
out.write(base64.b16encode(pk_bytes).decode('utf8'))

messages = []
for i in range(2**20):
    r = random.randrange(255)
    messages.append(r)

t0 = time.time()
while True:
    # r = util.number_to_string(random.randrange(255), 255)
    if not messages:
        break
    position += 1
    r = messages.pop(0)
    while True:
        d = sha256(pk_bytes)
        nonce += 1
        d.update(util.number_to_string(position, 2**64-1))
        d.update(util.number_to_string(nonce, 2**64-1))
        if util.string_to_number(d.digest()) < m:
            m = util.string_to_number(d.digest())
            print(d.hexdigest(), nonce, position, nonce/position)
        if nonce % 10000000 == 0:
            print(time.time() - t0, nonce, position, position/(time.time() - t0))
        if d.digest()[-1] == r:
            out.write("\n"+str(position)+' '+str(nonce)+' '+str(n)+' '+str(r))
            # print(d.hexdigest(), m, nonce, r)
            break

print(time.time() - t0)
