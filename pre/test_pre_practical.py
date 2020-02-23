from __future__ import print_function

import random
import time
from hashlib import blake2b

import numbertheory
import util

from keys import PrivateKey, PublicKey


l192 = 2**192-1
l160 = 2**160-1
l512 = 2**512-1

skA = PrivateKey.generate()
skB = PrivateKey.generate()

# D = (gECC^skA)^d, d = H(skA, r)
# E = g^e, e = H(m, w)
# F = H(g^d, E)) xor (m||w)
# V = gECC^v, v <- Zp
# S = gECC^s, s = v + skA * r


t0 = time.time()

gECC = skA.curve.generator
print('gECC', gECC)

p = numbertheory.next_prime(2**191)
print('p', p)

g = random.randrange(1, p)
print('g', g)

a = skA.privkey.secret_multiplier
print('skA', a)
print('pkA', skA.privkey.public_key.point)

r = random.randrange(1, l192)
print('r', r)

h = blake2b()
h.update(util.number_to_string(a, l192))
h.update(util.number_to_string(r, l192))
d = util.string_to_number(h.digest())
print('d = H(a, r)', d)

# D = (gECC^skA)^d, d = H(skA, r)
D = skA.privkey.public_key.point * d
print('D', D)
# print('D', gECC*d*a)

gECC_d = D*numbertheory.inverse_mod(a, skA.curve.order)
print('gECC^d', gECC_d)
# print('gECC^d', gECC*d)

m = b'This is the PRE!This is the PRE!This is the PRE!' #64-16 bytes
w = b'1234567890abcdef'

# V = g^v
v = random.randrange(1, l192)
V = skA.curve.generator * v
# V = numbertheory.modular_exp(g, v, l192)
# print('V', V)

t1 = time.time()
print('Setup TIME >>>>>>>>>', t1 - t0)
for x in range(10):
    for y in range(1000):

        # E = g^e, e = H(m, w)
        h = blake2b()
        h.update(m)
        h.update(w)
        e = util.string_to_number(h.digest())
        # print('e = H(m, w)', e)

        E = numbertheory.modular_exp(g, e, l192)
        # E = skA.curve.generator * r
        # print('E = g^e', E)

        # F = H(g^d, E)) xor (m||w)
        h = blake2b()
        h.update(util.number_to_string(gECC_d.x(), l192))
        h.update(util.number_to_string(E, l192))
        k = util.string_to_number(h.digest())
        j = util.string_to_number(m+w)
        c = k^j
        # print('k', k)
        F = util.number_to_string(c, l512)
        # print('F = H(gECC^d, E)) xor (m||w)', F)

    t2 = time.time()
    print('TIME >>>>>>>>>', t2 - t0)

print('m||w', util.number_to_string(c^k, l512))

# s = v + a * r
s = v + a * r
print('s = v + a * r', s)


S = skA.curve.generator * s
print('S', S)
print('V*g^(skA*r)', V + skA.curve.generator*(a*r))
print('g^s ?= V*pkA^r', S == V + skA.curve.generator*(a*r))

#rk = (g^b/g^a)^d
b = skB.privkey.secret_multiplier
rk = gECC * ((b-a) * d)
print('rk', rk)

# A generates the key DB replacing D
DB = D + rk
print('DB', DB)
# DB = skB.privkey.public_key.point * d
# print('DB', DB)

# B using the skB and DB to get g^d
# g^d = DB^(1/b)
gECC_d2 = DB * numbertheory.inverse_mod(b, skB.curve.order)
print('gECC^d', gECC_d2)
# print('gECC^d', gECC_d)


# B decode
h = blake2b()
h.update(util.number_to_string(gECC_d2.x(), l192))
h.update(util.number_to_string(E, l192))
k = util.string_to_number(h.digest())
print('k', k)
c = util.string_to_number(F)
print('F', F)
print('m||w', util.number_to_string(c^k, l512))
