from __future__ import print_function

import random
# import os
import time
# import shutil
# import subprocess
# from binascii import hexlify, unhexlify
# from hashlib import sha1, sha256, sha512

import numbertheory
import util

l = 2**128-1
q = util.randrange(l*8)
p = numbertheory.next_prime(2**128+q)
print(hex(q))
print(hex(p))

# g = numbertheory.modular_exp(numbertheory.square_root_mod_prime(random.randrange(1,p), p), 2, p)
g = random.randrange(1, p)
r = random.randrange(1, p)
a = random.randrange(1, p)
b = random.randrange(1, p)
ga = numbertheory.modular_exp(g, a, p)
gb = numbertheory.modular_exp(g, b, p)
# print(g, a, ga, b, gb)
assert a != b

plaintext = "Text may be any length you wish, no padding is required"*5
t = len(plaintext)
# m = b'\xff'*16

t0 = time.time()
print(t0)
for c in range(t/16):
    m = b'This is the PRE!'
    i = util.string_to_number(m)
    s = util.number_to_string(i, l)
    # print(hex(i), i)
    # assert i < p

    ca = numbertheory.modular_exp(g,r,p), numbertheory.modular_exp(g, r*a, p) * i % p
    # print('ca:', ca)
    # ma = (ca[1] * numbertheory.modular_exp(numbertheory.modular_exp(ca[0], a, p), p-2, p) ) % p
    # print('ma:', ma)

    # ba = r*(b-a)
    # print(ba)
    # if ba < 0:
    #     rk = numbertheory.modular_exp(numbertheory.modular_exp(g, -ba, p), p-2, p)
    # else:
    #     rk = numbertheory.modular_exp(g, ba, p)
    # print(rk)
    # cb = ca[0], ca[1] * rk % p
    # print('cb:', cb)

    # mb = (cb[1] * numbertheory.modular_exp(numbertheory.modular_exp(cb[0], b, p), p-2, p) ) % p
    # print('mb:', mb, util.number_to_string(mb, l))
    # print('cb:', util.number_to_string(cb[1], l))

t1 = time.time()
print(t1-t0)


