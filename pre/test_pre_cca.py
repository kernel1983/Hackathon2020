from __future__ import print_function

import random
import time
from hashlib import blake2b

import numbertheory
import util

from keys import PrivateKey, PublicKey

'''
$ PRE = <D, pk_A, r, E_i, F_i, s_i> $

$a$, $b$ is secret keys and $g^a$, $g^b$ is the public keys of user $A$ and $B$

$m = m_1 || m_2 || m_3 || ...$

$ D = (g^a)^d, d = H(a, r), r \leftarrow Z_p $

$ E_i = g^{e_i}, e_i \leftarrow Z_p $

$ F_i = H(g^d, E_i) \oplus (m_i||w_i), $

$ S = g^s, s = v + a \cdot r $

and validation $S \overset{?}{=} V \cdot pk^r $

ReKey $D' = (g^b)^d $
'''

l192 = 2**192-1
l160 = 2**160-1
l512 = 2**512-1

skA = PrivateKey.generate()
skB = PrivateKey.generate()

# D = (g^skA)^d, d = H(skA, r)
# E = g^e, e = H(m, w)
# F = H(g^d, E)) xor (m||w)
# V = g^v
# S = g^s, s = v + skA^r


t0 = time.time()

a = skA.privkey.secret_multiplier
print('a', a)

r = random.randrange(1, l192)
print('r', r)

# D = (g^skA)^d, t = H(skA, r)
h = blake2b()
h.update(util.number_to_string(a, l192))
h.update(util.number_to_string(r, l192))
d = util.string_to_number(h.digest())
print('d = H(a, r)', d)

D = skA.privkey.public_key.point * d
print('D = (g^a)^d', D)

# g2 = random.randrange(1, l192)
gd = skA.curve.generator * d
print('g^d', gd)

m = b'This is the PRE!This is the PRE!This is the PRE!' #64-16 bytes
w = b'1234567890abcdef'

v = random.randrange(1, l192)
V = skA.curve.generator * v
# V = numbertheory.modular_exp(g2, v, l192)

t1 = time.time()
print('Setup TIME >>>>>>>>>', t1 - t0)
for x in range(10):
    for y in range(1000):

        # E = g^e, e = H(m, w)
        e = random.randrange(1, l192)
        E = skA.curve.generator * e
        # E = numbertheory.modular_exp(g2, r, l192)
        # print('E = g^e', E)

        # F = H(g^d, E)) xor (m||w)
        h = blake2b()
        h.update(util.number_to_string(gd.x(), l192))
        h.update(util.number_to_string(E.x(), l192))
        k = util.string_to_number(h.digest())

        j = util.string_to_number(m+w)
        c = j^k
        # print('k', k)
        F = util.number_to_string(c, l512)
        # print('F = H(g^d, E)) xor m', F)

    t2 = time.time()
    print(t2 - t0)

print('m', util.number_to_string(c^k, l512))


# s = v + a*r
s = v + a * r
print('s = v + a * r', s)

# V+pkA*r = V+g*a*r = g*v+g*a*r = g*(v+a*r)
# g*s = g*(v+a*r)
S = skA.curve.generator * s
print('S', S)
print('V*pkA^r', V + skA.curve.generator*(a*r))
print('S ?= V*pkA^r', S == V + skA.curve.generator*(a*r))


# A generates the key DB replacing D
b = skB.privkey.secret_multiplier
# DB = skB.curve.generator * (b + d)
DB = skB.privkey.public_key.point + skB.curve.generator * d
# print('DB', DB)


# B using the skB and DB to get g^d
# g^d = DB^(1/b)
# gd = DB + skB.curve.generator * -b
gd2 = DB * numbertheory.inverse_mod(b, skB.curve.order)
# print('gd', gd2)
# print('gd', skB.curve.generator*t)
# print('gd', gd2 == skB.curve.generator * d)

# B decode
h = blake2b()
# h.update(util.number_to_string((gt+E).x(), l192))
h.update(util.number_to_string(gd.x(), l192))
h.update(util.number_to_string(E.x(), l192))
k = util.string_to_number(h.digest())
print('k', k)
c = util.string_to_number(F)
print('F', F)
print('m', util.number_to_string(c^k, l512))
