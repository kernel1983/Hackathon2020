from __future__ import print_function

import time
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
while True:
    # r = util.number_to_string(random.randrange(255), 255)
    position += 1
    r = random.randrange(255)
    d = sha256(pk_bytes)
    while True:
        nonce += 1
        d.update(util.number_to_string(position, 2**64-1))
        d.update(util.number_to_string(nonce, 2**64-1))
        if util.string_to_number(d.digest()) < m:
            m = util.string_to_number(d.digest())
            print(d.hexdigest(), nonce, position, nonce/position)
        if d.digest()[-1] == r:
            # print(d.hexdigest(), m, nonce, r)
            break
