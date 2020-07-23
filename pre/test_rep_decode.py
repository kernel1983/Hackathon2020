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

# sk = PrivateKey.generate()
# pk_bytes = sk.verifying_key.to_string()

# l160 = 2**160-1
# l192 = 2**192-1
# l256 = 2**256-1
# l512 = 2**512-1

# print(pk_bytes)
t0 = time.time()
# m = l256
# nonce = 0
# position = 0

f = open('./rep.txt', 'r')
pk = f.readline()
print(pk)
pk_bytes = base64.b32decode(pk.strip())

# messages = []
reps = []
p = 0
prev_rep = 0
max_interval = 0
while True:
    line = f.readline()
    if not line:
        break
    p += 1
    position, rep, r = line.split(' ')
    assert int(position) == p
    assert prev_rep < int(rep)
    if int(rep) - prev_rep > max_interval:
        max_interval = int(rep) - prev_rep
    prev_rep = int(rep)
    print(position, rep, r)
    d = sha256(pk_bytes)
    d.update(util.number_to_string(int(position), 2**64-1))
    d.update(util.number_to_string(int(rep), 2**64-1))
    print(d.digest()[-1])
    assert d.digest()[-1] == int(r)

print(time.time() - t0)
print(max_interval)
