from __future__ import print_function

import random
from hashlib import blake2b

# import numbertheory
import util

from keys import PrivateKey, PublicKey


skA = PrivateKey.generate()
skB = PrivateKey.generate()

# D = (g^a)^t, t = H(a, V)
# V = g^v
# E = g^r
# F = H(g^t*E)) xor m
# s = r + a*H(m, E)

l192 = 2**192-1
l160 = 2**160-1
l512 = 2**512-1

# V = g^v
v = random.randrange(1, l192)
V = skA.privkey.public_key.point * v
print('V = g^v', V)


# D = (g^a)^t, t = H(a, V)
a = skA.privkey.secret_multiplier
print('a', a)
# print('a in bytes', util.number_to_string(a, l192))
d = blake2b()
d.update(util.number_to_string(a, l192))
d.update(util.number_to_string(V.x(), l192))
t = util.string_to_number(d.digest())
print('t = H(a,V)', t)
D = skA.privkey.public_key.point * t
print('D = (g^a)^t', D)


# E = g^r
r = random.randrange(1, l192)
E = skA.curve.generator * r
print('E = g^r', E)


# F = H(g^t*E)) xor m
m = b'This is the PRE!This is the PRE!This is the PRE!This is the PRE!' #64bytes
i = util.string_to_number(m)
gt = skA.curve.generator * t
d = blake2b()
d.update(util.number_to_string((gt + E).x(), l192))
k = util.string_to_number(d.digest())
c = i^k
print('k', k)
F = util.number_to_string(c, l512)
print('F = H(g^t*E)) xor m', F)
print('m', util.number_to_string(c^k, l512))


# s = r + a*H(m, E)
d = blake2b()
d.update(m)
d.update(util.number_to_string(E.x(), l192))
h = util.string_to_number(d.digest())
s = r + a * h
print('s = r + a*H(m, E)', s)


# E+pk*H(m,E) = E+g*a*h = g*r+g*a*h = g*(r+a*h)
# g*s = g*(r+a*h)
print('g^s', skA.curve.generator * s)
print('E*pk^H(m,E)', E + skA.curve.generator*(a*h))
print('g^s ?= E*pk^H(m,E)', skA.curve.generator * s == E + skA.curve.generator*(a*h))


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
d.update(util.number_to_string((gt+E).x(), l192))
k = util.string_to_number(d.digest())
print('k', k)
c = util.string_to_number(F)
print('F', F)
print('m', util.number_to_string(c^k, l512))
