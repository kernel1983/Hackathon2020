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

$ D = (g^a)^t, t = H(a, r), r \leftarrow Z_p^* $

$ E_i = g^{v_i}, v_i \leftarrow Z_p^* $

$ F_i = H(g^t, E_i) \oplus (m_i||w_i), $

$ s_i = r_i + a \cdot H(F_i, E_i) $

and validation $g^{s_i} \overset{?}{=} E_i \cdot pk^{H(F_i, E_i)} $

ReKey $D' = (g^b)^t $
'''

l192 = 2**192-1
l160 = 2**160-1
l512 = 2**512-1

skA = PrivateKey.generate()
skB = PrivateKey.generate()

# D = (g^skA)^t, t = H(skA, r)
# pkA
# E = g^v, v = H(m, w)
# F = H(g^t, E)) xor (m||w)
# s = v + skA*H(F, E)


t0 = time.time()

a = skA.privkey.secret_multiplier
print('a', a)

r = random.randrange(1, l192)
print('r', r)

# D = (g^skA)^t, t = H(skA, r)
d = blake2b()
d.update(util.number_to_string(a, l192))
d.update(util.number_to_string(r, l192))
t = util.string_to_number(d.digest())
print('t = H(a, r)', t)

D = skA.privkey.public_key.point * t
print('D = (g^a)^t', D)

# g2 = random.randrange(1, l192)
gt = skA.curve.generator * t
print('g^t', gt)

for i in range(100):
    # E = g^v, v = H(m, w)
    v = random.randrange(1, l192)
    E = skA.curve.generator * v
    # E = numbertheory.modular_exp(g2, r, l192)
    print('E = g^v', E)

    # F = H(g^t, E)) xor (m||w)
    m = b'This is the PRE!This is the PRE!This is the PRE!' #64-16 bytes
    w = b'1234567890abcdef'
    d = blake2b()
    d.update(util.number_to_string(gt.x(), l192))
    d.update(util.number_to_string(E.x(), l192))
    k = util.string_to_number(d.digest())

    j = util.string_to_number(m+w)
    c = j^k
    # print('k', k)
    F = util.number_to_string(c, l512)
    # print('F = H(g^t, E)) xor m', F)

t1 = time.time()
print(t1 - t0)

print('m', util.number_to_string(c^k, l512))


# s = r + a*H(m, E)
d = blake2b()
d.update(m)
d.update(util.number_to_string(E.x(), l192))
h = util.string_to_number(d.digest())
s = r + a * h
print('s = r + a*H(m, E)', s)


# E+pk*H(m, E) = E+g*a*h = g*r+g*a*h = g*(r+a*h)
# g*s = g*(r+a*h)
print('g^s', skA.curve.generator * s)
# print('g^s', numbertheory.modular_exp(g2, s, l192))
print('E*pk^H(m, E)', E + skA.curve.generator*(a*h))
# print('E*g^(a*H(m, E))', (E * numbertheory.modular_exp(g2, a*h, l192))%l192)
print('g^s ?= E*pk^H(m, E)', skA.curve.generator * s == E + skA.curve.generator*(a*h))
# print('g^s ?= E*pk^H(m, E)', numbertheory.modular_exp(g2, s, l192) == (E * numbertheory.modular_exp(g2, a*h, l192))%l192)


# A generates the key DB replacing D
b = skB.privkey.secret_multiplier
# DB = skB.curve.generator * (b + t)
DB = skB.privkey.public_key.point + skB.curve.generator * t
# print('DB', DB)


# B using the skB and DB to get g^t
# g^t = DB^(1/b)
gt = DB + skB.curve.generator * -b
# print('gt', gt)
# print('gt', skB.curve.generator*t)
# print('gt', gt == skB.curve.generator * t)

# B decode
d = blake2b()
# d.update(util.number_to_string((gt+E).x(), l192))
d.update(util.number_to_string(gt.x(), l192))
d.update(util.number_to_string(E.x(), l192))
k = util.string_to_number(d.digest())
print('k', k)
c = util.string_to_number(F)
print('F', F)
print('m', util.number_to_string(c^k, l512))
