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

# D = (gECC^skA)^t, t = H(skA, r)
# V = g^skA
# E = g^v, v = H(m, w)
# F = H(g^t, E)) xor (m||w)
# s = v + skA*H(F, E)


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

d = blake2b()
d.update(util.number_to_string(a, l192))
d.update(util.number_to_string(r, l192))
t = util.string_to_number(d.digest())
print('t = H(a, r)', t)

# D = (gECC^skA)^t, t = H(skA, r)
D = skA.privkey.public_key.point * t
print('D', D)
# print('D', gECC*t*a)

gECC_t = D*numbertheory.inverse_mod(a, skA.curve.order)
print('gECC^t', gECC_t)
# print('gECC^t', gECC*t)

# V = g^skA
V = numbertheory.modular_exp(g, a, l192)
# V = g**a
print('V', V)


m = b'This is the PRE!This is the PRE!This is the PRE!' #64-16 bytes
w = b'1234567890abcdef'

t1 = time.time()
for i in range(10):
    for i in range(100000):

        # E = g^v, v = H(m, w)
        d = blake2b()
        d.update(m)
        d.update(w)
        v = util.string_to_number(d.digest())
        # print('v = H(m, w)', v)

        E = numbertheory.modular_exp(g, v, l192)
        # E = skA.curve.generator * r
        # print('E = g^v', E)

        # F = H(g^t, E)) xor (m||w)
        d = blake2b()
        d.update(util.number_to_string(gECC_t.x(), l192))
        d.update(util.number_to_string(E, l192))
        k = util.string_to_number(d.digest())
        j = util.string_to_number(m+w)
        c = k^j
        # print('k', k)
        F = util.number_to_string(c, l512)
        # print('F = H(gECC^t, E)) xor (m||w)', F)

    t2 = time.time()
    print('TIME >>>>>>>>>', t2 - t1)

print('m||w', util.number_to_string(c^k, l512))

# s = v + skA*H(F, E)
d = blake2b()
d.update(F)
d.update(util.number_to_string(E, l192))
h = util.string_to_number(d.digest())
s = v + a * h
print('s = v + sk_A*H(F, E)', s)


print('g^s', numbertheory.modular_exp(g, s, l192))
print('E*g^(a*H(F, E))', (E * numbertheory.modular_exp(g, a*h, l192))%l192)
print('g^s ?= E*pk^H(F, E)', numbertheory.modular_exp(g, s, l192) == (E * numbertheory.modular_exp(g, a*h, l192))%l192)

#rk = (g^b/g^a)^t
b = skB.privkey.secret_multiplier
rk = gECC * ((b-a) * t)
print('rk', rk)

# A generates the key DB replacing D
DB = D + rk
print('DB', DB)
# DB = skB.privkey.public_key.point * t
# print('DB', DB)

# B using the skB and DB to get g^t
# g^t = DB^(1/b)
gECC_t2 = DB * numbertheory.inverse_mod(b, skB.curve.order)
print('gECC^t', gECC_t2)
# print('gECC^t', gECC_t)


# B decode
d = blake2b()
d.update(util.number_to_string(gECC_t2.x(), l192))
d.update(util.number_to_string(E, l192))
k = util.string_to_number(d.digest())
print('k', k)
c = util.string_to_number(F)
print('F', F)
print('m||w', util.number_to_string(c^k, l512))
