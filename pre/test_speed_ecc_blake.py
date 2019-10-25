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

# D = (g^a)^t, t = H(a, v)
# v random
# E = g^r
# F = H(g^t, E)) xor m
# s = r + a*H(m, E)

l192 = 2**192-1
l160 = 2**160-1
l512 = 2**512-1

# t0 = time.time()
# for i in range(1000):
#     v = random.randrange(1, l192)
#     V = sk.privkey.public_key.point * v
#     # print('V = g^v', V)
# print('time ecc ', time.time() - t0)


t0 = time.time()
for i in range(1000):
    d = blake2b(digest_size=24)
    a = random.randrange(1, l192)
    v = random.randrange(1, l192)
    d.update(util.number_to_string(a, l192))
    d.update(util.number_to_string(v, l192))
    t = util.string_to_number(d.digest())
    # print('t = H(a,v)', t)
print('time blake2b ', time.time() - t0)

t0 = time.time()
for i in range(1000):
    d = sha1()
    a = random.randrange(1, l192)
    v = random.randrange(1, l192)
    d.update(util.number_to_string(a, l192))
    d.update(util.number_to_string(v, l192))
    t = util.string_to_number(d.digest())
print('time sha1 ', time.time() - t0)

t0 = time.time()
for i in range(1000):
    d = sha256()
    a = random.randrange(1, l192)
    v = random.randrange(1, l192)
    d.update(util.number_to_string(a, l192))
    d.update(util.number_to_string(v, l192))
    t = util.string_to_number(d.digest())
print('time sha256 ', time.time() - t0)


g = random.randrange(1, l192)
for i in range(1000):
    v = random.randrange(1, l192)
    V = numbertheory.modular_exp(g, v, l192)
print('time exp ', time.time() - t0)
